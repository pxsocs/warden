from yaspin import yaspin
import logging
import configparser
import os
import sys
import atexit
import warnings
import emoji
import requests
from logging.handlers import RotatingFileHandler
from packaging import version
from ansi.colour import fg
from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from pathlib import Path
from connections.connections import (internet_connected, get_local_host_name,
                                     runningInDocker,
                                     determine_docker_host_ip_address)
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_ERROR
from backend.ansi_management import (warning, success, error, info,
                                     clear_screen, muted, yellow, blue)


def create_app():
    # Load config file
    from backend.config import Config

    # Config of Logging
    formatter = "[%(asctime)s] {%(module)s:%(funcName)s:%(lineno)d} %(levelname)s in %(module)s: %(message)s"
    logging.basicConfig(handlers=[
        RotatingFileHandler(filename=str(Config.debug_file),
                            mode='w',
                            maxBytes=120000,
                            backupCount=0)
    ],
                        level=logging.INFO,
                        format=formatter,
                        datefmt='%m/%d/%Y %I:%M:%S %p')

    # Change some config messages Levels (to avoid excessive logging)
    logging.getLogger('apscheduler').setLevel(logging.CRITICAL)
    logging.getLogger('werkzeug').setLevel(logging.DEBUG)
    # Ignores warnings
    warnings.filterwarnings('ignore')

    # Launch app + set configs
    app = Flask(__name__)
    app.config.from_object(Config)
    logging.info("Flask App created successfully. Starting main program...")
    return app


def create_tor():
    from backend.ansi_management import (warning, success, error, info,
                                         clear_screen, bold, muted, yellow,
                                         blue)
    from backend.config import Config
    # ----------------------------------------------
    #                 Test Tor
    # ----------------------------------------------
    with yaspin(text="Testing Tor", color="cyan") as spinner:
        from connections.connections import test_tor
        tor = test_tor()
        if tor['status']:
            logging.info(success("Tor Available"))
            spinner.ok("✅ ")
            spinner.text = success("    Tor Available [Success]")
            print("")
            return (tor)
        else:
            logging.error(error("Could not connect to Tor"))
            spinner.fail("💥 ")
            spinner.text = warning("    Tor NOT available")
            print(error("    Could not connect to Tor network."))

            print(
                info(
                    "    [i] If you have a Tor Browser installed try opening (leave it running) and try again."
                ))

            print(
                info("    [i] If you are running Linux try the command: ") +
                yellow('service tor start'))
            print(
                info(
                    "    or download Tor at: https://www.torproject.org/download/"
                ))
            print(
                yellow("    [i] Application will launch without Tor support."))
            print("")
            return ('error')


def create_loginmanager(app):
    # Create instance of FLASK LOGIN Manager
    # --------------------------------------------
    # Database initiation
    table_error = False
    try:
        # create empty instance of LoginManager
        app.login_manager = LoginManager()
    except sqlite3.OperationalError:
        table_error = True
    #  There was an initial error on getting users
    #  probably because tables were not created yet.
    # The above create_all should have solved it so try again.
    if table_error:
        # create empty instance of LoginManager
        app.login_manager = LoginManager()
    # If login required - go to login:
    app.login_manager.login_view = "warden.login"
    # To display messages - info class (Bootstrap)
    app.login_manager.login_message_category = "secondary"
    app.login_manager.init_app(app)
    app.warden_status['loginmanager_initiated'] = True
    return (app)


def create_config(app):
    # Load config.ini into app
    # --------------------------------------------
    # Read Global Variables from warden.config(s)
    # Can be accessed as a dictionary like:
    # app.settings['PORTFOLIO']['RENEW_NAV']
    from backend.config import Config
    config_file = Config.config_file
    config_settings = configparser.ConfigParser()
    config_settings.read(config_file)
    app.settings = config_settings
    return (app)


def create_db(app):
    # Create instance of SQLAlchemy database
    # --------------------------------------------
    app.db = SQLAlchemy()
    app.db.init_app(app)
    # Import models so tables are created
    # It's important to import all models here even if not used.
    # Importing forces the creation of tables.
    from models.models import (Trades, User, AccountInfo, TickerInfo,
                               SpecterInfo, Allocation, RequestData)

    # Create all tables
    try:
        app.db.create_all()
    except Exception:
        pass
    app.warden_status['db_initiated'] = True
    return (app)


