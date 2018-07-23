import logging
from enum import Enum

import pandas as pd

import flora_tools.sim.sim_network as sim_network
import flora_tools.sim.sim_node as sim_node


class SimEventType(Enum):
    TX_DONE = 1
    RX_TIMEOUT = 2
    RX_DONE = 3
    CAD_DONE = 4
    GENERIC = 5
    TX_DONE_BEFORE_RX_TIMEOUT = 6


class SimEventManager:
    def __init__(self, network: 'sim_network.SimNetwork', event_count: int = None, time_limit: float = None):
        self.logger = logging.getLogger(self.__class__.__qualname__)

        self.network = network
        self.event_count = event_count
        self.time_limit = time_limit

        self.eq = pd.DataFrame(
            columns=['timestamp', 'local_timestamp', 'node', 'type', 'data', 'callback'])
        self.processed_eq = pd.DataFrame(
            columns=['timestamp', 'local_timestamp', 'node', 'type', 'data', 'callback'])

    def loop(self, iterations=1):
        while (self.event_count is not None and self.event_count > 0) or (
                self.time_limit is not None) and self.network.global_timestamp <= self.time_limit:
            self.log_event_queue()

            self.eq = self.eq.sort_values(by=['timestamp'])
            event = self.eq.iloc[0]
            self.eq = self.eq.iloc[1:len(self.eq), :]
            self.process_event(event)

            if self.event_count is not None:
                self.event_count -= 1

    def process_event(self, event):
        self.logger.info(
            "{:12f}\t{:3d}\t{:24s}\t{:24s}\t{}".format(event['timestamp'], event['node'].id, event['type'],
                                                       event['callback'].__qualname__, event['data']))
        self.network.global_timestamp = event['timestamp']

        event['node'].local_timestamp = event['local_timestamp']
        event['callback'](event)
        self.processed_eq.loc[len(self.processed_eq)] = event

    def register_event(self, timestamp: float, node: 'sim_node.SimNode', event_type: SimEventType,
                       callback, data=None, local=True):
        if local:
            local_timestamp = timestamp
            timestamp = node.transform_local_to_global_timestamp(timestamp)
        else:
            local_timestamp = node.transform_global_to_local_timestamp(timestamp)

        tmp_df = pd.DataFrame([[timestamp,
                                local_timestamp, node, event_type, data, callback]],
                              columns=['timestamp', 'local_timestamp', 'node', 'type', 'data', 'callback'])

        self.eq = self.eq.append(tmp_df)

    def unregister_event(self, index):
        self.eq = self.eq.drop(index, inplace=True)

    def remove_all_events(self, node, event_type):
        self.eq = self.eq.loc[(self.eq.node != node) | (self.eq.type != event_type)]

    def log_event_queue(self):
        self.logger.debug("{}\n{}\n".format("Event Queue:", self.eq.to_string()))
