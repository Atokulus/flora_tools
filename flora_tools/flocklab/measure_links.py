import time

from flora_tools.node import Node

from flora_tools.lwb_slot import POWERS, MODULATIONS
from flora_tools.radio_configuration import RadioConfiguration

TARGET_ID_LIST = [
    1, 3, 4, 7, 8, 10, 11, 13, 15, 20, 22, 23, 24, 25, 26, 28, 32, 33
]

ITERATIONS = 5


class MeasureLinksExperiment:
    def __init__(self):
        self.nodes = None

    def run(self):
        self.connect_nodes()

        for node in self.nodes:
            self.iterate_from_node(node)

        self.disconnect_nodes()

    def connect_nodes(self):
        self.nodes = [Node(flocklab=True, id=id) for id in TARGET_ID_LIST]

        for node in self.nodes:
            node.interactive_mode(False)  # Enable single-line JSON Output

    def disconnect_nodes(self):
        for node in self.nodes:
            node.interactive_mode(True)
            node.close()

    def iterate_from_node(self, tx_node):
        for i in range(ITERATIONS):
            for modulation in MODULATIONS:
                for power in POWERS:
                    for node in self.nodes:
                        self.configure_node(node, (node.id == tx_node.id), modulation, power)
                        if node.id != tx_node.id:
                            self.receive(node)
                    time.sleep(0.2)
                    self.send(tx_node)

    @staticmethod
    def configure_node(node, tx: bool, modulation, power):
        config = RadioConfiguration(modulation, power=power, tx=tx)
        node.cmd(config.cmd)

    @staticmethod
    def receive(node):
        node.cmd(b'radio receive')

    @staticmethod
    def send(node):
        node.cmd(b'radio send "Hello World!"')
