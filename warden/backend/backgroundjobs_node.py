import threading
from datetime import datetime
from pricing_engine.engine import realtime_price
from connections.mempoolspace import (node_searcher, check_api_health,
                                      get_tip_height, nodes_status,
                                      get_max_height, get_sync_height)


# Updates the stats used in dashboard
# summarizing nodes online, etc...
def get_nodes_status(app):
    with app.app_context():
        get_max_height()
        nodes_status()


def update_nodes(app):
    with app.app_context():
        # First check if any nodes are in database
        from models.models import Nodes, load_Node
        nodes = load_Node()

        # No nodes in database, run the add known nodes function
        if nodes == []:
            app = seek_standard_nodes(app)

        # Update the nodes
        else:
            # create threads to update each of the nodes
            threads = []
            for node in nodes:
                threads.append(
                    threading.Thread(target=check_node, args=[app, node]))

            for thread in threads:
                thread.start()
            # Join all threads
            for thread in threads:
                thread.join()


def node_indbase(node):
    from models.models import load_Node
    nodes = load_Node(name=node.name)
    if nodes is not None:
        return True
    return False


# Creates background thread to check all servers
def check_node(app, node):
    node = check_api_health(node)
    # Save the last time this node was refreshed with data
    with app.app_context():
        # check if this node is still in database
        # it may have been deleted while doing the background job
        if node_indbase(node) is True:
            # node = app.db.session.merge(node)
            app.db.session.commit()


# Check all tip heights
def check_tip_heights(app):
    from models.models import load_Node
    # First check if any nodes are in database
    with app.app_context():
        nodes = load_Node()

    # create threads to update each of the nodes
    threads = []
    for node in nodes:
        threads.append(
            threading.Thread(target=check_tip_node, args=[app, node]))

    for thread in threads:
        thread.start()
    # Join all threads
    for thread in threads:
        thread.join()


def check_tip_node(app, node):
    with app.app_context():
        node = get_sync_height(node)
        if node_indbase(node) is True:
            if node.is_reachable is True:
                node.last_check = datetime.utcnow()
                node.last_online = datetime.utcnow()
            node = app.db.session.merge(node)
            app.db.session.commit()


def seek_standard_nodes(app):
    print(
        " [i] No nodes found. Including the standard public nodes and searching local network..."
    )
    from models.models import Nodes
    nodes = node_searcher()

    # Store user name so the node is available only to the user
    try:
        username = app.warden_status['username']
    except AttributeError:
        username = None

    # Include these nodes into the database
    for node in nodes:
        try:
            node_info = {
                'user_id': username,
                'name': node[1],
                'url': node[0],
                'is_public': node[2]
            }
            new_node = Nodes(**node_info)
            app.db.session.add(new_node)
            app.db.session.commit()
        except Exception as e:
            print(e)

    return (app)