# ------------------------------------
# FLASK Application Factory
# ------------------------------------
def init_app(app):
    # Create an empty dict to store warden metadata
    # --------------------------------------------
    app.warden_status = {'username': None}

    # Check if running inside Docker container
    # --------------------------------------------
    app.runningInDocker = runningInDocker()
    if runningInDocker() is True:
        print(
            success(
                f"✅ Running inside docker container {emoji.emojize(':whale:')} Feeling some James Bartley vibes..."
            ))
        print("")

    # Load config.ini into app
    # --------------------------------------------
    app = create_config(app)
    app.app_context().push()

    # Create instance of FLASK LOGIN Manager
    # --------------------------------------------
    app = create_loginmanager(app)
    app.app_context().push()

    # Create instance of SQLAlchemy database
    # --------------------------------------------
    app = create_db(app)
    app.app_context().push()

    # Create empty instance of messagehandler
    # --------------------------------------------
    from connections.message_handler import MessageHandler
    app.message_handler = MessageHandler()
    app.message_handler.clean_all()
    app.app_context().push()

    # Checks if Cryptocompare is available and has valid API key
    # --------------------------------------------
    print("")
    check_cryptocompare()
    print("")

    # Check if there are any users on database.
    # If not, needs initial setup
    # --------------------------------------------
    from models.models import User
    users = User.query.all()
    if users == []:
        print("[i] No users found. Running initial setup.")
        app.warden_status['initial_setup'] = True

    # Get WARden App Version - check for upgrade
    # --------------------------------------------
    app = check_version(app)
    app.app_context().push()

    # Check if the provided port at config.ini is available
    # If not, switch to an available port
    # --------------------------------------------
    from connections.connections import find_usable_port
    port = app.settings['SERVER'].getint('port')
    app = find_usable_port(port, app)
    app.app_context().push()

    # TOR Server through Onion Address --
    # USE WITH CAUTION - ONION ADDRESSES CAN BE EXPOSED!
    # An exposed onion address means outside users can connect to
    # the app remotely
    # --------------------------------------------
    if app.settings['SERVER'].getboolean('onion_server'):
        launch_hidden_services(app)

    # Prepare Flask Blueprints & Register
    # --------------------------------------------
    app = register_blueprints(app)
    app.app_context().push()

    # Create Flask App
    # Get FX information into application configuration
    default_fx = app.settings['PORTFOLIO']['base_fx']
    from backend.utils import fxsymbol
    app.fx = app.fx = fxsymbol(default_fx, 'all')
    app.app_context().push()

    # Specter Server Setup
    # Prepare app to receive Specter Server info
    # For the first load, just get a saved file if available
    # The background jobs will update later
    # --------------------------------------------
    from specter.specter_importer import Specter
    app.specter = Specter()
    app.specter.refresh_txs(load=True)
    # Sets downloading status to false
    app.warden_status['downloading_specter_txs'] = False
    app.app_context().push()

    # Test Tor and store status
    # --------------------------------------------
    app.tor = create_tor()
    app.app_context().push()

    # Launch Background Jobs
    # --------------------------------------------
    app = create_background_jobs(app)
    app.app_context().push()
    app.scheduler.start()
    app.warden_status['scheduler_initiated'] = True
    print("")
    print(success("✅ Background jobs running"))

    # Finished Application Factory Method - return application
    # --------------------------------------------
    print("")
    print(success("✅ Application Factory successfully assembled app"))
    return app


def create_background_jobs(app):
    # Start Schedulers and Background Jobs
    # --------------------------------------------
    from backend.backgroundjobs import (background_settings_update,
                                        background_scan_network)
    from backend.backgroundjobs_node import (update_nodes, get_nodes_status,
                                             check_tip_heights)
    from connections.mempoolspace import node_searcher

    app.scheduler = BackgroundScheduler()

    app.scheduler.add_job(background_settings_update,
                          'interval',
                          args=[app],
                          seconds=1,
                          max_instances=1)

    app.scheduler.add_job(background_scan_network,
                          'interval',
                          args=[app],
                          seconds=1,
                          max_instances=1)

    app.scheduler.add_job(check_tip_heights,
                          'interval',
                          args=[app],
                          seconds=5,
                          max_instances=1)

    app.scheduler.add_job(update_nodes,
                          'interval',
                          args=[app],
                          seconds=5,
                          max_instances=1)

    app.scheduler.add_job(get_nodes_status,
                          'interval',
                          args=[app],
                          seconds=5,
                          max_instances=1)

    app.scheduler.add_job(node_searcher,
                          'interval',
                          args=[True],
                          seconds=120,
                          max_instances=1)

    # Add listener to catch errors on background jobs
    def listener(event):
        logging.info(
            error(
                f'Job {event.job_id} raised {event.exception.__class__.__name__}'
            ))
        logging.info(error(f'Job {event.job_id} raised {event.exception}'))
        logging.info(error(f'Job {event.job_id} raised {event.traceback}'))

    # Start listener
    app.scheduler.add_listener(listener, EVENT_JOB_ERROR)

    from connections.mempoolspace import get_max_height
    with app.app_context():
        get_max_height()

    return (app)


