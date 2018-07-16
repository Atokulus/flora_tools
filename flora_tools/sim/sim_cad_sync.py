import numpy as np
from flora_tools.sim.sim_event_manager import SimEventType

import flora_tools.sim.sim_lwb as sim_lwb
import flora_tools.sim.sim_cad_search as sim_cad_search
import flora_tools.sim.sim_node as sim_node
from flora_tools.sim.sim_message import SimMessage, SimMessageType

MAX_BACKOFF_EXPONENT = 5  # 143.165576533 min


class SimCADSync:
    def __init__(self, node: 'sim_node.SimNode'):
        self.node = node
        self.cad_scanner = None

        self.start: float = None
        self.backoff_counter: int = -1

    @property
    def backoff_period(self):
        return sim_lwb.SYNC_PERIOD

    def run(self, callback):
        self.start = self.node.local_timestamp
        self.backoff_counter = -1
        self.callback = callback

        self.scan()

    def scan(self):
        self.cad_scanner = sim_cad_search.SimCADSearch(self.node, self.scanner_callback)

    def scanner_callback(self, message: SimMessage):
        if message is not None:
            self.start = self.node.local_timestamp
            self.backoff_counter = -1

            if message.type is SimMessageType.SYNC:
                self.node.lwb.lwb_schedule_manager.register_sync()
                self.sync_timestamp()
                self.callback()
            elif message.type is SimMessageType.SLOT_SCHEDULE:
                self.node.lwb.lwb_schedule_manager.register_slot_schedule(message)
                self.sync_timestamp()
                self.callback()
            elif message.type is SimMessageType.ROUND_SCHEDULE:
                self.node.lwb.lwb_schedule_manager.register_round_schedule(message)
                self.sync_timestamp()
                self.callback()
            else:
                self.scan()

        else:
            elapsed = self.node.local_timestamp - self.start

            if elapsed > self.backoff_period:
                if self.backoff_counter < MAX_BACKOFF_EXPONENT - 1:
                    self.backoff_counter += 1
                self.node.em.register_event(self.node.local_timestamp + self.backoff_period * np.exp2(self.backoff_counter), self.node, SimEventType.GENERIC, self.run)
            else:
                self.scan()

    def sync_timestamp(self, message: SimMessage):
        self.node.local_timestamp = message.timestamp + message.tx_end - message.tx_start
