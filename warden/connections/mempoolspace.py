from copyreg import pickle
from datetime import datetime
from flask import current_app, has_app_context
from flask_login import current_user, login_required
from embit import bip32, script
from embit.networks import NETWORKS
import threading
import logging
import pandas as pd
from connections.connections import tor_request, url_reachable, url_parser
from backend.ansi_management import (warning, success, error, info,
                                     clear_screen, muted, yellow, blue,
                                     jformat)
from backend.utils import pickle_it
from backend.decorators import MWT


# Method used to search for nodes - used at first config to
# check for typical nodes and if they are available
# to then include them in database
def node_searcher(silence=False):
    known_names = [
        ('http://mempool.space/', 'mempool.space (Public)', True),
        ('http://mempoolhqx4isw62xs7abwphsq7ldayuidyx2v2oethdhhj6mlo2r6ad.onion/',
         'mempool.space (public) [onion]', True),
        ('http://raspberrypi.local:4080/', 'RaspiBlitz  (Local Network)',
         False),
        ('http://raspberrypi-2.local:4080/', 'RaspiBlitz  (Local Network)',
         False),
        ('http://ronindojo.local:3006/', 'Ronin Dojo (Local Network)', False),
        ('http://umbrel.local:3006/', 'Umbrel (Local Network)', False),
        ('http://umbrel-2.local:3006/', 'Umbrel (Local Network)', False),
        ('http://umbrel-3.local:3006/', 'Umbrel (Local Network)', False),
        ('http://umbrel-3.local:3006/', 'Umbrel (Local Network)', False),
    ]

    if silence is False:
        print(" 🔍  Searching for nodes...")
        print("     ----------------------")
        print("     WARden searches for nodes by trying to connect to")
        print("     the mempool.space API at different addresses.")
        print("     If you run a node and would like to connect, make sure")
        print("     that the node has the API installed.")
        print("     https://github.com/mempool/mempool")
        print("")
        print("     ----------------------")

    found_nodes = []

    def check_node(server):
        url = server[0]
        if silence is False:
            print(" [i] Checking for node at " + url)
        if url_reachable(url) is True:
            if silence is False:
                print(" [i] Node at " + url + " is reachable")
            api_reached, _ = is_url_mp_api(url)
            if api_reached is True:
                if silence is False:
                    print(" [i] Node at " + url + " has a mempool.space API")
                    print(success(" [OK] Found node at " + url))
                found_nodes.append(server)

                return True
        else:
            return False

    threads = []

    for server in known_names:
        threads.append(threading.Thread(target=check_node, args=[server]))

    for thread in threads:
        thread.start()

    # Join all threads
    for thread in threads:
        thread.join()

    if found_nodes == []:
        # At a minimum will return one public node
        # there's actually no reason for this not to be found
        # unless the app is offline or there's a connection issue
        # with all the nodes (should not happen)
        if silence is False:
            print(
                yellow(
                    " [i] No nodes found, using only Mempool.space - you can add a node later"
                ))
        found_nodes = [('http://mempool.space/', 'mempool.space', True)]
    else:
        if silence is False:
            print(success(" [i] Found " + str(len(found_nodes)) + " nodes"))
            print("")

    return found_nodes


# Creates a list of URLs and names for the public and private addresses
def node_actions(action=None, url=None, name=None, public=True):
    # Sample list_all output:
    # [
    #   ('http://raspberrypi.local:4080/', 'RaspiBlitz Home', False),
    #   ('http://mempool.space/', 'mempool.space', True),
    #   ('http://mempoolhqx4isw62xs7abwphsq7ldayuidyx2v2oethdhhj6mlo2r6ad.onion/', 'mempool.space [onion]', True)
    # ]

    from models.models import Nodes

    # add name to url (actually it's an add or replace if exists)
    # so add = edit
    if action == 'add':
        # check if exists, if so, load to edit, if not create new
        from models.models import load_Node
        node = load_Node(url=url)
        if node is None:
            node = Nodes()
            node.user_id = current_user.username if current_user.username is not None else 0

        node.url = url_parser(url)
        node.name = name
        node.is_public = public
        node = check_api_health(node)
        current_app.db.session.add(node)
        current_app.db.session.commit()
        return node

    # Remove name from list
    if action == 'delete' or action == 'remove':
        node = Nodes.query.filter_by(url=url).first()
        current_app.db.session.delete(node)
        current_app.db.session.commit()

    if action == 'get':
        if url is not None:
            node = Nodes.query.filter_by(url=url).first()
        if name is not None:
            node = Nodes.query.filter_by(name=name).first()
        return node

    # No action, just list all
    nodes = Nodes.query.all()
    list_nodes = []
    for node in nodes:
        list_nodes.append(node.as_dict())
    return list_nodes


