import os
from stem.control import Controller
from warden_modules import home_path
from ansi_management import (warning, success, error, info, clear_screen, bold,
                             muted, yellow, blue)


def start_hidden_service(app):
    app.controller.reconnect()
    key_path = os.path.abspath(
        os.path.join(home_path(), ".tor_service_key")
    )
    app.tor_service_id = None

    if not os.path.exists(key_path):
        service = app.controller.create_ephemeral_hidden_service(
            {app.tor_port: app.port}, await_publication=True
        )
        app.tor_service_id = service.service_id
        print(
            "* Started a new hidden service with the address of %s.onion"
            % app.tor_service_id
        )

        with open(key_path, "w") as key_file:
            key_file.write("%s:%s" % (service.private_key_type, service.private_key))
    else:
        with open(key_path) as key_file:
            key_type, key_content = key_file.read().split(":", 1)

        service = app.controller.create_ephemeral_hidden_service(
            {app.tor_port: app.port},
            key_type=key_type,
            key_content=key_content,
            await_publication=True,
        )
        app.tor_service_id = service.service_id
        print(success("✅ Resumed %s.onion" % app.tor_service_id))

    # save address to file
    if app.save_tor_address_to is not None:
        with open(app.save_tor_address_to, "w") as f:
            f.write("%s.onion" % app.tor_service_id)
    app.tor_service_id = app.tor_service_id
    app.tor_enabled = True

    print(error(""))
    print(error(" * ############################# Warning! #############################"))
    print(error(
        " * Your are running WARden over Tor with no authentication settings configured."
    ))
    print(error(
        " * This means your WARden instance is accessible to anyone with the .onion URL."
    ))
    print(error(
        " * This .onion URL is publicly exposed and indexed on the Tor network - it is not secret!"
    ))
    print(error(
        " * It is stronly adviced that you configure proper authentication while running WARden behind a Tor hidden service."
    ))
    print(error(
        " * Please go to Settings -> Authentication and set up an authentication method."
    ))
    print(error(" * ####################################################################"))
    print(error(""))


def stop_hidden_services(app):
    try:
        app.controller.reconnect()
        hidden_services = app.controller.list_ephemeral_hidden_services()
        print(" * Shutting down our hidden service")
        for tor_service_id in hidden_services:
            app.controller.remove_ephemeral_hidden_service(tor_service_id)
        # Sanity
        if len(app.controller.list_ephemeral_hidden_services()) != 0:
            print(" * Failed to shut down our hidden services...")
        else:
            print(" * Hidden services were shut down successfully")
            app.tor_service_id = None
    except Exception:
        pass  # we tried...
