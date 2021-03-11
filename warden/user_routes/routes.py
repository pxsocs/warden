import requests
from flask import (Blueprint, flash, redirect, render_template, request,
                   url_for, current_app)
from flask_login import current_user, login_required, login_user
from werkzeug.security import generate_password_hash

from forms import RegistrationForm, LoginForm, TradeForm
from models import User, AccountInfo, Trades
from utils import update_config

user_routes = Blueprint('user_routes', __name__)


@user_routes.route("/initial_setup", methods=["GET", "POST"])
# First run setup
def initial_setup():
    if current_user.is_authenticated:
        return redirect(url_for("warden.warden_page"))

    page = request.args.get("page")
    setup = request.args.get("setup")
    # initial setup will cycle through different pages

    if page is None or page == 'welcome' or page == '1':
        return render_template("warden/welcome.html",
                               title="Welcome to the WARden")

    if page == '2' or page == 'register':
        form = RegistrationForm()
        if form.validate_on_submit():
            hash = generate_password_hash(form.password.data)
            user = User(username=form.username.data,
                        password=hash)
            current_app.db.session.add(user)
            current_app.db.session.commit()
            flash(f"Account created for {form.username.data}", "success")
            login_user(user, remember=True)
            return redirect("/initial_setup?page=3&setup=True")

        return render_template("warden/register.html",
                               title="Welcome to the WARden | Register",
                               form=form)

    if page == '3' or page == 'specter_connect':
        # Make a few checks

        # Maybe Specter is already running?
        try:
            current_app.specter.home_parser['alias_list']
            url_reached = True
            needs_auth = False
            specter_running = True
        except Exception:
            specter_running = False

        # Not running, so do some quick checks
        if not specter_running:
            # 1. Try to reach specter with no auth at standard url
            specter_typical_urls = [
                'http://127.0.0.1:25441',
                'http://localhost:25441'
            ]
            specter_running = False
            url_reached = False
            for url in specter_typical_urls:
                try:
                    if int(requests.head(url).status_code) < 400:
                        url_reached = True
                        break
                except Exception:
                    pass

            # OK, if one found, let's see if auth is needed
            needs_auth = True
            if url_reached:
                home_url = url + '/about'
                response = requests.get(home_url).text
                if "<h1>Login to Specter</h1>" in response:
                    needs_auth = True
                else:
                    needs_auth = False

        return render_template("warden/specter_connect.html",
                               title="Connect Specter",
                               needs_auth=needs_auth,
                               url=url,
                               url_reached=url_reached,
                               specter_running=specter_running,
                               current_app=current_app,
                               current_user=current_user,
                               setup=setup)
