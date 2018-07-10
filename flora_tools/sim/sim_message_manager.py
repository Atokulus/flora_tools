from copy import copy

import pandas as pd

import flora_tools.sim.sim_network as sim_network
import flora_tools.sim.sim_node as sim_node
from flora_tools.lwb_slot import POWERS
from flora_tools.sim.sim_event_manager import SimEventType
from flora_tools.sim.sim_message import SimMessage


class SimMessageManager:
    def __init__(self, network: 'sim_network.SimNetwork'):
        self.network = network
        self.mq = pd.DataFrame(
            columns=['source', 'modulation', 'band', 'power', 'tx_start', 'tx_end', 'message', 'message_id'])
        self.rxq = []  # [{'rx_node', 'modulation', 'band', 'rx_start', 'callback'}]

    def tx(self, source: 'sim_node.SimNode', modulation, band, power, message: SimMessage):
        power = POWERS[power]

        message = copy(message)
        message.hop_count += 1
        message.tx_start = source.transform_local_to_global_timestamp(message.timestamp)

        self.mq.loc[len(self.mq)] = [source,
                                     modulation,
                                     band,
                                     power,
                                     message.tx_start,
                                     message.tx_end,
                                     message,
                                     message.id]

        for rx_node_item in self.rxq:
            if (rx_node_item is not None and
                    rx_node_item['modulation'] is modulation and
                    rx_node_item['band'] is band):
                self.network.em.register_event(message.tx_end,
                                               rx_node_item['rx_node'],
                                               SimEventType.TX_DONE_BEFORE_RX_TIMEOUT,
                                               rx_node_item['callback'],
                                               {'message': message, 'rx': rx_node_item})

    def register_rx(self, rx_node: 'sim_node.SimNode', rx_start: float, modulation: int, band: int, callback):
        rx_start = rx_node.transform_local_to_global_timestamp(rx_start)
        self.rxq[rx_node.id] = {'rx_node': rx_node,
                                'modulation': modulation,
                                'band': band,
                                'rx_start': rx_start,
                                'callback': callback}

    def unregister_rx(self, rx_node: 'sim_node.SimNode'):
        self.rxq[rx_node.id] = None
