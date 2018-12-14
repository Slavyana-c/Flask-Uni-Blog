# Reference: Patrick's Software Blog
# https://www.patricksoftwareblog.com/unit-testing-a-flask-application/

# project/test_basic.py


import os
import unittest

from app import app, db, mail

TEST_DB = 'test.db'

class AppTests(unittest.TestCase):

# Setup and teardown

    # executed prior to each test
    def setUp(self):

        basedir = os.path.abspath(os.path.dirname(__file__))
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['DEBUG'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + \
            os.path.join(basedir, TEST_DB)
        self.app = app.test_client()
        db.drop_all()
        db.create_all()

        # Disable sending emails during unit testing
        mail.init_app(app)
        self.assertEqual(app.debug, False)

    # executed after each test
    def tearDown(self):
        pass

# Tests

    # Testing the main pages
    def test_main_page(self):
        response = self.app.get('/', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_login_page(self):
        response = self.app.get('/login', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Forgot Password?', response.data)

    def test_about_page(self):
        response = self.app.get('/about', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'This blog is part of coursework 2', response.data)


    # Testing register
    def test_valid_user_registration(self):
        response = self.register('Admin','admin@blog.com', 'admin123', 'admin123')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b' Your account has been created! You can now log in.', response.data)

    def test_invalid_user_registration_different_passwords(self):
        response = self.register('Admin','admin@blog.com', 'admin123', 'admin00')
        self.assertIn(b'Field must be equal to password.', response.data)

    def test_invalid_user_registration_duplicate_email(self):
        response = self.register('Admin','admin@blog.com', 'admin123', 'admin123')
        self.assertEqual(response.status_code, 200)
        response = self.register('User','admin@blog.com', 'pass', 'pass')
        self.assertIn(b'That email is taken. Please choose a different one.', response.data)

    # Testing Login
    def test_valid_user_login(self):
        response = self.register('Admin','admin@blog.com', 'admin123', 'admin123')
        response = self.login('admin@blog.com', 'admin123')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Logout', response.data)

    def test_invalid_user_login(self):
        response = self.login('random@user.com', 'randomUser')
        self.assertIn(b'Login Unsuccessful.', response.data)


    def test_incomplete_user_login(self):
        response = self.login('', '12345')
        self.assertIn(b'This field is required.', response.data)

    # Testing Logout
    def test_user_logout(self):
        response = self.register('Admin','admin@blog.com', 'admin123', 'admin123')
        response = self.login('admin@blog.com', 'admin123')
        response = self.logout()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)

    def test_invalid_user_logout(self):
        response = self.logout()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please log in to access this page.', response.data)

    # Testing Post Creation
    def test_post_create(self):
        response = self.register('Admin','admin@blog.com', 'admin123', 'admin123')
        response = self.login('admin@blog.com', 'admin123')
        response = self.app.post(
            '/post/new',
            data=dict(title='My Title', content='My Content'),
            follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'My Title', response.data)
        self.assertIn(b'My Content', response.data)


    def test_post_create_invalid(self):
        response = self.register('Admin','admin@blog.com', 'admin123', 'admin123')
        response = self.login('admin@blog.com', 'admin123')
        response = self.app.post(
            '/post/new',
            data=dict(title='My Title', content=''),
            follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'This field is required.', response.data)

    # Testing Account Form
    def test_update_account(self):
        response = self.register('Admin','admin@blog.com', 'admin123', 'admin123')
        response = self.login('admin@blog.com', 'admin123')
        response = self.app.post(
            '/account',
            data=dict(username='NewName', email='new@email.com'),
            follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'NewName', response.data)
        self.assertIn(b'new@email.com', response.data)

    def test_update_account_username_taken(self):
        response = self.register('Admin','admin@blog.com', 'admin123', 'admin123')
        response = self.register('NewName','new@blog.com', 'new122', 'new122')
        response = self.login('admin@blog.com', 'admin123')
        response = self.app.post(
            '/account',
            data=dict(username='NewName', email='new@email.com'),
            follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'That username is taken. Please choose a different one.', response.data)




# Helper methods

    def register(self, username, email, password, confirm):
        return self.app.post(
            '/register',
            data=dict(username=username, email=email, password=password, confirm_password=confirm),
            follow_redirects=True
        )

    def login(self, email, password):
        return self.app.post(
            '/login',
            data=dict(email=email, password=password),
            follow_redirects=True
        )

    def logout(self):
        return self.app.get(
            '/logout',
            follow_redirects=True
        )



if __name__ == "__main__":
    unittest.main()
