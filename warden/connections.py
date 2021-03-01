import urllib
import requests
from time import time
from warden_decorators import MWT


@MWT(timeout=1)
def test_tor():
    url = "http://httpbin.org/ip"
    response = {}
    session = requests.session()

    try:
        time_before = time()  # Save Ping time to compare
        r = session.get(url)
        time_after = time()
        pre_proxy_ping = time_after - time_before
        pre_proxy = r.json()
    except Exception as e:
        pre_proxy = pre_proxy_ping = "Connection Error: " + str(e)

    PORTS = ['9050', '9150']

    # Activate TOR proxies
    for PORT in PORTS:
        session.proxies = {
            "http": "socks5h://0.0.0.0:" + PORT,
            "https": "socks5h://0.0.0.0:" + PORT,
        }
        try:
            failed = False
            time_before = time()  # Save Ping time to compare
            r = session.get(url)
            time_after = time()
            post_proxy_ping = time_after - time_before
            post_proxy_difference = post_proxy_ping / pre_proxy_ping
            post_proxy = r.json()

            if pre_proxy["origin"] != post_proxy["origin"]:
                response = {
                    "pre_proxy": pre_proxy,
                    "post_proxy": post_proxy,
                    "post_proxy_ping": "{0:.2f} seconds".format(post_proxy_ping),
                    "pre_proxy_ping": "{0:.2f} seconds".format(pre_proxy_ping),
                    "difference": "{0:.2f}".format(post_proxy_difference),
                    "status": True,
                    "port": PORT,
                    "url": url,
                }
                session.close()
                return response
        except Exception as e:
            failed = True
            post_proxy_ping = post_proxy = "Failed checking TOR status. Error: " + str(
                e)

        if not failed:
            break

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


@MWT(timeout=5)
def tor_request(url, tor_only=True, method="get", payload=None):
    # Tor requests takes arguments:
    # url:       url to get or post
    # tor_only:  request will only be executed if tor is available
    # method:    'get or' 'post'
    global TOR
    tor_check = TOR
    url = urllib.parse.urlparse(url).geturl()
    session = requests.session()

    if tor_check["status"] is True:
        try:
            # Activate TOR proxies
            session.proxies = {
                "http": "socks5h://0.0.0.0:" + TOR['port'],
                "https": "socks5h://0.0.0.0:" + TOR['port'],
            }

            if method == "get":
                request = session.get(url, timeout=60)
            if method == "post":
                request = session.post(url, timeout=60, data=payload)

        except (
                requests.exceptions.ConnectionError,
                requests.exceptions.ReadTimeout,
        ):
            session.close()
            return "ConnectionError"
    else:
        if tor_only:
            return "Tor not available"
        try:
            if method == "get":
                request = requests.get(url, timeout=30)
            if method == "post":
                request = requests.post(url, timeout=30, data=payload)

        except requests.exceptions.ConnectionError:
            session.close()
            return "ConnectionError"

    session.close()
    return request
