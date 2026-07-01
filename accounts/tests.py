from django.test import TestCase

from records.factories import PASSWORD, ScenarioMixin


class AuthenticationTests(ScenarioMixin, TestCase):
    def test_valid_login_lands_on_dashboard(self):
        response = self.client.post('/', {'username': 'admin', 'password': PASSWORD})
        self.assertRedirects(response, '/dashboard/')

    def test_logout_returns_to_login(self):
        self.login('admin')
        response = self.client.post('/logout/')
        self.assertRedirects(response, '/')
        # The landing page now shows the sign-in form again.
        self.assertContains(self.client.get('/'), 'Sign in')

    def test_wrong_password_is_rejected(self):
        response = self.client.post('/', {'username': 'admin', 'password': 'wrong-password'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'correct username and password', status_code=200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_protected_pages_redirect_anonymous_to_login(self):
        for path in ('/dashboard/', '/records/', '/audit/'):
            response = self.client.get(path)
            self.assertRedirects(response, f'/?next={path}')

    def test_each_role_sees_its_own_dashboard(self):
        cases = {
            'admin': 'Administrator dashboard',
            'counselor1': 'Counselor dashboard',
            'student1': 'Student dashboard',
        }
        for username, heading in cases.items():
            self.login(username)
            response = self.client.get('/dashboard/')
            self.assertContains(response, heading)
            self.client.logout()
