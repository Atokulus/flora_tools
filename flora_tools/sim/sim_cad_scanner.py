from flora_tools.gloria_flood import GloriaTimings
from flora_tools.lwb_slot import BANDS, MODULATIONS, LWBSlot
from flora_tools.radio_configuration import RadioConfiguration
from flora_tools.radio_math import RadioMath
from flora_tools.sim.sim_event_manager import SimEventType
from flora_tools.sim.sim_node import SimNode

SCAN_BANDS = BANDS

RX_SYMBOL_TIMEOUT = [LWBSlot.create_empty_slot(i) for i in MODULATIONS]
CAD_SYMBOL_TIMEOUT = [1, 1, 1]


class SimCADScanner:
    def __init__(self, node: 'SimNode', callback):
        self.node = node
        self.current_modulation = len(MODULATIONS) - 1
        self.current_band = SCAN_BANDS[0]
        self.callback = callback
        self.rx_start = None
        self.potential_message = None
        self.rx_timeout_event = None

        self.process_next_slot()

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

        self.rx_start = self.node.local_timestamp + GloriaTimings(self.current_modulation).rx_setup_time
        self.node.mm.register_rx(self.node,
                                 self.rx_start,
                                 self.current_modulation,
                                 self.current_band,
                                 self.process_tx_done_before_rx_timeout_callback)
        self.rx_timeout_event = self.node.em.register_event(self.rx_start + math.get_preamble_time(),
                                                            self.node,
                                                            SimEventType.RX_TIMEOUT,
                                                            self.process_rx_timeout)

    def process_tx_done_before_rx_timeout_callback(self, event):
        message = self.node.network.mc.receive_message_on_tx_done_before_rx_timeout(self.node,
                                                                                    self.current_modulation,
                                                                                    self.current_band,
                                                                                    event['data']['message'],
                                                                                    self.rx_start,
                                                                                    event['data']['message'].tx_start)
        if message is not None:
            self.node.em.unregister_event(self.rx_timeout_event)
            self.callback()

    def process_rx_timeout(self):
        self.potential_message = self.node.network.mc.receive_message_on_rx_timeout(modulation=self.current_modulation,
                                                                                    band=self.current_band,
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
        if self.node.network.mc.check_if_successfully_received(self.current_modulation, self.current_band,
                                                               self.potential_message, self.rx_start,
                                                               self.node):
            self.callback(self.potential_message)
        else:
            self.process_next_slot()

    def process_lora_cad(self):
        config = RadioConfiguration(modulation=self.current_modulation)
        math = RadioMath(config)

        self.node.em.register_event(self.node.local_timestamp + GloriaTimings(
            self.current_modulation).rx_setup_time + math.get_symbol_time() * (
                CAD_SYMBOL_TIMEOUT[self.current_modulation] + 0.5),
                                    self.node,
                                    SimEventType.CAD_DONE,
                                    self.process_lora_cad_done)

    def process_lora_cad_done(self):
        if self.node.network.mc.cad_process(modulation=self.current_modulation,
                                            band=self.current_band,
                                            rx_node=self.node,
                                            timestamp=self.node.local_timestamp) is not None:
            self.process_rx()
        else:
            self.process_next_slot()
