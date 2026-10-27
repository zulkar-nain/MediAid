from datetime import datetime
import re
from urllib.parse import urlsplit

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
import pymysql
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from sqlalchemy import or_
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.config['SECRET_KEY']='dsfcsdvsdv'

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://mediaidctrl:abcd1234@localhost:3306/mediaid'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(10000))
    date = db.Column(db.DateTime(timezone=True), default=func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self) -> str:
        return f'{self.id} - {self.data}'


class User(UserMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    username = db.Column(db.String(100))
    password = db.Column(db.String(255))
    notes = db.relationship('Note')


    def __repr__(self) -> str:
        return f'{self.id} - {self.email} - {self.username}'

class hospital(db.Model):
    
    id = db.Column(db.Integer, primary_key=True)
    hos_name = db.Column(db.String(100))
    hos_loc = db.Column(db.String(100))
    hos_phone = db.Column(db.String(100))
    hos_email = db.Column(db.String(100))
    hos_website = db.Column(db.String(100))
    hos_cap = db.Column(db.Integer)
    hos_subs = db.Column(db.String(100))
    hos_docs = db.Column(db.String(100))
    hos_rev = db.Column(db.String(100))

    def __repr__(self) -> str:
        return f'{self.id} - {self.hos_name} - {self.hos_loc} - {self.hos_phone} - {self.hos_email} - {self.hos_website} - {self.hos_cap} - {self.hos_subs} - {self.hos_docs} - {self.hos_rev}'

class docs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doc_name = db.Column(db.String(100))
    doc_loc = db.Column(db.String(100))
    doc_phone = db.Column(db.String(100))
    doc_email = db.Column(db.String(100))
    doc_fee = db.Column(db.Integer)
    doc_hos = db.Column(db.String(100))
    doc_subs = db.Column(db.String(100))
    doc_rev = db.Column(db.String(100))

    def __repr__(self) -> str:
        return f'{self.id} - {self.doc_name} - {self.doc_loc} - {self.doc_phone} - {self.doc_email} - {self.doc_fee} - {self.doc_hos} - {self.doc_subs} - {self.doc_rev}'


class mediaid(db.Model):
    __tablename__ = 'mediaid_disease'
    id = db.Column(db.Integer, primary_key=True)
    dis_name = db.Column(db.String(100),nullable=False)
    sub_name = db.Column(db.String(100), nullable=False)

    def __repr__(self) -> str:
        return f'{self.id} - {self.dis_name} - {self.sub_name}'


class ContactMessage(db.Model):
    __tablename__ = 'contact_message'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now(), nullable=False)


def initialize_database() -> None:
    with app.app_context():
        db.create_all()

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)





@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}



@login_manager.user_loader
def load_user(user):
    return User.query.get(int(user))

@app.route("/", methods=['GET', 'POST'])

def index():
    return render_template("landing.html", user=current_user)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/faq")
def faq():
    return render_template("faq.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/contact", methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        email = (request.form.get('email') or '').strip()
        subject = (request.form.get('subject') or '').strip()
        message = (request.form.get('message') or '').strip()

        if (
            not name
            or len(name) > 100
            or not is_valid_email(email)
            or len(email) > 255
            or not subject
            or len(subject) > 150
            or not message
            or len(message) > 5000
        ):
            flash('Please complete each field with a valid email address and keep within the character limits.', category='error')
            return render_template("contact.html"), 400

        db.session.add(ContactMessage(name=name, email=email, subject=subject, message=message))
        db.session.commit()
        flash('Thanks for contacting MediAid. Your message has been received.', category='success')
        return redirect(url_for('contact'))

    return render_template("contact.html")


def is_valid_email(email):
    return bool(re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email))


def search_directory(model, search, search_fields, sort_field):
    query = model.query
    if search:
        pattern = f'%{search}%'
        query = query.filter(or_(*(getattr(model, field).ilike(pattern) for field in search_fields)))
    return query.order_by(getattr(model, sort_field)).all()