def register_blueprints(app):
    from routes.routes import warden
    from routes.errors.handlers import errors
    from routes.api.routes import api
    from routes.csv.routes import csv_routes
    from routes.user.routes import user_routes
    app.register_blueprint(warden)
    app.register_blueprint(errors)
    app.register_blueprint(api)
    app.register_blueprint(csv_routes)
    app.register_blueprint(user_routes)
    from routes.jinja_filters import jinja_filters
    app.register_blueprint(jinja_filters)
    # Orangenomics Blueprint
    from routes.orangenomics.main import orangenomics
    app.register_blueprint(orangenomics)
    # HODL Analysis Blueprint
    from routes.HODL_analysis.HODL_analysis import hodl_analysis
    app.register_blueprint(hodl_analysis)
    # Node Managements Blueprint
    from routes.node_management.node_management import node_management
    from routes.node_management.sockets import sockets
    app.register_blueprint(node_management)
    app.register_blueprint(sockets)
    return app


def launch_hidden_services(app):
    from stem.control import Controller
    from urllib.parse import urlparse
    app.tor_port = app.settings['SERVER'].getint('onion_port')
    app.port = app.settings['SERVER'].getint('port')
    from backend.config import home_dir
    toraddr_file = os.path.join(home_dir, "onion.txt")
    app.save_tor_address_to = toraddr_file
    proxy_url = "socks5h://localhost:9050"
    tor_control_port = ""
    try:
        tor_control_address = urlparse(proxy_url).netloc.split(":")[0]
        if tor_control_address == "localhost":
            tor_control_address = "127.0.0.1"
        app.controller = Controller.from_port(
            address=tor_control_address,
            port=int(tor_control_port) if tor_control_port else "default",
        )
    except Exception:
        app.controller = None
    from connections.tor import start_hidden_service
    start_hidden_service(app)
    return app


def check_version(app):
    from backend.config import Config
    from connections.connections import tor_request
    print("")
    # Load version from local version file
    try:
        version_file = Config.version_file
        with open(version_file, 'r') as file:
            current_version = file.read().replace('\n', '')
    except Exception:
        # Version file does not exist - could be an older version
        current_version = '** UNKNOWN **'
    with app.app_context():
        app.version = current_version

    print(f"[i] Running WARden version: {current_version}")
    app.warden_status['running_version'] = current_version

    # CHECK FOR UPGRADE at GitHub
    repo_url = 'https://api.github.com/repos/pxsocs/warden/releases'
    try:
        github_version = tor_request(repo_url).json()[0]['tag_name']
        print(f"[i] Latest version available at GitHub: {github_version}")
        parsed_github = version.parse(github_version)
        parsed_version = version.parse(current_version)
        app.warden_status['needs_upgrade'] = False
        if parsed_github > parsed_version:
            print(warning("[i] Upgrade Available"))
            app.warden_status['needs_upgrade'] = True
        if parsed_github == parsed_version:
            print(success("[ok] You are running the latest version"))
        else:
            print(
                success(
                    "[i] The Local Version is newer than the remote version."))

    except Exception as e:
        # Could not retrieve github version
        github_version = f"[!] GitHub version. Error: {str(e)}"
        print(warning("[!] Could not check GitHub for updates"))
        print(github_version)

    app.warden_status['github_version'] = github_version

    return app


