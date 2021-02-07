# See specter_importer.MD for instructions
# and sample json return variables

import requests
import json
import re
from datetime import datetime

from requests.sessions import merge_cookies

from bs4 import BeautifulSoup
from utils import pickle_it, load_config


class Specter():
    def __init__(self):
        config = load_config()

        # URL Lists
        self.base_url = config['SPECTER']['specter_url']
        if self.base_url[-1] != '/':
            self.base_url += '/'
        self.login_url = self.base_url + 'auth/login'
        self.tx_url = self.base_url + 'wallets/wallets_overview/txlist'
        self.core_url = self.base_url + 'settings/bitcoin_core?'
        # Payload lists
        self.tx_payload = {
            'idx': 0,
            'limit': 0,
            'search': None,
            'sortby': 'time',
            'sortdir': 'desc'
        }
        self.login_payload = {
            'username': config['SPECTER']['specter_login'],
            'password': config['SPECTER']['specter_password']
        }

    def rescan_progress(self, wallet_alias, load=True):
        if load:
            data = pickle_it(action='load', filename='specter_rescan.pkl')
            if data != 'file not found':
                return (data)
        try:
            url = self.base_url + f"wallets/wallet/{wallet_alias}/rescan_progress"
            session = self.init_session()
            response = session.get(url)
            data = response.json()
            # Save to pickle file
            pickle_it(action='save', filename='specter_rescan.pkl', data=data)
            return(data)
        except Exception as e:
            return('[Specter Error] [rescan] {0}'.format(e))

    def wallet_alias_list(self, load=True):
        try:
            wallets = self.home_parser(load=load)['alias_list']
            return(wallets)
        except Exception as e:
            return('[Specter Error] [wallets] {0}'.format(e))

    def post_request(self, url, payload):
        session = self.init_session()
        url = self.base_url + url
        response = session.post(url, data=payload)
        return (response)

    def init_session(self):
        with requests.session() as session:
            response = session.post(
                self.login_url,
                data=self.login_payload,
                timeout=30
            )
            # Check if authorized
            if response.status_code == 401:
                raise Exception(
                    'Unauthorized Login to Specter. Check Username and/or Password.'
                )
            return(session)

    def refresh_txs(self, load=True):
        # Returns a dictionary with keys
        # dict_keys(['pageCount', 'txlist', 'last_update'])
        try:
            if load:
                data = pickle_it(action='load', filename='specter_txs.pkl')
                if data != 'file not found':
                    return (data)

            session = self.init_session()
            response = session.post(self.tx_url, data=self.tx_payload)
            specter_data = response.json()
            # Include last update_time
            specter_data['last_update'] = datetime.now().strftime('%m/%d/%Y, %H:%M:%S')
            specter_data['txlist'] = json.loads(specter_data['txlist'])
            # Save to pickle file
            pickle_it(action='save', filename='specter_txs.pkl', data=specter_data)
            return(specter_data)

        except requests.exceptions.Timeout as e:
            return(
                '[Specter Error] [refresh] Could not login to ' +
                f'{self.base_url} <> Check address <> Error: {e}'
            )
        except Exception as e:
            return('[Specter Error] [refresh] {0}'.format(e))

    def wallet_info(self, wallet_alias, load=True):
        if load:
            data = pickle_it(action='load',
                             filename=f'wallet_info_{wallet_alias}.pkl')
            if data != 'file not found':
                return (data)
        url = self.base_url + f'wallets/wallet/{wallet_alias}/settings/'
        metadata = {}
        session = self.init_session()
        page = session.get(url)
        soup = BeautifulSoup(page.text, 'html.parser')
        metadata['url'] = url
        # Get device list
        div_id = 'wallet_info_settings_tab'
        data = soup.find("div", {"id": div_id})
        metadata['title'] = data.find('h2').get_text()
        if metadata['title'] == 'Devices':
            metadata['subtitle'] = data.find_all('p')[0].get_text()
        else:
            metadata['subtitle'] = 'Single key'
        # Get list of devices for this wallet
        data = data.find_all('a', href=True)
        metadata['devices'] = {}
        for element in data:
            device_info = {}
            link = element['href']
            alias = list(filter(None, link.split('/')))[-1]
            device_info['url'] = self.base_url[:-1] + link
            device_info['image'] = self.base_url[:-1] + element.find('img').get('src')
            tmp = element.get_text().split('\n')
            tmp = list(filter(None, tmp))
            device_info['name'] = tmp[0].lstrip()
            metadata['devices'][alias] = device_info

        # Save to pickle file
        pickle_it(action='save',
                  filename=f'wallet_info_{wallet_alias}.pkl',
                  data=metadata)
        return metadata

    def home_parser(self, load=True):
        if load:
            data = pickle_it(action='load',
                             filename='specter_home.pkl')
            if data != 'file not found':
                return (data)
        url = self.base_url + 'about'
        metadata = {}
        session = self.init_session()
        page = session.get(url)
        soup = BeautifulSoup(page.text, 'html.parser')
        # Get Specter Version
        try:
            metadata['version'] = (
                soup.find(text=re.compile('Specter Version')).parent()[0].get_text()
            )
        except Exception as e:
            metadata['version'] = f'Error: {e}'
        # Get Bitcoin Core Data
        try:
            div_id = 'bitcoin_core_info'
            data = soup.find("div", {"id": div_id})
            data = data.find('table')
            data = data.find_all('tr')
            bitcoin_core_data = {}
            for element in data:
                cols = element.find_all('td')
                bitcoin_core_data[cols[0].get_text().split(':')[0]] = cols[1].get_text()
            metadata['bitcoin_core_data'] = bitcoin_core_data
        except Exception as e:
            metadata['bitcoin_core_html'] = (
                f"<span class='text-warning'>Error: {str(e)}</span>"
            )
            metadata['bitcoin_core_data'] = {
                'error': str(e)
            }
        # Get Wallet Names
        wallet_dict = {}
        wallet_alias = []
        try:
            div_id = "wallets_list"
            data = soup.find("div", {"id": div_id})
            data = data.find_all('a', href=True)
            for element in data:
                link = element['href']
                alias = list(filter(None, link.split('/')))[-1]
                wallet_alias.append(alias)
                wallet_dict[alias] = {}
                wallet_dict[alias]['url'] = self.base_url[:-1] + link
                find_class = 'grow'
                wallet_info = element.findAll("div", {"class": find_class})[0]
                wallet_info = wallet_info.get_text().split('\n')
                wallet_info = list(filter(None, wallet_info))
                wallet_dict[alias]['name'] = wallet_info[0].lstrip()
                wallet_dict[alias]['keys'] = wallet_info[1]
            metadata['alias_list'] = wallet_alias
            metadata['wallet_dict'] = wallet_dict
        except Exception as e:
            metadata['alias_list'] = None
            metadata['wallet_dict'] = {
                'error': str(e)
            }
        # Get Device Names
        device_dict = {}
        device_list = []
        try:
            div_id = "devices_list"
            data = soup.find("div", {"id": div_id})
            data = data.find_all('a', href=True)
            for element in data:
                link = element['href']
                alias = list(filter(None, link.split('/')))[-1]
                device_list.append(alias)
                device_dict[alias] = {}
                device_dict[alias]['url'] = self.base_url[:-1] + link
                device_dict[alias]['image'] = self.base_url[:-1] + element.find('img').get('src')
                device_info = element.get_text().split('\n')
                device_dict[alias]['name'] = list(filter(None, device_info))[0].lstrip()
                device_dict[alias]['keys'] = list(filter(None, device_info))[1]

            metadata['device_list'] = device_list
            metadata['device_dict'] = device_dict

            metadata['last_update'] = datetime.now().strftime('%m/%d/%Y, %H:%M:%S')
        except Exception as e:
            metadata['device_list'] = None
            metadata['device_dict'] = {
                'error': str(e)
            }

        # Save to pickle file
        pickle_it(action='save',
                  filename='specter_home.pkl',
                  data=metadata)
        return (metadata)
