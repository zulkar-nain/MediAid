import os
import re
import secrets
from datetime import datetime
from functools import wraps
from urllib.parse import urlsplit

import click
from flask import Flask, abort, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from sqlalchemy import inspect, or_, text
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
    set_login_view,
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get('MEDIAID_SECRET_KEY') or secrets.token_hex(32)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://mediaidctrl:abcd1234@localhost:3306/mediaid'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
if os.environ.get('MEDIAID_DATABASE_URI'):
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['MEDIAID_DATABASE_URI']
db = SQLAlchemy(app)
csrf = CSRFProtect(app)


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(10000))
    date = db.Column(db.DateTime(timezone=True), default=func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', back_populates='notes')

    def __repr__(self) -> str:
        return f'{self.id} - {self.data}'


class User(UserMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    username = db.Column(db.String(100))
    password = db.Column(db.String(255))
    is_super_admin = db.Column(db.Boolean, nullable=False, default=False, server_default='0')
    notes = db.relationship('Note', back_populates='user')
    memberships = db.relationship('TenantMembership', back_populates='user', cascade='all, delete-orphan')


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
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=True, index=True)

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
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=True, index=True)

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


class Organization(db.Model):
    __tablename__ = 'organization'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now(), nullable=False)
    memberships = db.relationship('TenantMembership', back_populates='organization', cascade='all, delete-orphan')


class TenantMembership(db.Model):
    __tablename__ = 'tenant_membership'
    __table_args__ = (db.UniqueConstraint('organization_id', 'user_id', name='uq_tenant_membership'),)

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False, default='member')
    created_at = db.Column(db.DateTime(timezone=True), default=func.now(), nullable=False)
    organization = db.relationship('Organization', back_populates='memberships')
    user = db.relationship('User', back_populates='memberships')


class AdminAuditEvent(db.Model):
    __tablename__ = 'admin_audit_event'

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=True, index=True)
    action = db.Column(db.String(80), nullable=False)
    target_type = db.Column(db.String(80), nullable=True)
    target_id = db.Column(db.String(80), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now(), nullable=False, index=True)
    actor = db.relationship('User')
    organization = db.relationship('Organization')


def initialize_database() -> None:
    with app.app_context():
        db.create_all()
        migrations = {
            'user': {'is_super_admin': 'BOOLEAN NOT NULL DEFAULT 0'},
            'hospital': {'organization_id': 'INTEGER NULL'},
            'docs': {'organization_id': 'INTEGER NULL'},
        }
        inspector = inspect(db.engine)
        with db.engine.begin() as connection:
            for table, columns in migrations.items():
                if not inspector.has_table(table):
                    continue
                existing_columns = {column['name'] for column in inspector.get_columns(table)}
                quoted_table = db.engine.dialect.identifier_preparer.quote(table)
                for name, definition in columns.items():
                    if name not in existing_columns:
                        quoted_name = db.engine.dialect.identifier_preparer.quote(name)
                        connection.execute(text(f'ALTER TABLE {quoted_table} ADD COLUMN {quoted_name} {definition}'))


@app.cli.command('create-super-admin')
def create_super_admin():
    """Create or promote an account to global super administrator."""
    email = click.prompt('Administrator email').strip().lower()
    if not is_valid_email(email) or len(email) > 100:
        raise click.ClickException('Enter a valid email address (maximum 100 characters).')
    username = click.prompt('Administrator username').strip()
    if not username or len(username) > 100:
        raise click.ClickException('Enter a username of up to 100 characters.')
    password = click.prompt('Administrator password', hide_input=True, confirmation_prompt=True)
    if len(password) < 12:
        raise click.ClickException('Use an administrator password with at least 12 characters.')
    initialize_database()
    user = User.query.filter_by(email=email).first()
    if user:
        user.is_super_admin = True
        if not user.username:
            user.username = username
        action = 'super_admin.promoted'
    else:
        user = User()
        user.email = email
        user.username = username
        user.password = generate_password_hash(password)
        user.is_super_admin = True
        db.session.add(user)
        action = 'super_admin.created'
    db.session.flush()
    event = AdminAuditEvent()
    event.actor_id = user.id
    event.action = action
    event.target_type = 'user'
    event.target_id = str(user.id)
    db.session.add(event)
    db.session.commit()
    click.echo(f'Super administrator ready: {user.email}')

