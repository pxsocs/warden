import json
from flask import Blueprint, render_template, request, jsonify
from backend.utils import pickle_it
from connections.connections import url_parser, url_reachable
from connections.mempoolspace import node_actions, is_url_mp_api, get_tx_df, node_searcher

sockets = Blueprint("sockets", __name__)

templateData = {"title": "WARden Monitor"}

# ---------------------------
#  API Node Functions
# ---------------------------


@sockets.route("/node_list", methods=['GET'])
def node_list():
    # When asked to GET, will return the current list of nodes
    node_list = node_actions()
    js = json.dumps(node_list, default=str)
    return (js)


@sockets.route("/initial_search", methods=['POST'])
def initial_search():
    if request.method == 'POST':
        node_searcher()
        return json.dumps("success")


@sockets.route("/tx_getter", methods=['GET'])
def tx_getter():
    try:
        btc_address = request.args.get("btc_address")
        node_url = pickle_it('load', 'default_node.pkl')[0]
        df = get_tx_df(node_url, btc_address)
        txs = {
            'address':
            btc_address,
            'tx_count':
            df['txid'].count(),
            'vout':
            df['vout'].sum(),
            'vin':
            df['vin'].sum(),
            'balance': (df['vout'].sum() - df['vin'].sum()),
            'max_block_height':
            df['block_height'].max(),
            'max_block_time':
            df['block_time'].max(),
            'total_fees':
            df['fee'].sum(),
            'unconfirmed_balance':
            (df[df['confirmed'] == False]['vout'].sum() -
             df[df['confirmed'] == False]['vin'].sum()),
            'unconfirmed_txs':
            df[df['confirmed'] == False]['txid'].count(),
            'activity_detected':
            pickle_it('load', f"{btc_address}.activity"),
            'node_name':
            df['node_name'].iloc[0],
            'node_url':
            df['node_url'].iloc[0],
        }

        pickle_it("save", "tx_message.pkl",
                  f"done getting {txs['tx_count']} txs")
        return (json.dumps(txs, default=str))

    except Exception as e:
        return (json.dumps("Error on tx_getter: " + str(e)))


@sockets.route("/address_getter", methods=['GET'])
def address_getter():
    try:
        # get args from url
        pickle_it("save", "tx_message.pkl", "retrieving utxos...")
        node_name = request.args.get("node_name")
        node_url = request.args.get("node_url")
        btc_address = request.args.get("btc_address")
        # Save this node as the default from now on
        if (node_name != None and node_url != None and node_url != ''
                and node_name != '' and node_name != 'none'
                and node_url != 'none'):
            pickle_it('save', 'default_node.pkl', (node_url, node_name))

        # Just update with default node
        if btc_address == None or btc_address == '':
            return json.dumps("error: no address provided")
        else:
            from mempoolspace import get_address_utxo
            url = pickle_it('load', 'default_node.pkl')[0]
            if url == None:
                return json.dumps("error: no default node chosen")
            utxos = get_address_utxo(url, btc_address)
            # convert the dataframe into a dict
            if 'df' in utxos:
                utxos['df'] = utxos['df'].to_dict('split')
                pickle_it("save", "tx_message.pkl",
                          f"done getting utxos: {len(utxos['df']['index'])}")
            else:
                message = f"There was an error retrieving UTXOs: {utxos['status']}"
                pickle_it("save", "tx_message.pkl", message)

            return json.dumps(utxos, default=str)

    except Exception as e:
        json.dumps("Error on address_getter: " + str(e))


@sockets.route("/node_action", methods=['GET', 'POST'])
def node_action():
    # When asked to GET, will return the current list of nodes
    if request.method == 'GET':
        node_list = node_actions()
        return json.dumps(node_list, default=str)

    if request.method == 'POST':
        try:
            data = json.loads(request.data)
            url = url_parser(data['node_url'])
            if 'action' in data:
                if data['action'] == 'delete':
                    node_name = data['node_name']
                    node_actions('delete', url=url)
                    return json.dumps(f"{node_name} deleted")

            if url_reachable(url) == False:
                return json.dumps("Node is not reachable. Check the URL.")
            # Check if this URL is a mempool.space API
            if is_url_mp_api(url) == False:
                return json.dumps(
                    "URL was found but the mempool.space API does not seem to be installed. Check your node apps."
                )
            # Include new node
            node_actions('add',
                         url=url,
                         name=data['node_name'],
                         public=not (data['is_private_node']))
            return json.dumps("success")
        except Exception as e:
            return json.dumps(f"Error: {e}")


# Gets a local pickle file and dumps - does not work with pandas df
# Do not include extension pkl on argument
@sockets.route("/get_pickle", methods=['GET'])
def get_pickle():
    filename = request.args.get("filename")
    serialize = request.args.get("serialize")
    if not serialize:
        serialize = True
    if not filename:
        return None
    filename += ".pkl"
    data_loader = pickle_it(action='load', filename=filename)
    if serialize is True:
        return (json.dumps(data_loader,
                           default=lambda o: '<not serializable>'))
    else:
        return (json.dumps(data_loader, default=str))
