import os
import unittest

from sqlalchemy import inspect
from werkzeug.security import generate_password_hash

os.environ['MEDIAID_DATABASE_URI'] = 'sqlite://'

from mediaidmain import (
    AdminAuditEvent,
    Note,
    Organization,
    TenantMembership,
    User,
    app,
    db,
    hospital,
    initialize_database,
)


def model_instance(model, **values):
    instance = model()
    for field, value in values.items():
        setattr(instance, field, value)
    return instance


class AdminAccessTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        with app.app_context():
            db.session.remove()
            db.drop_all()
            initialize_database()
            self.organization = model_instance(Organization, name='Clinic A')
            self.other_organization = model_instance(Organization, name='Clinic B')
            self.super_admin = model_instance(
                User,
                email='root@example.test',
                username='root',
                password=generate_password_hash('test-password'),
                is_super_admin=True,
            )
            self.tenant_admin = model_instance(
                User,
                email='admin@example.test',
                username='tenant-admin',
                password=generate_password_hash('test-password'),
            )
            self.member = model_instance(
                User,
                email='member@example.test',
                username='member',
                password=generate_password_hash('test-password'),
            )
            db.session.add_all([
                self.organization,
                self.other_organization,
                self.super_admin,
                self.tenant_admin,
                self.member,
            ])
            db.session.flush()
            db.session.add_all([
                model_instance(
                    TenantMembership,
                    organization_id=self.organization.id,
                    user_id=self.tenant_admin.id,
                    role='admin',
                ),
                model_instance(
                    TenantMembership,
                    organization_id=self.organization.id,
                    user_id=self.member.id,
                    role='member',
                ),
                model_instance(
                    TenantMembership,
                    organization_id=self.other_organization.id,
                    user_id=self.member.id,
                    role='member',
                ),
                model_instance(
                    hospital,
                    hos_name='Clinic A Hospital',
                    organization_id=self.organization.id,
                ),
                model_instance(
                    hospital,
                    hos_name='Clinic B Hospital',
                    organization_id=self.other_organization.id,
                ),
                model_instance(hospital, hos_name='Shared Hospital'),
                model_instance(Note, data='private note content', user_id=self.member.id),
            ])
            db.session.commit()
            self.super_admin_id = self.super_admin.id
            self.tenant_admin_id = self.tenant_admin.id
            self.member_id = self.member.id
            self.organization_id = self.organization.id
            self.other_organization_id = self.other_organization.id

    def client_as(self, user_id):
        client = app.test_client()
        with client.session_transaction() as session:
            session['_user_id'] = str(user_id)
            session['_fresh'] = True
        return client

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.engine.dispose()

    def test_tenant_admin_is_scoped_and_cannot_view_notes(self):
        client = self.client_as(self.tenant_admin_id)
        self.assertEqual(client.get('/admin').status_code, 200)
        self.assertEqual(client.get('/admin/members').status_code, 200)
        self.assertEqual(client.get('/admin/notes').status_code, 403)
        directory = client.get('/hospital-area').data
        self.assertIn(b'Clinic A Hospital', directory)
        self.assertIn(b'Shared Hospital', directory)
        self.assertNotIn(b'Clinic B Hospital', directory)
        with app.app_context():
            other_provider_id = hospital.query.filter_by(hos_name='Clinic B Hospital').one().id
        self.assertEqual(
            client.get(f'/admin/providers/hospitals/{other_provider_id}/edit').status_code,
            404,
        )

    def test_tenant_admin_can_create_only_tenant_provider_data(self):
        client = self.client_as(self.tenant_admin_id)
        response = client.post(
            '/admin/providers/hospitals',
            data={'hos_name': 'New Tenant Hospital'},
        )
        self.assertEqual(response.status_code, 302)
        with app.app_context():
            self.assertEqual(
                hospital.query.filter_by(
                    hos_name='New Tenant Hospital',
                    organization_id=self.organization_id,
                ).count(),
                1,
            )
            self.assertEqual(
                AdminAuditEvent.query.filter_by(
                    action='provider.created',
                    organization_id=self.organization_id,
                ).count(),
                1,
            )

    def test_multi_organization_member_can_switch_only_to_membership(self):
        client = self.client_as(self.member_id)
        switched = client.post(
            '/admin/tenant',
            data={'organization_id': self.other_organization_id},
        )
        self.assertEqual(switched.status_code, 302)
        self.assertEqual(switched.location, '/')
        directory = client.get('/hospital-area').data
        self.assertIn(b'Clinic B Hospital', directory)
        self.assertNotIn(b'Clinic A Hospital', directory)
        denied = client.post('/admin/tenant', data={'organization_id': '99999'})
        self.assertEqual(denied.status_code, 403)

    def test_only_super_admin_can_view_notes_and_access_is_audited(self):
        tenant_client = self.client_as(self.tenant_admin_id)
        self.assertEqual(tenant_client.get('/admin/notes').status_code, 403)
        root_client = self.client_as(self.super_admin_id)
        response = root_client.get('/admin/notes')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'private note content', response.data)
        with app.app_context():
            self.assertEqual(
                AdminAuditEvent.query.filter_by(action='private_notes.viewed').count(),
                1,
            )

    def test_super_admin_bootstrap_cli_creates_global_account(self):
        result = app.test_cli_runner().invoke(
            args=['create-super-admin'],
            input='bootstrap@example.test\nbootstrap\n'
            'StrongBootstrapPassword123!\nStrongBootstrapPassword123!\n',
        )
        self.assertEqual(result.exit_code, 0, result.output)
        with app.app_context():
            user = User.query.filter_by(email='bootstrap@example.test').one()
            self.assertTrue(user.is_super_admin)
            self.assertTrue(
                AdminAuditEvent.query.filter_by(
                    action='super_admin.created',
                    target_id=str(user.id),
                ).one()
            )

    def test_super_admin_views_render_for_selected_organization(self):
        client = self.client_as(self.super_admin_id)
        with client.session_transaction() as session:
            session['active_organization_id'] = self.organization_id
        for path in (
            '/admin',
            '/admin/organizations',
            '/admin/members',
            '/admin/users',
            '/admin/providers/hospitals',
            '/admin/providers/doctors',
            '/admin/messages',
            '/admin/notes',
            '/admin/audit',
        ):
            with self.subTest(path=path):
                self.assertEqual(client.get(path).status_code, 200)

    def test_mutations_require_csrf_token_and_logout_is_post_only(self):
        app.config['WTF_CSRF_ENABLED'] = True
        client = self.client_as(self.tenant_admin_id)
        response = client.post(
            '/admin/providers/hospitals',
            data={'hos_name': 'Should not be created'},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(client.get('/logout').status_code, 405)

    def test_authentication_security_events_are_recorded(self):
        client = app.test_client()
        failed = client.post(
            '/login',
            data={'useremail': 'admin@example.test', 'userpassword': 'wrong-password'},
        )
        self.assertEqual(failed.status_code, 401)
        succeeded = client.post(
            '/login',
            data={'useremail': 'admin@example.test', 'userpassword': 'test-password'},
        )
        self.assertEqual(succeeded.status_code, 302)
        profile = client.get('/profiles')
        self.assertEqual(profile.status_code, 200)
        self.assertIn(b'name="csrf_token"', profile.data)
        self.assertEqual(client.post('/logout').status_code, 302)
        with app.app_context():
            self.assertEqual(
                AdminAuditEvent.query.filter_by(action='auth.login_failed').count(),
                1,
            )
            self.assertEqual(
                AdminAuditEvent.query.filter_by(
                    action='auth.login_succeeded',
                    organization_id=self.organization_id,
                ).count(),
                1,
            )
            self.assertEqual(
                AdminAuditEvent.query.filter_by(
                    action='auth.logout',
                    organization_id=self.organization_id,
                ).count(),
                1,
            )

    def test_database_initialization_adds_columns_without_dropping_data(self):
        with app.app_context():
            db.drop_all()
            with db.engine.begin() as connection:
                connection.exec_driver_sql(
                    'CREATE TABLE user (id INTEGER PRIMARY KEY, email VARCHAR(100), '
                    'username VARCHAR(100), password VARCHAR(100))'
                )
                connection.exec_driver_sql(
                    'CREATE TABLE hospital (id INTEGER PRIMARY KEY, hos_name VARCHAR(100))'
                )
                connection.exec_driver_sql(
                    'CREATE TABLE docs (id INTEGER PRIMARY KEY, doc_name VARCHAR(100))'
                )
                connection.exec_driver_sql(
                    "INSERT INTO user (id, email, username) VALUES (1, 'kept@example.test', 'kept')"
                )
            initialize_database()
            inspector = inspect(db.engine)
            self.assertIn(
                'is_super_admin',
                {column['name'] for column in inspector.get_columns('user')},
            )
            self.assertIn(
                'organization_id',
                {column['name'] for column in inspector.get_columns('hospital')},
            )
            self.assertIn(
                'organization_id',
                {column['name'] for column in inspector.get_columns('docs')},
            )
            with db.engine.connect() as connection:
                row = connection.exec_driver_sql(
                    'SELECT email, username FROM user WHERE id = 1'
                ).one()
            self.assertEqual(row, ('kept@example.test', 'kept'))


if __name__ == '__main__':
    unittest.main()
