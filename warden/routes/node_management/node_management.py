import os
from flask import (Blueprint, render_template, current_app)
from flask_login import current_user
from datetime import datetime
from backend.utils import pickle_it

node_management = Blueprint("node_management", __name__)

# Minimum TemplateData used for render_template in all routes
# This ensures FX and current_app are sent to the render page
# at all times
templateData = {
    "title": "WARden Node Monitor",
    "current_app": current_app,
    "current_user": current_user
}


@node_management.route("/node_management/monitor", methods=['GET'])
def main_page():
    from models.models import load_Node
    templateData['nodes'] = load_Node()
    templateData['default_node'] = pickle_it('load', 'default_node.pkl')
    return (render_template('node_management/main/node_monitor.html',
                            **templateData))