login_manager = LoginManager()
login_manager.init_app(app)
with app.app_context():
    set_login_view('login')





@app.context_processor
def inject_current_year():
    memberships = []
    active_membership = None
    if current_user.is_authenticated:
        memberships = (
            TenantMembership.query
            .join(Organization)
            .filter(TenantMembership.user_id == current_user.id)
            .order_by(Organization.name)
            .all()
        )
        selected_id = session.get('active_organization_id')
        active_membership = next(
            (membership for membership in memberships if membership.organization_id == selected_id),
            None,
        )
        if active_membership is None and memberships and not current_user.is_super_admin:
            active_membership = memberships[0]
            session['active_organization_id'] = active_membership.organization_id
    active_organization = active_membership.organization if active_membership else None
    if current_user.is_authenticated and current_user.is_super_admin:
        active_id = session.get('active_organization_id')
        active_organization = db.session.get(Organization, active_id) if active_id else None
    is_admin = current_user.is_authenticated and (
        current_user.is_super_admin or any(item.role == 'admin' for item in memberships)
    )
    return {
        'current_year': datetime.now().year,
        'tenant_memberships': memberships,
        'admin_organizations': (
            Organization.query.order_by(Organization.name).all()
            if current_user.is_authenticated and current_user.is_super_admin
            else []
        ),
        'active_organization': active_organization,
        'is_site_admin': is_admin,
        'is_super_admin': current_user.is_authenticated and current_user.is_super_admin,
    }


def current_memberships():
    if not current_user.is_authenticated:
        return []
    return TenantMembership.query.filter_by(user_id=current_user.id).all()


def active_membership():
    memberships = current_memberships()
    selected_id = session.get('active_organization_id')
    membership = next((item for item in memberships if item.organization_id == selected_id), None)
    if membership is None and memberships:
        membership = memberships[0]
        session['active_organization_id'] = membership.organization_id
    return membership


def active_organization_id():
    if current_user.is_authenticated and current_user.is_super_admin:
        selected_id = session.get('active_organization_id')
        if selected_id and db.session.get(Organization, selected_id) is None:
            session.pop('active_organization_id', None)
            return None
        return selected_id
    membership = active_membership()
    return membership.organization_id if membership else None


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_super_admin and not any(
            membership.role == 'admin' for membership in current_memberships()
        ):
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def super_admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_super_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def audit_event(action, target_type=None, target_id=None, organization_id=None, actor_id=None):
    event = AdminAuditEvent()
    event.actor_id = actor_id if actor_id is not None else (
        current_user.id if current_user.is_authenticated else None
    )
    event.organization_id = organization_id
    event.action = action
    event.target_type = target_type
    event.target_id = str(target_id) if target_id is not None else None
    db.session.add(event)


def require_active_organization():
    organization_id = active_organization_id()
    if organization_id is None:
        flash('Select or create an organization before managing tenant data.', category='error')
        return None
    return db.session.get(Organization, organization_id)



@login_manager.user_loader
def load_user(user):
    return db.session.get(User, int(user))

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

        contact_message = ContactMessage()
        contact_message.name = name
        contact_message.email = email
        contact_message.subject = subject
        contact_message.message = message
        db.session.add(contact_message)
        db.session.commit()
        flash('Thanks for contacting MediAid. Your message has been received.', category='success')
        return redirect(url_for('contact'))

    return render_template("contact.html")


def is_valid_email(email):
    return bool(re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email))


def search_directory(model, search, search_fields, sort_field):
    query = model.query
    organization_id = active_organization_id()
    if current_user.is_authenticated and current_user.is_super_admin and organization_id is None:
        pass
    elif organization_id is None:
        query = query.filter(model.organization_id.is_(None))
    else:
        query = query.filter(or_(model.organization_id == organization_id, model.organization_id.is_(None)))
    if search:
        pattern = f'%{search}%'
        query = query.filter(or_(*(getattr(model, field).ilike(pattern) for field in search_fields)))
    return query.order_by(getattr(model, sort_field)).all()


