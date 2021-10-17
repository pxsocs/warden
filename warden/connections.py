import urllib
import requests
import logging
from time import time
import socket
from datetime import datetime
from utils import load_config, pickle_it


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


# Check Local Network for nodes and services
# Need to optimize this to run several threads instead of sequentially
def scan_network():
    logging.info("Scanning Network for services...")
    host_list = [
        'umbrel.local', 'mynode.local', 'raspberrypi.local', 'ronindojo.local',
        'raspberrypi-2.local', 'umbrel-2.local', 'umbrel-3.local', '127.0.0.1'
    ]

    # try to Load history of nodes reached
    hosts_found = pickle_it('load', 'hosts_found.pkl')

    if hosts_found == 'file not found' or not isinstance(hosts_found, dict):
        hosts_found = {}

    just_found = []
    # First check which nodes receive a ping
    for host in host_list:
        try:
            host_ip = socket.gethostbyname(host)
            utc_time = datetime.utcnow()
            epoch_time = (utc_time - datetime(1970, 1, 1)).total_seconds()
            hosts_found[str(host_ip)] = {
                'ip': host_ip,
                'host': host,
                'last_time': epoch_time
            }
            just_found.append((host, host_ip))
            logging.info(f"Found Host at {host} // {host_ip} // {datetime.utcnow()}")
        except Exception as e:
            logging.error(f"Error importing host {host}: {e}")

    pickle_it('save', 'hosts_found.pkl', hosts_found)
    # Sample File format saved:
    # {'192.168.1.124': {
    #            'ip': '192.168.1.124',
    #            'host': 'umbrel.local',
    #            'last_time': timestamp(datetime.utcnow())
    #        }
    # }
    # Now try to reach typical services
    port_list = [(80, 'Web Server'), (3010, 'Ride the Lightning'),
                 (25441, 'Specter Server'), (3005, 'Samourai Server Dojo'),
                 (50001, 'Electrum Server'), (50002, 'Electrum Server'),
                 (3002, 'Bitcoin RPC Explorer'),
                 (3006, 'Mempool.space Explorer'),
                 (3008, 'BlueWallet Lightning')]

    # Additional Services (from Umbrel mostly - add this later)
    # (8082, 'Pi-Hole'),
    # (8091, 'VSCode Server'),
    # (8085, 'Gitea'),
    # (8081, 'Nextcloud'),
    # (8083, "Home Assistant")

    services_found = []
    for host in just_found:
        for port in port_list:
            try:
                url = 'http://' + host[0] + ':' + str(int(port[0])) + '/'
                result = tor_request(url)
                if not isinstance(result, requests.models.Response):
                    # Let's try https (some services use one or the other)
                    url = 'https://' + host[0] + ':' + str(int(port[0])) + '/'
                    result = tor_request(url)
                    if not isinstance(result, requests.models.Response):
                        raise Exception(f'Did not get a return from {url}')
                if not result.ok:
                    raise Exception(
                        'Reached URL but did not get a code 200 [ok]')

                utc_time = datetime.utcnow()
                epoch_time = (utc_time - datetime(1970, 1, 1)).total_seconds()

                services_found.append([host, port, epoch_time])
                logging.info(f"Found Service at {host}:{port}")
            except Exception as e:
                logging.error(f"Error importing service {port[1]}: {e}")

    pickle_it('save', 'services_found.pkl', services_found)
    # Sample File format saved to services_found
    # [(('umbrel.local', '192.168.1.124', utc_now()), ...]
    logging.info('Running Services saved under pickles...')

    return (services_found)


def is_service_running(service):
    from utils import pickle_it
    services = pickle_it('load', 'services_found.pkl')
    found = False
    meta = []
    if services != 'file not found' and services is not None:
        for data in services:
            if service in data[1][1]:
                found = True
                meta.append(data)
    # Sample data return format
    # (True,
    #  [(('umbrel.local', '192.168.1.124'), (3002, 'Bitcoin RPC Explorer')),
    #   (('umbrel.local', '192.168.1.124'), (3006, 'Mempool.space Explorer'))])
    return (found, meta)
