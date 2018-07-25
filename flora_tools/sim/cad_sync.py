import logging

import numpy as np

import flora_tools.sim.cad_search as sim_cad_search
import flora_tools.sim.sim_event_manager as sim_event_manager
import flora_tools.sim.sim_node as sim_node
from flora_tools import lwb_slot
from flora_tools.sim.sim_message import SimMessage, SimMessageType

MAX_BACKOFF_EXPONENT = 5  # 143.165576533 min


class CADSync:
    def __init__(self, node: 'sim_node.SimNode'):
        self.logger = logging.getLogger(self.__class__.__qualname__)

        self.node = node
        self.cad_scanner = None
        self.callback = None

        self.start: float = None
        self.backoff_counter: int = -1

    @property
    def backoff_period(self):
        return lwb_slot.SYNC_PERIOD

    def run(self, callback):
        self.start = self.node.local_timestamp
        self.backoff_counter = -1
        self.callback = callback

        self.scan()

    def scan(self, modulation: int = None):
        self.cad_scanner = sim_cad_search.CADSearch(self.node, self.scanner_callback, start_modulation=modulation)

    def scanner_callback(self, message: SimMessage):
        if message is not None:
            self.start = self.node.local_timestamp
            self.backoff_counter = -1

            self.logger.info(
                "Marker:{:10f}\tNode:{:3d}\tTx_End:{:10f}\tMod:{:2d}\tType:{:16s}".format(self.node.local_timestamp,
                                                                                          self.node.id,
                                                                                          message.tx_end,
                                                                                          message.modulation,
                                                                                          message.type))

            if message.type is SimMessageType.SYNC:
                self.node.lwb.schedule_manager.register_sync(message)
                self.sync_timestamp(message)
                self.callback()
            elif message.type is SimMessageType.SLOT_SCHEDULE:
                self.node.lwb.schedule_manager.register_slot_schedule(message)
                self.sync_timestamp(message)
                self.callback()
            elif message.type is SimMessageType.ROUND_SCHEDULE:
                self.node.lwb.schedule_manager.register_round_schedule(message)
                self.sync_timestamp(message)
                self.callback()
            else:
                self.scan(modulation=message.modulation)

        else:
            elapsed = self.node.local_timestamp - self.start

            if elapsed > self.backoff_period:
                if self.backoff_counter < MAX_BACKOFF_EXPONENT - 1:
                    self.backoff_counter += 1
                self.node.em.register_event(
                    self.node.local_timestamp + self.backoff_period * np.exp2(self.backoff_counter), self.node,
                    sim_event_manager.SimEventType.GENERIC, self.run)
            else:
                self.scan()

    def sync_timestamp(self, message: SimMessage):
        self.node.local_timestamp = message.timestamp + message.tx_end - message.tx_start
