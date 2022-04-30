import urllib
import requests
import logging
from time import time
import socket
from datetime import datetime
from utils import load_config, pickle_it
import concurrent.futures
from concurrent.futures import wait, ALL_COMPLETED


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
                    "last_refresh":
                    datetime.now().strftime('%d-%b-%Y %H:%M:%S')
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
    session.close()
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

    # Do not use Tor for Local Network requests
    if '.local' in url or '127.0.0.1' in url or 'localhost' in url:
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
                    request = session.get(url,
                                          timeout=20,
                                          headers=headers,
                                          verify=False)
                else:
                    request = session.get(url, timeout=20, verify=False)
            if method == "post":
                request = session.post(url, timeout=20, verify=False)

            session.close()
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
def scan_network():
    # !!!!!!!!!!! Important
    # Need to include a check for added onion addresses. Particularly
    # for Speter Server included as an onion address. After that is verified
    # will need to save that specter server details in a file and later load it.

    # Add WARden to services
    onion = pickle_it('load', 'onion_address.pkl')
    local_ip = pickle_it('load', 'local_ip_address.pkl')

    host_list = [
        'umbrel.local', 'mynode.local', 'raspberrypi.local', 'ronindojo.local',
        'raspberrypi-2.local', 'umbrel-2.local', 'umbrel-3.local', '127.0.0.1',
        onion, local_ip
    ]

    just_found = []
    # Add any host not on list above but saved on hosts_found
    # This ensures that added hosts will be searched
    hosts_found = pickle_it('load', 'hosts_found.pkl')
    for host, value in hosts_found.items():
        if value['host'] not in host_list:
            host_list.append(value['host'])
            just_found.append(value['host'])

    def check_host(host):
        # try to Load history of nodes reached
        host_found = {}
        try:
            if 'onion' in host:
                request = tor_request(host)
                if not request.ok:
                    raise Exception
                utc_time = datetime.utcnow()
                epoch_time = (utc_time - datetime(1970, 1, 1)).total_seconds()
                if request.ok is True:
                    host_found[host] = {
                        'ip': host,
                        'host': host,
                        'last_time': epoch_time
                    }
            else:
                host_ip = socket.gethostbyname(host)
                utc_time = datetime.utcnow()
                epoch_time = (utc_time - datetime(1970, 1, 1)).total_seconds()
                host_found[str(host_ip)] = {
                    'ip': host_ip,
                    'host': host,
                    'last_time': epoch_time
                }
            just_found.append(host)
            return (host_found)
        except Exception as e:
            return None

    # Launch thread to check hosts
    with concurrent.futures.ThreadPoolExecutor(20) as executor:
        futures = [executor.submit(check_host, args) for args in host_list]
        wait(futures, timeout=120, return_when=ALL_COMPLETED)
        hosts_found = {}
        for element in futures:
            if isinstance(element.result(), dict):
                hosts_found = {**hosts_found, **element.result()}
        pickle_it('save', 'hosts_found.pkl', hosts_found)
        # Sample return:
        # {
        # '192.168.15.8': {'ip': '192.168.15.8', 'host': 'umbrel.local', 'last_time': 1634751093.1874},
        # '192.168.15.14': {'ip': '192.168.15.14', 'host': 'raspberrypi.local', 'last_time': 1634751093.18819},
        # '127.0.0.1': {'ip': '127.0.0.1', 'host': '127.0.0.1', 'last_time': 1634751093.185246},
        # '192.168.15.18': {'ip': '192.168.15.18', 'host': '192.168.15.18', 'last_time': 1634751093.185638}
        # }

    port_list = [(80, 'Web Server'), (3010, 'Ride the Lightning'),
                 (25441, 'Specter Server'), (3005, 'Samourai Server Dojo'),
                 (50001, 'Electrum Server'), (50002, 'Electrum Server'),
                 (3002, 'Bitcoin RPC Explorer'),
                 (3006, 'Mempool.space Explorer'),
                 (4080, 'Mempool.space Explorer'),
                 (3008, 'BlueWallet Lightning'), (5000, 'WARden Server')]

    # Save the list above for later
    pickle_it('save', 'port_list.pkl', port_list)
    # Additional Services (from Umbrel mostly - add this later)
    # (8082, 'Pi-Hole'),
    # (8091, 'VSCode Server'),
    # (8085, 'Gitea'),
    # (8081, 'Nextcloud'),
    # (8083, "Home Assistant")

    check_list = []
    # Create the list of hosts to reach
    for host in just_found:
        if 'onion' in host:
            url = url_parser(host)
            check_list.append(url)
        else:
            for port in port_list:
                url = 'http://' + host + ':' + str(int(port[0])) + '/'
                check_list.append(url)

    def service_name(port):
        for element in port_list:
            if element[0] == port:
                return element[1]
        return 'Unknown'

    def check_service_url(url):
        try:
            service_found = {}
            result = tor_request(url)
            status = 'ok'
            if not isinstance(result, requests.models.Response):
                # Let's try https (some services use one or the other)
                url = url.replace('http', 'https')
                result = tor_request(url)
                if not isinstance(result, requests.models.Response):
                    status = f'Did not get a response'
            if not result.ok:
                status = 'Reached URL but did not get a code 200 [ok]'
            epoch_time = None
            if status == 'ok':
                utc_time = datetime.utcnow()
                epoch_time = (utc_time - datetime(1970, 1, 1)).total_seconds()
                try:
                    # If the URL is the WARden Onion Address
                    if onion in url:
                        port = 5000
                    else:
                        port = int(url.split(':')[2].strip('/'))
                except:
                    port = None
                service_found[url] = {
                    'url': url,
                    'status': status,
                    'last_update': epoch_time,
                    'port': port,
                    'service': service_name(port)
                }

            return (service_found)
        except Exception:
            return None

    # Load services found
    services_found = pickle_it('load', 'services_found.pkl')
    if services_found == 'file not found' or not isinstance(
            services_found, dict):
        services_found = {}

    # Launch thread to check urls
    with concurrent.futures.ThreadPoolExecutor(30) as executor:
        futures = [
            executor.submit(check_service_url, args) for args in check_list
        ]
        wait(futures, timeout=120, return_when=ALL_COMPLETED)
        for element in futures:
            if isinstance(element.result(), dict):
                services_found = {**services_found, **element.result()}

    # Clean Checking Status
    try:
        for key, item in services_found.items():
            if item['service'] == 'Checking Status':
                del services_found[key]
                break
    except Exception:
        pass

    # Sort the list
    # services_found = sorted(services_found.items(), key=lambda k_v: k_v['last_update'], reverse=True)

    pickle_it('save', 'services_found.pkl', services_found)

    return (services_found)
    # {
    # 'http://umbrel.local:80/': {
    #   'url': 'http://umbrel.local:80/',
    #   'status': 'ok',
    #   'last_update': 1634758799.142936,
    #   'port': '80',
    #   'service': 'Web Server'
    #   }
    # }


def is_service_running(service, expiry=None):
    # Expiry in seconds since last time reached
    # usage: is_service_running('WARden Server', 10)
    services_found = pickle_it('load', 'services_found.pkl')
    if services_found == 'file not found':
        return (False, None)
    for key, val in services_found.items():
        if val['service'] == service:
            if expiry is not None:
                utc_time = datetime.utcnow()
                epoch_time = (utc_time - datetime(1970, 1, 1)).total_seconds()
                if epoch_time - val['last_update'] > expiry:
                    continue
            return (True, val)
    return (False, None)


def url_parser(url):
    # Parse it
    from urllib.parse import urlparse
    parse_object = urlparse(url)
    scheme = 'http' if parse_object.scheme == '' else parse_object.scheme
    if parse_object.netloc != '':
        url = scheme + '://' + parse_object.netloc + '/'
    if not url.startswith('http'):
        url = 'http://' + url
    if url[-1] != '/':
        url += '/'

    return (url)
