import numpy as np
from flora_tools.sim.sim_event_manager import SimEventType

from flora_tools.sim.sim_lwb import SYNC_PERIOD
from flora_tools.sim.sim_cad_scanner import SimCADScanner
import flora_tools.sim.sim_node as sim_node
from flora_tools.sim.sim_message import SimMessage, SimMessageType

BACKOFF_PERIOD = SYNC_PERIOD
MAX_BACKOFF_EXPONENT = 5  # 143.165576533 min


class SimSyncer:
    def __init__(self, node: 'sim_node.SimNode'):
        self.node = node
        self.cad_scanner = None

        self.start: float = None
        self.backoff_counter: int = -1

    def run(self, callback):
        self.start = self.node.local_timestamp
        self.backoff_counter = -1
        self.callback = callback

        self.scan()

    def scan(self):
        self.cad_scanner = SimCADScanner(self.node, self.scanner_callback)

    def scanner_callback(self, message: SimMessage):
        if message is not None:
            self.start = self.node.local_timestamp
            self.backoff_counter = -1

            if message.type is SimMessageType.SYNC:
                self.node.lwb_manager.lwb_schedule_manager.register_sync()
                self.callback()
            elif message.type is SimMessageType.SLOT_SCHEDULE:
                self.node.lwb_manager.lwb_schedule_manager.register_slot_schedule(message.content)
                self.callback()
            elif message.type is SimMessageType.ROUND_SCHEDULE:
                self.node.lwb_manager.lwb_schedule_manager.register_round_schedule(message.content)
                self.callback()
            else:
                self.scan()

        else:
            elapsed = self.node.local_timestamp - self.start

            if elapsed > BACKOFF_PERIOD:
                if self.backoff_counter < MAX_BACKOFF_EXPONENT - 1:
                    self.backoff_counter += 1
                self.node.em.register_event(self.node.local_timestamp + BACKOFF_PERIOD * np.exp2(self.backoff_counter), self.node, SimEventType.GENERIC, self.run)
            else:
                self.scan()
