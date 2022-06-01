from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, EmailField
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)
app.secret_key="blog" # It's must to create for use the Flask messages

# Database connections
app.config["MYSQL_HOST"]="localhost"
app.config["MYSQL_USER"]="root"
app.config["MYSQL_PASSWORD"]=""
app.config["MYSQL_DB"]="blog"
app.config["MYSQL_CURSORCLASS"]="DictCursor" # Cursor that allows us to extract data from the database in the form of a dictionary.
mysql=MySQL(app)

# User register control decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "login" in session:
            return f(*args, **kwargs)
        else:
            flash("You must Log In!","danger")
            return redirect(url_for("login"))
    return decorated_function

# Form of register
class RegisterForm(Form):
    name = StringField('Full Name', validators=[validators.DataRequired()])
    email = EmailField('E-mail', validators=[validators.DataRequired(),validators.Length(min=6),validators.Email('Please enter a valid e-mail!')])
    username = StringField('Username', validators=[validators.DataRequired(),validators.Length(min=3)])
    password = PasswordField('Password',validators=[validators.DataRequired('Please enter a valid password!'), validators.EqualTo(fieldname='confirm', message='Passwords did not matches!')])
    confirm = PasswordField('Password Valid')

# Form of login
class LoginForm(Form):
    username = StringField('Username')
    password = PasswordField('Password')

# Form of create article
class ArticleForm(Form):
    title = StringField('Title', validators=[validators.DataRequired(),validators.Length(min=5, max=75)])
    content = TextAreaField('Content', validators=[validators.DataRequired(),validators.Length(min=10)])

# Root page
@app.route("/")
def index():
    return render_template("index.html")

# About page
@app.route("/about")
def about():
    return render_template("about.html")

# Sign In
@app.route("/signup", methods=['GET', 'POST'])
def signup():
    # form instance
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate(): # formda sorun var mı ona bakar.

        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.hash(form.password.data) # alınan parolayı şifreleyerek database'e kaydeder. encrcypt veya hash kullanılabilir.

        cursor = mysql.connection.cursor() # sql sorgularını çalıştırmak için cursor oluşturulur.
        query = "INSERT INTO users2(name,email,username,password) VALUES(%s,%s,%s,%s)"
        cursor.execute(query,(name,email,username,password)) # sorguyu çalıştırır.
        mysql.connection.commit() # database üzerinde işlem yapılacağı durumlarda kullanılır(ekleme, silme, güncelleme).
        cursor.close()

        flash('Registration successful!', category="success")
        return redirect(url_for('login')) # post request ile butona tıklandığı zaman gidilecek url'i belirledik
    else:
        return render_template("signup.html",form=form) #form nesnesini formumuzu görüntülemek için vermeliyiz.