# Returns the highest block height in all servers
def get_max_height():
    from models.models import Nodes
    from sqlalchemy import func
    max_tip_height = current_app.db.session.query(
        func.max(Nodes.node_tip_height))[0][0]
    pickle_it('save', 'max_blockchain_tip_height.pkl', max_tip_height)
    return max_tip_height


@MWT(timeout=5)
def get_sync_height(node):
    # Get the max tip height currently stored locally
    max_tip = pickle_it('load', 'max_blockchain_tip_height.pkl')
    if max_tip == 'file not found' or not isinstance(max_tip, int):
        max_tip = 0

    # Check the node status
    logging.info(
        muted("Checking tip height for " + node.name +
              " - comparing to local max tip: " + str(max_tip)))

    url = node.url
    endpoint = 'api/blocks/tip/height'
    tip = tor_request(url + endpoint)

    #  Update the node instance
    try:
        tip = int(tip.text)
    except Exception:
        tip = 0

    node.node_tip_height = tip
    node.blockchain_tip_height = max_tip

    if tip == max_tip:
        # Save the top tip block details - top_block_details.pkl
        top_blk_details = get_last_block_info(node.url, max_tip)
        pickle_it('save', 'top_node_url.pkl', node.url)
        if node.is_public is True:
            pickle_it('save', 'top_node_public_url.pkl', node.url)
        else:
            pickle_it('save', 'top_node_private_url.pkl', node.url)
        pickle_it('save', 'top_block_details.pkl', top_blk_details)

    return node


# Get Block Header and return when was it found
@MWT(timeout=30)
def get_last_block_info(url, height):
    # Get Hash
    end_point = 'api/block-height/' + str(height)
    hash = tor_request(url + end_point)
    try:
        hash = hash.text
    except AttributeError:
        return None
    if hash == 'Block height out of range':
        logging.info(
            error("Block height out of range -- could not get latest time"))
        return None
    # Know get the latest data
    end_point = 'api/block/' + hash
    block_info = tor_request(url + end_point)
    try:
        block_info = block_info.json()
    except Exception:
        return None
    return (block_info)


@MWT(timeout=6000)
def check_block(url, block):
    end_point = 'api/block-height/'
    try:
        result = tor_request(url + end_point + str(block))
        result = result.text
    except Exception:
        result = None
    return result


# Check if this url is a mempool.space API
# returns true if reachable + request time
# zero = no response or error
def is_url_mp_api(url):
    end_point = 'api/v1/difficulty-adjustment'
    requests = tor_request(url + end_point)
    try:
        if requests.status_code == 200:
            # There seems to be an issue with deployments
            # through RaspiBlitz and Umbrel
            # Researching NGINX issues as described below
            # https://github.com/mempool/mempool/issues/1030
            if 'Cannot GET' in str(requests.text) == '':
                return (False, 0)

            return (True, requests.elapsed)
        else:
            return (False, 0)
    except Exception:
        return (False, 0)


# Get the highest tip height from a certain url
# this is not the synch tip height but rather
# the block with most proof of work - that can be
# ahead of the synch tip height
@MWT(timeout=2)
def get_tip_height(url):
    endpoint = 'api/blocks/tip/height'
    result = tor_request(url + endpoint)
    try:
        result = result.text
        result = int(result)
        return result
    except Exception:
        return None


@MWT(timeout=2)
def check_api_health(node):
    # . Reachable
    # . ping time
    # . Last time reached
    # . Mempool API active
    # . Tip_height
    # . Current Block Height
    # . is_tor
    # . is_localhost
    # . name
    # . progress
    # . blocks behind

    logging.info(muted("Checking server: " + node.name))
    url = node.url

    # Store ping time and return that it's reacheable
    reachable, ping = is_url_mp_api(url)
    node.mps_api_reachable = reachable
    node.ping_time = ping

    # mps API not found, let's see if at least the node
    # is alive but it's a problem with API
    if reachable is False:
        node.is_reachable = url_reachable(url)
    else:
        node.is_reachable = True

    # Node is online and reachable with a MPS API working
    # store the last time it was online
    if node.is_reachable is True:
        node.last_online = datetime.utcnow()
        tip = get_tip_height(node.url)
        if tip is not None:
            node.blockchain_tip_height = tip

    # Other data
    node.onion = True if '.onion' in url else False

    local_host_strings = ['localhost', '.local', '192.', '0.0.0.0']
    node.is_localhost = True if any(host in url
                                    for host in local_host_strings) else False

    # Save the node information to the database
    return node


