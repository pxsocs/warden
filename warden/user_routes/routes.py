from flask import (Blueprint, flash, redirect, render_template, request,
                   url_for, current_app)
from flask_login import current_user, login_required, login_user
from werkzeug.security import generate_password_hash

from forms import RegistrationForm, LoginForm, TradeForm
from models import User, AccountInfo, Trades

user_routes = Blueprint('user_routes', __name__)


@user_routes.route("/initial_setup", methods=["GET", "POST"])
# First run setup
def initial_setup():
    if current_user.is_authenticated:
        return redirect(url_for("warden.warden_page"))

    page = request.args.get("page")
    # initial setup will cycle through different pages

    if page is None or page == 'welcome' or page == '1':
        return render_template("warden/welcome.html",
                               title="Welcome to the WARden",
                               next_page='2',
                               previous_page=None)

    if page == '2' or page == 'register':
        form = RegistrationForm()
        if form.validate_on_submit():
            hash = generate_password_hash(form.password.data)
            user = User(username=form.username.data,
                        password=hash)
            current_app.db.session.add(user)
            current_app.db.session.commit()
            flash(f"Account created for {form.username.data}.", "success")
            login_user(user, remember=True)
            # Before redirecting from here, make a few checks
            # 1. Try to reach specter with no auth at standard url
            specter_typical_urls = [
                'http://127.0.0.1:25441',
                'http://localhost:25441'
            ]

            return redirect(url_for("warden.warden_page"))

        return render_template("warden/register.html",
                               title="Register",
                               form=form,
                               previous_page='1',
                               next_page='3')
