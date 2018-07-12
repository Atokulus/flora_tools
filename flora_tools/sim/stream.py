from copy import copy
from typing import List, Union, Tuple

import flora_tools.sim.service as service
from flora_tools.sim.sim_message import SimMessage, SimMessageType
import flora_tools.sim.sim_node as sim_node
import flora_tools.lwb_slot as lwb_slot

MAX_TTL = 3


class DataStream:
    def __init__(self, node: 'sim_node.SimNode', master: 'sim_node.SimNode', id: str, service: 'service.Service', priority, subpriority,
                 datarate, period,
                 max_slot_size=255):
        self.node = node
        self.master = master
        self.id = id
        self.service = service
        self.priority = priority
        self.subpriority = subpriority
        self.datarate = datarate
        self.period = period
        self.max_slot_size = max_slot_size
        self.stream_manager: LWBStreamManager = None

        self.last_consumation = None

        self.ttl = MAX_TTL
        self.is_ack = False

    def __copy__(self):
        return DataStream(self.node, self.master, self.id, None, self.priority, self.subpriority, self.datarate, self.period,
                          self.max_slot_size)

    def get(self):
        return self.service.get_data()

    def available(self):
        if self.last_consumation - self.service.node.local_timestamp > self.period:
            if self.service is not None:
                return self.service.data_available()
            else:
                return True
        else:
            return None

    def success(self):
        self.last_consumation = self.stream_manager.node.local_timestamp
        self.ttl = MAX_TTL
        if self.service is not None:
            self.service.ack_data_callback()

    def fail(self):
        self.ttl -= 1
        if self.ttl is 0:
            self.stream_manager.remove_data(self)
            if self.service is not None:
                self.service.failed_datastream_callback(self)

    def retry(self):
        self.ttl = MAX_TTL
        self.is_ack = False
        self.stream_manager.register_data(self)


class NotificationStream:
    def __init__(self, node: 'sim_node.SimNode', master: 'sim_node.SimNode', id: str, service: 'service.Service', priority: int,
                 subpriority: int, period, low_power = False):
        self.node = node
        self.master = master
        self.id = id
        self.service = service
        self.priority = priority
        self.subpriority = subpriority
        self.period = period
        self.stream_manager: LWBStreamManager = None
        self.low_power = low_power

        self.last_consumation = self.stream_manager.node.local_timestamp

        self.ttl = MAX_TTL
        self.is_ack = True

    def __copy__(self):
        return NotificationStream(self.node, self.master, self.id, None, self.priority, self.subpriority, self.period)

    def get(self):
        return self.service.get_notification()

    def available(self):
        if self.last_consumation - self.service.node.local_timestamp > self.period:
            if self.service is not None:
                return self.service.notification_available()
            else:
                return True
        else:
            return None

    def success(self):
        self.last_consumation = self.stream_manager.node.local_timestamp
        self.ttl = MAX_TTL
        if self.service is not None:
            self.service.ack_notification_callback()

    def fail(self):
        self.ttl -= 1
        if self.ttl is 0:
            self.stream_manager.remove_notification(self)
            if self.service is not None:
                self.service.failed_notification_callback(self)

    def retry(self):
        self.ttl = MAX_TTL
        self.is_ack = False
        self.stream_manager.register_notification(self)


