# Imports go here
from pathlib import Path
import os
import socket

from utils import pickle_it
from message_handler import MessageHandler, Message


# WARden diagnostics and health methods
# All checks will run here and save to ~/warden/diags/
# folder as pickle files that can be retrieved from
# different parts of the application later
# Check if folder exists, if not create
def create_diags_path():
    home = str(Path.home())
    diags_path = os.path.join(home, 'ward/diags/')
    try:
        os.makedirs(os.path.dirname(diags_path))
    except Exception:
        pass


# Checks for internet conection [7]
# Saved to: internet_connected.pkl
# Returns: True / False
def internet_connected(host="8.8.8.8", port=53, timeout=3):
    """
    Host: 8.8.8.8 (google-public-dns-a.google.com)
    OpenPort: 53/tcp
    Service: domain (DNS/TCP)
    """
    connected = False
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        connected = True
    except socket.error as ex:
        connected = False
    pickle_it('save', 'diags/internet_connected.pkl', connected)
    return(connected)

# Checks if ever setup


def first_run():
    pass

# CHECKS ON PORTFOLIO


def portfolio_is_empty():
    pass


# Sends a critical alert to web pages
# These can be HTML formatted
def critical_alert(message):
    pass


def full_diags():
    msg_handler = MessageHandler()
    message = Message(category='Full Diagnosis',
                      message_txt=f"<span class='text-info'>Kicking off full diagnostic</span>")
    msg_handler.add_message(message)

    # Check if the diags path was ever created
    # if not, create
    create_diags_path()

    # Is internet running
    is_connected = internet_connected()
    if is_connected is False:
        critical_alert(
            "<span class='text-danger'>No Internet Connection</span>")


"""
Notes - these are checks that need to be implemented (in no specific order) + their dependency list
1. Check if portfolio exists [Critical]
2. Check if portfolio is not empty [Critical]
3. Check if Tor is running [Critical but give a warning]
4. Check if Specter is running [Not Critical]
5. Check pricing feeds & API Keys [Critical]
6. Check if config.ini was created [Check and create if not]
7. Check for internet connection [Critical] [If not, can proceed but use pickles]
8. Check if users in database [If not, demo mode]
9. Check for upgrade [Upgrade & restart & install libraries (10)]
10. Check for libraries (First time & upgrade)
11. Check if running Onion hidden Server 
12. Check for Nodes, services and health
12. a. Check if nodes are synched; b. check latest block hash and compare
13. Check if running inside Docker
14. Check if Mempool.space is running locally at some service
15. Check for wallet activity
16. Check if can authenticate and Download Txs. from Specter 
17. Check if an NAV was created
18. Check if enough historical data to generate NAV
19. Check if database is present (warden.db)
20. Check use counter
21. Check for price alerts
22. Check if running in debug mode
23. Check if running inside MacOs, Linux, etc
24. If inside Raspberry Pi - check temperature, voltage, CPU Usage, Memory, Storage
25. Check users logged in. Alert of any new SSH into this computer.
26. Check if bitcoin-cli running and try to get wallet info / balances
27. Check when a block was last found - alert new block
"""
