import logging
import os
import time
from typing import List

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

import flora_tools.lwb_slot as lwb_slot
from flora_tools.flocklab.flocklab import FlockLab
from flora_tools.node import Node
from flora_tools.radio_configuration import RadioConfiguration
from flora_tools.radio_math import RadioMath

ITERATIONS = 5
POWERS = [0, 10, 22]
PREAMBLES = [2, 3, 4, 6, 8, 10, 12]

FLOCKLAB_TARGET_ID_LIST = [
    1, 3, 4, 8, 10, 13, 15, 20, 22, 23, 24, 25, 26, 28, 32, 33  # 11, 7 not working?
]

FLOCKLAB_TARGET_POSITIONS = {
    1: (110, -149), 3: (188, -359), 4: (171, -182), 7: (778, -237), 8: (166, -248), 10: (457, -323),
    11: (657, -240), 13: (711, -423), 15: (216, -246), 20: (579, -441), 22: (257, -461), 23: (397, -420),
    24: (424, -512), 25: (682, -353), 26: (538, -334), 28: (240, -425), 32: (289, -318), 33: (163, -306)
}


class MeasureLinksExperiment:
    def __init__(self, local=False, register_test=False):
        self.nodes: List[Node] = None
        self.serial_nodes: List[Node] = None
        self.logger = logging.getLogger('flocklab_link_measurement')

        self.local = local

        if register_test:
            xmlfile = os.path.join(os.path.dirname(__file__), 'flocklab-dpp2lora-flora_cli.xml')
            flocklab = FlockLab()
            flocklab.schedule_test(xmlfile, self.run)
        else:
            self.run()

    def run(self):
        self.connect_nodes()

        for i in range(ITERATIONS):
            for node in self.nodes:
                self.iterate_from_node(node)

        self.disconnect_nodes()

    def connect_nodes(self):
        self.nodes = [Node(flocklab=True, id=id, test=False) for id in FLOCKLAB_TARGET_ID_LIST]
        if self.local:
            self.serial_nodes = Node.get_serial_all()
            self.nodes.extend(self.serial_nodes)

        for node in self.nodes:
            node.interactive_mode(False)  # Enable single-line JSON Output

    def disconnect_nodes(self):
        for node in self.nodes:
            node.interactive_mode(True)
            node.close()

    def iterate_from_node(self, tx_node: Node):
        for preamble_len in PREAMBLES:
            for modulation in lwb_slot.RADIO_MODULATIONS:
                for power in POWERS:  # lwb_slot.POWERS:
                    self.logger.info(
                        "Tx on Node {}: Mod: {}, Power: {}, Preamble_Length: {}".format(
                            tx_node.id, modulation, power, preamble_len))

                    config = RadioConfiguration(modulation, preamble=preamble_len)
                    math = RadioMath(config)

                    message = "Hello World! from FlockLab Node {}: Mod: {}, Pow: {}, Prmbl: {}".format(
                        tx_node.id, modulation, power, preamble_len)

                    for node in self.nodes:
                        self.configure_node(node, (node.id == tx_node.id), modulation, power, preamble_len)
                        if node.id != tx_node.id:
                            self.receive(node)
                    time.sleep(0.1)
                    self.send(tx_node, message=message)
                    time.sleep(math.get_message_toa(len(message) + 1) * 1.5 + 0.1)

    @staticmethod
    def configure_node(node: Node, tx: bool, modulation, power, preamble: int):
        config = RadioConfiguration(modulation, power=power, tx=tx, preamble=preamble)
        node.cmd(config.cmd)

    @staticmethod
    def receive(node: Node):
        node.cmd('radio receive')

    @staticmethod
    def send(node, message):
        node.cmd('radio send "{}"'.format(message))

    @staticmethod
    def reconstruct_receptions(df, csv_path):
        receptions = [
            pd.DataFrame(
                columns=['tx_node', 'rx_node', 'modulation', 'power', 'preamble', 'rssi', 'snr', 'timestamp'],
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
                        and row['output']['type'] == 'radio_cfg'
                        and 'power' in row['output']):

                    modulation = row['output']['modulation']
                    power = row['output']['power']
                    preamble = row['output']['preamble']

                    config = RadioConfiguration(modulation, preamble=preamble)
                    math = RadioMath(config)

                    message = "Hello World! from FlockLab Node {}: Mod: {:d}, Pow: {:d}, Prmbl: {:d}".format(
                        node, modulation, power, preamble)

                    offset = math.get_message_toa(len(message) + 1) * 1.5 + 0.3

                    rx_subset = df[(df.timestamp > row.timestamp)
                                   & (df.timestamp < (row.timestamp + offset))
                                   & (df.node_id != node)
                                   & (df.rx == True)]

                    receptions.append(pd.DataFrame({
                        'tx_node': [node],
                        'rx_node': [None],
                        'modulation': [modulation],
                        'power': [power],
                        'preamble': [preamble],
                        'rssi': [None],
                        'snr': [None],
                        'timestamp': [row.timestamp],
                    }))

                    for rx_index, rx_row in rx_subset.iterrows():
                        if (type(rx_row['output']) is dict
                                and 'type' in rx_row['output']
                                and rx_row['output']['type'] == 'radio_rx_msg'
                                and 'text' in rx_row['output']
                                and rx_row['output']['text'] == message):
                            receptions.append(pd.DataFrame({
                                'tx_node': [node],
                                'rx_node': [rx_row['node_id']],
                                'modulation': [modulation],
                                'power': [power],
                                'preamble': [preamble],
                                'rssi': [rx_row['output']['rssi']],
                                'snr': [rx_row['output']['snr']],
                                'timestamp': [row.timestamp],
                            }))

        receptions = pd.concat(receptions, ignore_index=True)

        receptions.to_csv(csv_path)
        return receptions

    @staticmethod
    def draw_links(df, tx_node='all', percentage=None):
        nodes = FLOCKLAB_TARGET_ID_LIST
        pos = FLOCKLAB_TARGET_POSITIONS

        G = nx.Graph()
        G.add_nodes_from(nodes)

        background = mpimg.imread(os.path.join(os.path.dirname(__file__), "map.png"))
        plt.imshow(background, aspect='auto', extent=(20, 1085, -580, 0), origin='upper')

        nx.draw_networkx_nodes(G, node_size=500, node_color='black', font_color='white', pos=pos)

        groups = df.groupby(['tx_node', 'rx_node', 'modulation', 'power', 'preamble'])

        for criteria, group in groups:
            iterations = df[df.tx_node == criteria[0]].rx_node.isnull().sum()
            count = group.shape[0]

            if (tx_node != criteria[1]
                    and count <= iterations * percentage):
                G.add_edge(criteria[0], criteria[1], color=(0, 0, 0), weight=count / iterations * 5)

        edges = G.edges()
        colors = [G[u][v]['color'] for u, v in edges]
        weights = [G[u][v]['weight'] for u, v in edges]

        nx.draw_networkx_edges(G, pos=pos, edgelist=edges, edge_color=colors, width=weights,
                               alpha=(0.3 if tx_node is 'all' else 0.1))

        if tx_node is not 'all':
            subset = df[df.tx_node == int(tx_node)]
            groups = subset.groupby(['rx_node', 'modulation', 'power', 'preamble'])

            edges = []
            rssi = []

            for criteria, group in groups:
                iterations = df[df.tx_node == criteria[0]].rx_node.isnull().sum()
                count = group.shape[0]

                if count <= iterations * percentage:
                    G.add_edge(int(tx_node), criteria[0], color=(0.1, 0.2, 0.8), weight=count / iterations * 5)
                    edges.append((int(tx_node), criteria[0]))
                    rssi.append(group['rssi'].mean())

            colors = [G[u][v]['color'] for u, v in edges]
            weights = [G[u][v]['weight'] for u, v in edges]

            nx.draw_networkx_edges(G, pos=pos, edgelist=edges, edge_color=colors, width=weights, alpha=0.8)

            edge_labels = dict([(edges[i], "{:.2f}".format(rssi[i])) for i in range(len(edges))])
            nx.draw_networkx_edge_labels(G, pos=pos, edge_labels=edge_labels, font_size=10)

        plt.axis('off')
