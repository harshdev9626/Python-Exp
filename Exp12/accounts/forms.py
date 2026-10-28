import re
from django import forms

class LoginForm(forms.Form):
    username = forms.CharField(
        label="Username",
        max_length=20,
        widget=forms.TextInput(attrs={
            "placeholder": "Enter your username",
            "autocomplete": "username",
            "class": "form-control",
        }),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            "placeholder": "Enter your password",
            "autocomplete": "current-password",
            "class": "form-control",
        }),
    )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if not re.fullmatch(r"[A-Za-z0-9_]{4,20}", username):
            raise forms.ValidationError(
                "Use 4–20 characters: letters, numbers, and underscores only."
            )
        return username
