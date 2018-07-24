import logging

import numpy as np

import flora_tools.lwb_round as lwb_round
import flora_tools.lwb_slot as lwb_slot
import flora_tools.sim.sim_lwb as sim_lwb_manager
import flora_tools.sim.sim_node as sim_node
from flora_tools.sim.sim_lwb_slot import SimLWBSlot
from flora_tools.sim.sim_message import SimMessage, SimMessageType


class SimLWBRound:
    def __init__(self, node: 'sim_node.SimNode', lwb: 'sim_lwb_manager.SimLWB',
                 round: 'lwb_round.LWBRound', callback):

        self.logger = logging.getLogger(self.__class__.__qualname__)

        self.node = node
        self.lwb = lwb
        self.round = round
        self.callback = callback

        self.current_slot_index = 0
        self.ack_stream = None

        self.log_round()
        self.process_slot()

    def log_round(self):
        self.logger.info(
            "Marker:{:10f}\tNode:{:3d}\tMod:{:2d}\tType:{:16s}\tTime:{:10f}".format(self.round.round_marker,
                                                                                    self.node.id,
                                                                                    self.round.modulation,
                                                                                    self.round.type,
                                                                                    self.round.total_time))

    def process_next_slot(self):
        self.current_slot_index += 1
        self.process_slot()

    def process_slot(self):
        if self.slot_valid():
            slot = self.round.slots[self.current_slot_index]

            if slot.type is not lwb_slot.LWBSlotType.ACK:
                self.ack_stream = None

            if slot.type is lwb_slot.LWBSlotType.SYNC:
                self.process_sync_slot(slot)
            elif slot.type is lwb_slot.LWBSlotType.SLOT_SCHEDULE:
                self.process_slot_schedule_slot(slot)
            elif slot.type is lwb_slot.LWBSlotType.ROUND_SCHEDULE:
                self.process_round_schedule_slot(slot)
            elif slot.type is lwb_slot.LWBSlotType.CONTENTION:
                self.process_contention_slot(slot)
            elif slot.type is lwb_slot.LWBSlotType.DATA:
                self.process_data_slot(slot)
            elif slot.type is lwb_slot.LWBSlotType.ACK:
                self.process_ack_slot(slot)
            else:
                self.callback(False)
        else:
            self.callback(False)

    def process_sync_slot(self, slot: 'lwb_slot.LWBSlot'):
        if self.node.role is sim_node.SimNodeRole.BASE:
            message = SimMessage(slot.slot_marker, self.node, slot.payload,
                                 modulation=slot.modulation, destination=None, type=SimMessageType.SYNC,
                                 power_level=slot.power_level)

            SimLWBSlot(self.node, slot, self.process_sync_slot_callback, master=self.node,
                       message=message)
        else:
            SimLWBSlot(self.node, slot, self.process_sync_slot_callback, master=self.lwb.base,
                       message=None)

    def process_sync_slot_callback(self, message: SimMessage):
        if self.node.role is not sim_node.SimNodeRole.BASE and message is not None:
            self.lwb.schedule_manager.register_sync(message)
        self.process_next_slot()

    def process_slot_schedule_slot(self, slot: 'lwb_slot.LWBSlot'):
        if self.node.role is sim_node.SimNodeRole.BASE:
            slot_schedule = self.lwb.schedule_manager.get_slot_schedule(self.round)
            message = SimMessage(slot.slot_marker, self.node, slot.payload,
                                 modulation=slot.modulation, destination=None, type=SimMessageType.SLOT_SCHEDULE,
                                 content=slot_schedule, power_level=slot.power_level)
            SimLWBSlot(self.node, slot, self.process_slot_schedule_slot_callback, master=self.node,
                       message=message)
        else:
            SimLWBSlot(self.node, slot, self.process_slot_schedule_slot_callback,
                       master=self.lwb.base,
                       message=None)

    def process_slot_schedule_slot_callback(self, message: SimMessage):
        if self.node.role is not sim_node.SimNodeRole.BASE and \
                message is not None and message.type is SimMessageType.SLOT_SCHEDULE:
            self.round = self.lwb.schedule_manager.register_slot_schedule(message)

        self.process_next_slot()

    def process_data_slot(self, slot: 'lwb_slot.LWBSlot'):
        if slot.master is self.node:
            if self.round.type is lwb_round.LWBRoundType.DATA:
                stream, message = self.lwb.stream_manager.get_data(slot.payload)
            else:
                stream, message = self.node.lwb.stream_manager.get_notification()

            if message is not None:

                message.timestamp = slot.slot_marker
                message.modulation = slot.modulation

                power_level = self.lwb.link_manager.get_link(target_node=self.round.master)['power_level']
                if power_level is None:
                    power_level = lwb_slot.DEFAULT_POWER_LEVELS[lwb_slot.MODULATIONS[slot.modulation]]

                message.power_level = power_level

                SimLWBSlot(self.node, slot, self.process_data_slot_callback, master=slot.master,
                           message=message)

                self.ack_stream = stream
            else:
                self.process_next_slot()

        else:
            self.ack_stream = slot.stream
            SimLWBSlot(self.node, slot, self.process_data_slot_callback, master=slot.master,
                       message=None)

    def process_data_slot_callback(self, message: SimMessage):
        if self.node.role is sim_node.SimNodeRole.BASE and self.ack_stream is not None and self.ack_stream.master is not self.node:
            self.ack_stream.fail()

        if message is not None and message.type is SimMessageType.DATA:
            self.ack_stream = message.content['stream']
        else:
            self.ack_stream = None

        self.process_next_slot()

    def process_contention_slot(self, slot: 'lwb_slot.LWBSlot'):
        message = None

        if self.node.role is not sim_node.SimNodeRole.BASE and (slot.master is None or slot.master is self.node):
            if self.round.type is lwb_round.LWBRoundType.SYNC:
                message = self.lwb.stream_manager.get_round_request()
            elif self.round.type is lwb_round.LWBRoundType.LP_NOTIFICATION:
                stream, message = self.lwb.stream_manager.get_notification(low_power=True)
            elif self.round.type is lwb_round.LWBRoundType.STREAM_REQUEST:
                stream, message = self.lwb.stream_manager.get_stream_request(slot.modulation,
                                                                             self.lwb.link_manager.get_link(
                                                                                 self.round.master)['power_level'])
            else:
                stream = None
                message = None

            if message is not None:
                message.timestamp = slot.slot_marker
                message.modulation = slot.modulation
                power_level = self.lwb.link_manager.get_link(target_node=self.round.master)['power_level']

                if np.isnan(power_level):
                    power_level = lwb_slot.DEFAULT_POWER_LEVELS[lwb_slot.MODULATIONS[slot.modulation]]

                message.power_level = power_level

                SimLWBSlot(self.node, slot, self.process_contention_slot_callback, master=self.node,
                           message=message)

                if self.round.type is not lwb_round.LWBRoundType.SYNC:
                    self.ack_stream = stream
            else:
                SimLWBSlot(self.node, slot, self.process_contention_slot_callback)

        elif (self.round.type is not lwb_round.LWBRoundType.LP_NOTIFICATION
              or self.node.role is sim_node.SimNodeRole.BASE):
            SimLWBSlot(self.node, slot, self.process_contention_slot_callback, master=slot.master,
                       message=None)
        else:
            self.process_next_slot()

    def process_contention_slot_callback(self, message: SimMessage):
        if message is not None and self.node.role is sim_node.SimNodeRole.BASE:
            if message.type in [SimMessageType.NOTIFICATION, SimMessageType.STREAM_REQUEST]:
                if message.type is SimMessageType.STREAM_REQUEST:
                    if not self.node.lwb.stream_manager.register(message.content['stream']):
                        self.ack_stream = message.content['stream']
                    elif message.type is SimMessageType.NOTIFICATION:
                        self.ack_stream = message.content['stream']
            elif message.type is SimMessageType.ROUND_REQUEST:
                self.node.lwb.lwb_schedule_manager.round_request(message.content)

        if self.round.type is lwb_round.LWBRoundType.STREAM_REQUEST and self.node.role is sim_node.SimNodeRole.BASE:
            if message is None:
                self.lwb.schedule_manager.decrement_contention(self.round.modulation)
            elif message.type is SimMessageType.STREAM_REQUEST:
                self.lwb.schedule_manager.increment_contention(self.round.modulation)

        self.process_next_slot()

    def process_ack_slot(self, slot: 'lwb_slot.LWBSlot'):
        if self.ack_stream:
            if self.node.role is sim_node.SimNodeRole.BASE:
                if self.round.type in [lwb_round.LWBRoundType.DATA, lwb_round.LWBRoundType.NOTIFICATION,
                                       lwb_round.LWBRoundType.LP_NOTIFICATION]:
                    message = self.lwb.stream_manager.tx_ack(self.ack_stream)
                    power_level = self.lwb.link_manager.get_link(message.destination)['power_level']
                    if np.isnan(power_level):
                        power_level = lwb_slot.DEFAULT_POWER_LEVELS[lwb_slot.MODULATIONS[slot.modulation]]
                    message.power_level = power_level
                    message.modulation = slot.modulation

                    SimLWBSlot(self.node, slot, self.process_ack_slot_callback, master=self.node,
                               message=message)

                elif self.round.type is lwb_round.LWBRoundType.STREAM_REQUEST:
                    message = self.lwb.stream_manager.tx_ack_stream_request(self.ack_stream)
                    power_level = self.lwb.link_manager.get_link(message.destination)['power_level']
                    if np.isnan(power_level):
                        power_level = lwb_slot.DEFAULT_POWER_LEVELS[lwb_slot.MODULATIONS[slot.modulation]]
                    message.power_level = power_level
                    message.modulation = slot.modulation

                    SimLWBSlot(self.node, slot, self.process_ack_slot_callback, master=self.node,
                               message=message)
            else:
                SimLWBSlot(self.node, slot, self.process_ack_slot_callback, master=self.round.master,
                           message=None)
        else:
            SimLWBSlot(self.node, slot, self.process_ack_slot_callback, master=self.round.master,
                       message=None)

    def process_ack_slot_callback(self, message: SimMessage):
        if (message is not None
                and message.type is SimMessageType.ACK
                and message.destination is self.node):
            if self.round.type in [lwb_round.LWBRoundType.NOTIFICATION, lwb_round.LWBRoundType.LP_NOTIFICATION,
                                   lwb_round.LWBRoundType.DATA]:
                self.lwb.stream_manager.rx_ack(message)
            elif self.round.type is lwb_round.LWBRoundType.STREAM_REQUEST:
                self.lwb.stream_manager.rx_ack_stream_request(message)
        elif self.ack_stream is not None:
            self.ack_stream.fail()

        self.ack_stream = None

        self.process_next_slot()

    def process_round_schedule_slot(self, slot: 'lwb_slot.LWBSlot'):
        if self.node.role is sim_node.SimNodeRole.BASE:
            round_schedule = self.lwb.schedule_manager.get_round_schedule(self.round)
            message = SimMessage(slot.slot_marker, self.node, slot.payload,
                                 modulation=slot.modulation, destination=None, type=SimMessageType.ROUND_SCHEDULE,
                                 content=round_schedule, power_level=slot.power_level)
            SimLWBSlot(self.node, slot, self.process_round_schedule_slot_callback, master=self.node,
                       message=message)
        else:
            SimLWBSlot(self.node, slot, self.process_round_schedule_slot_callback,
                       message=None)

    def process_round_schedule_slot_callback(self, message: SimMessage):
        if (self.node.role is not sim_node.SimNodeRole.BASE and
                message is not None and
                message.type is SimMessageType.ROUND_SCHEDULE):
            self.lwb.schedule_manager.register_round_schedule(message)

        self.process_next_slot()

    def slot_valid(self):
        return self.current_slot_index < len(self.round.slots) and self.round.slots[self.current_slot_index] is not None
