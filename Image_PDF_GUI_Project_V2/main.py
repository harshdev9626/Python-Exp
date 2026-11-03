import hashlib
import hmac
import json
import os
import tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageOps
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4, LETTER, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image as RLImage
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from xml.sax.saxutils import escape


class AccountStore:
    ITERATIONS = 310_000

    def __init__(self):
        data_directory = os.environ.get("LOCALAPPDATA")
        if not data_directory:
            data_directory = os.path.join(
                os.path.expanduser("~"), ".image_pdf_utility"
            )
        self.path = os.path.join(data_directory, "ImagePdfUtility", "accounts.json")

    def _read_accounts(self):
        try:
            with open(self.path, "r", encoding="utf-8") as account_file:
                accounts = json.load(account_file)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError as error:
            raise ValueError("The saved account file is not valid JSON.") from error
        if not isinstance(accounts, dict):
            raise ValueError("The saved account file has an invalid format.")
        return accounts

    def _write_accounts(self, accounts):
        directory = os.path.dirname(self.path)
        os.makedirs(directory, exist_ok=True)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=directory, delete=False
            ) as account_file:
                temporary_path = account_file.name
                json.dump(accounts, account_file, indent=2)
            os.replace(temporary_path, self.path)
        finally:
            if temporary_path and os.path.exists(temporary_path):
                os.unlink(temporary_path)

    def create_account(self, name, email, password):
        accounts = self._read_accounts()
        email = email.strip().lower()
        if email in accounts:
            raise ValueError("An account with this email already exists.")

        salt = os.urandom(16)
        password_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, self.ITERATIONS
        )
        accounts[email] = {
            "name": name.strip(),
            "salt": salt.hex(),
            "password_hash": password_hash.hex(),
        }
        self._write_accounts(accounts)

    def authenticate(self, email, password):
        accounts = self._read_accounts()
        account = accounts.get(email.strip().lower())
        if account is None:
            return None
        if not isinstance(account, dict):
            raise ValueError("The saved account file has an invalid format.")
        try:
            salt = bytes.fromhex(account["salt"])
            expected_hash = bytes.fromhex(account["password_hash"])
            name = account["name"]
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("The saved account file has an invalid format.") from error
        if not isinstance(name, str) or len(salt) != 16 or len(expected_hash) != 32:
            raise ValueError("The saved account file has an invalid format.")

        password_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, self.ITERATIONS
        )
        if hmac.compare_digest(password_hash, expected_hash):
            return name
        return None


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Resizer & PDF Utility")
        self.root.geometry("1180x800")
        self.root.minsize(1020, 760)
        self.account_store = AccountStore()
        self.screen = None
        self.current_user = None

        self.current_image = None
        self.current_image_path = None
        self.preview_image = None
        self.pdf_files = []

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        self.configure_theme(style)

        self.show_login_page()

    def configure_theme(self, style):
        palette = {
            "background": "#f4f6fb",
            "surface": "#ffffff",
            "surface_alt": "#eef1f8",
            "text": "#172033",
            "muted": "#687386",
            "border": "#dfe4ee",
            "accent": "#5b5bd6",
            "accent_hover": "#4949bd",
            "selection": "#e6e9ff",
            "error": "#b42318",
        }
        self.theme_palette = palette
        self.root.configure(background=palette["background"])

        style.configure(".", font=("Segoe UI", 10), foreground=palette["text"])
        style.configure(
            "TFrame", background=palette["background"]
        )
        style.configure(
            "TLabel", background=palette["background"], foreground=palette["text"]
        )
        style.configure(
            "TButton", background=palette["surface_alt"],
            foreground=palette["text"], borderwidth=0, padding=(8, 8),
            font=("Segoe UI", 9, "bold")
        )
        style.map(
            "TButton",
            background=[
                ("disabled", palette["surface_alt"]),
                ("pressed", "#dfe3ef"),
                ("active", "#e4e8f2"),
            ],
            foreground=[("disabled", palette["muted"])],
            relief=[("pressed", "flat"), ("!pressed", "flat")],
        )
        style.configure(
            "Primary.TButton", background=palette["accent"],
            foreground=palette["surface"]
        )
        style.map(
            "Primary.TButton",
            background=[
                ("pressed", palette["accent_hover"]),
                ("active", palette["accent_hover"]),
            ],
            foreground=[("active", palette["surface"]), ("pressed", palette["surface"])],
        )
        style.configure(
            "Toolbar.TFrame", background=palette["surface"],
            borderwidth=0, padding=(10, 7)
        )
        style.configure(
            "TEntry", fieldbackground=palette["surface"],
            foreground=palette["text"], insertcolor=palette["text"],
            bordercolor=palette["border"], lightcolor=palette["border"],
            darkcolor=palette["border"], padding=7
        )
        style.map(
            "TEntry",
            bordercolor=[("focus", palette["accent"])],
            lightcolor=[("focus", palette["accent"])],
            darkcolor=[("focus", palette["accent"])],
        )
        style.configure(
            "TCombobox", fieldbackground=palette["surface"],
            background=palette["surface"], foreground=palette["text"],
            bordercolor=palette["border"], padding=5, arrowsize=12
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", palette["surface"])],
            selectbackground=[("readonly", palette["surface"])],
            selectforeground=[("readonly", palette["text"])],
            bordercolor=[("focus", palette["accent"])],
        )
        style.configure(
            "TCheckbutton", background=palette["background"],
            foreground=palette["text"], padding=4
        )
        style.map(
            "TCheckbutton",
            background=[("active", palette["background"])],
            foreground=[("disabled", palette["muted"])],
        )
        style.configure(
            "TLabelFrame", background=palette["background"],
            bordercolor=palette["border"], relief="solid", borderwidth=1
        )
        style.configure(
            "TLabelFrame.Label", background=palette["background"],
            foreground=palette["text"], font=("Segoe UI", 10, "bold")
        )
        style.configure(
            "TNotebook", background=palette["background"],
            borderwidth=0, tabmargins=(0, 0, 0, 0)
        )
        style.configure(
            "TNotebook.Tab", background=palette["surface_alt"],
            foreground=palette["muted"], padding=(20, 11),
            font=("Segoe UI", 9, "bold"), borderwidth=0
        )
        style.map(
            "TNotebook.Tab",
            background=[
                ("selected", palette["surface"]),
                ("active", "#e4e8f2"),
            ],
            foreground=[
                ("selected", palette["accent"]),
                ("active", palette["text"]),
            ],
        )
        style.configure(
            "Vertical.TScrollbar", background=palette["surface_alt"],
            troughcolor=palette["background"], borderwidth=0,
            arrowsize=12
        )
        style.configure(
            "Header.TFrame", background=palette["surface"],
            borderwidth=0, padding=(18, 8)
        )
        style.configure(
            "Sidebar.TFrame", background="#151927"
        )
        style.configure(
            "SidebarBrand.TLabel", background="#151927",
            foreground="#ffffff", font=("Segoe UI", 17, "bold")
        )
        style.configure(
            "SidebarCaption.TLabel", background="#151927",
            foreground="#9098ad", font=("Segoe UI", 8, "bold")
        )
        style.configure(
            "SidebarNote.TLabel", background="#151927",
            foreground="#aab1c2", font=("Segoe UI", 9)
        )
        style.configure(
            "Nav.TButton", background="#151927", foreground="#c2c8d6",
            anchor="w", padding=(14, 12), font=("Segoe UI", 10)
        )
        style.map(
            "Nav.TButton",
            background=[("active", "#242a3b"), ("pressed", "#242a3b")],
            foreground=[("active", "#ffffff"), ("pressed", "#ffffff")],
        )
        style.configure(
            "NavActive.TButton", background="#302f59",
            foreground="#ffffff", anchor="w", padding=(14, 12),
            font=("Segoe UI", 10, "bold")
        )
        style.map(
            "NavActive.TButton",
            background=[("active", "#3a3969"), ("pressed", "#3a3969")],
            foreground=[("active", "#ffffff"), ("pressed", "#ffffff")],
        )
        style.configure(
            "AuthShell.TFrame", background=palette["surface"],
            bordercolor=palette["border"], borderwidth=1, relief="solid"
        )
        style.configure(
            "AuthHero.TFrame", background="#151927"
        )
        style.configure(
            "AuthHeroBrand.TLabel", background="#151927",
            foreground="#ffffff", font=("Segoe UI", 14, "bold")
        )
        style.configure(
            "AuthHeroTitle.TLabel", background="#151927",
            foreground="#ffffff", font=("Segoe UI", 24, "bold")
        )
        style.configure(
            "AuthHeroBody.TLabel", background="#151927",
            foreground="#b7bfd0", font=("Segoe UI", 10)
        )
        style.configure(
            "AuthHeroAccent.TLabel", background="#151927",
            foreground="#b8b7ff", font=("Segoe UI", 10, "bold")
        )
        style.configure(
            "Title.TLabel", background=palette["surface"],
            foreground=palette["text"], font=("Segoe UI", 20, "bold")
        )
        style.configure(
            "HeaderMuted.TLabel", background=palette["surface"],
            foreground=palette["muted"], font=("Segoe UI", 9)
        )
        style.configure(
            "Muted.TLabel", background=palette["background"],
            foreground=palette["muted"], font=("Segoe UI", 9)
        )
        style.configure(
            "Preview.TLabel", background=palette["surface"],
            foreground=palette["muted"], font=("Segoe UI", 11)
        )
        style.configure(
            "Status.TLabel", background=palette["background"],
            foreground=palette["muted"], font=("Segoe UI", 9)
        )
        style.configure(
            "AuthBackground.TFrame", background=palette["background"]
        )
        style.configure(
            "AuthCard.TFrame", background=palette["surface"],
            bordercolor=palette["border"], borderwidth=1, relief="solid"
        )
        style.configure(
            "AuthBrand.TLabel", background=palette["surface"],
            foreground=palette["accent"],
            font=("Segoe UI", 10, "bold")
        )
        style.configure(
            "AuthTitle.TLabel", background=palette["surface"],
            foreground=palette["text"],
            font=("Segoe UI", 22, "bold")
        )
        style.configure(
            "AuthSubtitle.TLabel", background=palette["surface"],
            foreground=palette["muted"],
            font=("Segoe UI", 10)
        )
        style.configure(
            "AuthField.TLabel", background=palette["surface"],
            foreground=palette["text"],
            font=("Segoe UI", 10, "bold")
        )
        style.configure(
            "AuthError.TLabel", background=palette["surface"],
            foreground=palette["error"],
            font=("Segoe UI", 9)
        )
        style.configure(
            "AuthPrimary.TButton", font=("Segoe UI", 10, "bold"),
            padding=8, background=palette["accent"],
            foreground=palette["surface"]
        )
        style.map(
            "AuthPrimary.TButton",
            background=[
                ("active", palette["accent_hover"]),
                ("pressed", palette["accent_hover"]),
            ],
            foreground=[
                ("active", palette["surface"]),
                ("pressed", palette["surface"]),
            ],
        )
        style.configure(
            "AuthLink.TButton", background=palette["surface"],
            foreground=palette["accent"],
            font=("Segoe UI", 9, "bold"), borderwidth=0, padding=2
        )
        style.map(
            "AuthLink.TButton",
            foreground=[
                ("active", palette["accent_hover"]),
                ("pressed", palette["accent_hover"]),
            ],
        )

    def _replace_screen(self):
        if self.screen is not None:
            self.screen.destroy()
        self.screen = ttk.Frame(self.root)
        self.screen.pack(fill="both", expand=True)

    def _auth_error(self, message):
        self.auth_error.configure(text=message)

    def _build_auth_header(self, parent, title, subtitle):
        ttk.Label(parent, text="", style="AuthBrand.TLabel").pack(
            pady=(0, 12)
        )
        ttk.Label(parent, text=title, style="AuthTitle.TLabel").pack()
        ttk.Label(
            parent, text=subtitle, style="AuthSubtitle.TLabel", wraplength=340
        ).pack(pady=(7, 22))

    def _build_auth_field(self, parent, label, show=None):
        ttk.Label(parent, text=label, style="AuthField.TLabel").pack(
            anchor="w", pady=(10, 5)
        )
        field = ttk.Entry(parent, font=("Segoe UI", 11), show=show)
        field.pack(fill="x", ipady=7)
        return field

    def _build_auth_page(self, title, subtitle):
        self._replace_screen()
        self.screen.configure(style="AuthBackground.TFrame")
        shell = ttk.Frame(self.screen, style="AuthShell.TFrame")
        shell.place(relx=0.5, rely=0.5, anchor="center")

        hero = ttk.Frame(shell, style="AuthHero.TFrame", padding=(34, 36))
        hero.pack(side="left", fill="y")
        ttk.Label(
            hero, text="PIXEL / PAPER", style="AuthHeroBrand.TLabel"
        ).pack(anchor="w", pady=(0, 64))
        ttk.Label(
            hero, text="Good work\nstarts here.", style="AuthHeroTitle.TLabel",
            justify="left"
        ).pack(anchor="w")
        ttk.Label(
            hero,
            text="A thoughtful little workspace for your images and documents.",
            style="AuthHeroBody.TLabel", wraplength=230, justify="left"
        ).pack(anchor="w", pady=(14, 28))
        ttk.Label(
            hero, text="IMAGE STUDIO", style="AuthHeroAccent.TLabel"
        ).pack(anchor="w", pady=(0, 10))
        ttk.Label(
            hero, text="Resize, refine, and export.", style="AuthHeroBody.TLabel"
        ).pack(anchor="w", pady=(0, 12))
        ttk.Label(
            hero, text="PDF WORKSPACE", style="AuthHeroAccent.TLabel"
        ).pack(anchor="w", pady=(0, 10))
        ttk.Label(
            hero, text="Merge, extract, and create.", style="AuthHeroBody.TLabel"
        ).pack(anchor="w")

        card = ttk.Frame(shell, style="AuthCard.TFrame", padding=(42, 42))
        card.pack(side="left", fill="both", expand=True)
        self._build_auth_header(card, title, subtitle)
        self.auth_error = ttk.Label(
            card, text="", style="AuthError.TLabel", wraplength=340
        )
        self.auth_error.pack(fill="x", pady=(0, 2))
        return card

    def show_login_page(self, email=""):
        card = self._build_auth_page(
            "Welcome back", "Sign in to continue to your image and PDF tools."
        )
        self.login_email = self._build_auth_field(card, "Email address")
        self.login_email.insert(0, email)
        self.login_password = self._build_auth_field(
            card, "Password", show="*"
        )
        self.login_password.bind("<Return>", lambda _event: self.sign_in())
        ttk.Button(
            card, text="Sign in", style="AuthPrimary.TButton",
            command=self.sign_in
        ).pack(fill="x", pady=(24, 16), ipady=6)
        ttk.Label(
            card, text="New here?", style="AuthSubtitle.TLabel"
        ).pack(side="left")
        ttk.Button(
            card, text="Create an account", style="AuthLink.TButton",
            command=self.show_sign_up_page
        ).pack(side="left", padx=(5, 0))
        self.login_email.focus_set()

    def show_sign_up_page(self):
        card = self._build_auth_page(
            "Create your account", "Your account stays on this device."
        )
        self.signup_name = self._build_auth_field(card, "Name")
        self.signup_email = self._build_auth_field(card, "Email address")
        self.signup_password = self._build_auth_field(
            card, "Password (at least 8 characters)", show="*"
        )
        self.signup_confirm = self._build_auth_field(
            card, "Confirm password", show="*"
        )
        self.signup_confirm.bind("<Return>", lambda _event: self.create_account())
        ttk.Button(
            card, text="Create account", style="AuthPrimary.TButton",
            command=self.create_account
        ).pack(fill="x", pady=(22, 14), ipady=6)
        ttk.Button(
            card, text="Back to sign in", style="AuthLink.TButton",
            command=self.show_login_page
        ).pack()
        self.signup_name.focus_set()

    def create_account(self):
        name = self.signup_name.get().strip()
        email = self.signup_email.get().strip()
        password = self.signup_password.get()
        confirmation = self.signup_confirm.get()

        if not name or not email or not password or not confirmation:
            self._auth_error("Complete all fields to create your account.")
            return
        if len(name) > 80:
            self._auth_error("Name must be 80 characters or fewer.")
            return
        email_parts = email.split("@")
        if (
            len(email) > 254
            or len(email_parts) != 2
            or not email_parts[0]
            or "." not in email_parts[1]
            or email_parts[1].startswith(".")
            or email_parts[1].endswith(".")
            or any(character.isspace() for character in email)
        ):
            self._auth_error("Enter a valid email address.")
            return
        if len(password) < 8:
            self._auth_error("Choose a password with at least 8 characters.")
            return
        if password != confirmation:
            self._auth_error("The passwords do not match.")
            return

        try:
            self.account_store.create_account(name, email, password)
        except (OSError, ValueError) as error:
            self._auth_error(str(error))
            return

        self.show_login_page(email=email)
        self._auth_error("Account created. Sign in with your new credentials.")

    def sign_in(self):
        email = self.login_email.get().strip()
        password = self.login_password.get()
        if not email or not password:
            self._auth_error("Enter your email address and password.")
            return
        try:
            name = self.account_store.authenticate(email, password)
        except (OSError, ValueError) as error:
            self._auth_error(f"Unable to read saved accounts: {error}")
            return
        if name is None:
            self._auth_error("The email address or password is incorrect.")
            return

        self.current_user = name
        self.build_main_app()

    def build_main_app(self):
        self._replace_screen()
        layout = ttk.Frame(self.screen)
        layout.pack(fill="both", expand=True)

        sidebar = ttk.Frame(layout, style="Sidebar.TFrame", width=236)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        ttk.Label(
            sidebar, text="PIXEL / PAPER", style="SidebarBrand.TLabel"
        ).pack(anchor="w", padx=22, pady=(28, 4))
        ttk.Label(
            sidebar, text="IMAGE & DOCUMENT STUDIO",
            style="SidebarCaption.TLabel"
        ).pack(anchor="w", padx=23, pady=(0, 34))
        ttk.Label(
            sidebar, text="WORKSPACE", style="SidebarCaption.TLabel"
        ).pack(anchor="w", padx=23, pady=(0, 9))

        self.nav_buttons = {}
        nav_items = (
            ("image", "01   Image studio"),
            ("pdf", "02   PDF workspace"),
            ("creator", "03   PDF writer"),
        )
        for key, label in nav_items:
            button = ttk.Button(
                sidebar, text=label, style="Nav.TButton",
                command=lambda selected=key: self.show_workspace_tab(selected)
            )
            button.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[key] = button

        ttk.Frame(sidebar, style="Sidebar.TFrame").pack(fill="both", expand=True)
        ttk.Label(
            sidebar, text="LOCAL & PRIVATE\nYour files stay on this device.",
            style="SidebarNote.TLabel", justify="left"
        ).pack(anchor="w", padx=22, pady=(0, 18))

        workspace = ttk.Frame(layout)
        workspace.pack(side="left", fill="both", expand=True)
        header = ttk.Frame(workspace, style="Header.TFrame")
        header.pack(fill="x")
        header_copy = ttk.Frame(header, style="Header.TFrame")
        header_copy.pack(side="left")
        self.workspace_title = ttk.Label(
            header_copy, text="", style="Title.TLabel"
        )
        self.workspace_title.pack(anchor="w")
        self.workspace_subtitle = ttk.Label(
            header_copy, text="", style="HeaderMuted.TLabel"
        )
        self.workspace_subtitle.pack(anchor="w", pady=(2, 0))

        account = ttk.Frame(header, style="Header.TFrame")
        account.pack(side="right")
        ttk.Label(
            account, text=f"Hi, {self.current_user}",
            style="HeaderMuted.TLabel"
        ).pack(side="left", padx=(0, 10))
        ttk.Button(
            account, text="Sign out", command=self.sign_out
        ).pack(side="left")

        self.content_area = ttk.Frame(workspace, padding=(16, 14))
        self.content_area.pack(fill="both", expand=True)
        self.image_tab = ttk.Frame(self.content_area)
        self.pdf_tab = ttk.Frame(self.content_area)
        self.creator_tab = ttk.Frame(self.content_area)

        self.build_image_tab()
        self.build_pdf_tab()
        self.build_creator_tab()
        self.show_workspace_tab("image")

    def show_workspace_tab(self, selected):
        pages = {
            "image": (
                self.image_tab, "Image studio",
                "Resize, transform, and export your images."
            ),
            "pdf": (
                self.pdf_tab, "PDF workspace",
                "Organize files, merge documents, or extract pages."
            ),
            "creator": (
                self.creator_tab, "PDF writer",
                "Write and format a document, then export it as a PDF."
            ),
        }
        page, title, subtitle = pages[selected]
        for tab in pages.values():
            tab[0].pack_forget()
        page.pack(fill="both", expand=True)
        self.workspace_title.configure(text=title)
        self.workspace_subtitle.configure(text=subtitle)
        for key, button in self.nav_buttons.items():
            button.configure(style="NavActive.TButton" if key == selected else "Nav.TButton")

    def sign_out(self):
        self.current_user = None
        self.show_login_page()

    # ---------------- IMAGE ----------------
    def build_image_tab(self):
        controls = ttk.LabelFrame(self.image_tab, text="Image Tools", padding=12)
        controls.pack(fill="x", padx=15, pady=12)

        ttk.Button(
            controls, text="Open Image", style="Primary.TButton",
            command=self.open_image
        ).grid(
            row=0, column=0, padx=5, pady=5)

        ttk.Button(controls, text="Save As", command=self.save_image).grid(
            row=0, column=1, padx=5, pady=5)

        ttk.Label(controls, text="Width:").grid(row=1, column=0, sticky="e", padx=5)
        self.width_var = tk.StringVar()
        ttk.Entry(controls, textvariable=self.width_var, width=12).grid(row=1, column=1, padx=5)

        ttk.Label(controls, text="Height:").grid(row=1, column=2, sticky="e", padx=5)
        self.height_var = tk.StringVar()
        ttk.Entry(controls, textvariable=self.height_var, width=12).grid(row=1, column=3, padx=5)

        self.keep_ratio = tk.BooleanVar(value=True)
        ttk.Checkbutton(controls, text="Keep aspect ratio",
                        variable=self.keep_ratio).grid(row=1, column=4, padx=10)

        ttk.Button(controls, text="Resize", command=self.resize_image).grid(
            row=2, column=0, padx=5, pady=8)
        ttk.Button(controls, text="Compress", command=self.compress_image).grid(
            row=2, column=1, padx=5)
        ttk.Button(controls, text="Rotate Left", command=lambda: self.rotate(-90)).grid(
            row=2, column=2, padx=5)
        ttk.Button(controls, text="Rotate Right", command=lambda: self.rotate(90)).grid(
            row=2, column=3, padx=5)
        ttk.Button(controls, text="Flip H", command=lambda: self.flip("h")).grid(
            row=2, column=4, padx=5)
        ttk.Button(controls, text="Flip V", command=lambda: self.flip("v")).grid(
            row=2, column=5, padx=5)

        self.image_info = ttk.Label(self.image_tab, text="No image selected.")
        self.image_info.pack(pady=4)

        self.image_preview = ttk.Label(self.image_tab, text="Image Preview",
                                       anchor="center", style="Preview.TLabel")
        self.image_preview.pack(
            fill="both", expand=True, padx=20, pady=(8, 16), ipadx=12, ipady=12
        )

    def open_image(self):
        path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.webp *.bmp *.gif")]
        )
        if not path:
            return
        try:
            self.current_image = Image.open(path).convert("RGBA")
            self.current_image_path = path
            self.width_var.set(str(self.current_image.width))
            self.height_var.set(str(self.current_image.height))
            self.update_image()
        except Exception as e:
            messagebox.showerror("Image Error", str(e))

    def update_image(self):
        if not self.current_image:
            return
        preview = self.current_image.copy()
        preview.thumbnail((700, 400))
        self.preview_image = ImageTk.PhotoImage(preview)
        self.image_preview.configure(image=self.preview_image, text="")
        self.image_info.configure(
            text=f"{os.path.basename(self.current_image_path or 'Image')}  |  "
                 f"{self.current_image.width} × {self.current_image.height} px"
        )

    def resize_image(self):
        if not self.current_image:
            messagebox.showwarning("Image", "Open an image first.")
            return
        try:
            w = int(self.width_var.get())
            h = int(self.height_var.get())
            if w <= 0 or h <= 0:
                raise ValueError

            if self.keep_ratio.get():
                ratio = self.current_image.width / self.current_image.height
                if self.current_image.width >= self.current_image.height:
                    h = max(1, round(w / ratio))
                else:
                    w = max(1, round(h * ratio))
                self.width_var.set(str(w))
                self.height_var.set(str(h))

            self.current_image = self.current_image.resize(
                (w, h), Image.Resampling.LANCZOS)
            self.update_image()
        except ValueError:
            messagebox.showerror("Image Error", "Enter valid positive width and height.")

    def compress_image(self):
        if not self.current_image:
            messagebox.showwarning("Image", "Open an image first.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("JPEG Compression")
        dialog.geometry("360x190")
        dialog.transient(self.root)
        dialog.grab_set()

        quality = tk.IntVar(value=80)
        ttk.Label(dialog, text="JPEG quality (10–100)").pack(pady=(18, 5))
        ttk.Scale(dialog, from_=10, to=100, variable=quality,
                  orient="horizontal").pack(fill="x", padx=30)
        ttk.Label(dialog, textvariable=quality).pack(pady=5)

        def save():
            path = filedialog.asksaveasfilename(
                title="Save Compressed Image",
                defaultextension=".jpg",
                filetypes=[("JPEG", "*.jpg")]
            )
            if not path:
                return
            self.current_image.convert("RGB").save(
                path, "JPEG", quality=int(quality.get()), optimize=True)
            dialog.destroy()
            messagebox.showinfo("Success", "Compressed image saved.")

        ttk.Button(dialog, text="Save", command=save).pack(pady=8)

    def rotate(self, angle):
        if not self.current_image:
            messagebox.showwarning("Image", "Open an image first.")
            return
        self.current_image = self.current_image.rotate(angle, expand=True)
        self.width_var.set(str(self.current_image.width))
        self.height_var.set(str(self.current_image.height))
        self.update_image()

    def flip(self, direction):
        if not self.current_image:
            messagebox.showwarning("Image", "Open an image first.")
            return
        self.current_image = (ImageOps.mirror(self.current_image)
                              if direction == "h"
                              else ImageOps.flip(self.current_image))
        self.update_image()

    def save_image(self):
        if not self.current_image:
            messagebox.showwarning("Image", "Open an image first.")
            return
        path = filedialog.asksaveasfilename(
            title="Save Image",
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("WEBP", "*.webp")]
        )
        if not path:
            return
        try:
            ext = os.path.splitext(path)[1].lower()
            if ext in (".jpg", ".jpeg"):
                self.current_image.convert("RGB").save(path, "JPEG",
                                                        quality=95, optimize=True)
            elif ext == ".webp":
                self.current_image.save(path, "WEBP", quality=95)
            else:
                self.current_image.save(path, "PNG", optimize=True)
            messagebox.showinfo("Success", "Image saved successfully.")
        except Exception as e:
            messagebox.showerror("Image Error", str(e))

    # ---------------- PDF ----------------
    def build_pdf_tab(self):
        outer = ttk.Frame(self.pdf_tab, padding=15)
        outer.pack(fill="both", expand=True)

        toolbar = ttk.Frame(outer)
        toolbar.pack(fill="x", pady=(0, 10))

        ttk.Button(toolbar, text="Add PDFs", command=self.add_pdfs).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Remove", command=self.remove_pdf).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Move Up", command=self.move_up).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Move Down", command=self.move_down).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Clear", command=self.clear_pdfs).pack(side="left", padx=4)

        ttk.Button(
            toolbar, text="Merge PDFs", style="Primary.TButton",
            command=self.merge_pdfs
        ).pack(
            side="right", padx=4)

        self.pdf_list = tk.Listbox(
            outer, selectmode=tk.SINGLE, font=("Segoe UI", 11),
            background=self.theme_palette["surface"],
            foreground=self.theme_palette["text"],
            selectbackground=self.theme_palette["selection"],
            selectforeground=self.theme_palette["text"],
            highlightbackground=self.theme_palette["border"],
            highlightcolor=self.theme_palette["accent"],
            highlightthickness=1, relief="flat", borderwidth=0,
            selectborderwidth=0, activestyle="none"
        )
        self.pdf_list.pack(fill="both", expand=True)

        info = ttk.LabelFrame(outer, text="PDF Page Tools", padding=10)
        info.pack(fill="x", pady=10)

        ttk.Button(info, text="Page Count", command=self.page_count).grid(
            row=0, column=0, padx=5)
        ttk.Label(info, text="Pages to extract:").grid(row=0, column=1, padx=5)
        self.pages_var = tk.StringVar()
        ttk.Entry(info, textvariable=self.pages_var, width=22).grid(
            row=0, column=2, padx=5)
        ttk.Button(info, text="Extract Pages", command=self.extract_pages).grid(
            row=0, column=3, padx=5)

        self.pdf_status = ttk.Label(
            outer, text="Add one or more PDF files. The list order is the merge order.",
            style="Status.TLabel")
        self.pdf_status.pack(anchor="w")

    def add_pdfs(self):
        files = filedialog.askopenfilenames(
            title="Select PDF files",
            filetypes=[("PDF files", "*.pdf")]
        )
        if not files:
            return

        added = 0
        for path in files:
            if path not in self.pdf_files:
                # Validate the PDF before adding it.
                try:
                    PdfReader(path)
                except Exception as e:
                    messagebox.showwarning(
                        "Invalid PDF",
                        f"Could not read:\n{os.path.basename(path)}\n\n{e}"
                    )
                    continue
                self.pdf_files.append(path)
                added += 1

        self.refresh_pdf_list()
        self.pdf_status.configure(
            text=f"{len(self.pdf_files)} PDF(s) loaded. "
                 f"Merge order follows the list above."
        )

    def refresh_pdf_list(self):
        self.pdf_list.delete(0, "end")
        for i, path in enumerate(self.pdf_files, start=1):
            self.pdf_list.insert("end", f"{i}. {os.path.basename(path)}")

    def remove_pdf(self):
        sel = self.pdf_list.curselection()
        if not sel:
            messagebox.showwarning("PDF", "Select a PDF to remove.")
            return
        self.pdf_files.pop(sel[0])
        self.refresh_pdf_list()

    def clear_pdfs(self):
        self.pdf_files.clear()
        self.refresh_pdf_list()
        self.pdf_status.configure(text="PDF list cleared.")

    def move_up(self):
        sel = self.pdf_list.curselection()
        if not sel or sel[0] == 0:
            return
        i = sel[0]
        self.pdf_files[i - 1], self.pdf_files[i] = self.pdf_files[i], self.pdf_files[i - 1]
        self.refresh_pdf_list()
        self.pdf_list.selection_set(i - 1)

    def move_down(self):
        sel = self.pdf_list.curselection()
        if not sel or sel[0] >= len(self.pdf_files) - 1:
            return
        i = sel[0]
        self.pdf_files[i + 1], self.pdf_files[i] = self.pdf_files[i], self.pdf_files[i + 1]
        self.refresh_pdf_list()
        self.pdf_list.selection_set(i + 1)

    def merge_pdfs(self):
        if len(self.pdf_files) < 1:
            messagebox.showwarning("PDF", "Add at least one PDF first.")
            return

        output = filedialog.asksaveasfilename(
            title="Save Merged PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )
        if not output:
            return

        # Prevent overwriting one of the input files.
        output_abs = os.path.abspath(output)
        if output_abs in {os.path.abspath(p) for p in self.pdf_files}:
            messagebox.showerror(
                "PDF Error",
                "Choose a different output file; it cannot be one of the input PDFs."
            )
            return

        try:
            writer = PdfWriter()

            for path in self.pdf_files:
                reader = PdfReader(path, strict=False)
                for page in reader.pages:
                    writer.add_page(page)

            # Transfer document metadata when available.
            writer.add_metadata({
                "/Producer": "Image & PDF Utility"
            })

            with open(output, "wb") as f:
                writer.write(f)

            # Verify the generated PDF can be opened.
            check = PdfReader(output, strict=False)
            messagebox.showinfo(
                "Merge Complete",
                f"PDFs merged successfully.\n\n"
                f"Files: {len(self.pdf_files)}\n"
                f"Pages: {len(check.pages)}\n"
                f"Saved to:\n{output}"
            )
        except Exception as e:
            messagebox.showerror(
                "PDF Merge Error",
                f"Could not merge the PDFs.\n\n{e}"
            )

    def page_count(self):
        if not self.pdf_files:
            messagebox.showwarning("PDF", "Add a PDF first.")
            return

        lines = []
        try:
            for path in self.pdf_files:
                reader = PdfReader(path, strict=False)
                lines.append(f"{os.path.basename(path)}: {len(reader.pages)} page(s)")
            messagebox.showinfo("PDF Page Count", "\n".join(lines))
        except Exception as e:
            messagebox.showerror("PDF Error", str(e))

    def parse_pages(self, value, total):
        pages = []
        for part in value.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                a, b = part.split("-", 1)
                a, b = int(a.strip()), int(b.strip())
                if a > b:
                    a, b = b, a
                pages.extend(range(a, b + 1))
            else:
                pages.append(int(part))

        # User enters 1-based page numbers.
        zero_based = sorted(set(p - 1 for p in pages if 1 <= p <= total))
        return zero_based

    def extract_pages(self):
        sel = self.pdf_list.curselection()
        if not sel:
            messagebox.showwarning("PDF", "Select one PDF from the list.")
            return

        spec = self.pages_var.get().strip()
        if not spec:
            messagebox.showwarning(
                "PDF",
                "Enter pages such as 1,3,5-7."
            )
            return

        source = self.pdf_files[sel[0]]
        try:
            reader = PdfReader(source, strict=False)
            indexes = self.parse_pages(spec, len(reader.pages))

            if not indexes:
                messagebox.showerror("PDF", "No valid pages were found.")
                return

            output = filedialog.asksaveasfilename(
                title="Save Extracted PDF",
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")]
            )
            if not output:
                return

            writer = PdfWriter()
            for index in indexes:
                writer.add_page(reader.pages[index])

            with open(output, "wb") as f:
                writer.write(f)

            messagebox.showinfo(
                "Success",
                f"Extracted {len(indexes)} page(s) successfully."
            )
        except Exception as e:
            messagebox.showerror("PDF Extraction Error", str(e))


    # ---------------- WORD-LIKE PDF CREATOR ----------------
    def build_creator_tab(self):
        toolbar = ttk.Frame(self.creator_tab, style="Toolbar.TFrame")
        toolbar.pack(fill="x")

        ttk.Button(toolbar, text="New", command=self.new_document).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Undo", command=self.undo_text).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Redo", command=self.redo_text).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Open .txt", command=self.open_text_document).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Save .txt", command=self.save_text_document).pack(side="left", padx=2)
        ttk.Button(
            toolbar, text="Export PDF", style="Primary.TButton",
            command=self.export_created_pdf
        ).pack(side="right", padx=2)

        formatting = ttk.Frame(self.creator_tab, style="Toolbar.TFrame")
        formatting.pack(fill="x", pady=(0, 4))

        ttk.Label(formatting, text="Font").pack(side="left", padx=(2, 5))
        self.font_var = tk.StringVar(value="Helvetica")
        self.font_combo = ttk.Combobox(
            formatting, textvariable=self.font_var,
            values=["Helvetica", "Times-Roman", "Courier"],
            width=12, state="readonly"
        )
        self.font_combo.pack(side="left", padx=2)
        self.font_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_font())

        ttk.Label(formatting, text="Size").pack(side="left", padx=(12, 5))
        self.size_var = tk.StringVar(value="12")
        self.size_combo = ttk.Combobox(
            formatting, textvariable=self.size_var,
            values=["8", "9", "10", "11", "12", "14", "16", "18", "20", "24", "28", "32", "36", "48"],
            width=5
        )
        self.size_combo.pack(side="left", padx=2)
        self.size_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_font_size())
        self.size_combo.bind("<Return>", lambda e: self.apply_font_size())

        ttk.Button(formatting, text="Bold", command=self.format_bold).pack(side="left", padx=2)
        ttk.Button(formatting, text="Italic", command=self.format_italic).pack(side="left", padx=2)
        ttk.Button(formatting, text="Underline", command=self.format_underline).pack(side="left", padx=2)

        alignment = ttk.Frame(self.creator_tab, style="Toolbar.TFrame")
        alignment.pack(fill="x", pady=(0, 4))
        ttk.Label(alignment, text="Align").pack(side="left", padx=(2, 8))
        ttk.Button(alignment, text="Left", command=lambda: self.set_alignment("left")).pack(side="left", padx=2)
        ttk.Button(alignment, text="Center", command=lambda: self.set_alignment("center")).pack(side="left", padx=2)
        ttk.Button(alignment, text="Right", command=lambda: self.set_alignment("right")).pack(side="left", padx=2)

        options = ttk.Frame(self.creator_tab, style="Toolbar.TFrame")
        options.pack(fill="x")

        ttk.Label(options, text="Page:").pack(side="left")
        self.page_size_var = tk.StringVar(value="A4")
        ttk.Combobox(
            options, textvariable=self.page_size_var,
            values=["A4", "Letter"], width=10, state="readonly"
        ).pack(side="left", padx=5)

        ttk.Button(options, text="Heading 1", command=lambda: self.apply_heading(1)).pack(side="left", padx=3)
        ttk.Button(options, text="Heading 2", command=lambda: self.apply_heading(2)).pack(side="left", padx=3)
        ttk.Button(options, text="Bullet List", command=self.insert_bullet).pack(side="left", padx=3)
        ttk.Button(options, text="Insert Page Break", command=self.insert_page_break).pack(side="left", padx=3)

        editor_frame = ttk.Frame(self.creator_tab)
        editor_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.editor = tk.Text(
            editor_frame, wrap="word", undo=True, maxundo=-1,
            font=("Arial", 12), padx=18, pady=18,
            background=self.theme_palette["surface"],
            foreground=self.theme_palette["text"],
            insertbackground=self.theme_palette["accent"],
            selectbackground=self.theme_palette["selection"],
            selectforeground=self.theme_palette["text"],
            highlightbackground=self.theme_palette["border"],
            highlightcolor=self.theme_palette["accent"],
            highlightthickness=1, relief="flat", borderwidth=0,
            spacing1=3, spacing3=3
        )
        scroll = ttk.Scrollbar(editor_frame, orient="vertical", command=self.editor.yview)
        self.editor.configure(yscrollcommand=scroll.set)
        self.editor.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.creator_status = ttk.Label(
            self.creator_tab,
            text="Type your document here, format it, then click Export PDF.",
            style="Status.TLabel"
        )
        self.creator_status.pack(anchor="w", padx=12, pady=5)

        self.editor.tag_configure("bold", font=("Arial", 12, "bold"))
        self.editor.tag_configure("italic", font=("Arial", 12, "italic"))
        self.editor.tag_configure("underline", underline=True)
        self.editor.tag_configure("font_helvetica", font=("Arial", 12))
        self.editor.tag_configure("font_times", font=("Times New Roman", 12))
        self.editor.tag_configure("font_courier", font=("Courier New", 12))
        for s in [8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48]:
            self.editor.tag_configure(f"size_{s}", font=("Arial", s))
        self.editor.tag_configure("h1", font=("Arial", 22, "bold"), spacing3=8)
        self.editor.tag_configure("h2", font=("Arial", 16, "bold"), spacing3=5)
        self.editor.tag_configure("align_left", justify="left")
        self.editor.tag_configure("align_center", justify="center")
        self.editor.tag_configure("align_right", justify="right")
        self.editor.tag_configure("bullet", lmargin1=25, lmargin2=45)

    def _apply_tag(self, tag):
        try:
            start = self.editor.index("sel.first")
            end = self.editor.index("sel.last")
        except tk.TclError:
            messagebox.showwarning("Editor", "Select some text first.")
            return

        if tag in self.editor.tag_names(start):
            self.editor.tag_remove(tag, start, end)
        else:
            self.editor.tag_add(tag, start, end)

    def undo_text(self):
        try:
            self.editor.edit_undo()
        except tk.TclError:
            pass

    def redo_text(self):
        try:
            self.editor.edit_redo()
        except tk.TclError:
            pass

    def apply_font(self):
        try:
            start = self.editor.index("sel.first")
            end = self.editor.index("sel.last")
        except tk.TclError:
            messagebox.showwarning("Font", "Select text first.")
            return

        for tag in ("font_helvetica", "font_times", "font_courier"):
            self.editor.tag_remove(tag, start, end)

        tag = {
            "Helvetica": "font_helvetica",
            "Times-Roman": "font_times",
            "Courier": "font_courier"
        }.get(self.font_var.get(), "font_helvetica")
        self.editor.tag_add(tag, start, end)

    def apply_font_size(self):
        try:
            size = int(self.size_var.get())
            start = self.editor.index("sel.first")
            end = self.editor.index("sel.last")
        except (ValueError, tk.TclError):
            messagebox.showwarning("Font Size", "Select text and choose a valid size.")
            return

        for s in [8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48]:
            self.editor.tag_remove(f"size_{s}", start, end)
        self.editor.tag_add(f"size_{size}", start, end)

    def format_bold(self):
        self._apply_tag("bold")

    def format_italic(self):
        self._apply_tag("italic")

    def format_underline(self):
        self._apply_tag("underline")

    def set_alignment(self, alignment):
        try:
            start = self.editor.index("sel.first")
            end = self.editor.index("sel.last")
        except tk.TclError:
            start = "1.0"
            end = "end"

        for tag in ("align_left", "align_center", "align_right"):
            self.editor.tag_remove(tag, start, end)
        self.editor.tag_add("align_" + alignment, start, end)

    def apply_heading(self, level):
        try:
            start = self.editor.index("sel.first")
            end = self.editor.index("sel.last")
        except tk.TclError:
            start = self.editor.index("insert linestart")
            end = self.editor.index("insert lineend")

        self.editor.tag_add("h1" if level == 1 else "h2", start, end)

    def insert_bullet(self):
        line = self.editor.index("insert linestart")
        self.editor.insert(line, "• ")

    def insert_page_break(self):
        self.editor.insert("insert", "\n\n--- PAGE BREAK ---\n\n")

    def new_document(self):
        if messagebox.askyesno("New Document", "Clear the current document?"):
            self.editor.delete("1.0", "end")
            self.creator_status.configure(text="New document created.")

    def open_text_document(self):
        path = filedialog.askopenfilename(
            title="Open Text Document",
            filetypes=[("Text Files", "*.txt")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = f.read()
            self.editor.delete("1.0", "end")
            self.editor.insert("1.0", data)
            self.creator_status.configure(text=os.path.basename(path))
        except Exception as e:
            messagebox.showerror("Open Error", str(e))

    def save_text_document(self):
        path = filedialog.asksaveasfilename(
            title="Save Text Document",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt")]
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.editor.get("1.0", "end-1c"))
            messagebox.showinfo("Saved", "Text document saved.")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def _reportlab_font(self, tags):
        base = "Helvetica"
        if "font_times" in tags:
            base = "Times"
        elif "font_courier" in tags:
            base = "Courier"

        bold = "bold" in tags
        italic = "italic" in tags

        if base == "Times":
            if bold and italic:
                return "Times-BoldItalic"
            if bold:
                return "Times-Bold"
            if italic:
                return "Times-Italic"
            return "Times-Roman"

        if base == "Courier":
            if bold and italic:
                return "Courier-BoldOblique"
            if bold:
                return "Courier-Bold"
            if italic:
                return "Courier-Oblique"
            return "Courier"

        if bold and italic:
            return "Helvetica-BoldOblique"
        if bold:
            return "Helvetica-Bold"
        if italic:
            return "Helvetica-Oblique"
        return "Helvetica"

    def _reportlab_size(self, tags):
        for s in [48, 36, 32, 28, 24, 20, 18, 16, 14, 12, 11, 10, 9, 8]:
            if f"size_{s}" in tags:
                return s
        if "h1" in tags:
            return 22
        if "h2" in tags:
            return 16
        try:
            return int(self.size_var.get())
        except ValueError:
            return 12

    def _paragraph_from_tk_line(self, line_start, line_end, raw_line, number):
        # Build rich text by splitting the line into ranges with identical tags.
        segments = []
        pos = self.editor.index(line_start)

        while self.editor.compare(pos, "<", line_end):
            tags = set(self.editor.tag_names(pos))
            next_pos = self.editor.index(f"{pos}+1c")
            while self.editor.compare(next_pos, "<", line_end):
                next_tags = set(self.editor.tag_names(next_pos))
                if next_tags != tags:
                    break
                next_pos = self.editor.index(f"{next_pos}+1c")

            try:
                piece = self.editor.get(pos, next_pos)
            except tk.TclError:
                piece = ""

            if piece:
                font = self._reportlab_font(tags)
                size = self._reportlab_size(tags)
                safe = escape(piece).replace("\n", "<br/>")
                if "underline" in tags:
                    safe = f"<u>{safe}</u>"
                segments.append(
                    f'<font name="{font}" size="{size}">{safe}</font>'
                )

            pos = next_pos

        tags_at_start = set(self.editor.tag_names(line_start))
        alignment = TA_LEFT
        if "align_center" in tags_at_start:
            alignment = TA_CENTER
        elif "align_right" in tags_at_start:
            alignment = TA_RIGHT

        if not segments:
            segments = ["&nbsp;"]

        style = ParagraphStyle(
            f"rich_line_{number}",
            fontName=self._reportlab_font(tags_at_start),
            fontSize=self._reportlab_size(tags_at_start),
            leading=max(self._reportlab_size(tags_at_start) * 1.35, 14),
            alignment=alignment,
            spaceAfter=5
        )
        return Paragraph("".join(segments), style)

    def export_created_pdf(self):
        content = self.editor.get("1.0", "end-1c")
        if not content.strip():
            messagebox.showwarning("PDF Creator", "Write something before exporting.")
            return

        output = filedialog.asksaveasfilename(
            title="Export Document as PDF",
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")]
        )
        if not output:
            return

        try:
            pagesize = A4 if self.page_size_var.get() == "A4" else LETTER
            doc = SimpleDocTemplate(
                output, pagesize=pagesize,
                rightMargin=50, leftMargin=50,
                topMargin=50, bottomMargin=50
            )

            story = []
            line_count = int(self.editor.index("end-1c").split(".")[0])

            for i in range(1, line_count + 1):
                start = f"{i}.0"
                end = f"{i}.end"
                raw_line = self.editor.get(start, end)

                if raw_line.strip() == "--- PAGE BREAK ---":
                    story.append(PageBreak())
                    continue

                # Add bullet indentation when line begins with bullet.
                paragraph = self._paragraph_from_tk_line(
                    start, end, raw_line, i
                )
                story.append(paragraph)

            doc.build(story)

            # Verify the generated PDF.
            check = PdfReader(output, strict=False)
            messagebox.showinfo(
                "PDF Created",
                f"Document created successfully.\n\n"
                f"Pages: {len(check.pages)}\n"
                f"Saved to:\n{output}"
            )
            self.creator_status.configure(
                text=f"PDF created: {os.path.basename(output)}"
            )
        except Exception as e:
            messagebox.showerror("PDF Creator Error", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()