from flask import Flask,render_template,flash, redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField,validators 
from passlib.hash import sha256_crypt
from MySQLdb.cursors import DictCursor
from functools import wraps

import COVID19Py



#kullanıcı giris kontrolü decorator

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapın..","danger")
            return redirect(url_for("login"))
    return decorated_function

#son

#kullanıcı kayıt formu
class RegisterForm(Form):
    name=StringField("İsim Soyisim",validators=[validators.length(min=4,max=25)])
    username=StringField("Kullanıcı Adı",validators=[validators.length(min=5,max=35)])
    email=StringField("E-mail Adresi",validators=[validators.Email(message="Lütfen geçerli bir e-mail adresi giriniz..")])
    password=PasswordField("Parola",validators=[
            validators.DataRequired(message="lütfen bir parola belirleyiniz..."),
            validators.EqualTo(fieldname="confirmPass",message="parolanız uyuşmuyor..."),
            ])
    
    confirmPass=PasswordField("Parola Doğrula")

#son

#Kullanıcı girişi

class LoginForm(Form):
    username=StringField("kullanıcı adı:")
    password=PasswordField("Parola")

# son

#veri tabanı bağlantısı
app=Flask(__name__)
app.secret_key="ybblog"

app.config["MYSQL_HOST"]="localhost"
app.config["MYSQL_USER"]="root"
app.config["MYSQL_PASSWORD"]=""
app.config["MYSQL_DB"]="ybblog"
app.config["MYSQL_CURSORCLASS"]="DictCursor"

mysql=MySQL(app)
#son

@app.route("/")
def index():
    covid19 = COVID19Py.COVID19()
    covid19 = COVID19Py.COVID19(data_source="csbs")
    latest = covid19.getLatest()
    locations = covid19.getLocations()
    data = covid19.getAll(timelines=True)
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/articles/<string:id>")
def detail(id):
    return "Articles Id:"+id

#makale güncelleme
@app.route("/edit/<string:id>",methods=["GET","POST"])
@login_required #kullanıcı girişi olmadan çalışmaması için
def update(id):
    if request.method == "GET":
        cursor=mysql.connection.cursor()

        sorgu="select * from articles where id = %s and author = %s"

        result = cursor.execute(sorgu,(id,session["username"]))

        if result == 0:
            flash("Böyle bir makale yok yada yetkiniz yok","danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()

            form.title.data = article["title"]
            form.content.data = article["content"]

            return render_template("update.html",form=form)

    else:
        #post requests
        form = ArticleForm(request.form)

        newTitle= form.title.data
        newContent= form.content.data

        sorgu2="update articles set title=%s,content=%s where id=%s"

        cursor=mysql.connection.cursor()

        cursor.execute(sorgu2,((newTitle,newContent,id)))

        mysql.connection.commit()

        flash("Makale güncellendi","success")
        
        return redirect(url_for("dashboard"))

#son



#makale silme
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor=mysql.connection.cursor()
    
    sorgu="select * from articles where author = %s and id = %s"

    result = cursor.execute(sorgu,(session["username"],id))

    if result>0:
        sorgu2 = "delete from articles where id = %s"

        cursor.execute(sorgu2,(id,))

        mysql.connection.commit()

        return redirect(url_for("dashboard"))


    else: 
        flash("Böyle bir makale yok ya da sizin bu işleme yetkiniz yok.","danger")
        return redirect(url_for("index"))
#son

#makale sayfası

@app.route("/articles")
def articles():
    cursor=mysql.connection.cursor()

    sorgu="select * from articles"

    result = cursor.execute(sorgu)

    if result>0:

        articles=cursor.fetchall()

        return render_template("articles.html",articles=articles)
    
    else:
        return render_template("articles.html")

    

 
@app.route("/dashboard")
@login_required
def dashboard():
    cursor=mysql.connection.cursor()

    sorgu="select * from articles where author= %s"

    result=cursor.execute(sorgu,(session["username"],))

    if result >0:
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles=articles)

    else:
        return render_template("dashboard.html")

    return render_template("dashboard.html")


#kayıt olma

@app.route("/register",methods=["GET","POST"])
def register():
    form=RegisterForm(request.form)

    if request.method=="POST" and form.validate():

        name=form.name.data
        username=form.username.data
        email=form.email.data
        password=sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()

        sorgu="Insert into users(name,email,username,password) VALUES(%s,%s,%s,%s)"
       
        cursor.execute(sorgu,(name,email,username,password))
      
        mysql.connection.commit()

        cursor.close()
      
        flash("İşleminiz başarılı şekilde gerçekleştirildi...","success")

        return redirect(url_for("index"))
    else:
        return render_template("register.html",form=form)

#login

@app.route("/login",methods=["GET","POST"])
def login():
    form=LoginForm(request.form)
    if request.method=="POST" and form.validate():
        username=form.username.data
        password_entered=form.password.data

        cursor=mysql.connection.cursor()

        sorgu="Select * From users where username = %s" 
       
        result = cursor.execute(sorgu,(username,))
    
        if result > 0:
            data=cursor.fetchone()
            real_password=data["password"]
            if sha256_crypt.verify(password_entered,real_password):
                flash("Giriş Başarılı","success")

                session["logged_in"]=True
                session["username"]=username


                return redirect(url_for("index"))
            else:
                flash("Hatalı Parola","danger")
                return redirect(url_for("login"))
       
        else:
            flash("Böyle bir kullanıcı bulunmuyor..","danger")
            return redirect(url_for("login"))
       
    return render_template("login.html", form=form)

#detay sayfası
@app.route("/article/<string:id>")
def article(id):

    cursor=mysql.connection.cursor()
    
    sorgu="Select * from articles where id = %s"
    
    result = cursor.execute(sorgu,(id,))

    if result > 0:
        article = cursor.fetchone()

        return render_template("article.html",article=article)
    else:
        return render_template("article.html")






#son

#logout

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

#son

#makale ekleme

@app.route("/addarticle",methods=["GET","POST"])
def addarticle():
    form=ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title=form.title.data
        content=form.content.data

        cursor=mysql.connection.cursor()

        sorgu="Insert into articles(title,author,content) VALUES(%s,%s,%s)"

        cursor.execute(sorgu,(title,session["username"],content))

        mysql.connection.commit()

        cursor.close() 

        flash("Makale başarıyla eklendi..","success")

        return redirect(url_for("dashboard"))
    
    return render_template("addarticle.html",form=form)

#makale form

class ArticleForm(Form):
    title=StringField("Makale Başlığı",validators=[validators.length(min=5,max=100)])
    content=TextAreaField("Makale İçeriği",validators=[validators.length(min=10)])


#arama url

@app.route("/search",methods=["GET","POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword") #search e yazılan degerı alır

        cursor=mysql.connection.cursor()

        sorgu="select * from articles where title like '%" + keyword + "%'"

        result = cursor.execute(sorgu)

        if result == 0:
            flash("Aranan kelimeye uygun makale bulunamadı","warning")
            return redirect(url_for("articles"))
        else:
            articles=cursor.fetchall()
            return render_template("articles.html",articles=articles)


if __name__ == "__main__":
    app.run(debug=True)
