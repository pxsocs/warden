import os
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
               \033[1;37;40m
       Privacy Focused Portfolio & Bitcoin Address Tracker
\033[1;32;40m-----------------------------------------------------------------
\033[1;37;40m
   Application loaded...
\033[1;32;40m-----------------------------------------------------------------
\033[1;31;40m                  Always go for the red pill
\033[1;32;40m-----------------------------------------------------------------
\033[1;37;40m
""")

app = create_app()

flask_debug = False

#  To debug the application set an evironment variable:
#  EXPORT WARDEN_STATUS=developer
WARDEN_STATUS = os.environ.get("WARDEN_STATUS")
if WARDEN_STATUS == "developer":
    flask_debug = True

if __name__ == "__main__":

    app.run(debug=flask_debug,
            threaded=True,
            host='0.0.0.0',
            port=25442,
            use_reloader=False)
    from warden import scheduler
    if not scheduler.running:
        scheduler.start()
