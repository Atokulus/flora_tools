import logging
import os
import time
from typing import List

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

import lwb_slot
from flora_tools.flocklab.flocklab import FlockLab, FLOCKLAB_TARGET_ID_LIST, FLOCKLAB_TARGET_POSITIONS
from flora_tools.node import Node
from flora_tools.radio_configuration import RadioConfiguration
from lwb_slot import RADIO_MODULATIONS

ITERATIONS = 50
OFFSET = 0.2

POWER_LEVELS = [0, 1]
POWERS = [10, 22]


class MeasureGloriaExperiment:
    def __init__(self, ack=True):
        self.ack = ack
        self.nodes: List[Node] = None
        self.serial_nodes: List[Node] = None
        self.logger = logging.getLogger('flocklab_gloria_measurement')

        xmlfile = os.path.join(os.path.dirname(__file__), 'flocklab-dpp2lora-flora_cli.xml')
        flocklab = FlockLab()
        flocklab.schedule_test(xmlfile, self.run)

        # self.run()

    def run(self):
        self.connect_nodes()

        for i in range(ITERATIONS):
            for node in self.nodes:
                self.iterate_from_node(node)

        self.disconnect_nodes()

    def connect_nodes(self):
        self.nodes: List[Node] = [Node(flocklab=True, id=id, test=True) for id in FLOCKLAB_TARGET_ID_LIST]
        # self.nodes: List[Node] = []
        # self.serial_nodes = Node.get_serial_all()
        # self.nodes.extend(self.serial_nodes)

        for node in self.nodes:
            node.cmd('config set uid {:d}'.format(node.id))
            node.cmd('config set role 1')
            node.cmd('config store')
            node.cmd('system reset')
            node.interactive_mode(False)  # Enable single-line JSON Output

        time.sleep(0.1)

    def disconnect_nodes(self):
        for node in self.nodes:
            node.close()

    def iterate_from_node(self, tx_node: Node):
        for modulation in RADIO_MODULATIONS:
            self.logger.info("Gloria flood from Node {}".format(tx_node.id, modulation))

            sync_time = lwb_slot.LWBSlot.create_empty_slot(0, acked=False).total_time

            if self.ack:
                destination = np.random.choice([node for node in self.nodes if node.id != tx_node.id]).id
            else:
                destination = None

            message = "Hello World! from FlockLab Node {}, Mod: {}".format(tx_node.id, modulation)
            data_time = lwb_slot.LWBSlot.create_empty_slot(0, payload=lwb_slot.GLORIA_HEADER_LENGTH + len(message) + 1,
                                                           acked=self.ack).total_time

            for node in self.nodes:
                if node.id != tx_node.id:
                    self.sync(node, False)
            time.sleep(0.1)
            self.sync(tx_node, True)
            time.sleep(sync_time)

            for node in self.nodes:
                if node.id != tx_node.id:
                    self.receive(node, modulation, lwb_slot.GLORIA_HEADER_LENGTH + len(message) + 1, OFFSET, self.ack)
            self.send(tx_node, modulation, message, OFFSET, destination)

            time.sleep(data_time + OFFSET + 0.2)

    @staticmethod
    def sync(node: Node, tx: bool):
        if tx:
            node.cmd('gloria sync')
        else:
            node.cmd('gloria rx')

    @staticmethod
    def receive(node: Node, mod: int, message_len: int, offset: float, ack: bool):
        if ack:
            node.cmd('gloria rx -m {} -s {} -t {} -a'.format(
                mod,
                message_len,
                int(offset * 8E6)
            ))
        else:
            node.cmd('gloria rx -m {} -s {} -t {}'.format(
                mod,
                message_len,
                int(offset * 8E6)
            ))

    @staticmethod
    def send(node: Node, mod: int, message: str, offset: float, dst: int):
        if dst:
            node.cmd('gloria tx -m {} -p "{}" -t {} -d {}'.format(
                mod,
                message,
                int(offset * 8E6),
                dst
            ))
        else:
            node.cmd('gloria tx -m {} -p "{}" -t {}'.format(
                mod,
                message,
                int(offset * 8E6)
            ))

    @staticmethod
    def reconstruct_receptions(df, csv_path):
        receptions = [
            pd.DataFrame(
                columns=['tx_node',
                         'rx_node',
                         'modulation',
                         'timestamp',
                         'rx_slot',
                         'hop_count',
                         'power_level',
                         'acked',
                         'initial',
                         ],
                dtype='float')
        ]

        nodes = df.node_id.sort_values().unique()

        for node in nodes:

            subset = df[(df.node_id == node) & (df.rx == True)]
            counter = 0

            for index, row in subset.iterrows():
                counter += 1
                if (counter % 100) == 0:
                    print("{}@{}".format(index, node), end=',')

                if (type(row['output']) is dict
                        and 'type' in row['output']
                        and row['output']['type'] == 'gloria_flood'
                        and row['output']['initial'] is False
                        and row['output']['type'] != 1
                        and 'msg_src' in row['output']):
                    modulation = row['output']['mod']
                    tx_node = row['msg_src']['msg_src']

                    message = "Hello World! from FlockLab Node {}, Mod: {}".format(
                        tx_node, modulation)

                    receptions.append(pd.DataFrame({
                        'tx_node': [tx_node],
                        'rx_node': [row['node_id']],
                        'modulation': [modulation],
                        'timestamp': [row.timestamp],
                        'rx_slot': [row['output']['frst_rx_idx']],
                        'hop_count': [row['output']['msg_hop']],
                        'power_level': [row['output']['msg_pow']],
                        'acked': ([row['output']['acked'] if 'acked' in row['output'] else False]),
                        'initial': False
                    }))
                elif (type(row['output']) is dict
                      and 'type' in row['output']
                      and row['output']['type'] == 'gloria_flood'
                      and row['output']['initial'] is True
                      and row['output']['type'] != 1):

                    modulation = row['output']['mod']
                    tx_node = row['node_id']

                    message = "Hello World! from FlockLab Node {}, Mod: {}".format(
                        tx_node, modulation)

                    receptions.append(pd.DataFrame({
                        'tx_node': [tx_node],
                        'rx_node': [row['content']['msg_dst']],
                        'modulation': [modulation],
                        'timestamp': [row.timestamp],
                        'rx_slot': -2,
                        'hop_count': 0,
                        'power_level': lwb_slot.GLORIA_DEFAULT_POWER_LEVELS[0],
                        'acked': ([row['output']['acked'] if 'acked' in row['output'] else False]),
                        'initial': False
                    }))

        receptions = pd.concat(receptions, ignore_index=True)
        receptions.to_csv(csv_path)
        return receptions

    @staticmethod
    def draw_links(df, modulation: int, power_level: int, hop_count: int, tx_node='all', percentage=None,
                   iterations=None):
        if iterations is None:
            iterations = 1

        nodes = FLOCKLAB_TARGET_ID_LIST
        pos = FLOCKLAB_TARGET_POSITIONS

        G = nx.Graph()
        G.add_nodes_from(nodes)

        background = mpimg.imread(os.path.join(os.path.dirname(__file__), "map.png"))
        plt.imshow(background, aspect='auto', extent=(20, 1085, -580, 0), origin='upper')

        nx.draw_networkx_nodes(G, node_size=500, node_color='black', font_color='white', pos=pos)

        subset = df[(df.modulation == modulation) & (df.power_level == power_level) & (df.hop_count == hop_count)]

        groups = subset.groupby(['tx_node', 'rx_node', 'modulation'])

        for criteria, group in groups:
            count = group.shape[0]

            if (tx_node != criteria[1]
                    and (count / iterations <= percentage / 100.0 if iterations is not None else True)):
                G.add_edge(criteria[0], criteria[1], color=(0, 0, 0), weight=count / iterations * 5)

        edges = G.edges()
        colors = [G[u][v]['color'] for u, v in edges]
        weights = [G[u][v]['weight'] for u, v in edges]

        nx.draw_networkx_edges(G, pos=pos, edgelist=edges, edge_color=colors, width=weights,
                               alpha=(0.3 if tx_node is 'all' else 0.1))

        if tx_node is not 'all':
            subset = df[(df.tx_node == int(tx_node)) & (df.modulation == modulation) & (df.power_level == power_level)]
            groups = subset.groupby(['tx_node', 'rx_node', 'modulation'])

            edges = []
            hops = []

            for criteria, group in groups:
                count = group.shape[0]

                if count / iterations <= percentage / 100.0 if iterations is not None else True:
                    G.add_edge(int(tx_node), criteria[0], color=(0.1, 0.2, 0.8), weight=count / iterations * 5)
                    edges.append((int(tx_node), criteria[0]))
                    hops.append(group['hop_count'].mean())

            colors = [G[u][v]['color'] for u, v in edges]
            weights = [G[u][v]['weight'] for u, v in edges]

            nx.draw_networkx_edges(G, pos=pos, edgelist=edges, edge_color=colors, width=weights, alpha=0.8)

            edge_labels = dict([(edges[i], "{:.1f}".format(hops[i])) for i in range(len(edges))])
            nx.draw_networkx_edge_labels(G, pos=pos, edge_labels=edge_labels, font_size=10)

        plt.axis('off')

    @staticmethod
    def analyze_tx_count(receptions_no_ack, receptions_ack):

        with plt.style.context("bmh"):
            columns = ['modulation_name', 'tx_glossy', 'tx_gloria_no_ack', 'tx_gloria_ack', 'tx_gloria_ack_acks']
            tx_count = pd.DataFrame(columns=columns)
            tx_count.index.name = 'modulation'

            modulations = receptions_no_ack.modulation.sort_values().unique()

            for modulation in modulations:
                config = RadioConfiguration(modulation)

                subset_no_ack = receptions_no_ack[(receptions_no_ack.modulation == modulation)]
                subset_ack = receptions_ack[(receptions_ack.modulation == modulation)]

                slot_count_gloria_no_ack = (2 * lwb_slot.GLORIA_RETRANSMISSIONS_COUNTS[modulation] - 1) + (
                        lwb_slot.GLORIA_HOP_COUNTS[modulation] - 1)
                slot_count_gloria_ack = slot_count_gloria_no_ack * 2 - 1

                tx_glossy = lwb_slot.GLORIA_RETRANSMISSIONS_COUNTS[modulation]

                tx_gloria_no_ack = np.floor((slot_count_gloria_no_ack - subset_no_ack.rx_slot) / 2)
                tx_gloria_no_ack = np.clip(tx_gloria_no_ack, 0,
                                           lwb_slot.GLORIA_RETRANSMISSIONS_COUNTS[modulation]) * np.less(
                    subset_no_ack.hop_count, lwb_slot.GLORIA_HOP_COUNTS[modulation])
                tx_gloria_no_ack = np.mean(tx_gloria_no_ack)

                tx_gloria_ack = np.floor((slot_count_gloria_ack + 1 - subset_ack.rx_slot) / 4)
                tx_gloria_ack = np.clip(tx_gloria_ack, 0, lwb_slot.GLORIA_RETRANSMISSIONS_COUNTS[modulation]) * np.less(
                    subset_ack.hop_count, lwb_slot.GLORIA_HOP_COUNTS[modulation])
                tx_gloria_ack = np.mean(tx_gloria_ack)

                tx_gloria_ack_acks = np.mean(subset_ack.acked)

                tx_count.loc[len(columns)] = [config.modulation_name, tx_glossy, tx_gloria_no_ack, tx_gloria_ack,
                                              tx_gloria_ack_acks]

            fig = plt.figure(figsize=(10, 8))

            ax = plt.gca()
            plt.title("Flood Tx Activity on FlockLab ({} floods)".format(receptions_no_ack.shape[0]))

            glossy_rects = ax.bar(modulations - 0.3, tx_count.loc[:, 'tx_glossy'], width=0.2)
            gloria_no_ack_rects = ax.bar(modulations - 0.1, tx_count.loc[:, 'tx_gloria_no_ack'], width=0.2)
            gloria_acks_rects = ax.bar(modulations + 0.1, tx_count.loc[:, 'tx_gloria_ack'], width=0.2)
            gloria_acks_ack_rects = ax.bar(modulations + 0.3, tx_count.loc[:, 'tx_gloria_ack_acks'], width=0.2)

            for i, rect in zip(modulations, gloria_no_ack_rects):
                rect.set_fc(RadioConfiguration(i).color)

            rect = glossy_rects[0]
            ax.text(rect.get_x() + rect.get_width() / 2.,
                    rect.get_height() / 0,
                    "Glossy Tx",
                    rotation=90,
                    ha='center', va='center',
                    color='white')

            rect = gloria_no_ack_rects[0]
            ax.text(rect.get_x() + rect.get_width() / 2.,
                    rect.get_height() / 0,
                    "Gloria Tx without ACK",
                    rotation=90,
                    ha='center', va='center',
                    color='white')

            rect = gloria_acks_rects[0]
            ax.text(rect.get_x() + rect.get_width() / 2.,
                    rect.get_height() / 0,
                    "Gloria Tx with ACK",
                    rotation=90,
                    ha='center', va='center',
                    color='white')

            rect = gloria_acks_ack_rects[0]
            ax.text(rect.get_x() + rect.get_width() / 2.,
                    rect.get_height() / 0,
                    "Gloria ACKs",
                    rotation=90,
                    ha='center', va='center',
                    color='white')

            ax.grid(False)
            ax.grid(which='minor', axis='y', alpha=0.2)
            ax.grid(which='major', axis='y', alpha=0.5)
            plt.ylabel('Average Tx count')
            plt.xticks(modulations, map(RadioConfiguration.get_modulation_name, modulations))
