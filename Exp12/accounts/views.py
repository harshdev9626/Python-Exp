from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import LoginForm

def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    message = ""
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
            )
            if user is not None:
                login(request, user)
                return redirect("dashboard")
            message = "Invalid username or password."
    else:
        form = LoginForm()

    return render(
        request,
        "accounts/login.html",
        {"form": form, "message": message},
    )

@login_required
def dashboard(request):
    return render(request, "accounts/dashboard.html")

def logout_view(request):
    if request.method == "POST":
        logout(request)
        return redirect("login")
    return render(request, "accounts/logout_confirm.html")