class LWBStreamManager:
    def __init__(self, node: 'sim_node.SimNode'):
        self.node = node
        self.datastreams: List[DataStream] = []
        self.notification_streams: List[NotificationStream] = []

    def register_data(self, datastream: DataStream):
        datastream.node = self.node
        self.datastreams.append(datastream)
        datastream.stream_manager = self

    def remove_data(self, datastream: DataStream):
        self.datastreams.remove(datastream)

    def register_notification(self, notification_stream: NotificationStream):
        notification_stream.node = self.node
        self.notification_streams.append(notification_stream)
        notification_stream.stream_manager = self

    def remove_notification(self, notification_stream: NotificationStream):
        self.notification_streams.remove(notification_stream)

    def select_data(self, payload_size: int = None, selection: List[DataStream] = None):
        if selection is None:
            selection = self.datastreams
        if payload_size is None:
            payload_size = 255

        best_match: DataStream = None

        stream: DataStream
        for stream in selection:
            if stream.is_ack and stream.available() and stream.available().payload <= payload_size:
                if best_match is None:
                    best_match = stream
                else:
                    if best_match.priority >= stream.priority \
                            and best_match.subpriority >= stream.subpriority \
                            and best_match.available().payload < stream.available().payload:
                        best_match = stream

        return best_match

    def select_notification(self, selection: List[NotificationStream] = None, low_power=False):
        if selection is None:
            selection = self.notification_streams

        best_match: NotificationStream = None
        stream: NotificationStream
        for stream in selection:
            if stream.is_ack and stream.available() and (not low_power or (low_power and stream.low_power)):
                if best_match is None:
                    best_match = stream
                else:
                    if best_match.priority >= stream.priority \
                            and best_match.subpriority > stream.subpriority:
                        best_match = stream

        return best_match

    def schedule_data(self, slot_count: int, modulation: int):
        selection = self.datastreams

        streams: List[DataStream] = []

        count = 0

        while count < slot_count:
            stream = self.select_data(selection=selection)
            if stream is not None:
                link = self.node.lwb.link_manager.get_acknowledged_link(stream.master)
                if link['modulation'] is modulation:
                    if stream.priority <= modulation:
                        streams.append(stream)
                        count += 1

                selection.remove(stream)
            else:
                break

        return streams

    def schedule_notification(self, slot_count: int, modulation: int):
        selection = self.notification_streams

        streams: List[NotificationStream] = []

        count = 0

        while count < slot_count:
            stream = self.select_notification(selection=selection)
            if stream is not None:
                link = self.node.lwb.link_manager.get_acknowledged_link(stream.master)
                if link['modulation'] is modulation:
                    if stream.priority <= modulation:
                        streams.append(stream)
                        count += 1

                selection.remove(stream)
            else:
                break
        return streams

    def get_round_request(self):
        if (not all([stream.is_ack for stream in self.notification_streams])
                or not all([stream.is_ack for stream in self.datastreams])):
            return SimMessage(self.node.local_timestamp, self.node, lwb_slot.contention_length, 0, self.node.lwb.base,
                              SimMessageType.ROUND_REQUEST)
        else:
            return None

    def get_notification(self, low_power=False) -> Tuple[NotificationStream, SimMessage]:
        stream = self.select_notification(low_power)
        content = {'notification': stream.get(), 'stream': stream}

        message = SimMessage(self.node.local_timestamp, self.node, lwb_slot.contention_length, 0, self.node.lwb.base,
                             SimMessageType.NOTIFICATION, content=content)

        return stream, message

    def get_data(self) -> Tuple[DataStream, SimMessage]:
        stream = self.select_data()
        content = {'data': stream.get(), 'stream': copy(stream)}

        message = SimMessage(self.node.local_timestamp, self.node, lwb_slot.contention_length, 0, self.node.lwb.base,
                             SimMessageType.DATA, content=content)

        return stream, message

    def get_stream_request(self) -> Tuple[Union[DataStream, NotificationStream], SimMessage]:
        for stream in self.notification_streams:
            if not stream.is_ack:
                message = SimMessage(self.node.local_timestamp, self.node, lwb_slot.contention_length, 0,
                                     self.node.lwb.base,
                                     SimMessageType.STREAM_REQUEST,
                                     content={'type': 'notification', 'stream': copy(stream)})
                return stream, message

        for stream in self.datastreams:
            if not stream.is_ack:
                message = SimMessage(self.node.local_timestamp, self.node, lwb_slot.contention_length, 0,
                                     self.node.lwb.base,
                                     SimMessageType.STREAM_REQUEST, content={'type': 'data', 'stream': copy(stream)})
                return stream, message
        return None, None

    def rx_ack_stream_request(self, message: SimMessage):
        if message.content['type'] is 'data':
            for stream in self.datastreams:
                if stream.id is message.content['stream'].id:
                    stream.is_ack = True
                    break
        elif message.content['type'] is 'notification':
            for stream in self.notification_streams:
                if stream.id is message.content['stream'].id:
                    stream.to_be_registered = False
                    break

    def tx_ack_stream_request(self, stream):
        return SimMessage(self.node.local_timestamp, self.node, lwb_slot.gloria_header_length, 0,
                          stream.master_node,
                          SimMessageType.STREAM_REQUEST, content={'type': 'notification', 'stream': copy(stream)})

    def tx_ack(self, stream: Union[DataStream, NotificationStream]):
        stream.success(self)
        return SimMessage(self.node.local_timestamp, self.node, lwb_slot.gloria_header_length, 0,
                          stream.master,
                          SimMessageType.ACK, content={'stream': copy(stream)})

    def rx_ack(self, message: SimMessage):
        for stream in self.datastreams:
            if stream.id is message.content['stream'].id:
                stream.success()
                return

        for stream in self.notification_streams:
            if stream.id is message.content['stream'].id:
                stream.success()
                return