def check_cryptocompare():
    from backend.utils import pickle_it

    with yaspin(text="Testing price grab from Cryptocompare",
                color="green") as spinner:
        data = {'Response': 'Error', 'Message': None}
        try:
            api_key = pickle_it('load', 'cryptocompare_api.pkl')
            if api_key != 'file not found':
                baseURL = (
                    "https://min-api.cryptocompare.com/data/pricemultifull?fsyms=BTC"
                    + "&tsyms=USD&api_key=" + api_key)
                req = requests.get(baseURL)
                data = req.json()
                btc_price = (data['DISPLAY']['BTC']['USD']['PRICE'])
                spinner.text = (success(f"BTC price is: {btc_price}"))
                spinner.ok("✅ ")
                pickle_it('save', 'cryptocompare_api.pkl', api_key)
                return
            else:
                data = {'Response': 'Error', 'Message': 'No API Key is set'}
        except Exception as e:
            data = {'Response': 'Error', 'Message': str(e)}
            logging.error(data)

        try:
            if data['Response'] == 'Error':
                spinner.color = 'yellow'
                spinner.text = "CryptoCompare Returned an error " + data[
                    'Message']
                # ++++++++++++++++++++++++++
                #  Load Legacy API Key
                # ++++++++++++++++++++++++++
                try:
                    # Let's try to use one of the
                    # legacy api keys stored under
                    # cryptocompare_api.keys file
                    # You can add as many as you'd like there
                    filename = 'warden/static/cryptocompare_api.keys'
                    file = open(filename, 'r')
                    for line in file:
                        legacy_key = str(line)

                        spinner.text = (
                            warning(f"Trying different API Keys..."))

                        baseURL = (
                            "https://min-api.cryptocompare.com/data/pricemultifull?fsyms=BTC"
                            + "&tsyms=USD&api_key=" + legacy_key)

                        try:
                            data = None
                            logging.debug(f"Trying API Key {legacy_key}")
                            request = requests.get(baseURL)
                            data = request.json()
                            btc_price = (
                                data['DISPLAY']['BTC']['USD']['PRICE'])
                            spinner.text = (
                                success(f"BTC price is: {btc_price}"))
                            spinner.ok("✅ ")
                            logging.debug(f"API Key {legacy_key} Success")
                            pickle_it('save', 'cryptocompare_api.pkl',
                                      legacy_key)
                            return
                        except Exception as e:
                            logging.debug(f"API Key {legacy_key} ERROR: {e}")
                            logging.debug(
                                f"API Key {legacy_key} Returned: {data}")
                            spinner.text = "Didn't work... Trying another."
                except Exception:
                    pass
                spinner.text = (error("Failed to get API Key - read below."))
                spinner.fail("[!]")
                print(
                    '    -----------------------------------------------------------------'
                )
                print(yellow("    Looks like you need to get an API Key. "))
                print(yellow("    The WARden comes with a shared key that"))
                print(yellow("    eventually gets to the call limit."))
                print(
                    '    -----------------------------------------------------------------'
                )
                print(
                    yellow(
                        '    Go to: https://www.cryptocompare.com/cryptopian/api-keys'
                    ))
                print(
                    yellow(
                        '    To get an API Key. Keys from cryptocompare are free.'
                    ))
                print(
                    yellow(
                        '    [Tip] Get a disposable email to signup and protect privacy.'
                    ))
                print(
                    yellow(
                        '    Services like https://temp-mail.org/en/ work well.'
                    ))

                print(muted("    Current API:"))
                print(f"    {api_key}")
                new_key = input('    Enter new API key (Q to quit): ')
                if new_key == 'Q' or new_key == 'q':
                    exit()
                pickle_it('save', 'cryptocompare_api.pkl', new_key)
                check_cryptocompare()
        except KeyError:
            try:
                btc_price = (data['DISPLAY']['BTC']['USD']['PRICE'])
                spinner.ok("✅ ")
                spinner.write(success(f"BTC price is: {btc_price}"))
                pickle_it('save', 'cryptocompare_api.pkl', api_key)
                return
            except Exception:
                spinner.text = (
                    warning("CryptoCompare Returned an UNKNOWN error"))
                spinner.fail("💥 ")
        return (data)


# Stop running threads before exiting
# Perform clean up of files
def close_running_threads(app):
    print("")
    print("")
    print(yellow("[i] Please Wait... Shutting down."))
    # Delete Debug File
    try:
        from backend.config import Config
        os.remove(Config.debug_file)
    except FileNotFoundError:
        pass
    # Clean all messages
    app.message_handler.clean_all()
    # Breaks background jobs
    app.scheduler.shutdown(wait=False)
    from ansi_messages import goodbye

    # Stop Onion hidden services if running
    if app.settings['SERVER'].getboolean('onion_server'):
        from connections.tor import stop_hidden_services
        stop_hidden_services(app)

    goodbye()
    os._exit(1)


