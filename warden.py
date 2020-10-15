import os
import sys
from warden import create_app

# CLS + Welcome
print("\033[1;32;40m")
for _ in range(50):
    print("")
print(f"""
\033[1;32;40m
-----------------------------------------------------------------
      _   _           __        ___    ____     _
     | |_| |__   ___  \ \      / / \  |  _ \ __| | ___ _ __
     | __| '_ \ / _ \  \ \ /\ / / _ \ | |_) / _` |/ _ \ '_  |
     | |_| | | |  __/   \ V  V / ___ \|  _ < (_| |  __/ | | |
      \__|_| |_|\___|    \_/\_/_/   \_\_| \_\__,_|\___|_| |_|

-----------------------------------------------------------------
\033[1;37;40m       Privacy Focused Portfolio & Bitcoin Address Tracker
\033[1;32;40m-----------------------------------------------------------------
\033[1;37;40m                      Application Loaded
\033[1;32;40m-----------------------------------------------------------------
\033[1;37;40m                Open your browser and navigate to:
\033[1;37;40m
\033[1;37;40m                     http://localhost:25442/
\033[1;37;40m                               or
\033[1;37;40m                     http://127.0.0.1:25442/
\033[1;32;40m-----------------------------------------------------------------
\033[1;37;40m                     CTRL + C to quit server
\033[1;32;40m-----------------------------------------------------------------
""")

app = create_app()

if __name__ == "__main__":
    #  To debug the application set an environment variable:
    #  EXPORT WARDEN_STATUS=developer
    flask_debug = False
    WARDEN_STATUS = os.environ.get("WARDEN_STATUS")
    if 'debug' in sys.argv:
       flask_debug = True
    if WARDEN_STATUS == "developer":
        print (">> Developer Mode: Debug is On")
        flask_debug = True

    app.run(debug=flask_debug,
            threaded=True,
            host='0.0.0.0',
            port=25442,
            use_reloader=False)

    from warden import scheduler
    # Start Scheduler to grab service data
    if not scheduler.running:
        scheduler.start()