MEDICAL_TOPICS = (
    {
        'slug': 'ear-nose-throat',
        'title': 'Ear, nose, and throat (ENT)',
        'category': 'Head and neck',
        'icon': 'E',
        'directory_term': 'ENT',
        'summary': 'Learn about the specialty concerned with the ears, nose, throat, and related areas of the head and neck.',
        'overview': 'Otolaryngology, commonly called ENT, is a medical and surgical specialty focused on the ears, nose, throat, and related structures of the head and neck.',
        'scope': 'A qualified clinician can help decide whether an ENT professional or another type of care is appropriate for an individual concern.',
    },
    {
        'slug': 'brain-and-nervous-system',
        'title': 'Brain and nervous system',
        'category': 'Nervous system',
        'icon': 'N',
        'directory_term': 'Neurology',
        'summary': 'Get an introduction to neurology and the medical specialty focused on the brain, spinal cord, and nerves.',
        'overview': 'Neurology is the medical specialty focused on the brain, spinal cord, and peripheral nerves.',
        'scope': 'A qualified healthcare professional can assess symptoms and help determine the right clinician and next steps.',
    },
    {
        'slug': 'bones-joints-and-muscles',
        'title': 'Bones, joints, and muscles',
        'category': 'Musculoskeletal system',
        'icon': 'B',
        'directory_term': 'Orthopedics',
        'summary': 'Explore the musculoskeletal system and the specialty that cares for bones, joints, and related movement structures.',
        'overview': 'Orthopedics focuses on the musculoskeletal system, including bones, joints, ligaments, tendons, and muscles.',
        'scope': 'Different concerns may need different kinds of care. A qualified clinician can help assess an individual situation.',
    },
    {
        'slug': 'heart-and-circulation',
        'title': 'Heart and circulation',
        'category': 'Circulatory system',
        'icon': 'H',
        'directory_term': 'Cardiology',
        'summary': 'Learn about cardiology, the medical specialty focused on the heart and circulatory system.',
        'overview': 'Cardiology is the medical specialty concerned with the heart and the circulatory system.',
        'scope': 'This introduction cannot assess symptoms or determine urgency. For personal concerns, contact a qualified healthcare professional.',
    },
    {
        'slug': 'kidneys-and-urinary-health',
        'title': 'Kidneys and urinary health',
        'category': 'Kidney health',
        'icon': 'K',
        'directory_term': 'Nephrology',
        'summary': 'Explore kidney health and learn about nephrology, the specialty focused on kidney care.',
        'overview': 'Nephrology is the medical specialty focused on the kidneys and their role in health.',
        'scope': 'A qualified clinician can explain which tests or type of care may be relevant to an individual.',
    },
    {
        'slug': 'general-health',
        'title': 'General health',
        'category': 'Primary care',
        'icon': 'G',
        'directory_term': 'Medicine',
        'summary': 'Start with general medical information and learn about the role of primary and general healthcare.',
        'overview': 'Primary and general healthcare can be a starting point for many everyday health questions and for coordinating care.',
        'scope': 'A qualified healthcare professional who knows the person’s health history can help decide what care is appropriate.',
    },
)


@app.route("/medisugg", methods=['GET', 'POST'])
def medisugg():
    search = (request.args.get('q') or '').strip()[:100]
    search_terms = search.casefold().split()
    topics = [
        topic for topic in MEDICAL_TOPICS
        if all(
            term in ' '.join((topic['title'], topic['category'], topic['summary'], topic['directory_term'])).casefold()
            for term in search_terms
        )
    ]
    return render_template("medical_topics.html", search=search, topics=topics)


@app.route("/topics/<slug>")
def medical_topic(slug):
    topic = next((topic for topic in MEDICAL_TOPICS if topic['slug'] == slug), None)
    if topic is None:
        return render_template(
            "error.html",
            code=404,
            title="Topic not found",
            message="That medical topic is not available. Browse all topics to see the current guides.",
        ), 404
    return render_template("medical_topic.html", topic=topic)


