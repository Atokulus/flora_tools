import numpy as np

import flora_tools.gloria as gloria_flood
import flora_tools.lwb_slot as lwb_slot
import flora_tools.sim.sim_event_manager as sim_event_manager
import flora_tools.sim.sim_node as sim_node
from flora_tools.sim.sim_message import SimMessage, SimMessageType

MAX_ACKS = 1


class SimGloriaFlood:
    def __init__(self, node: 'sim_node.SimNode', flood: 'gloria_flood.GloriaFlood', callback,
                 init_tx_message: SimMessage = None,
                 power_increase=True, update_timestamp=False):
        self.node = node
        self.flood = flood
        self.finished_callback = callback
        self.tx_message = init_tx_message
        self.slot_index = 0
        self.first_rx_slot_index = (-2 if self.flood.acked else -1)
        self.is_ack = False
        self.retransmission_count = flood.retransmission_count
        self.hop_count = flood.hop_count
        self.ack_counter = 0
        self.potential_message: SimMessage = None
        self.potential_node: sim_node.SimNode = None
        self.ack_message = None
        self.is_initial_node = True if init_tx_message is not None else False
        self.power_increase = power_increase
        self.update_timestamp = update_timestamp
        self.rx_timeout_event = None

        slot = flood.slots[self.slot_index]
        self.last_slot = slot

        if init_tx_message is not None:
            self.tx_message.timestamp = slot.tx_marker

            if self.valid_to_send():

                self.node.mm.tx(self.node,
                                self.flood.modulation,
                                self.flood.band,
                                self.tx_message)

                self.node.em.register_event(slot.tx_done_marker,
                                            self.node, sim_event_manager.SimEventType.TX_DONE,
                                            self.progress_gloria_flood)

                if (self.power_increase and
                        self.tx_message.power_level < len(lwb_slot.POWERS) - 1):
                    self.tx_message.power_level += 1
                self.retransmission_count -= 1
            else:
                self.finished_callback(None)

        else:
            self.node.mm.register_rx(self.node,
                                     slot.rx_marker,
                                     flood.modulation,
                                     flood.band,
                                     self.progress_gloria_flood)
            self.rx_timeout_event = self.node.em.register_event(slot.rx_timeout_marker,
                                                                self.node,
                                                                sim_event_manager.SimEventType.RX_TIMEOUT,
                                                                self.progress_gloria_flood)

    def progress_gloria_flood(self, event):
        if event['type'] is sim_event_manager.SimEventType.TX_DONE:
            if self.is_ack:
                self.process_next_ack()
            else:
                self.slot_index += 1
                if self.slot_index < len(self.flood.slots) and \
                        self.flood.slots[self.slot_index].rx_marker > self.node.local_timestamp:

                    slot = self.flood.slots[self.slot_index]

                    self.node.mm.register_rx(self.node,
                                             slot.rx_marker,
                                             self.flood.modulation,
                                             self.flood.band,
                                             self.progress_gloria_flood)

                    self.rx_timeout_event = self.node.em.register_event(slot.rx_timeout_marker,
                                                                        self.node,
                                                                        sim_event_manager.SimEventType.RX_TIMEOUT,
                                                                        self.progress_gloria_flood)
                else:
                    self.finished_callback(self.tx_message)

        elif event['type'] is sim_event_manager.SimEventType.TX_DONE_BEFORE_RX_TIMEOUT:
            slot = self.flood.slots[self.slot_index]

            message, tx_node = self.node.network.mc.receive_message_on_tx_done_before_rx_timeout(
                self.node,
                self.flood.modulation,
                self.flood.band,
                event['data']['message'],
                slot.rx_marker,
                event['data']['message'].tx_start,
                transmission=event['data'])
            if message is not None:
                self.potential_message = message
                self.potential_node = tx_node
                self.node.em.remove_all_events(self.node, sim_event_manager.SimEventType.RX_TIMEOUT)
                self.process_rx_message()

        elif event['type'] is sim_event_manager.SimEventType.RX_TIMEOUT:
            slot = self.flood.slots[self.slot_index]
            self.potential_message, self.potential_node = self.node.network.mc.receive_message_on_rx_timeout(
                modulation=self.flood.modulation,
                band=self.flood.band,
                rx_node=self.node,
                rx_start=slot.rx_marker,
                rx_timeout=self.node.local_timestamp)

            if self.potential_message is not None:
                self.node.em.register_event(np.max([self.potential_message.tx_end, slot.rx_end_marker]),
                                            self.node,
                                            sim_event_manager.SimEventType.RX_DONE,
                                            self.progress_gloria_flood)

            else:
                self.process_next_slot()

        elif event['type'] is sim_event_manager.SimEventType.RX_DONE:
            slot = self.flood.slots[self.slot_index]

            if self.node.network.mc.check_if_successfully_received(self.flood.modulation, self.flood.band,
                                                                   self.potential_message, slot.rx_marker,
                                                                   self.node, self.potential_node):
                self.process_rx_message()
            else:
                if (self.power_increase and
                        self.tx_message.power_level < len(lwb_slot.POWERS) - 1):
                    self.tx_message.power_level += 1

                self.process_next_slot()
        else:
            self.finished_callback(self.tx_message)

    def process_rx_message(self):
        slot = self.flood.slots[self.slot_index]

        if (slot.type in [gloria_flood.GloriaSlotType.RX_ACK,
                          gloria_flood.GloriaSlotType.TX_ACK]
                and self.potential_message.type is SimMessageType.ACK):
            self.is_ack = True
            self.ack_message = self.potential_message

            self.process_next_ack()
        else:
            if not self.is_initial_node:
                if self.tx_message is None:
                    self.tx_message = self.potential_message
                    self.tx_message.freeze()
                    self.first_rx_slot_index = self.slot_index
                elif (self.power_increase
                      and self.tx_message.power_level < len(lwb_slot.POWERS) - 1):
                    self.tx_message.power_level += 1

                if self.update_timestamp:
                    self.update_local_timestamp(slot, self.potential_message)

            self.process_next_slot()

    def process_next_slot(self):
        self.slot_index += 1

        if self.is_not_finished():
            slot = self.flood.slots[self.slot_index]

            if slot.type in [gloria_flood.GloriaSlotType.RX_ACK, gloria_flood.GloriaSlotType.TX_ACK]:
                if self.tx_message is not None and self.tx_message.destination is self.node and self.ack_message is None:
                    self.is_ack = True

                    self.ack_message = SimMessage(slot.tx_marker,
                                                  source=self.tx_message.source,
                                                  payload=lwb_slot.gloria_header_length,
                                                  destination=self.tx_message.source,
                                                  type=SimMessageType.ACK,
                                                  power_level=self.tx_message.power_level,
                                                  modulation=self.tx_message.modulation)
                    self.node.mm.tx(self.node,
                                    self.flood.modulation,
                                    self.flood.band,
                                    self.ack_message)

                    self.node.em.register_event(slot.tx_done_marker,
                                                self.node, sim_event_manager.SimEventType.TX_DONE,
                                                self.progress_gloria_flood)

                    self.ack_counter += 1
                elif self.ack_message is not None:
                    self.ack_message.timestamp = slot.tx_marker

                    self.node.mm.tx(self.node,
                                    self.flood.modulation,
                                    self.flood.band,
                                    self.ack_message)

                    self.node.em.register_event(slot.tx_done_marker,
                                                self.node, sim_event_manager.SimEventType.TX_DONE,
                                                self.progress_gloria_flood)

                    self.ack_counter += 1

                else:
                    self.node.mm.register_rx(self.node,
                                             slot.rx_marker,
                                             self.flood.modulation,
                                             self.flood.band,
                                             self.progress_gloria_flood)

                    self.rx_timeout_event = self.node.em.register_event(slot.rx_timeout_marker,
                                                                        self.node,
                                                                        sim_event_manager.SimEventType.RX_TIMEOUT,
                                                                        self.progress_gloria_flood)
            elif (self.tx_message and self.retransmission_count > 0 and
                  (int((self.slot_index - self.first_rx_slot_index) / 2) % 2 if self.flood.acked else int(self.slot_index - self.first_rx_slot_index) % 2)):

                self.tx_message.timestamp = slot.tx_marker

                self.node.mm.tx(self.node,
                                self.flood.modulation,
                                self.flood.band,
                                self.tx_message)

                self.node.em.register_event(slot.tx_done_marker,
                                            self.node, sim_event_manager.SimEventType.TX_DONE,
                                            self.progress_gloria_flood)

                if (self.power_increase and
                        self.tx_message.power_level < len(lwb_slot.POWERS) - 1):
                    self.tx_message.power_level += 1
                self.retransmission_count -= 1

            else:
                self.node.mm.register_rx(self.node,
                                         slot.rx_marker,
                                         self.flood.modulation,
                                         self.flood.band,
                                         self.progress_gloria_flood)

                self.rx_timeout_event = self.node.em.register_event(slot.rx_timeout_marker,
                                                                    self.node,
                                                                    sim_event_manager.SimEventType.RX_TIMEOUT,
                                                                    self.progress_gloria_flood)

        else:
            self.finished_callback(self.tx_message)

    def process_next_ack(self):
        self.is_ack = True
        self.slot_index += 2
        if (self.is_not_finished()
                and self.flood.slots[self.slot_index].type in [gloria_flood.GloriaSlotType.RX_ACK,
                                                               gloria_flood.GloriaSlotType.TX_ACK]
                and self.ack_counter < MAX_ACKS):

            slot = self.flood.slots[self.slot_index]

            self.ack_message.timestamp = slot.tx_marker

            self.node.mm.tx(self.node,
                            self.flood.modulation,
                            self.flood.band,
                            self.ack_message)

            self.node.em.register_event(slot.tx_done_marker,
                                        self.node, sim_event_manager.SimEventType.TX_DONE,
                                        self.progress_gloria_flood)

            self.ack_counter += 1

        else:
            self.finished_callback(self.tx_message)

    def is_not_finished(self):
        if (self.slot_index < len(self.flood.slots)
            and self.flood.slots[self.slot_index].rx_marker > self.node.local_timestamp) \
                and self.ack_counter < MAX_ACKS:
            return True
        else:
            return False

    def valid_to_send(self):
        if self.is_not_finished() and self.tx_message.hop_count < self.hop_count and self.retransmission_count > 0:
            return True
        else:
            return False

    def get_slot_offset(self, count=1):
        return self.flood.slots[self.slot_index - count].tx_marker - self.flood.slots[self.slot_index - 1].tx_marker

    def update_local_timestamp(self, slot: 'gloria_flood.GloriaSlot', message: 'SimMessage'):
        correction = self.node.transform_local_to_global_timestamp(slot.tx_marker) - message.tx_start

        self.node.local_timestamp += correction
