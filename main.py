from flask import Flask, render_template, redirect, url_for, flash, abort, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from functools import wraps
from dotenv import load_dotenv
import os
load_dotenv()  # take environment variables from .env.


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///blog.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

MY_EMAIL = os.environ["my_email"]
PASSWORD = os.environ["password"]

# Flask Login
login_manager = LoginManager()
login_manager.init_app(app)


# Gravatar
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,

                    base_url=None)


def send_email(name, email, phone, message):
    email_msg = f"Subject: Form Contact. \n\nName: {name}" \
                f"\nEmail: {email}"\
                f"\nPhone: {phone}"\
                f"\n\nMessage: {message}"
    with smtplib.SMTP("smtp.gmail.com") as connection:
        connection.starttls()
        connection.login(user=MY_EMAIL, password=PASSWORD)
        connection.sendmail(from_addr=MY_EMAIL, to_addrs=MY_EMAIL, msg=email_msg )


@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(user_id)
    return user


# Decorator Function
""" This decorator makes sure that only admin can make changes to the website """


def admin_only(function):
    @wraps(function)
    def wrapper_function(**kwargs):
        if current_user.get_id() == "1":
            return function(**kwargs)
        abort(403)
    return wrapper_function


##CONFIGURE TABLES


class User(UserMixin, db.Model):
    # __tablename__ gives a name to your spreadsheet. Otherwise, chooses a default name.
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    name = db.Column(db.String(250), nullable=False)

    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    # See how author property is removed now in BlogPost Class and replaced by a relationship from this class
    # i.e., The "author" is now an "object" of User class.
    posts = db.relationship("BlogPost", backref="author")

    #*******Add parent relationship*******#
    #"comment_author" creates a new column in the Comment class.
    comments = db.relationship("Comment", backref="comment_author")


# Below code only once.
# db.create_all()


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(250), unique=True, nullable=False)

    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    #******* Add parent relationship *******#
    #"parent_post" creates a new column in the Comment class.
    comments = db.relationship("Comment", backref="parent_post")


# Below code only once.
# db.create_all()


# Comments Table
class Comment(db.Model):
    # __tablename__ gives a name to your spreadsheet. Otherwise, chooses a default name.
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

    # ******* Add child relationship *******#
    # "users.id" The users refers to the tablename of the Users class.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    # ******* Add child relationship *******#
    # "blog_posts.id" The blog_posts refers to the tablename of the BlogPost class.
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))


# Below code only once.
# db.create_all()


@app.route('/')
def get_all_posts():
    # Get all the posts from database
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts,
                           logged_in=current_user.is_authenticated, id=current_user.get_id())


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():

        # Check if the user is already in the database
        if User.query.filter_by(email=form.email.data).first():
            flash("You are already registered. Try logging in instead.")
            return redirect(url_for("login"))
        new_user = User()
        new_user.email = form.email.data
        new_user.password = generate_password_hash(password=form.password.data,
                                                   method='pbkdf2:sha256',
                                                   salt_length=8)
        new_user.name = form.name.data

        db.session.add(new_user)
        db.session.commit()

        # When users successfully register they are taken back to the home page
        # And are logged in with Flask-Login.
        login_user(new_user)
        return redirect(url_for("get_all_posts"))

    return render_template("register.html", form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():

        # check if user is registered in the database OR if the email entered is valid.
        # If not redirect back to log in with a flash message
        user = User.query.filter_by(email=form.email.data).first()
        if not user:
            flash("The email is not valid. Please try again.")
            return redirect(url_for("login"))

        # Check if the password entered is correct?
        # If not redirect back to log in with a flash message
        if not check_password_hash(pwhash=user.password, password=form.password.data):
            flash("The password is incorrect. Please try again.")
            return redirect(url_for("login"))

        # If above conditions were not met, meaning both email & passwords were correct
        # Hence in which case, we will make the user login to the system
        login_user(user)
        return redirect(url_for("get_all_posts"))

    return render_template("login.html", form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    form = CommentForm()
    requested_post = BlogPost.query.get(post_id)
    comments = Comment.query.all()
    if form.validate_on_submit():
        if current_user.is_authenticated:
            new_comment = Comment(
                text=form.body.data,
                comment_author=current_user,
                parent_post=requested_post
            )
            db.session.add(new_comment)
            db.session.commit()
            return redirect(url_for("show_post", post_id=post_id))
        else:
            flash("You're not logged in. Please Login first")
            return redirect(url_for("login"))

    return render_template("post.html", post=requested_post,
                           id=current_user.get_id(), form=form,
                           comments=comments, logged_in=current_user.is_authenticated,
                           gravatar=gravatar)


@app.route("/about")
def about():
    return render_template("about.html", logged_in=current_user.is_authenticated)


@app.route("/contact")
def contact():
    if request.method == "POST":
        data = request.form
        send_email(data["username"], data["email"], data["phone"], data["message"])
        return render_template("contact.html")
    return render_template("contact.html", logged_in=current_user.is_authenticated)


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
            date=date.today().strftime("%B %d, %Y"),
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, logged_in=current_user.is_authenticated)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
