import urllib
import requests
import logging
from time import time
import socket
from datetime import datetime
from utils import load_config, pickle_it


def test_tor():
    response = {}
    session = requests.session()
    try:
        time_before = time()  # Save Ping time to compare
        r = session.get("https://api.myip.com")
        time_after = time()
        pre_proxy_ping = time_after - time_before
        pre_proxy = r.json()
    except Exception as e:
        pre_proxy = pre_proxy_ping = "Connection Error: " + str(e)

    PORTS = ['9050', '9150']

    # Activate TOR proxies
    for PORT in PORTS:
        session.proxies = {
            "http": "socks5h://localhost:" + PORT,
            "https": "socks5h://localhost:" + PORT,
        }
        try:
            failed = False
            time_before = time()  # Save Ping time to compare
            r = session.get("https://api.myip.com")
            time_after = time()
            post_proxy_ping = time_after - time_before
            post_proxy_ratio = post_proxy_ping / pre_proxy_ping
            post_proxy = r.json()

            if pre_proxy["ip"] != post_proxy["ip"]:
                response = {
                    "pre_proxy": pre_proxy,
                    "post_proxy": post_proxy,
                    "post_proxy_ping":
                    "{0:.2f} seconds".format(post_proxy_ping),
                    "pre_proxy_ping": "{0:.2f} seconds".format(pre_proxy_ping),
                    "difference": "{0:.2f}".format(post_proxy_ratio),
                    "status": True,
                    "port": PORT,
                    "last_refresh": datetime.now().strftime('%d-%b-%Y %H:%M:%S')
                }
                pickle_it('save', 'tor.pkl', response)
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
        "last_refresh": None,
    }

    pickle_it('save', 'tor.pkl', response)
    return response


def tor_request(url, tor_only=False, method="get", headers=None):
    # Tor requests takes arguments:
    # url:       url to get or post
    # tor_only:  request will only be executed if tor is available
    # method:    'get or' 'post'
    # Store TOR Status here to avoid having to check on all http requests
    if not 'http' in url:
        url = 'http://' + url 
    TOR = pickle_it('load', 'tor.pkl')
    if TOR == 'file not found':
        TOR = {
            "status": False,
            "port": "failed",
            "last_refresh": None,
        }
    if '.local' in url:
        try:
            if method == "get":
                request = requests.get(url, timeout=20)
            if method == "post":
                request = requests.post(url, timeout=20)
            return (request)

        except requests.exceptions.ConnectionError:
            return "ConnectionError"

    if TOR["status"] is True:
        try:
            # Activate TOR proxies
            session = requests.session()
            session.proxies = {
                "http": "socks5h://localhost:" + TOR['port'],
                "https": "socks5h://localhost:" + TOR['port'],
            }
            if method == "get":
                if headers:
                    request = session.get(url, timeout=20, headers=headers)
                else:
                    request = session.get(url, timeout=20)
            if method == "post":
                request = session.post(url, timeout=20)

        except (
                requests.exceptions.ConnectionError,
                requests.exceptions.ReadTimeout,
        ):
            return "ConnectionError"
    else:
        if tor_only:
            return "Tor not available"
        try:
            if method == "get":
                request = requests.get(url, timeout=10)
            if method == "post":
                request = requests.post(url, timeout=10)

        except requests.exceptions.ConnectionError:
            return "ConnectionError"

    return request


# Check Local Network for nodes and services
# Need to optimize this to run several threads instead of sequentially
def scan_network():
    logging.info("Scanning Network for services...")

    # Add WARden to services
    onion = pickle_it('load', 'onion_address.pkl')
    local_ip = pickle_it('load', 'local_ip_address.pkl')

    host_list = [
        'umbrel.local', 'mynode.local', 'raspberrypi.local', 'ronindojo.local',
        'raspberrypi-2.local', 'umbrel-2.local', 'umbrel-3.local', '127.0.0.1', 
        onion, local_ip
    ]

    # try to Load history of nodes reached
    hosts_found = pickle_it('load', 'hosts_found.pkl')

    if hosts_found == 'file not found' or not isinstance(hosts_found, dict):
        hosts_found = {}

    just_found = []
    # First check which nodes receive a ping
    for host in host_list:
        try:
            if 'onion' in host:
                request = tor_request(host)                    
                utc_time = datetime.utcnow()
                epoch_time = (utc_time - datetime(1970, 1, 1)).total_seconds()
                if request.ok is True:
                    hosts_found[host] = {
                        'ip': host,
                        'host': host,
                        'last_time': epoch_time
                    }
                    just_found.append((host, host))

            else:
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
                 (3008, 'BlueWallet Lightning'),
                 (5000, 'WARden Server')]

    # Additional Services (from Umbrel mostly - add this later)
    # (8082, 'Pi-Hole'),
    # (8091, 'VSCode Server'),
    # (8085, 'Gitea'),
    # (8081, 'Nextcloud'),
    # (8083, "Home Assistant")

    # try to Load history of services reached
    services_found = pickle_it('load', 'services_found.pkl')

    if services_found == 'file not found' or not isinstance(services_found, list):
        services_found = []

    for host in just_found:
        if 'onion' in host:
            utc_time = datetime.utcnow()
            epoch_time = (utc_time - datetime(1970, 1, 1)).total_seconds()
            url = 'http://' + host[0] + '/'

            # Remove old instances 
            for item in services_found:
                tmp_url = 'http://' + item[0][0] + '/'
                if tmp_url == url:
                    services_found.remove(item)

            services_found.append([host, ('Onion Address', 'Onion Address'), epoch_time])


        else:
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

                    # remove old instance and replace with new one
                    for item in services_found:
                        tmp_url = 'http://' + item[0][0] + ':' + str(int(item[1][0])) + '/'
                        if tmp_url == url:
                            services_found.remove(item)

                    services_found.append([host, port, epoch_time])
                    logging.info(f"Found Service at {host}:{port}")
                except Exception as e:
                    logging.error(f"Error importing service {port[1]}: {e}")

    pickle_it('save', 'services_found.pkl', services_found)
    # Sample File format saved to services_found
    # [(('umbrel.local', '192.168.1.124', utc_now()), ...]
    logging.info('Running Services saved under pickle...')

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