@app.route("/admin")
@admin_required
def admin_dashboard():
    organization_id = active_organization_id()
    if current_user.is_super_admin:
        users_count = User.query.count()
        organizations_count = Organization.query.count()
        hospitals_query = hospital.query
        doctors_query = docs.query
        notes_count = Note.query.count()
        messages_count = ContactMessage.query.count()
    else:
        organization = require_active_organization()
        if organization is None:
            return redirect(url_for('admin_dashboard'))
        users_count = TenantMembership.query.filter_by(organization_id=organization_id).count()
        organizations_count = 1
        hospitals_query = hospital.query.filter_by(organization_id=organization_id)
        doctors_query = docs.query.filter_by(organization_id=organization_id)
        notes_count = None
        messages_count = None
    return render_template(
        "admin_dashboard.html",
        users_count=users_count,
        organizations_count=organizations_count,
        hospitals_count=hospitals_query.count(),
        doctors_count=doctors_query.count(),
        notes_count=notes_count,
        messages_count=messages_count,
    )


@app.route("/admin/tenant", methods=['POST'])
@login_required
def select_admin_tenant():
    value = (request.form.get('organization_id') or '').strip()
    if value and not value.isdigit():
        abort(400)
    organization_id = int(value) if value.isdigit() else None
    if current_user.is_super_admin:
        if organization_id is not None and db.session.get(Organization, organization_id) is None:
            abort(404)
        if organization_id is None:
            session.pop('active_organization_id', None)
        else:
            session['active_organization_id'] = organization_id
    else:
        membership = next(
            (item for item in current_memberships() if item.organization_id == organization_id),
            None,
        )
        if membership is None:
            abort(403)
        session['active_organization_id'] = membership.organization_id
    if current_user.is_super_admin or any(
        membership.role == 'admin' for membership in current_memberships()
    ):
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('index'))


@app.route("/admin/organizations", methods=['GET', 'POST'])
@super_admin_required
def admin_organizations():
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        if not name or len(name) > 120:
            flash('Enter an organization name of up to 120 characters.', category='error')
        elif Organization.query.filter_by(name=name).first():
            flash('An organization with that name already exists.', category='error')
        else:
            organization = Organization()
            organization.name = name
            db.session.add(organization)
            db.session.flush()
            audit_event('organization.created', 'organization', organization.id, organization.id)
            db.session.commit()
            session['active_organization_id'] = organization.id
            flash('Organization created. Select it to manage its members and directory.', category='success')
            return redirect(url_for('admin_organizations'))
    organizations = Organization.query.order_by(Organization.name).all()
    return render_template("admin_organizations.html", organizations=organizations)


@app.route("/admin/members", methods=['GET', 'POST'])
@admin_required
def admin_members():
    organization = require_active_organization()
    if organization is None:
        return redirect(url_for('admin_organizations' if current_user.is_super_admin else 'admin_dashboard'))
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        role = (request.form.get('role') or 'member').strip()
        user = User.query.filter(func.lower(User.email) == email).first() if is_valid_email(email) else None
        if user is None:
            flash('An account with that email was not found. Ask them to register first.', category='error')
        elif user.is_super_admin:
            flash('Super administrators do not need tenant memberships.', category='error')
        elif role not in ('member', 'admin'):
            flash('Choose a valid tenant role.', category='error')
        elif TenantMembership.query.filter_by(organization_id=organization.id, user_id=user.id).first():
            flash('That account already belongs to this organization.', category='error')
        else:
            membership = TenantMembership()
            membership.organization_id = organization.id
            membership.user_id = user.id
            membership.role = role
            db.session.add(membership)
            db.session.flush()
            audit_event('membership.created', 'user', user.id, organization.id)
            db.session.commit()
            flash('Account added to the organization.', category='success')
            return redirect(url_for('admin_members'))
    memberships = (
        TenantMembership.query
        .join(User)
        .filter(TenantMembership.organization_id == organization.id)
        .order_by(User.username, User.email)
        .all()
    )
    return render_template("admin_members.html", memberships=memberships, organization=organization)


@app.route("/admin/members/<int:membership_id>/role", methods=['POST'])
@admin_required
def change_member_role(membership_id):
    organization = require_active_organization()
    if organization is None:
        abort(404)
    membership = TenantMembership.query.filter_by(
        id=membership_id,
        organization_id=organization.id,
    ).first_or_404()
    role = (request.form.get('role') or '').strip()
    if membership.user.is_super_admin or role not in ('member', 'admin'):
        abort(400)
    if membership.user_id == current_user.id and role != 'admin':
        flash('You cannot remove your own administrator access.', category='error')
    else:
        membership.role = role
        audit_event('membership.role_changed', 'user', membership.user_id, organization.id)
        db.session.commit()
        flash('Organization role updated.', category='success')
    return redirect(url_for('admin_members'))


