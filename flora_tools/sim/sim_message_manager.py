from copy import copy

import pandas as pd

import flora_tools.lwb_slot as lwb_slot
import flora_tools.sim.sim_event_manager as sim_event_type
import flora_tools.sim.sim_network as sim_network
import flora_tools.sim.sim_node as sim_node
from flora_tools.radio_configuration import RadioConfiguration
from flora_tools.sim.sim_message import SimMessage
from flora_tools.sim.sim_tracer import TxActivity


class SimMessageManager:
    def __init__(self, network: 'sim_network.SimNetwork'):
        self.network = network
        self.mq = pd.DataFrame(
            columns=['source', 'modulation', 'band', 'power', 'tx_start', 'tx_end', 'message', 'message_hash'])
        self.rxq = pd.DataFrame(
            columns=['rx_node', 'modulation', 'band', 'rx_start', 'callback'])

    def tx(self, source: 'sim_node.SimNode', modulation, band, message: SimMessage):
        power = lwb_slot.POWERS[message.power_level]

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
                                     message.hash]

        self.network.tracer.log_activity(
            TxActivity(message.tx_start, message.tx_end, source,
                       RadioConfiguration.tx_energy(power, message.tx_end - message.tx_start), power, modulation)
        )

        for rx_node_item_index, rx_node_item in self.rxq.iterrows():
            if (rx_node_item is not None and
                    rx_node_item['rx_start'] < message.tx_start and
                    rx_node_item['modulation'] is modulation and
                    rx_node_item['band'] is band):
                self.network.em.register_event(
                    message.tx_end,
                    rx_node_item['rx_node'],
                    sim_event_type.SimEventType.TX_DONE_BEFORE_RX_TIMEOUT,
                    rx_node_item['callback'],
                    {'source': source, 'message': message, 'rx': rx_node_item},
                    local=False)

    def register_rx(self, rx_node: 'sim_node.SimNode', rx_start: float, modulation: int, band: int, callback):
        rx_start_global = rx_node.transform_local_to_global_timestamp(rx_start)
        self.rxq.loc[rx_node.id, :] = [rx_node, modulation, band, rx_start_global, callback]

        future_transmissions = self.mq.loc[self.mq.tx_start > rx_start_global]
        for future_transmission_idx, future_transmission in future_transmissions.iterrows():
            if (future_transmission['modulation'] is modulation and
                    future_transmission['band'] is band):
                self.network.em.register_event(
                    future_transmission['tx_end'],
                    rx_node,
                    sim_event_type.SimEventType.TX_DONE_BEFORE_RX_TIMEOUT,
                    callback,
                    {'message': future_transmission['message'],
                     'rx': [rx_node, modulation, band, rx_start_global, callback]},
                    local=False)

    def unregister_rx(self, rx_node: 'sim_node.SimNode'):
        self.network.em.remove_all_events(rx_node, sim_event_type.SimEventType.TX_DONE_BEFORE_RX_TIMEOUT)
        self.network.em.remove_all_events(rx_node, sim_event_type.SimEventType.RX_TIMEOUT)
        self.rxq = self.rxq.drop(rx_node.id)
