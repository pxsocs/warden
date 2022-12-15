if __name__ == '__main__':
    import os
    import glob
    import os.path
    import sys
    from application_factory import main
    from backend.ansi_management import yellow
    from backend.config import Config, home_path
    from ansi_messages import goodbye

    # Check for system arguments
    # --------------------------------
    debug = True if "debug" in sys.argv else False
    print(yellow(f"  [i] DEBUG MODE: {str(debug).upper()}"))
    reloader = True if "reloader" in sys.argv else False
    print(yellow(f"  [i] RELOADER MODE: {str(reloader).upper()}"))

    # Create App and Start Flask Server
    # --------------------------------
    app = main(debug=debug, reloader=reloader)
    # Check port and host

    app.run(debug=True,
            host=app.settings['SERVER'].get('host'),
            port=app.settings['SERVER'].getint('port'))

    # Run after exiting Flask Server
    # --------------------------------
    print("Exiting...")

    # Cleaning Files
    # --------------------------------
    # debug.log
    try:
        os.remove(Config.debug_file)
    except Exception:
        pass
    # clean historical prices & metadata
    filelist = glob.glob(os.path.join(home_path, "*.price"))
    for f in filelist:
        os.remove(f)
    filelist = glob.glob(os.path.join(home_path, "*.meta"))
    for f in filelist:
        os.remove(f)
    # Finish message
    goodbye()