# Log In
@app.route("/login",methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        username=form.username.data
        login_password = form.password.data # giriş ekranına girilen password
        # giriş bilgilerini database'den kontrol etmemeiz gerekiyor.
        cursor = mysql.connection.cursor()
        query = """SELECT username,password
                   FROM users2
                   WHERE username=%s"""
        result = cursor.execute(query,(username,)) # database'den kullanıcı var ise 1 döner.
        if result > 0:
            data = cursor.fetchone() # giriş başarılı, o kullanıcının tüm bilgilerini bu fonksiyon ile alıyoruz.
            real_password = data["password"] # database'de bulunan gerçek parolayı çektik
            if sha256_crypt.verify(login_password,hash=real_password):
                flash(f"Welcome {data['username']}!",category="success")

                session['login']=True
                session['username']=username
                return redirect(url_for("index"))
            else:
                flash("Password or username is incorrect!",category="danger")
                return redirect(url_for("login"))

        else:
            flash("Password or username is incorrect!",category="danger")
            return redirect(url_for('login'))
        
    return render_template("login.html",form=form)

# Log Out
@app.route("/logout")
def logout():
    session.clear()
    return render_template("index.html")

# Control panel page and decorator control
@app.route("/dashboard")
@login_required 
def dashboard():
    # sadece giriş yapan kullanıcıların makalesinin gözükmesi
    cursor = mysql.connection.cursor()
    query="SELECT * FROM articles WHERE author=%s"
    result=cursor.execute(query,(session['username'],))
    if result >0:
        articles=cursor.fetchall()
        print(articles)
        cursor.close()
        return render_template("dashboard.html",articles=articles)
    else:
        cursor.close()
        return render_template("dashboard.html")

# View article
@app.route("/go_article/<string:id>")
def edit_article(id):
    cursor = mysql.connection.cursor()
    query = "SELECT * FROM articles WHERE id=%s"
    result=cursor.execute(query,(id,))
    if result >0:
        article = cursor.fetchone()
        cursor.close()
        return render_template("go_article.html",article=article)
    else:
        cursor.close()
        return render_template("articles.html")

# Update article
@app.route("/update/<string:id>", methods=['GET','POST'])
@login_required
def update(id):
    if request.method == 'GET':
        cursor = mysql.connection.cursor()
        query = "SELECT * FROM articles WHERE id=%s and author=%s"
        result=cursor.execute(query,(id,session['username']))
        if result > 0:
            article = cursor.fetchone()
            form = ArticleForm()
            form.title.data = article['title']
            form.content.data = article['content']
            return render_template("update.html", form = form)
        else:
            flash("No such article was found!","warning")
            return redirect(url_for("index"))
    else:
        form = ArticleForm(request.form)
        newTitle = form.title.data
        newContent = form.content.data

        cursor = mysql.connection.cursor()
        query = "UPDATE articles SET  title = %s, content = %s WHERE id = %s"
        result=cursor.execute(query,(newTitle,newContent,id))
        mysql.connection.commit()
        cursor.close()

        flash("Update is successful!","success")
        return redirect(url_for("dashboard"))
        
# Delete article
@app.route("/delete_article/<string:id>")
@login_required
def delete_article(id):
    cursor = mysql.connection.cursor()
    query = "SELECT * FROM articles WHERE id=%s and author=%s"
    result=cursor.execute(query,(id,session['username']))
    if result >0:
        query2="DELETE FROM articles WHERE id=%s"
        cursor.execute(query2,(id,))
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for("dashboard"))
    else:
        cursor.close()
        flash("No such article was found!","warning")
        return redirect(url_for("index"))
    
# Add article
@app.route("/add_article", methods=['GET','POST'])
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title=form.title.data
        content=form.content.data
        cursor = mysql.connection.cursor()
        query = "INSERT INTO articles(title,author,content) VALUES(%s,%s,%s)"
        cursor.execute(query,(title,session['username'],content))
        mysql.connection.commit()
        flash("Article successfully added!","success")
        return redirect(url_for("dashboard"))
    else:
        return render_template("add_article.html",form=form)

# Get article from database
@app.route("/article")
@login_required # sadece giriş yapan kullanıcıların makale sayfasına erişmesi kontrolü
def articles():
    cursor = mysql.connection.cursor()
    query = "SELECT * FROM articles"
    result=cursor.execute(query)
    if result > 0:
        articles = cursor.fetchall()
        cursor.close()
        return render_template("articles.html",articles=articles)
    else:
        cursor.close()
        return render_template("articles.html")

# Search article
@app.route("/search", methods=['GET','POST'])
@login_required
def search():
    if request.method == 'GET':
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword") # Get data from post request

        cursor = mysql.connection.cursor()
        query = "SELECT * FROM articles WHERE title LIKE '%" + keyword + "%' OR content LIKE '%" + keyword + "%'"
        result = cursor.execute(query)
        if result > 0:
            articles = cursor.fetchall()
            return render_template("articles.html",articles=articles)
        else:
            flash("No article found matching the search term","info")
            return redirect(url_for("articles"))
    
# Execute condition
if __name__ == "__main__":
    app.run(debug=True)
