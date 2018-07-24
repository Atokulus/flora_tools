from typing import Tuple, Optional

import numpy as np

import flora_tools.gloria as gloria
import flora_tools.lwb_slot as lwb_slot
import flora_tools.sim.sim_network as sim_network
import flora_tools.sim.sim_node as sim_node
from flora_tools.radio_configuration import RadioConfiguration
from flora_tools.radio_math import RadioMath, RADIO_SNR
from flora_tools.sim.sim_message import SimMessage


class SimMessageChannel:
    def __init__(self, network: 'sim_network.SimNetwork'):
        self.network = network
        self.mm = network.mm

    def receive_message_on_tx_done_before_rx_timeout(
            self, rx_node: 'sim_node.SimNode', modulation, band,
            message: SimMessage,
            rx_start: float, tx_start: float, transmission
    ) -> Tuple[Optional[SimMessage], Optional['sim_node.SimNode']]:
        if not self.is_reachable(modulation, rx_node, message.source,
                                 lwb_slot.POWERS[message.power_level]):
            return None, None

        config = RadioConfiguration(modulation, preamble=gloria.GloriaTimings(modulation).preamble_len)
        math = RadioMath(config)

        valid_rx_start = rx_start + math.get_symbol_time() * 0.1

        if valid_rx_start > message.tx_start:
            return None, None

        interfering_set = (self.mm.mq.loc[
            (self.mm.mq.modulation == modulation) &
            (self.mm.mq.band == band) &
            (self.mm.mq.tx_end >= message.tx_start) &
            (self.mm.mq.tx_start <= message.tx_end)
            ]).copy()

        def calc_power_message(item):
            return -self.calculate_path_loss(rx_node, item.source) + item.power

        interfering_set['rx_power'] = interfering_set.apply(calc_power_message, axis=1)
        rx_power = -self.calculate_path_loss(rx_node, message.source) + lwb_slot.POWERS[message.power_level]

        interfering_power = 0
        for interferer_index, interferer in interfering_set.iterrows():
            if interferer['message_hash'] != message.hash or not (
                    (tx_start - 100E6) < interferer['tx_start'] < (tx_start + 100E6)):
                interfering_power += np.power(10, interferer['rx_power'] / 10)

        if np.power(10, rx_power / 10) > (interfering_power * np.power(10, RADIO_SNR[modulation])):
            rx_node.mm.unregister_rx(rx_node)
            return message.copy(), transmission['source']
        else:
            return None, None

    def receive_message_on_rx_timeout(self, modulation, band, rx_node: 'sim_node.SimNode', rx_start,
                                      rx_timeout) -> Tuple[Optional[SimMessage], Optional['sim_node.SimNode']]:
        self.mm.unregister_rx(rx_node)
        rx_start = rx_node.transform_local_to_global_timestamp(rx_start)

        def mark_reachable_message(item):
            return self.is_reachable(modulation, rx_node, item['source'], power=item['power'])

        def calc_power_message(item):
            return -self.calculate_path_loss(rx_node, self.network.nodes[item.source.id]) + item['power']

        config = RadioConfiguration(modulation)
        math = RadioMath(config)

        valid_rx_start = rx_start + math.get_symbol_time() * 0.1
        keep_quiet_start = rx_start - 100E-6

        interfering_set = (self.mm.mq.loc[
            (self.mm.mq.band == band) &
            (self.mm.mq.tx_end >= keep_quiet_start) &
            (self.mm.mq.tx_start <= valid_rx_start)
            ]).copy()

        subset = (self.mm.mq.loc[
            (self.mm.mq.modulation == modulation) &
            (self.mm.mq.band == band) &
            (self.mm.mq.tx_start >= valid_rx_start) &
            (self.mm.mq.tx_start <= rx_timeout) &
            (self.mm.mq.tx_end > rx_timeout)
            ]).copy()

        if len(subset):
            subset['reachable'] = subset.apply(mark_reachable_message, axis=1)
            subset = subset.loc[subset.reachable == True]

            if len(subset) > 0:
                if len(interfering_set):
                    interfering_set['rx_power'] = interfering_set.apply(calc_power_message, axis=1)

                subset['rx_power'] = subset.apply(calc_power_message, axis=1)

                candidates = []
                for index_candidate, candidate in subset.sort_values(by=['tx_start'], ascending=False).iterrows():
                    interfering_power = 0
                    for index_interferer, interferer in interfering_set.iterrows():
                        if interferer['message_hash'] is not candidate['message_hash'] or not (
                                (candidate['tx_start'] - 100E6) < interferer['tx_start'] < (
                                candidate['tx_start'] + 100E6)):
                            interfering_power += np.power(10, interferer['rx_power'] / 10)

                    if np.power(10, candidate['rx_power'] / 10) > (
                            interfering_power * np.power(10, RADIO_SNR[modulation] / 10)):
                        candidates.append(candidate)

                if len(candidates) > 0:
                    return candidates[0]['message'].copy(), candidates[0]['source']
                else:
                    return None, None
            else:
                return None, None
        else:
            return None, None

    def check_if_successfully_received(self, modulation, band, potential_message: 'SimMessage', rx_start: float,
                                       rx_node: 'sim_node.SimNode', tx_node: 'sim_node.SimNode'):
        rx_start = rx_node.transform_local_to_global_timestamp(rx_start)

        def calc_power_message(item):
            return -self.calculate_path_loss(rx_node, item['source']) + lwb_slot.POWERS[item['message'].power_level]

        interfering_set = (self.mm.mq.loc[
            (self.mm.mq.modulation == modulation) &
            (self.mm.mq.band == band) &
            (self.mm.mq.tx_end > rx_start) &
            (self.mm.mq.tx_start < potential_message.tx_end) &
            (
                    (self.mm.mq.message_hash != potential_message.hash) |
                    ((self.mm.mq.tx_start < (potential_message.tx_start - 100E6)) |
                     (self.mm.mq.tx_start > (potential_message.tx_start + 100E6)))
            )
            ]).copy()

        if len(interfering_set):
            interfering_set['rx_power'] = interfering_set.apply(calc_power_message, axis=1)

        rx_power = calc_power_message({'message': potential_message, 'source': tx_node})

        interfering_power = 0
        if len(interfering_set):
            for i in interfering_set.rx_power:
                interfering_power += np.power(10, i / 10)

        if np.power(10, rx_power / 10) > (interfering_power * np.power(10, RADIO_SNR[modulation] / 10)):
            return True
        else:
            return False

    def cad_process(self, timestamp, rx_node: 'sim_node.SimNode', modulation, band):
        timestamp = rx_node.transform_local_to_global_timestamp(timestamp)

        def mark_reachable_message(item):
            return self.is_reachable(modulation, rx_node, item.source, power=item.power)

        def calc_power_message(item):
            return -self.calculate_path_loss(rx_node, item.source) + item.power

        config = RadioConfiguration(modulation)
        math = RadioMath(config)

        cad_start = timestamp - math.get_symbol_time() * (1.5 - 0.5)  # -0.5 as signal had to present for longer time
        cad_end = timestamp - math.get_symbol_time() * 0.5

        subset = (self.mm.mq.loc[
            (self.mm.mq.modulation == modulation) &
            (self.mm.mq.band == band) &
            (self.mm.mq.tx_end >= cad_start) &
            (self.mm.mq.tx_start <= cad_end)
            ]).copy()

        if len(subset):
            subset.loc[:, 'reachable'] = subset.apply(mark_reachable_message, axis=1)
            subset = subset.loc[subset.reachable == True]

            if len(subset):
                subset.loc[:, 'rx_power'] = subset.apply(calc_power_message, axis=1)

                return subset.rx_power.max()

            else:
                return None
        else:
            return None

    def calculate_path_loss(self, node_a: 'sim_node.SimNode', node_b: 'sim_node.SimNode'):
        if node_a is not node_b:
            return self.network.G[node_a.id][node_b.id]['path_loss']
        else:
            return 0

    def is_reachable(self, modulation, node_a: 'sim_node.SimNode', node_b: 'sim_node.SimNode', power=22):
        config = RadioConfiguration(modulation)
        math = RadioMath(config)
        pl = self.calculate_path_loss(node_a, node_b)

        if pl <= math.link_budget(power=power):
            return True
        else:
            return False