# get a set of statistics from the nodes
# to be displayed in the dashboard
def nodes_status():
    from models.models import load_Node
    stats = {}
    # Load node info
    full_data = load_Node()
    stats['check_time'] = datetime.utcnow()
    stats['total_nodes'] = len(full_data)
    stats['online'] = sum(x.mps_api_reachable == True for x in full_data)
    stats['is_public'] = sum(x.is_public == True for x in full_data)
    stats['at_tip'] = sum(x.is_at_tip() == True for x in full_data)
    stats['is_onion'] = sum(x.is_onion() == True for x in full_data)
    stats['is_localhost'] = sum(x.is_localhost == True for x in full_data)
    # # Save for later consumption
    pickle_it('save', 'node_stats.pkl', stats)
    return (stats)


def get_address_utxo(url, address):
    # Endpoint
    # GET /api/address/:address/utxo
    pickle_it("save", "tx_message.pkl", "retrieving utxos... please wait...")
    endpoint = 'api/address/' + address + '/utxo'
    address_info = {'address': address}
    result = tor_request(url + endpoint)

    try:
        address_json = result.json()
    except Exception:
        try:
            rslt = result.text
            address_info['status'] = rslt
            return address_info
        except Exception as e:
            raise Exception(
                f"Error getting UTXO from {url + endpoint}. error: {e}")

    # Clean results and include into a dataframe
    df = pd.DataFrame().from_dict(address_json)
    address_info['df'] = df
    # Include total balance
    if df.empty is not True:
        address_info['balance'] = df['value'].sum()
    else:
        address_info['balance'] = 0

    # Get date of last activity confirmed and unconfirmed
    max_confirmed = 0
    count_unconfirmed = 0
    utxos = 0
    for __, row in df.iterrows():
        status = row.status
        if status['confirmed'] == True:
            utxos += 1
            max_confirmed = max(max_confirmed, status['block_time'])
        else:
            count_unconfirmed += 1
            utxos += 1

    address_info['last_confirmed'] = max_confirmed
    address_info['count_unconfirmed'] = count_unconfirmed
    address_info['utxos'] = utxos

    # Save into database if new or update
    # Let's check if there's been any activity on this address since last check
    from models.models import BitcoinData
    bitcoin_address = BitcoinData.query.filter_by(address=address).first()

    # if this is not in the database, means it is not a monitored address
    # that was saved in the address book - no need to check for activity
    if not bitcoin_address:
        address_info['in_addressbook'] = False
        address_info['BitcoinData'] = None
        address_info['activity_detected'] = None
        return address_info
    # ----- Found in address book - check for activity
    address_info['in_addressbook'] = True
    address_info['BitcoinData'] = bitcoin_address
    address_info['status'] = 'success'

    # Create a dictionary to save change activity - the idea
    # is to keep this data saved until it is dismissed by the
    # user - which will then delete the pickle.

    # Check if there's a previous state for activity detected (not dismissed yet)

    # File not found means that the file was deleted and no activity alerts are set

    return address_info


