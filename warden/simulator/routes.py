from flask import (Blueprint, flash, redirect, render_template, request,
                   url_for, current_app)
from flask_login import current_user, login_required, login_user

simulator = Blueprint('simulator', __name__)


@simulator.route("/simulator", methods=["GET", "POST"])
def simulator_main():
    return ("OK")
