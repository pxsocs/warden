import logging
import configparser
import os
import sys
import atexit
import json

from datetime import datetime
from logging.handlers import RotatingFileHandler
from flask import (Flask, request, current_app,
                   has_request_context)

from flask_apscheduler import APScheduler
from flask_mail import Mail
from pathlib import Path

from warden.config import Config


# Method to create a new config file if not found
# Copies data from config_default.ini into a new config.ini
def create_config(config_file):
    logging.warn("Config File not found. Getting default values and saving.")
    # Get the default config and save into config.ini
    default_file = Config.default_config_file

    default_config = configparser.ConfigParser()
    default_config.read(default_file)

    with open(config_file, 'w') as file:
        default_config.write(file)


# Method to create a new config file if not found
# Copies data from config_default.ini into a new config.ini
def update_config(config_file=Config.config_file):
    logging.info("Updating Config file")
    with open(config_file, 'w') as file:
        current_app.settings.write(file)


# Critical checks for specter
def specter_checks():
    # Check if Python Library is present - this is a requirement
    specter_library_check()
    # Check if data folder is present
    # does config have a specter folder? If yes, test
    # data_folder = g.settings['SPECTER']['specter_datafolder']
    check = specter_datafolder_check()


def load_specter():
    # First, try to get the json that is saved
    logging.info("Updating Specter Class...")
    from warden.warden import specter_update
    specter = specter_update(load=False)
    return (specter)


def specter_datafolder_check():
    logging.info("Starting... Looking for Specter Data Folder...")
    # Get Python Library
    from cryptoadvance.specter.specter import Specter
    # First use whatever is in config.ini
    data_folder = current_app.settings['SPECTER']['specter_datafolder']
    specter = Specter(data_folder=data_folder)
    if specter.is_running:
        logging.info(f"[Success] Specter is running from {data_folder}")
        return (True)
    logging.warn("[WARN] Specter does not seem to be running at {datafolder}")
    # Let's try to find the specter data folder
    home = str(Path.home())
    home = os.path.join(home, '.specter')
    typical_folders = [home, '/.specter',
                       '/mnt/hdd/mynode/specter', '/home/admin/.specter']
    for folder in typical_folders:
        # check if the file config.json is in this folder and has info
        json_file = os.path.join(folder, 'config.json')
        try:
            with open(json_file) as data_file:
                json_data = json.loads(data_file.read())
            if json_data['rpc']:
                current_app.specter_config = json_data
                current_app.settings['SPECTER']['specter_datafolder'] = folder
                update_config()
                return(True)
                break
        except Exception as e:
            pass
    return (False)


def specter_library_check():
    logging.info("Starting... Looking for Specter Library...")
    try:
        if current_app.settings['SPECTER']['specter_python'] != '':
            sys.path = sys.path + g.settings['SPECTER']['specter_python']
        from cryptoadvance.specter.specter import Specter
        from cryptoadvance.specter.config import DATA_FOLDER
        logging.info("\u001b[32mSuccess, found Specter Library...\u001b[0m")
    except Exception:
        logging.info("\u001b[33mCould not import Specter Library..." +
                     " Trying other paths.\u001b[0m")
        # MyNode stores these libraries at different path, will also try different
        # places
        found = False
        # list of paths to look for libraries recursively
        home = str(Path.home())
        path_list = ['/home/usr', '/usr/lib', '/usr/local', '/usr', home]
        for path_search in path_list:
            if found:
                break
            logging.debug(f"Looking into {path_search}...")
            try:
                result = list(Path(path_search).rglob("site-packages"))
                result.append(list(Path(path_search).rglob("dist-packages")))
            except Exception:
                result = []
            # Try to import
            for element in result:
                logging.debug(f"Trying to import from {element}...")
                sys.path.append(str(element))
                try:
                    from cryptoadvance.specter.specter import Specter
                    from cryptoadvance.specter.config import DATA_FOLDER
                    logging.debug("\u001b[32mSuccess, found Specter Library...\u001b[0m")
                    logging.debug(f"\u001b[32mon folder {str(element)}\u001b[0m")
                    found = True
                    # save this for later
                    current_app.settings['SPECTER']['specter_python'] = str(element)
                    update_config()
                    break
                except Exception:
                    pass
        if not found:
            print("--------------------------------------------------------------------")
            print("              SPECTER IS REQUIRED BUT NOT FOUND")
            print("--------------------------------------------------------------------")
            print(f" Could not find Specter Library installed. Are you sure ")
            print(f" Specter is installed in this computer? ")
            print(f" If it is, you can include the path for the Specter Python Library")
            print(f" at the warden/config.ini file.")
            print("--------------------------------------------------------------------")
            exit()
