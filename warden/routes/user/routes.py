import requests
import os
from flask import (Blueprint, flash, redirect, render_template, request,
                   url_for, current_app)
from flask_login import current_user, login_required, login_user
from werkzeug.security import generate_password_hash

from forms.forms import RegistrationForm, UpdateAccountForm
from models.models import User, AccountInfo, Trades
from backend.config import update_config

user_routes = Blueprint('user_routes', __name__)


@user_routes.route("/initial_setup", methods=["GET", "POST"])
# First run setup
def initial_setup():

    if current_user.is_authenticated:
        # Send to main dashboard
        return redirect(url_for("warden.warden_page"))

    form = RegistrationForm()
    if form.validate_on_submit():
        hash = generate_password_hash(form.password.data)
        user = User(username=form.username.data, password=hash)
        current_app.db.session.add(user)
        current_app.db.session.commit()
        login_user(user, remember=True)
        flash(f"Account created for {form.username.data}. User Logged in.",
              "success")
        return redirect(url_for("warden.warden_page"))

    return render_template("warden/welcome.html",
                           form=form,
                           title="Welcome to the WARden")


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
        update_config(current_app)
        from stem.control import Controller
        from urllib.parse import urlparse
        current_app.tor_port = current_app.settings['SERVER'].getint(
            'onion_port')
        current_app.port = current_app.settings['SERVER'].getint('port')
        from backend.config import home_dir
        toraddr_file = os.path.join(home_dir, "onion.txt")
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
        from connections.tor import start_hidden_service
        start_hidden_service(current_app)

        flash(
            f"Started Tor Hidden Services at {current_app.tor_service_id}.onion",
            "success")
    if action == 'stop':
        current_app.settings['SERVER']['onion_server'] = 'False'
        update_config(current_app)
        from tor import stop_hidden_services
        stop_hidden_services(current_app)
        flash("Stopped Tor Hidden Services", "warning")
    return render_template("warden/tor.html",
                           title="Tor Hidden Services",
                           current_app=current_app)
