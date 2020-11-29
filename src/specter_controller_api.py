############### API endpoints ##################


# Specter Basic info
@app.route("/api/specter/", methods=["GET"])
@login_required
def api_specter():
    specter_data = app.specter

    return_dict = {
        'data_folder': specter_data.data_folder,
        'file_config': specter_data.file_config,
        'config': specter_data.config,
        'is_configured': specter_data._is_configured,
        'is_running': specter_data._is_running,
        'info': specter_data._info,
        'network_info': specter_data._network_info,
        'device_manager_datafolder': specter_data.device_manager.data_folder,
        'devices_names': specter_data.device_manager.devices_names,
        'wallets_names': specter_data.wallet_manager.wallets_names,
        'last_update': datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    }

    # Include alias list
    wallets_alias = []
    alias_name = {}
    name_alias = {}
    for wallet in return_dict['wallets_names']:
        alias = specter_data.wallet_manager.wallets[wallet].alias
        wallets_alias.append(alias)
        alias_name[alias] = wallet
        name_alias[wallet] = alias
    return_dict['alias_name'] = alias_name
    return_dict['name_alias'] = name_alias
    return_dict['wallets_alias'] = wallets_alias

    return (json.dumps(return_dict))


# Get wallet basic information
@app.route("/api/wallet_info/<wallet_alias>/", methods=["GET"])
@login_required
def api_wallet_info(wallet_alias):

    try:
        wallet = app.specter.wallet_manager.get_by_alias(wallet_alias)
        # update balances in the wallet
    except SpecterError as se:
        message = ("API error: %s" % se)
        app.logger.error(message)
        return json.dumps(message)

    wallet.get_balance()

    return_dict = {}
    # Get full list of idx from specter
    address_index = wallet.address_index
    validate_merkle_proofs = app.specter.config.get("validate_merkle_proofs")

    tx_data = []
    for idx in range(0, address_index + 1):
        tx_data.append(wallet.txlist(idx, validate_merkle_proofs=validate_merkle_proofs))

    # Check if scanning
    scan = wallet.rescan_progress
    # Clear public keys - no need to broadcast on API
    wallet.__dict__['keys'] = ''
    # Expand list of devices used to sign this wallet, store only alias
    wallet.__dict__['device_list'] = []
    for device in wallet.__dict__['devices']:
        wallet.__dict__['device_list'].append(device.name)
    # clear old device list - to not store pub keys
    # This also makes for a leaner json file
    wallet.__dict__['devices'] = ''
    wallet.__dict__['manager'] = ''
    wallet.__dict__['rpc'] = ''
    return_dict[wallet_alias] = (wallet.__dict__)
    return_dict['txlist'] = tx_data
    return_dict['scan'] = scan
    return_dict['address_index'] = address_index

    return (json.dumps(return_dict))
