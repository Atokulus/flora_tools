import numpy as np

import flora_tools.lwb_slot as lwb_slot
import flora_tools.sim.sim_network as sim_network
import flora_tools.sim.sim_node as sim_node
from flora_tools.gloria_flood import GloriaFlood
from flora_tools.radio_configuration import RadioConfiguration
from flora_tools.radio_math import RadioMath, RADIO_SNR
from flora_tools.sim.sim_message import SimMessage


class SimMessageChannel:
    def __init__(self, network: 'sim_network.SimNetwork'):
        self.network = network
        self.mm = network.mm

    def receive_message_on_tx_done_before_rx_timeout(self, rx_node: 'sim_node.SimNode', modulation, band,
                                                     message: SimMessage,
                                                     rx_start: float, tx_start: float) -> SimMessage:
        if not self.is_reachable(rx_node, self.network.nodes[message.source.id],
                                 lwb_slot.POWERS[self.message.power_level]):
            return None

        config = RadioConfiguration(modulation, preamble=GloriaFlood().preamble_len(modulation))
        math = RadioMath(config)

        valid_rx_start = rx_start + math.get_symbol_time() * 0.1

        if valid_rx_start > message.timestamp:
            return None

        interfering_set = (self.mm.mq.loc[
            self.modulation == band &
            self.mm.mq.tx_end >= message.timestamp &
            self.mm.mq.tx_start <= message.tx_end
            ]).copy()

        def calc_power_message(item):
            return self.calculate_path_loss(rx_node, self.network.nodes[item.source.id]) + item['power']

        interfering_set['rx_power'] = interfering_set.applymap(calc_power_message, axis=1)
        rx_power = self.calculate_path_loss(rx_node, message.source.id) + lwb_slot.POWERS[message.power_level]

        interfering_power = 0
        for interferer_index, interferer in interfering_set.rx_power:
            if interferer['message_hash'] is not message.hash or not (
                    (tx_start - 100E6) < interferer['tx_start'] < (tx_start + 100E6)):
                interfering_power += np.pow(10, interferer['rx_power'] / 10)

        if np.pow(10, rx_power / 10) > (interfering_power + np.pow(10, RADIO_SNR[modulation])):
            return message
        else:
            return None

    def receive_message_on_rx_timeout(self, modulation, band, rx_node: 'sim_node.SimNode', rx_start,
                                      rx_timeout=None) -> SimMessage:
        self.mm.unregister_rx(rx_node)
        rx_start = rx_node.transform_local_to_global_timestamp(rx_start)

        def mark_reachable_message(item):
            return self.is_reachable(rx_node, self.network.nodes[item['source'].id], power=item['power'])

        def calc_power_message(item):
            return self.calculate_path_loss(rx_node, self.network.nodes[item.source.id]) + item['power']

        config = RadioConfiguration(modulation, preamble=GloriaFlood().preamble_len(modulation))
        math = RadioMath(config)

        valid_rx_start = rx_start + math.get_symbol_time() * 0.1
        keep_quiet_start = rx_start - 100E-6

        interfering_set = (self.mm.mq.loc[
            self.modulation == band &
            self.mm.mq.tx_end >= keep_quiet_start &
            self.mm.mq.tx_start <= valid_rx_start
            ]).copy()

        if rx_timeout is None:
            rx_timeout = rx_start + math.get_preamble_time()

        subset = (self.mm.mq.loc[
            self.mm.mq.modulation == modulation &
            self.mm.mq.band == band &
            self.mm.mq.tx_start >= valid_rx_start &
            self.mm.mq.tx_start <= rx_timeout
            ]).copy()

        subset['reachable'] = subset.applymap(mark_reachable_message, axis=1)
        subset = subset.loc[subset.reachable == True]

        if len(subset) > 0:
            interfering_set['rx_power'] = interfering_set.applymap(calc_power_message, axis=1)
            subset['rx_power'] = calc_power_message(subset)

            candidates = []
            for index_candidate, candidate in subset.sort_values(by=['tx_start'], ascending=False):
                interfering_power = 0
                for index_interferer, interferer in interfering_set.iterrows():
                    if interferer['message_hash'] is not candidate['message_hash'] or not (
                            (candidate['tx_start'] - 100E6) < interferer['tx_start'] < (candidate['tx_start'] + 100E6)):
                        interfering_power += np.pow(10, interferer['rx_power'] / 10)

                if np.pow(10, candidate['rx_power'] / 10) > (interfering_power + np.pow(10, RADIO_SNR[modulation])):
                    candidates.append(candidate['message'])

            if len(candidates) > 0:
                return candidates[0]
            else:
                return None
        else:
            return None

    def check_if_successfully_received(self, modulation, band, potential_message: 'SimMessage', rx_start, rx_node):
        rx_start = rx_node.transform_local_to_global_timestamp(rx_start)

        def calc_power_message(item):
            return self.calculate_path_loss(rx_node, self.network.nodes[item.source.id]) + item['power']

        interfering_set = (self.mm.mq.loc[
            self.mm.mq.modulation == modulation &
            self.mm.mq.band == band & self.mm.mq.event_type == 'tx' &
            self.mm.mq.tx_end > rx_start &
            self.mm.mq.tx_start < potential_message.tx_end &
            (
                    self.mm.mq.message_hash != potential_message.hash |
                    ((self.mm.mq.tx_start < (potential_message.tx_start - 100E6)) | (
                            self.mm.mq.tx_start > (potential_message.tx_start + 100E6)))
            )
            ]).copy()

        interfering_set['rx_power'] = interfering_set.applymap(calc_power_message, axis=1)
        potential_message['rx_power'] = calc_power_message(potential_message)

        interfering_power = 0
        for i in interfering_set.rx_power:
            interfering_power += np.pow(10, i / 10)

        if np.pow(10, potential_message.rx_power / 10) > (interfering_power + np.pow(10, RADIO_SNR[modulation])):
            return True
        else:
            return False

    def cad_process(self, timestamp, rx_node: 'sim_node.SimNode', modulation, band):
        timestamp = rx_node.transform_local_to_global_timestamp(timestamp)

        def mark_reachable_message(item):
            return self.network.is_reachable(rx_node, self.network.nodes[item.source], power=item.power)

        def calc_power_message(item):
            return self.network.calculate_path_loss(rx_node, self.network.nodes[item.source]) + item['power']

        config = RadioConfiguration(modulation)
        math = RadioMath(config)

        cad_start = timestamp - math.get_symbol_time() * (1.5 - 0.5)  # -0.5 as signal had to present for longer time
        cad_end = timestamp - math.get_symbol_time() * 0.5

        subset = (self.mm.mq.loc[
            self.mm.mq.modulation == modulation &
            self.mm.mq.band == band &
            self.mm.mq.tx_end >= cad_start &
            self.mm.mq.tx_start <= cad_end
            ]).copy()

        subset['reachable'] = subset.applymap(mark_reachable_message, axis=1)
        subset = subset.loc[subset.reachable == True]

        subset['rx_power'] = subset.applymap(calc_power_message, axis=1)

        if len(subset) > 0:
            return subset.rx_power.max()
        else:
            return None

    def calculate_path_loss(self, node_a: 'sim_node.SimNode', node_b: 'sim_node.SimNode'):
        return self.network.G[node_a.id, node_b.id]['path_loss']

    def is_reachable(self, modulation, node_a: 'sim_node.SimNode', node_b: 'sim_node.SimNode', power=22):
        config = RadioConfiguration(modulation)
        math = RadioMath(config)
        pl = self.calculate_path_loss(node_a, node_b)
        if pl <= -math.link_budget(power=power):
            return True
        else:
            return False
