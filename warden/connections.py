import urllib
import requests
import logging
from time import time
from warden_decorators import MWT
from utils import load_config


def test_tor():
    url = "http://httpbin.org/ip"
    response = {}
    session = requests.session()
    if load_config().has_option('TOR', 'port'):
        tor_port = load_config()['TOR']['port']
    else:
        tor_port = 9050

    try:
        time_before = time()  # Save Ping time to compare
        r = session.get(url)
        time_after = time()
        pre_proxy_ping = time_after - time_before
        pre_proxy = r.json()
    except Exception as e:
        pre_proxy = pre_proxy_ping = "Connection Error: " + str(e)

    # Activate TOR proxies
    session.proxies = {
        "http": "socks5h://0.0.0.0:" + str(tor_port),
        "https": "socks5h://0.0.0.0:" + str(tor_port),
    }
    try:
        time_before = time()  # Save Ping time to compare
        r = session.get(url)
        time_after = time()
        post_proxy_ping = time_after - time_before
        post_proxy_difference = post_proxy_ping / pre_proxy_ping
        post_proxy = r.json()
        session.close()

        if pre_proxy["origin"] != post_proxy["origin"]:
            response = {
                "pre_proxy": pre_proxy,
                "post_proxy": post_proxy,
                "post_proxy_ping": "{0:.2f} seconds".format(post_proxy_ping),
                "pre_proxy_ping": "{0:.2f} seconds".format(pre_proxy_ping),
                "difference": "{0:.2f}".format(post_proxy_difference),
                "status": True,
                "port": tor_port,
                "url": url,
            }
            return response
    except Exception as e:
        post_proxy_ping = post_proxy = "Failed checking TOR status. Error: " + str(
            e)

    response = {
        "pre_proxy": pre_proxy,
        "post_proxy": post_proxy,
        "post_proxy_ping": post_proxy_ping,
        "pre_proxy_ping": pre_proxy_ping,
        "difference": "-",
        "status": False,
        "port": "failed",
        "url": url
    }
    session.close()
    return response


def tor_request(url, tor_only=False, method="get", payload=None):
    # Tor requests takes arguments:
    # url:       url to get or post
    # tor_only:  request will only be executed if tor is available
    # method:    'get or' 'post'
    if load_config().has_option('TOR', 'port'):
        tor_port = load_config()['TOR']['port']
    else:
        tor_port = 9050

    url = urllib.parse.urlparse(url).geturl()
    session = requests.session()

    try:
        # Activate TOR proxies
        session.proxies = {
            "http": "socks5h://0.0.0.0:" + str(tor_port),
            "https": "socks5h://0.0.0.0:" + str(tor_port),
        }

        if method == "get":
            request = session.get(url, timeout=60)
        if method == "post":
            request = session.post(url, timeout=60, data=payload)
        session.close()

    except Exception:

        if tor_only:
            return "Tor not available"

        if method == "get":
            request = requests.get(url, timeout=30)
        if method == "post":
            request = requests.post(url, timeout=30, data=payload)

        logging.warning(f'OpenNet Request (Tor could not be used) url: {url}')

    return request
