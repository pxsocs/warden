from time import sleep, time
import math

from dashing import *

if __name__ == '__main__':

    ui = HSplit(
        VSplit(
            Text('Tor [Running]\nBitcoin Core [Running]\nSpecter Server [Running]',
                 border_color=10, title='Services Status', color=10)
        ),
        VSplit(
            Text('Hello World,\nthis is dashing.', border_color=10),
            Log(title='Bitcoin Log', border_color=10),
            Log(title='WARden Log', border_color=10),
        ),
        title='WARden | Text Based Console', color=10
    )
    log = ui.items[1].items[1]
    log.append("0 -----")
    log.append("1 Hello")
    log.append("2 -----")
    prev_time = time()
    for cycle in range(0, 200):
        t = int(time())
        if t != prev_time:
            log.append(f"{t} {cycle}")
            prev_time = t
        ui.display()

        sleep(1.0/25)


class WardenWidget:
    def __init__(self, dashing_type, border_color=0, value=None, color=0, frequency=10):
        self.dashing_type = dashing_type
        self.age = age