PROVIDER_MODELS = {
    'hospitals': (hospital, {
        'hos_name': ('Hospital name', 100),
        'hos_loc': ('Area or location', 100),
        'hos_phone': ('Phone', 100),
        'hos_email': ('Email', 100),
        'hos_website': ('Website', 100),
        'hos_cap': ('Capacity', None),
        'hos_subs': ('Specialties', 100),
    }),
    'doctors': (docs, {
        'doc_name': ('Doctor name', 100),
        'doc_loc': ('Area or location', 100),
        'doc_phone': ('Phone', 100),
        'doc_email': ('Email', 100),
        'doc_fee': ('Fee', None),
        'doc_hos': ('Hospital', 100),
        'doc_subs': ('Specialty', 100),
    }),
}


def provider_model(kind):
    if kind not in PROVIDER_MODELS:
        abort(404)
    return PROVIDER_MODELS[kind]


def scoped_provider_query(model, organization_id):
    if current_user.is_super_admin:
        if organization_id is None:
            return model.query
        return model.query.filter(or_(model.organization_id == organization_id, model.organization_id.is_(None)))
    return model.query.filter_by(organization_id=organization_id)


@app.route("/admin/providers/<kind>", methods=['GET', 'POST'])
@admin_required
def admin_providers(kind):
    model, fields = provider_model(kind)
    organization = require_active_organization()
    if organization is None:
        return redirect(url_for('admin_organizations' if current_user.is_super_admin else 'admin_dashboard'))
    if request.method == 'POST':
        values = {}
        errors = []
        for field, (label, maximum) in fields.items():
            raw_value = (request.form.get(field) or '').strip()
            if field in ('hos_cap', 'doc_fee'):
                if raw_value:
                    try:
                        number = int(raw_value)
                        if number < 0 or number > 2_147_483_647:
                            raise ValueError
                        values[field] = number
                    except ValueError:
                        errors.append(f'{label} must be a whole number between 0 and 2,147,483,647.')
                else:
                    values[field] = None
            else:
                if field in ('hos_name', 'doc_name') and not raw_value:
                    errors.append(f'{label} is required.')
                if maximum is not None and len(raw_value) > maximum:
                    errors.append(f'{label} must be at most {maximum} characters.')
                values[field] = raw_value or None
        target_organization_id = organization.id
        if current_user.is_super_admin:
            submitted_org = (request.form.get('organization_id') or '').strip()
            if submitted_org == 'global':
                target_organization_id = None
            elif submitted_org.isdigit():
                target_organization_id = int(submitted_org)
                if db.session.get(Organization, target_organization_id) is None:
                    errors.append('Choose a valid organization.')
            else:
                errors.append('Choose an organization for this listing.')
        if errors:
            for error in errors:
                flash(error, category='error')
        else:
            record = model()
            for field, value in values.items():
                setattr(record, field, value)
            record.organization_id = target_organization_id
            db.session.add(record)
            db.session.flush()
            audit_event('provider.created', kind, record.id, target_organization_id)
            db.session.commit()
            if current_user.is_super_admin and target_organization_id is not None:
                session['active_organization_id'] = target_organization_id
            flash('Directory listing created.', category='success')
            return redirect(url_for('admin_providers', kind=kind))
    records = scoped_provider_query(model, organization.id).order_by(model.id.desc()).all()
    organizations = Organization.query.order_by(Organization.name).all() if current_user.is_super_admin else []
    return render_template(
        "admin_providers.html",
        kind=kind,
        model_name='Hospital' if kind == 'hospitals' else 'Doctor',
        fields=fields,
        records=records,
        organizations=organizations,
        organization=organization,
    )


