from connections.connections import tor_request, url_parser
from bs4 import BeautifulSoup

SERVICES = [
    'Umbrel Dashboard', 'Ride the Lightning', 'Specter Server',
    'Samourai Server Dojo', 'Electrum Server', 'Electrum Server',
    'Bitcoin RPC Explorer', 'Mempool.space Explorer', 'BlueWallet Lightning',
    'WARden Server', 'Pi-Hole', 'VSCode Server', 'Gitea', 'Nextcloud',
    "Home Assistant"
]


def url_text(url):
    page = tor_request(url)
    try:
        txt = page.text
    except Exception:
        txt = None
    return (txt)


def autodetect(url):
    url = url_parser(url)
    request = tor_request(url)


# They should return (boolean, data)
def search_in_txt(txt, search_terms):
    if txt is None:
        return False
    found = True
    for term in search_terms:
        if term not in txt:
            found = False
    return (found)


# --------------------------------------------------------
# Start here the autodetect functions.
# They should return (boolean, data)
def autodetect(url):
    txt = url_text(url)

    # Detect Umbrel
    search_terms = ['<title>Umbrel</title>']
    if search_in_txt(txt, search_terms) is True:
        return ("Umbrel Dashboard")

    # Detect Specter Desktop
    search_terms = ['<title>Specter Desktop</title>']
    if search_in_txt(txt, search_terms) is True:
        return ("Specter Server")

    # Detect Mempool Space
    search_terms = ['<title>mempool - Bitcoin Explorer</title>']
    if search_in_txt(txt, search_terms) is True:
        return ("Mempool.space Explorer")

    # Detect WARden
    search_terms = ['Welcome to the WARDen']
    if search_in_txt(txt, search_terms) is True:
        return ("WARden Server")

    # None Found
    return ("Unknown Service")
