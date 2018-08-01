import logging
import time

import flora_tools.lwb_slot as lwb_slot
from flora_tools.node import Node
from flora_tools.radio_configuration import RadioConfiguration
from flora_tools.radio_math import RadioMath

ITERATIONS = 5

FLOCKLAB_TARGET_ID_LIST = [
    1, 3, 4, 8, 10, 13, 15, 20, 22, 23, 24, 25, 26, 28, 32, 33  # 11, 7 not working?
]

FLOCKLAB_TARGET_POSITIONS = {
    1: (110, 149), 3: (188, 359), 4: (171, 182), 7: (778, 237), 8: (166, 248), 10: (457, 323),
    11: (657, 240), 13: (711, 423), 15: (216, 246), 20: (579, 441), 22: (257, 461), 23: (397, 420),
    24: (424, 512), 25: (682, 353), 26: (538, 334), 28: (240, 425), 32: (289, 318), 33: (163, 306)
}


class MeasureLinksExperiment:
    def __init__(self):
        self.nodes = None
        self.logger = logging.getLogger('flocklab_link_measurement')

    def run(self):
        self.connect_nodes()

        for node in self.nodes:
            self.iterate_from_node(node)

        self.disconnect_nodes()

    def connect_nodes(self):
        self.nodes = [Node(flocklab=True, id=id) for id in FLOCKLAB_TARGET_ID_LIST]

        for node in self.nodes:
            node.interactive_mode(False)  # Enable single-line JSON Output

    def disconnect_nodes(self):
        for node in self.nodes:
            node.interactive_mode(True)
            node.close()

    def iterate_from_node(self, tx_node):
        for i in range(ITERATIONS):
            for modulation in lwb_slot.RADIO_MODULATIONS:
                for power in [0, 10, 22]:  # lwb_slot.POWERS:
                    self.logger.info("Running Tx on Node: {}, Mod: {}, Power: {}".format(tx_node.id, modulation, power))

                    config = RadioConfiguration(modulation)
                    math = RadioMath(config)

                    for node in self.nodes:
                        self.configure_node(node, (node.id == tx_node.id), modulation, power)
                        if node.id != tx_node.id:
                            self.receive(node)
                    time.sleep(0.2)
                    self.send(tx_node)
                    time.sleep(math.get_message_toa(len("Hello World!") + 1) * 2 + 0.1)

    @staticmethod
    def configure_node(node, tx: bool, modulation, power):
        config = RadioConfiguration(modulation, power=power, tx=tx)
        node.cmd(config.cmd)

    @staticmethod
    def receive(node):
        node.cmd('radio receive')

    @staticmethod
    def send(node):
        node.cmd('radio send "Hello World!"')
