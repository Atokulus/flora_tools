from flora_tools.sim.sim_node import SimNode
from flora_tools.lwb_math import modulations
from flora_tools.gloria_math import GloriaMath
from flora_tools.radio_configuration import RadioConfiguration
from flora_tools.radio_math import RadioMath
from flora_tools.sim.sim_event_manager import SimEventType

CAD_SYMBOL_TIMEOUT = [1, 1, 1]


class SimChannelScanner:
    def __init__(self, node: 'SimNode', callback):
        self.node = node
        self.current_modulation = len(modulations) - 1
        self.callback = callback
        self.rx_start = None
        self.potential_message = None

        config = RadioConfiguration(modulation=self.current_modulation)

        if config.modem is 'FSK':
            self.process_fsk_rx()
        else:
            self.process_lora_cad()

    def process_next_slot(self):
        self.current_modulation -= 1

        config = RadioConfiguration(modulation=self.current_modulation)

        if self.current_modulation >= 1:
            if config.modem is 'FSK':
                self.process_rx()
            else:
                self.process_lora_cad()
        else:
            self.callback()

    def process_rx(self):
        config = RadioConfiguration(modulation=self.current_modulation)
        math = RadioMath(config)

        self.rx_start = self.node.local_timestamp + GloriaMath().rx_setup_time

        self.node.em.register_event(self.rx_start + math.get_preamble_time(),
                                    self.node,
                                    SimEventType.RX_TIMEOUT,
                                    self.process_rx_timeout)

    def process_rx_timeout(self):
        self.potential_message = self.node.network.mc.get_potential_rx_message(modulation=self.flood['modulation'],
                                                                               band=self.flood['band'],
                                                                               rx_node=self.node,
                                                                               rx_start=self.rx_start,
                                                                               rx_timeout=self.node.local_timestamp)

        if self.potential_message is not None:
            self.node.em.register_event(self.potential_message.tx_end,
                                        self.node,
                                        SimEventType.RX_DONE,
                                        self.process_rx_done)
        else:
            self.process_next_slot()

    def process_rx_done(self):
        if self.node.network.mc.check_if_successfully_received(self.flood['modulation'], self.flood['band'],
                                                               self.potential_message, self.node.local_timestamp,
                                                               self.node):
            self.callback(self.potential_message)
        else:
            self.process_next_slot()

    def process_lora_cad(self):
        config = RadioConfiguration(modulation=self.current_modulation)
        math = RadioMath(config)

        self.node.em.register_event(self.node.local_timestamp + GloriaMath().rx_setup_time + math.get_symbol_time() * (
                    CAD_SYMBOL_TIMEOUT[self.current_modulation] + 0.5),
                                    self.node,
                                    SimEventType.CAD_DONE,
                                    self.process_lora_cad_done)

    def process_lora_cad_done(self):
        if self.node.network.mc.cad_process(modulation=self.flood['modulation'],
                                            band=self.flood['band'],
                                            rx_node=self.node,
                                            timestamp=self.node.local_timestamp):
            self.process_rx()
        else:
            self.process_next_slot()