# Gets all txs for a given address and return a df
# Also saves the txs in a pickle + messages + an activity notifier file
def get_tx_df(url=None, address=None):
    pickle_it("save", "tx_message.pkl",
              "retrieving transactions... please wait...")
    # Endpoint
    # GET /api/address/:address/txs
    # url = 'https://mempool.space/'
    # address = 'bc1qxpvd7lyk5jgddrmlg8uq0r9ew2jpv06l75xm9d'
    # address = '1Ppd8MsuRubZuVLiADJomXk5Aer1HYuCGD'
    if url == '' or url is None:
        url = pickle_it('load', 'default_node.pkl')[0]
        node_name = pickle_it('load', 'default_node.pkl')[1]
    if url == '' or url is None:
        raise ("No URL provided and no default node found")

    endpoint = 'api/address/' + address + '/txs'
    result = tor_request(url + endpoint)
    for tries in range(3):
        try:
            address_json = result.json()
            if result == 'ConnectionError':
                continue
            break
        except Exception:
            pass

    tx_list = []
    # Process the JSON and return a dataframe
    tx_count = 999
    while tx_count >= 25:
        tx_count = 0
        for tx in address_json:
            tx_count += 1
            tx_element = {
                'txid': tx['txid'],
                'fee': tx['fee'],
                'confirmed': tx['status']['confirmed']
            }

            # Check if this is the latest transaction that is already saved
            # if so, break
            old_df = pickle_it('load', f'{address}.txs')
            try:
                df = old_df.set_index('txid')
                if tx['txid'] in df.index:
                    pickle_it("save", "tx_message.pkl",
                              "no new transactions found since last check")
                    pickle_it("save", f"{address}.activity", False)
                    return old_df
                else:
                    pickle_it("save", f"{address}.activity", True)
            except Exception:
                pass

            if tx_element['confirmed'] == True:
                tx_element['block_height'] = tx['status']['block_height']
                tx_element['block_hash'] = tx['status']['block_hash']
                tx_element['block_time'] = tx['status']['block_time']

            # Process VIN and VOUT
            from utils import cleanfloat
            vin_total = vout_total = 0
            for vin in tx['vin']:
                if vin['prevout']['scriptpubkey_address'] == address:
                    vin_total += cleanfloat(vin['prevout']['value'])
            for vout in tx['vout']:
                try:
                    if vout['scriptpubkey_address'] == address:
                        vout_total += cleanfloat(vout['value'])
                except Exception:
                    pass
            tx_element['vout'] = vout_total
            tx_element['vin'] = vin_total
            tx_list.append(tx_element)
            last_seen_txid = tx['txid']
            # May need to keep getting another json
            pickle_it("save", "tx_message.pkl",
                      f"Retrieved {len(tx_list)} transactions so far...")

            if tx_count >= 25:
                endpoint = 'api/address/' + address + '/txs/chain/' + last_seen_txid
                result = tor_request(url + endpoint)
                # Try up to 3 times - sometimes the rquest may timeout
                for attempt in range(3):
                    try:
                        address_json = result.json()
                        break
                    except Exception:
                        raise Exception(
                            f"Could not parse JSON from url: {url + endpoint}")

    # cols = ['txid', 'fee', 'vin',
    #         'vout', 'confirmed',
    #         'block_height', 'block_hash',
    #         'block_time']

    df = pd.DataFrame(tx_list)

    from models.models import load_Node
    node_name = load_Node(url=url).name
    df['node_name'] = node_name
    df['node_url'] = url

    # Save for later consumption
    pickle_it('save', f'{address}.txs', df)
    pickle_it("save", "tx_message.pkl",
              "retrieved a total of {len(tx_list)} transactions")

    return (df)


def xpub_derive(xpub,
                number_of_addresses,
                start_number=0,
                output_type='P2PKH'):
    # Output type: P2WPKH, P2PKH
    # Derivation Path: m/84'/0'
    hd = bip32.HDKey.from_string(xpub)
    add_list = []
    net = NETWORKS['main']
    for i in range(0, number_of_addresses):
        ad = hd.derive([start_number, i])
        if output_type == 'P2WPKH':
            add_list.append(script.p2wpkh(ad).address(net))
        elif output_type == 'P2PKH':
            add_list.append(script.p2pkh(ad).address(net))
        else:
            raise Exception("Invalid output type")
    return add_list


def xpub_balances(url, xpub, derivation_types=['P2WPKH', 'P2PKH']):
    # Scan addresses in xpubs and return a list of addresses and balances
    balance_list = []
    for derivation_type in derivation_types:
        counter = 0
        end_counter = 10
        while True:
            # Get the first address
            address = xpub_derive(xpub=xpub,
                                  number_of_addresses=1,
                                  start_number=counter,
                                  output_type=derivation_type)
            # Check balance
            balance = get_address_utxo(url, address[0])['balance']
            # Found something, include
            if balance != 0:
                # Tries at least 10 more addresses after the last balance
                # was found
                end_counter = counter + 10
                add_dict = {
                    'address': address,
                    'utxos': get_address_utxo(url, address[0]),
                    'balance': balance
                }
            # Empty address
            else:
                add_dict = {'address': address, 'utxos': None, 'balance': 0}

            counter += 1
            # Add to list
            balance_list.append(add_dict)

            # 10 sequential addresses with no balance found, break
            if counter >= end_counter:
                break

    return balance_list


def op_return_getter():
    pass


def op_return_streamer():
    pass
