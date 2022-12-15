import requests
import os
from flask import (Blueprint, flash, redirect, render_template, request,
                   url_for, current_app)
from flask_login import current_user, login_required, login_user
from werkzeug.security import generate_password_hash

from forms import RegistrationForm, UpdateAccountForm
from models import User, AccountInfo, Trades
from backend.utils import update_config

user_routes = Blueprint('user_routes', __name__)


@user_routes.route("/initial_setup", methods=["GET", "POST"])
# First run setup
def initial_setup():

    if current_user.is_authenticated:
        return redirect(url_for("warden.warden_page"))

    page = request.args.get("page")

    # initial setup will cycle through different pages
    if page is None or page == 'welcome' or page == '1':
        # Generate a random API key for Alphavantage
        import secrets
        key = secrets.token_hex(15)
        current_app.settings['API']['alphavantage'] = key
        update_config()

        return render_template("warden/welcome.html",
                               title="Welcome to the WARden")

    if page == '2' or page == 'register':
        form = RegistrationForm()
        if form.validate_on_submit():
            hash = generate_password_hash(form.password.data)
            user = User(username=form.username.data, password=hash)
            current_app.db.session.add(user)
            current_app.db.session.commit()
            login_user(user, remember=True)
            flash(f"Account created for {form.username.data}. User Logged in.",
                  "success")
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
                flash(
                    f"Succesfuly connected to Specter Server at {current_app.specter.base_url}"
                )
        except Exception:
            pass

        return redirect(url_for("warden.warden_page"))


@user_routes.route("/account", methods=["GET", "POST"])
@login_required
def account():
    form = UpdateAccountForm()
    if request.method == "POST":
        if form.validate_on_submit():
            hash = generate_password_hash(form.password.data)
            user = User.query.filter_by(username=current_user.username).first()
            user.password = hash
            current_app.db.session.commit()
            flash(f"Account password updated for user {current_user.username}",
                  "success")
            return redirect(url_for("warden.warden_page"))

        flash("Password Change Failed. Something went wrong. Try Again.",
              "danger")

    return render_template("warden/account.html",
                           title="Account",
                           form=form,
                           current_app=current_app)


@user_routes.route("/tor_services", methods=["GET", "POST"])
@login_required
def tor_services():
    action = request.args.get("action")
    if action == 'start':
        current_app.settings['SERVER']['onion_server'] = 'True'
        update_config()
        from stem.control import Controller
        from urllib.parse import urlparse
        current_app.tor_port = current_app.settings['SERVER'].getint(
            'onion_port')
        current_app.port = current_app.settings['SERVER'].getint('port')
        from backend.warden_modules import home_path
        toraddr_file = os.path.join(home_path(), "onion.txt")
        current_app.save_tor_address_to = toraddr_file
        proxy_url = "socks5h://localhost:9050"
        tor_control_port = ""
        try:
            tor_control_address = urlparse(proxy_url).netloc.split(":")[0]
            if tor_control_address == "localhost":
                tor_control_address = "127.0.0.1"
            current_app.controller = Controller.from_port(
                address=tor_control_address,
                port=int(tor_control_port) if tor_control_port else "default",
            )
        except Exception:
            current_app.controller = None
        from tor import start_hidden_service
        start_hidden_service(current_app)

        flash(
            f"Started Tor Hidden Services at {current_app.tor_service_id}.onion",
            "success")
    if action == 'stop':
        current_app.settings['SERVER']['onion_server'] = 'False'
        update_config()
        from tor import stop_hidden_services
        stop_hidden_services(current_app)
        flash("Stopped Tor Hidden Services", "warning")
    return render_template("warden/tor.html",
                           title="Tor Hidden Services",
                           current_app=current_app)
