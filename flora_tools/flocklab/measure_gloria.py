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
from gloria import GLORIA_ACK_LENGTH
from lwb_slot import RADIO_MODULATIONS
from radio_math import RadioMath

ITERATIONS = 10
OFFSET = 0.5

POWER_LEVELS = [0, 1]
POWERS = [10, 22]


class MeasureGloriaExperiment:
    def __init__(self, ack=False, local=True, register_test=False):
        self.ack = ack
        self.nodes: List[Node] = None
        self.serial_nodes: List[Node] = None
        self.logger = logging.getLogger('flocklab_gloria_measurement')
        self.local = local

        if not local:
            if register_test:
                xmlfile = os.path.join(os.path.dirname(__file__), 'flocklab-dpp2lora-flora_cli.xml')
                flocklab = FlockLab()
                flocklab.schedule_test(xmlfile, self.run)
            else:
                self.run()
        else:
            self.run()

    def run(self):
        self.connect_nodes()

        for i in range(ITERATIONS):
            for node in self.nodes:
                self.iterate_from_node(node, i)

        self.disconnect_nodes()

    def connect_nodes(self):
        if not self.local:
            self.nodes: List[Node] = [Node(flocklab=True, id=id, test=True) for id in FLOCKLAB_TARGET_ID_LIST]
        else:
            self.nodes: List[Node] = []
            self.serial_nodes = Node.get_serial_all()
            self.nodes.extend(self.serial_nodes)

        for node in self.nodes:
            node.cmd('config set uid {:d}'.format(node.id))
            node.cmd('config set role 1')
            node.cmd('config store')
            node.cmd('system reset')
            node.interactive_mode(False)  # Enable single-line JSON Output
            #node.flush()

        time.sleep(0.2)

    def disconnect_nodes(self):
        for node in self.nodes:
            node.close()

    def iterate_from_node(self, tx_node: Node, iteration):
        for modulation in RADIO_MODULATIONS:
            if self.ack and lwb_slot.GLORIA_RETRANSMISSIONS_COUNTS[modulation] < 2 and lwb_slot.GLORIA_HOP_COUNTS[modulation] < 2:
                continue

            self.logger.info("{:4d}\tGloria flood from Node {} @ Mod {}".format(iteration, tx_node.id, modulation))

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
            time.sleep(0.15)
            self.sync(tx_node, True)
            time.sleep(sync_time)

            for node in self.nodes:
                if node.id != tx_node.id:
                    self.receive(node, modulation, lwb_slot.GLORIA_HEADER_LENGTH + len(message) + 1, OFFSET, self.ack)
            self.send(tx_node, modulation, message, OFFSET, destination)

            time.sleep(data_time + OFFSET + 0.3)

            for node in self.nodes:
                if not node.flocklab:
                    output = node.read()
                    if output:
                        self.logger.info("Node {} output: {}".format(node.id, output))

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
                         'remaining_tx',
                         'size',
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
                    print("{}@{}".format(counter, node), end=',')

                if (type(row['output']) is dict
                        and 'type' in row['output']
                        and row['output']['type'] == 'gloria_flood'
                        and row['output']['initial'] is False
                        and 'msg' in row['output']
                        and 'msg_src' in row['output']):

                    modulation = row['output']['mod']
                    tx_node = row['output']['msg_src']

                    message = "Hello World! from FlockLab Node {}, Mod: {}".format(
                        tx_node, modulation)

                    if message == row['output']['msg']:
                        receptions.append(pd.DataFrame({
                            'tx_node': [tx_node],
                            'rx_node': [row['node_id']],
                            'modulation': [modulation],
                            'timestamp': [row.timestamp],
                            'rx_slot': [row['output']['frst_rx_idx']],
                            'hop_count': [row['output']['msg_hop']],
                            'power_level': [row['output']['frst_pow']],
                            'acked': ([row['output']['acked'] if 'acked' in row['output'] else False]),
                            'initial': False,
                            'remaining_tx': [row['output']['rmn_tx']],
                            'size': [row['output']['msg_size']],
                        }))
                elif (type(row['output']) is dict
                      and 'type' in row['output']
                      and row['output']['type'] == 'gloria_flood'
                      and row['output']['initial'] is True
                      and 'msg_src' in row['output']):

                    modulation = row['output']['mod']
                    tx_node = row['node_id']

                    receptions.append(pd.DataFrame({
                        'tx_node': [tx_node],
                        'rx_node': [row['output']['msg_dst']],
                        'modulation': [modulation],
                        'timestamp': [row.timestamp],
                        'rx_slot': -1,
                        'hop_count': 0,
                        'power_level': lwb_slot.GLORIA_DEFAULT_POWER_LEVELS[0],
                        'acked': ([row['output']['acked'] if 'acked' in row['output'] else False]),
                        'initial': True,
                        'remaining_tx': [row['output']['rmn_tx']],
                        'size': [row['output']['msg_size']],
                    }))

        receptions = pd.concat(receptions, ignore_index=True)
        receptions.to_csv(csv_path)
        return receptions

    @staticmethod
    def draw_links(df, modulation: int, power_level: int, hop_count: int, tx_node='all'):

        nodes = FLOCKLAB_TARGET_ID_LIST
        pos = FLOCKLAB_TARGET_POSITIONS

        G = nx.Graph()
        G.add_nodes_from(nodes)

        background = mpimg.imread(os.path.join(os.path.dirname(__file__), "map.png"))
        plt.imshow(background, aspect='auto', extent=(20, 1085, -580, 0), origin='upper')

        nx.draw_networkx_nodes(G, node_size=500, node_color='black', font_color='white', pos=pos)

        subset = df[(df.modulation == modulation) & (df.hop_count == hop_count) & (df.power_level == power_level) & (
                df.initial == False)]

        groups = subset.groupby(['tx_node', 'rx_node', 'modulation'])

        for criteria, group in groups:
            iterations = df[
                (df.tx_node == criteria[0]) & (df.modulation == modulation) & (df.initial == True)
                ].initial.sum()

            count = group.shape[0]

            if tx_node != criteria[0]:
                G.add_edge(criteria[0], criteria[1], color=(0, 0, 0), weight=count / iterations * 5)

        edges = G.edges()
        colors = [G[u][v]['color'] for u, v in edges]
        weights = [G[u][v]['weight'] for u, v in edges]

        nx.draw_networkx_edges(G, pos=pos, edgelist=edges, edge_color=colors, width=weights,
                               alpha=(0.3 if tx_node is 'all' else 0.1))

        if tx_node is not 'all':
            subset = df[
                (df.tx_node == int(tx_node)) & (df.modulation == modulation) & (df.power_level == power_level) & (
                        df.initial == False)]
            groups = subset.groupby(['tx_node', 'rx_node', 'modulation'])

            edges = []
            hops = []

            for criteria, group in groups:
                iterations = df[
                    (df.tx_node == int(tx_node)) & (df.modulation == modulation) & (df.initial == True)
                    ].initial.sum()
                count = group.shape[0]

                G.add_edge(criteria[0], criteria[1], color=(0.1, 0.2, 0.8), weight=count / iterations * 5)
                edges.append((criteria[0], criteria[1]))
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
            columns = ['modulation_name', 'tx_gloria_no_ack', 'tx_gloria_ack', 'tx_gloria_ack_acks']
            tx_count = pd.DataFrame(columns=columns)
            tx_count.index.name = 'modulation'

            receptions_no_ack.modulation = receptions_no_ack.modulation.astype(int)
            receptions_ack.modulation = receptions_ack.modulation.astype(int)

            modulations = receptions_ack.modulation.sort_values().unique()

            for modulation in modulations:
                config = RadioConfiguration(modulation)

                subset_no_ack = receptions_no_ack[(receptions_no_ack.modulation == modulation)]
                subset_ack = receptions_ack[(receptions_ack.modulation == modulation)]

                tx_gloria_no_ack = lwb_slot.GLORIA_RETRANSMISSIONS_COUNTS[
                                       modulation] - subset_no_ack.remaining_tx.mean()
                tx_gloria_ack = lwb_slot.GLORIA_RETRANSMISSIONS_COUNTS[modulation] - subset_ack.remaining_tx.mean()
                tx_gloria_ack_acks = np.mean(subset_ack.acked)

                config = RadioConfiguration(modulation)
                math = RadioMath(config)

                msg_toa = math.get_message_toa(payload_size=50)  # receptions_ack[receptions_ack.size != 0].size.mean())

                ack_toa = math.get_message_toa(payload_size=GLORIA_ACK_LENGTH)
                ack_ratio = ack_toa / msg_toa

                tx_count.loc[len(tx_count)] = [config.modulation_name, tx_gloria_no_ack, tx_gloria_ack,
                                               tx_gloria_ack_acks * ack_ratio]


            fig = plt.figure(figsize=(10, 8))

            ax = plt.gca()
            plt.title("Average Transmission count of Gloria Flood on FlockLab (based on {} floods)".format(
                receptions_no_ack.shape[0]))

            gloria_no_ack_rects = ax.bar(modulations - 0.3, tx_count.loc[:, 'tx_gloria_no_ack'], width=0.3)
            gloria_acks_rects = ax.bar(modulations, tx_count.loc[:, 'tx_gloria_ack'], width=0.3)
            gloria_acks_ack_rects = ax.bar(modulations + 0.3, tx_count.loc[:, 'tx_gloria_ack_acks'], width=0.3)

            # for i, rect in zip(modulations, gloria_no_ack_rects):
            #    rect.set_fc(RadioConfiguration(i).color)

            rect = gloria_no_ack_rects[1]
            ax.text(rect.get_x() + rect.get_width() / 2,
                    rect.get_height() / 2,
                    "Gloria Tx without ACK",
                    rotation=90,
                    ha='center', va='center',
                    color='white')

            rect = gloria_acks_rects[1]
            ax.text(rect.get_x() + rect.get_width() / 2,
                    rect.get_height() / 2,
                    "Gloria Tx with ACK",
                    rotation=90,
                    ha='center', va='center',
                    color='white')

            rect = gloria_acks_ack_rects[1]
            ax.text(rect.get_x() + rect.get_width() / 2,
                    rect.get_height() / 2,
                    "Gloria ACKs",
                    rotation=90,
                    ha='center', va='center',
                    color='white')

            ax.grid(False)
            ax.grid(which='minor', axis='y', alpha=0.2)
            ax.grid(which='major', axis='y', alpha=0.5)
            plt.ylabel('Average Tx count')
            plt.xticks(modulations, map(RadioConfiguration.get_modulation_name, modulations))