@app.route("/medisugg", methods=['GET', 'POST'])
def medisugg():
    return render_template("medisugg.html", user=current_user)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = (request.form.get('useremail') or '').strip()
        password = request.form.get('userpassword') or ''
        user = User.query.filter_by(email=email).first() if len(email) <= 100 else None
        if not user or not check_password_hash(user.password, password):
            flash('The email or password was not recognized. Please try again.', category='error')
            return render_template("auth.html", registering=False), 401

        login_user(user, remember=True)
        flash('Signed in successfully.', category='success')
        destination = request.args.get('next', '')
        if (
            not destination.startswith('/')
            or destination.startswith('//')
            or '\\' in destination
            or urlsplit(destination).scheme
            or urlsplit(destination).netloc
        ):
            destination = url_for('index')
        return redirect(destination)

    return render_template("auth.html", registering=False)

@app.route("/logout", methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route("/profiles", methods=['GET', 'POST'])
@login_required
def profiles():
    return render_template("profile.html", user=current_user)

@app.route("/hospital-area", methods=['GET', 'POST'])
@login_required
def hospital_area():
    search = (request.args.get('q') or '').strip()[:100]
    return render_template(
        "directory.html",
        title="Hospitals by area",
        description="Search hospital listings by area or hospital name.",
        search_label="Search by area or hospital name",
        search=search,
        records=search_directory(hospital, search, ('hos_loc', 'hos_name'), 'hos_name'),
        kind="hospital",
    )

@app.route("/hospital-subject", methods=['GET', 'POST'])
@login_required
def hospital_subject():
    search = (request.args.get('q') or '').strip()[:100]
    return render_template(
        "directory.html",
        title="Hospitals by specialty",
        description="Search hospital listings by specialty or hospital name.",
        search_label="Search by specialty or hospital name",
        search=search,
        records=search_directory(hospital, search, ('hos_subs', 'hos_name'), 'hos_name'),
        kind="hospital",
    )

@app.route("/doctor-area", methods=['GET', 'POST'])
@login_required
def doctor_area():
    search = (request.args.get('q') or '').strip()[:100]
    return render_template(
        "directory.html",
        title="Doctors by area",
        description="Search doctor listings by area or doctor name.",
        search_label="Search by area or doctor name",
        search=search,
        records=search_directory(docs, search, ('doc_loc', 'doc_name'), 'doc_name'),
        kind="doctor",
    )

@app.route("/doctor-subject", methods=['GET', 'POST'])
@login_required
def doctor_subject():
    search = (request.args.get('q') or '').strip()[:100]
    return render_template(
        "directory.html",
        title="Doctors by specialty",
        description="Search doctor listings by specialty or doctor name.",
        search_label="Search by specialty or doctor name",
        search=search,
        records=search_directory(docs, search, ('doc_subs', 'doc_name'), 'doc_name'),
        kind="doctor",
    )

@app.route("/emergency-info")
def emer_info():
    return render_template("emergency.html")
    

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = (request.form.get('useremail') or '').strip()
        username = (request.form.get('username') or '').strip()
        password = request.form.get('userpassword') or ''
        if (
            len(email) > 100
            or not is_valid_email(email)
            or not username
            or len(username) > 100
            or not password
            or len(password) > 256
        ):
            flash('Enter a valid email address, a username, and a password of up to 256 characters.', category='error')
            return render_template("auth.html", registering=True), 400

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists.', category='error')
            return render_template("auth.html", registering=True)
        else:
            new_user = User(email=email, username=username, password=generate_password_hash(password))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            flash('Your account is ready.', category='success')
            return redirect(url_for('index'))
        
    return render_template("auth.html", registering=True)


@app.errorhandler(404)
def page_not_found(error):
    return render_template(
        "error.html",
        code=404,
        title="Page not found",
        message="We couldn’t find the page you were looking for.",
    ), 404


@app.errorhandler(500)
def internal_server_error(error):
    app.logger.error("Unhandled application error: %s", error)
    return render_template(
        "error.html",
        code=500,
        title="Something went wrong",
        message="We couldn’t complete that request. Please try again later.",
    ), 500


if __name__ == "__main__":
    initialize_database()
    app.run(debug=False)