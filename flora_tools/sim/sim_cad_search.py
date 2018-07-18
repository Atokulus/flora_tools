import flora_tools.gloria as gloria
import flora_tools.lwb_slot as lwb_slot
import flora_tools.sim.sim_node as sim_node
from flora_tools.radio_configuration import RadioConfiguration
from flora_tools.radio_math import RadioMath
from flora_tools.sim.sim_event_manager import SimEventType

CAD_SYMBOL_TIMEOUT = [1, 1, 1]


class SimCADSearch:
    def __init__(self, node: 'sim_node.SimNode', callback, start_modulation: int=None):
        self.node = node
        if start_modulation is not None:
            self.current_modulation = start_modulation
        else:
            self.current_modulation = len(lwb_slot.MODULATIONS)
        self.current_band = gloria.BANDS[0]
        self.callback = callback
        self.rx_start = None
        self.potential_message = None
        self.rx_timeout_event = None

        self.radio_config: RadioConfiguration = None
        self.radio_math: RadioMath = None

        self.process_next_slot()

    @property
    def rx_symbol_timeout(self):
        return [lwb_slot.LWBSlot.create_empty_slot(i).total_time for i in range(len(lwb_slot.MODULATIONS))]

    def process_next_slot(self):
        self.current_modulation -= 1

        if self.current_modulation >= 0:
            self.radio_config = RadioConfiguration(modulation=lwb_slot.MODULATIONS[self.current_modulation])
            self.radio_math = RadioMath(self.radio_config)

            if self.radio_config.modem is 'FSK':
                self.process_rx()
            else:
                self.process_lora_cad()
        else:
            self.callback(None)

    def process_rx(self):
        self.rx_start = self.node.local_timestamp + gloria.GloriaTimings(
            lwb_slot.MODULATIONS[self.current_modulation]).rx_setup_time
        self.node.mm.register_rx(self.node,
                                 self.rx_start,
                                 lwb_slot.MODULATIONS[self.current_modulation],
                                 self.current_band,
                                 self.process_tx_done_before_rx_timeout_callback)
        self.rx_timeout_event = self.node.em.register_event(
            self.rx_start + self.rx_symbol_timeout[self.current_modulation],
            self.node,
            SimEventType.RX_TIMEOUT,
            self.process_rx_timeout)

    def process_tx_done_before_rx_timeout_callback(self, event):
        message = self.node.network.mc.receive_message_on_tx_done_before_rx_timeout(self.node,
                                                                                    lwb_slot.MODULATIONS[
                                                                                        self.current_modulation],
                                                                                    self.current_band,
                                                                                    event['data']['message'],
                                                                                    self.rx_start,
                                                                                    event['data']['message'].tx_start)
        if message is not None:
            self.node.local_timestamp = message.tx_end

            self.node.em.unregister_event(self.rx_timeout_event)
            self.callback()

    def process_rx_timeout(self, event):
        self.potential_message = self.node.network.mc.receive_message_on_rx_timeout(
            modulation=lwb_slot.MODULATIONS[self.current_modulation],
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
            self.node.local_timestamp = self.potential_message.tx_end
            self.callback(self.potential_message)
        else:
            self.process_next_slot()

    def process_lora_cad(self):

        self.node.em.register_event(self.node.local_timestamp + gloria.GloriaTimings(
            self.current_modulation).rx_setup_time + self.radio_math.get_symbol_time() * (
                                            CAD_SYMBOL_TIMEOUT[self.current_modulation] + 0.5),
                                    self.node,
                                    SimEventType.CAD_DONE,
                                    self.process_lora_cad_done)

    def process_lora_cad_done(self):
        if self.node.network.mc.cad_process(modulation=lwb_slot.MODULATIONS[self.current_modulation],
                                            band=self.current_band,
                                            rx_node=self.node,
                                            timestamp=self.node.local_timestamp) is not None:
            self.process_rx()
        else:
            self.process_next_slot()
