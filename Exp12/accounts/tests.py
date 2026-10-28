from django.test import TestCase
from .forms import LoginForm

class LoginFormRegexTests(TestCase):
    def test_valid_username(self):
        form = LoginForm(data={"username": "student_123", "password": "Example123!"})
        self.assertTrue(form.is_valid())

    def test_username_too_short(self):
        form = LoginForm(data={"username": "abc", "password": "Example123!"})
        self.assertFalse(form.is_valid())

    def test_username_with_space(self):
        form = LoginForm(data={"username": "student name", "password": "Example123!"})
        self.assertFalse(form.is_valid())