# Prints Onion Address
def onion_string(app):
    from backend.utils import pickle_it
    if app.settings['SERVER'].getboolean('onion_server'):
        try:
            pickle_it('save', 'onion_address.pkl',
                      app.tor_service_id + '.onion')
            return (f"""
    {emoji.emojize(':onion:')} Tor Onion server running at:
    {yellow(app.tor_service_id + '.onion')}
                """)
        except Exception:
            return (yellow("[!] Tor Onion Server Not Running"))
    else:
        return ('')


# Prints Local Network Address
def local_network_string(app):
    from connections.connections import get_local_ip
    host = app.settings['SERVER'].get('host')
    port = str(app.settings['SERVER'].getint('port'))
    if app.runningInDocker is True:
        return (f"""
        Or through your network at address:
        {yellow('http://')}{yellow(determine_docker_host_ip_address())}{yellow(f':{port}/')}
                """)
    else:
        if host == '0.0.0.0':
            return (f"""
        Or through your network at address:
        {yellow('http://')}{yellow(get_local_ip())}{yellow(f':{port}/')}
                """)


def main(debug, reloader):
    # Make sure current libraries are found in path
    current_path = os.path.abspath(os.path.dirname(__file__))
    sys.path.append(current_path)
    from backend.config import basedir
    sys.path.append(basedir)

    # Welcome Message
    print("")
    print("")
    print(success("[i] Welcome to the WARden <> Launching Application ..."))
    print("")

    # Check for internet connection- Crucial Check
    internet_ok = internet_connected()
    if internet_ok is True:
        print(success("✅ Internet Connected"))
    else:
        print(
            error(
                "[!] WARden needs an internet connection to run. Check your connection."
            ))
        print(warning("[!] Exiting"))
        exit()

    # Create the Flask Application
    app = create_app()
    app.app_context().push()

    # Initializes the Flask Application
    # this creates instances of Flask methods and
    # attaches them to the application
    app = init_app(app)
    app.app_context().push()

    # Register the closing method to run at close
    atexit.register(close_running_threads, app)

    # Ready to launch application
    print("")
    print(success("✅ WARden Server is Ready..."))
    print("")
    logging.info("[OK] Launched WARden Server")

    # Gets current Port
    port = app.settings['SERVER'].getint('port')

    # Get current host name
    hostname = get_local_host_name()

    print(
        fg.brightgreen("""
        _   _           __        ___    ____     _
       | |_| |__   ___  \ \      / / \  |  _ \ __| | ___ _ __
       | __| '_ \ / _ \  \ \ /\ / / _ \ | |_) / _` |/ _ \ '_  |
       | |_| | | |  __/   \ V  V / ___ \|  _ < (_| |  __/ | | |
        \__|_| |_|\___|    \_/\_/_/   \_\_| \_\__,_|\___|_| |_|"""))

    print(f"""
                                    {yellow("Powered by NgU technology")} {emoji.emojize(':rocket:')}


                    Privacy Focused Portfolio App
    -----------------------------------------------------------------
                          Application Loaded

      Open your browser and navigate to one of these addresses:
      {yellow('http://localhost:' + str(port) + '/')}
      {yellow('http://127.0.0.1:' + str(port) + '/')}
    {local_network_string(app)}
    {yellow(f'http://{hostname}.local:' + str(port) + '/')}
    {onion_string(app)}
    ----------------------------------------------------------------
                         CTRL + C to quit server
    ----------------------------------------------------------------

    """)

    # Try to launch webbrowser and open the url
    # Ignored on Debug mode to avoid opening several browser windows
    try:
        import webbrowser
        if debug is False:
            pass
            # webbrowser.open('http://localhost:' + str(port) + '/')
    except Exception:
        pass

    # Check if running in docker and change hostname to docker's IP address
    if app.runningInDocker is True:
        host_IP = determine_docker_host_ip_address()
    else:
        host_IP = app.settings['SERVER'].get('host')

    # Launch the Flask Webserver
    app.run(debug=debug,
            threaded=True,
            host=host_IP,
            port=port,
            use_reloader=reloader)
