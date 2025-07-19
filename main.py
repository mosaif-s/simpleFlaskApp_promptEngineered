import smtplib
from datetime import date
from typing import List

from flask import Flask, abort, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user, user_logged_in
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
# Import your forms from the forms.py
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from dotenv import load_dotenv
import os
'''
python -m pip install -r requirements.txt
'''

app = Flask(__name__)


load_dotenv()  # Load environment variables from .env

# Load into variables
OWN_EMAIL = os.getenv("OWN_EMAIL")
OWN_PASSWORD = os.getenv("OWN_PASSWORD")
SECRET_KEY = os.getenv("SECRET_KEY")
app.config['SECRET_KEY'] = SECRET_KEY
ckeditor = CKEditor(app)
Bootstrap5(app)

login_manager=LoginManager()
login_manager.init_app(app)



@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)
# CREATE DATABASE
class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)


# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)
    author_id: Mapped[int]=mapped_column(Integer, db.ForeignKey("users.id"))
    author=relationship("User", back_populates="posts")

    #Relationship with Comment
    comments_on_posts=relationship("Comment", back_populates="blog_")

class User(db.Model,UserMixin ):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    password: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    posts: Mapped[List["BlogPost"]]=relationship("BlogPost",back_populates="author")
    comments:Mapped[List["Comment"]]=relationship("Comment",back_populates="comment_author")


class Comment(db.Model):
    __tablename__="comments"
    id:Mapped[int]=mapped_column(Integer, primary_key=True)
    text:Mapped[str]=mapped_column(Text, nullable=False)
    comment_author=relationship("User", back_populates="comments")
    comment_author_id: Mapped[int]=mapped_column(Integer, db.ForeignKey("users.id"))

    #Relation with Blog
    blog_=relationship("BlogPost",back_populates="comments_on_posts")
    blog_id: Mapped[str]=mapped_column(Integer, db.ForeignKey("blog_posts.id"))
    #change to int

with app.app_context():
    db.create_all()
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)
def admin_only(function):
    @wraps(function)
    def decorated_f(*args,**kwargs):
        if not current_user.is_authenticated or current_user.id != 1:
            return abort(403)
        else:
            return function(*args, **kwargs)
    return decorated_f

@app.route('/register', methods=["GET","POST"])
def register():
    form=RegisterForm()
    if form.validate_on_submit():
        name = form.name.data
        password = form.password.data
        email = form.email.data
        hash=generate_password_hash(password, method="pbkdf2:sha256", salt_length=8)
        result = db.session.execute(db.select(User).where(User.email == email))
        user = result.scalar()
        if user:
            flash("Email already exists! Login Instead.")
            return redirect(url_for("login"))
        new_user = User(
            name=name,
            password=hash,
            email=email,

        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)

        return redirect(url_for("get_all_posts"))

    return render_template("register.html", form=form, current_user=current_user)


@app.route('/login', methods=['GET','POST'])
def login():
    form=LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        result=db.session.execute(db.select(User).where(User.email == email))
        user = result.scalar()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("get_all_posts"))
        elif not user:
            flash("This email does not exit. Register your email.")
        elif not check_password_hash(user.password, password):
            flash("Wrong Password! Try Again.")

    return render_template("login.html", form=form, current_user=current_user)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    if current_user.is_authenticated:
        return render_template("index.html", all_posts=posts, user_id=current_user.id)
    else:
        return render_template("index.html", all_posts=posts, user_id=0)

@app.route("/post/<int:post_id>", methods=["POST", "GET"])
def show_post(post_id):
    form=CommentForm()
    current_blog=db.get_or_404(BlogPost, post_id)
    #if request.method=="POST":#
    if form.validate_on_submit():
        #if not user_logged_in: Why is this wrong?
        # and you have to make a comment for THE RELATIOSHOP PARTS ALSO, N FOREIGN KEY NEEDED TO PUT EHRE
        if not current_user.is_authenticated:
            return redirect(url_for("login"))
        else:
            text=form.comment.data
            new_comment=Comment(text=text, comment_author=current_user, blog_=current_blog) # how does this know to connec to the blog in the tables
            db.session.add(new_comment)
            db.session.commit()
            return redirect(url_for("show_post", post_id=post_id))
    requested_post = db.get_or_404(BlogPost, post_id)
    #result = db.session.execute(db.select(Comment))
    #comments = result.scalars().all()
    comments = Comment.query.filter_by(blog_id=post_id).all()

    if current_user.is_authenticated:
        return render_template("post.html", post=requested_post, comments=comments, form=form, user_id=current_user.id)
    else:
        return render_template("post.html", post=requested_post, comments=comments, form=form, user_id=0)


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=["POST", "GET"])
def contact():
    if request.method=="GET":
        return render_template("contact.html", msg_sent=False)
    elif request.method=="POST":
        data = request.form
        send_mail(data["name"], data["email"],data["phone"], data["message"])
        return render_template("contact.html", msg_sent=True)

def send_mail(name,email,phone, message):
    email_message = f"Subject:New Message\n\nName: {name}\nEmail: {email}\nPhone: {phone}\nMessage:{message}"
    with smtplib.SMTP("smtp.gmail.com") as connection:
        connection.starttls()
        connection.login(OWN_EMAIL,OWN_PASSWORD)
        connection.sendmail(OWN_EMAIL,OWN_EMAIL, email_message)


if __name__ == "__main__":
    app.run(debug=True, port=5002)
