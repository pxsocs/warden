import emoji
from ansi.colour import fg


def logo():
    print(
        fg.brightgreen(f"""
  _   _           __        ___    ____     _
 | |_| |__   ___  \ \      / / \  |  _ \ __| | ___ _ __
 | __| '_ \ / _ \  \ \ /\ / / _ \ | |_) / _` |/ _ \ '_  |
 | |_| | | |  __/   \ V  V / ___ \|  _ < (_| |  __/ | | |
  \__|_| |_|\___|    \_/\_/_/   \_\_| \_\__,_|\___|_| |_|"""))
    print("")
    print(f"""
                                    {yellow("Powered by NgU technology")} {emoji.emojize(':rocket:')}

                        Portfolio Analytics Tool
    ----------------------------------------------------------------
                         CTRL + C to quit server
    ----------------------------------------------------------------""")


def goodbye():
    for n in range(0, 10):
        print("")
    print(
        fg.brightgreen(f"""
\ \ / (_)_ _ ___ ___
 \ V /| | '_/ -_|_-<
  \_/ |_|_| \___/__/
        (_)_ _
        | | '  |         _
| \| |_ |_|_||_| ___ _ _(_)___
| .` | || | '  \/ -_) '_| (_-<
|_|\_|\_,_|_|_|_\___|_| |_/__/


    """))