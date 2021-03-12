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
            login_user(user, remember=True)
            flash(f"Account created for {form.username.data}. User Logged in.", "success")
            return redirect("/initial_setup?page=3&setup=True")

        return render_template("warden/register.html",
                               title="Welcome to the WARden | Register",
                               form=form)

    if page == '3' or page == 'specter_connect':
        # First let's check where we can connect with Tor
        tor_ports = ['9050', '9150']
        session = requests.session()
        # Use DuckDuckGo Onion address to test tor
        url = 'https://3g2upl4pq6kufc4m.onion'
        failed = True
        for PORT in tor_ports:
            session.proxies = {
                "http": "socks5h://0.0.0.0:" + PORT,
                "https": "socks5h://0.0.0.0:" + PORT,
            }
            try:
                session.get(url)
                session.close()
                failed = False
            except Exception:
                failed = True
            if not failed:
                current_app.settings['TOR']['port'] = PORT
                update_config()
                break
        if failed:
            flash("Tor does not seem to be running in any ports...", "warning")

        # Maybe Specter is already running?
        try:
            if current_app.specter.home_parser()['alias_list'] != []:
                flash(f"Succesfuly connected to Specter Server at {current_app.specter.base_url}")
        except Exception:
            pass

        return redirect(url_for("warden.warden_page"))
