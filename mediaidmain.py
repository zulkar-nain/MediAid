from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
import pymysql
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
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
    password = db.Column(db.String(100))
    notes = db.relationship('Note')

    def __repr__(self) -> str:
        return f'{self.id} - {self.email} - {self.username}'


class mediaid(db.Model):
    __tablename__ = 'mediaid_disease'
    id = db.Column(db.Integer, primary_key=True)
    dis_name = db.Column(db.String(100),nullable=False)
    sub_name = db.Column(db.String(100), nullable=False)

    def __repr__(self) -> str:
        return f'{self.id} - {self.dis_name} - {self.sub_name}'

    app.app_context().push()

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user):
    return User.query.get(int(user))

@app.route("/", methods=['GET', 'POST'])

def index():
    return render_template("landing.html", user=current_user)

@app.route("/medisugg", methods=['GET', 'POST'])
def medisugg():
    return render_template("medisugg.html", user=current_user)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('useremail')
        password = request.form.get('userpassword')
        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                flash('Logged in successfully.', category='success')
                login_user(user, remember=True)
                return redirect(url_for('index'))
            else:
                flash('Incorrect password, try again.', category='error')
                return redirect(url_for('register'))
        else:
            flash('Email does not exist.', category='error')
    return render_template("signin.html", user=current_user)

@app.route("/logout", methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('useremail')
        username = request.form.get('username')
        password = request.form.get('userpassword')
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists.', category='error')
        else:
            new_user = User(email=email, username=username, password=generate_password_hash(password, method='sha256'))
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('index'))
        
    return render_template("signup.html", user=current_user)

if __name__ == "__main__":
    app.run(debug=True)