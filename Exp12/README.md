# Django Login and Regex Validation Practical

## Aim
To create a Django web application demonstrating user login and username validation using regular expressions.

## Requirements
- Python 3.10+
- Django
- VS Code or another editor
- Web browser

## Setup on Windows
Open a terminal in this folder and run:

```powershell
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
py manage.py migrate
py manage.py createsuperuser
py manage.py runserver
```

Open http://127.0.0.1:8000/ and log in with the superuser credentials.

## Regex rule
The username must contain 4–20 characters and only letters, digits, or underscores:
`[A-Za-z0-9_]{4,20}`

## Test
- A username shorter than 4 characters or containing spaces/symbols is rejected.
- A valid username with an incorrect password displays an authentication error.
- Valid credentials open the protected dashboard.
- Logout returns to the login page.

Note: This practical demonstrates login and regex validation. Create a superuser with `createsuperuser` to obtain login credentials.