@app.route("/admin/providers/<kind>/<int:record_id>/edit", methods=['GET', 'POST'])
@admin_required
def edit_provider(kind, record_id):
    model, fields = provider_model(kind)
    organization = require_active_organization()
    if organization is None:
        abort(404)
    record = scoped_provider_query(model, organization.id).filter_by(id=record_id).first_or_404()
    if request.method == 'POST':
        errors = []
        for field, (label, maximum) in fields.items():
            raw_value = (request.form.get(field) or '').strip()
            if field in ('hos_cap', 'doc_fee'):
                if raw_value:
                    try:
                        number = int(raw_value)
                        if number < 0 or number > 2_147_483_647:
                            raise ValueError
                        setattr(record, field, number)
                    except ValueError:
                        errors.append(f'{label} must be a whole number between 0 and 2,147,483,647.')
                else:
                    setattr(record, field, None)
            else:
                if field in ('hos_name', 'doc_name') and not raw_value:
                    errors.append(f'{label} is required.')
                if maximum is not None and len(raw_value) > maximum:
                    errors.append(f'{label} must be at most {maximum} characters.')
                setattr(record, field, raw_value or None)
        if errors:
            for error in errors:
                flash(error, category='error')
        else:
            audit_event('provider.updated', kind, record.id, record.organization_id)
            db.session.commit()
            flash('Directory listing updated.', category='success')
            return redirect(url_for('admin_providers', kind=kind))
    return render_template(
        "admin_provider_edit.html",
        kind=kind,
        model_name='Hospital' if kind == 'hospitals' else 'Doctor',
        fields=fields,
        record=record,
    )


@app.route("/admin/providers/<kind>/<int:record_id>/delete", methods=['POST'])
@admin_required
def delete_provider(kind, record_id):
    model, _ = provider_model(kind)
    organization = active_organization_id()
    record = scoped_provider_query(model, organization).filter_by(id=record_id).first_or_404()
    organization_id = record.organization_id
    db.session.delete(record)
    audit_event('provider.deleted', kind, record_id, organization_id)
    db.session.commit()
    flash('Directory listing deleted.', category='success')
    return redirect(url_for('admin_providers', kind=kind))


@app.route("/admin/users")
@admin_required
def admin_users():
    if current_user.is_super_admin:
        users = User.query.order_by(User.id.desc()).all()
    else:
        organization_id = active_organization_id()
        if organization_id is None:
            return redirect(url_for('admin_dashboard'))
        users = (
            User.query.join(TenantMembership)
            .filter(TenantMembership.organization_id == organization_id)
            .order_by(User.username, User.email)
            .all()
        )
    return render_template("admin_users.html", users=users)


@app.route("/admin/messages")
@super_admin_required
def admin_messages():
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).limit(200).all()
    return render_template("admin_messages.html", messages=messages)


@app.route("/admin/notes")
@super_admin_required
def admin_notes():
    notes = Note.query.join(User, Note.user_id == User.id).order_by(Note.date.desc()).limit(200).all()
    audit_event('private_notes.viewed', 'note', 'latest-200')
    db.session.commit()
    return render_template("admin_notes.html", notes=notes)


@app.route("/admin/audit")
@admin_required
def admin_audit():
    if current_user.is_super_admin:
        query = AdminAuditEvent.query
    else:
        organization_id = active_organization_id()
        if organization_id is None:
            return redirect(url_for('admin_dashboard'))
        query = AdminAuditEvent.query.filter_by(organization_id=organization_id)
    events = query.order_by(AdminAuditEvent.created_at.desc()).limit(300).all()
    return render_template("admin_audit.html", events=events)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = (request.form.get('useremail') or '').strip()
        password = request.form.get('userpassword') or ''
        user = User.query.filter_by(email=email).first() if len(email) <= 100 else None
        if not user or not check_password_hash(user.password, password):
            audit_event(
                'auth.login_failed',
                'user',
                user.id if user else None,
                actor_id=user.id if user else None,
            )
            db.session.commit()
            flash('The email or password was not recognized. Please try again.', category='error')
            return render_template("auth.html", registering=False), 401

        login_user(user, remember=True)
        audit_event('auth.login_succeeded', 'user', user.id, active_organization_id(), user.id)
        db.session.commit()
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

@app.route("/logout", methods=['POST'])
@login_required
def logout():
    audit_event('auth.logout', 'user', current_user.id, active_organization_id(), current_user.id)
    db.session.commit()
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
            new_user = User()
            new_user.email = email
            new_user.username = username
            new_user.password = generate_password_hash(password)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            flash('Your account is ready.', category='success')
            return redirect(url_for('index'))
        
    return render_template("auth.html", registering=True)


@app.errorhandler(404)
def page_not_found(_error):
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