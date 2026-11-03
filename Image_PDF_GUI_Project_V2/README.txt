IMAGE & PDF UTILITY - V2

Accounts:
- Create an account with your name, email address, and password.
- Sign in to use the image and PDF tools.
- Account data is stored locally in %LOCALAPPDATA%\ImagePdfUtility\accounts.json.
- Passwords are stored as salted PBKDF2 hashes; they are not saved as plain text.

Create PDF editor improvements:
- Undo / Redo
- Working font family selection
- Working font size selection
- Bold / Italic / Underline
- Headings
- Alignment
- Bullet lists
- Page breaks
- A4 / Letter
- Export rich formatted text to PDF

Other tools:
- Image resize/compress/rotate/flip
- PDF merge/reorder/remove
- PDF page count
- PDF page extraction

No database or network connection is required.

Install:
py -m pip install -r requirements.txt

Run:
py main.py
