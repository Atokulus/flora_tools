from copy import copy
from typing import List, Union, Tuple, Optional

import numpy as np

import flora_tools.lwb_slot as lwb_slot
import flora_tools.sim.service as service
import flora_tools.sim.sim_node as sim_node
from flora_tools.sim.sim_message import SimMessage, SimMessageType

MAX_TTL = 3

MAX_FAILED_REQUESTS = 5


class DataStream:
    def __init__(self, id: str, node: 'sim_node.SimNode', master: 'sim_node.SimNode', priority, subpriority, period,
                 service: 'service.Service' = None, destination: 'sim_node.SimNode' = None,
                 max_payload=None, needs_ack=True):
        self.id = id
        self.node = node
        self.master = master
        self.destination = destination
        self.service = service

        self.priority = priority
        self.subpriority = subpriority
        self.period = period

        self.max_payload = max_payload
        self.needs_ack = needs_ack

        self.stream_manager: LWBStreamManager = None
        self.last_consumption = self.node.local_timestamp - self.period
        self.ttl = MAX_TTL
        self.is_ack = False

        if max_payload is None:
            max_payload = lwb_slot.max_data_payload

        self.slot_count = int(np.ceil(self.max_payload / lwb_slot.max_data_payload))
        self.last_slot_size = self.max_payload % max_payload
        self.current_slot = 0

        self.last_power_level = None
        self.last_modulation = None
        self.failed_request_counter = 0

    def check_request(self, modulation: int, power_level: int) -> bool:
        if self.last_power_level is not None and self.last_modulation is not None:
            if (modulation >= self.last_modulation) and (power_level <= self.last_power_level):
                return True
            else:
                if self.failed_request_counter < MAX_FAILED_REQUESTS:
                    self.failed_request_counter += 1
                    return False
                else:
                    self.last_power_level = power_level
                    self.last_modulation = modulation
                    self.failed_request_counter = 0
                    return True
        else:
            self.last_power_level = power_level
            self.last_modulation = modulation
            return True

    @property
    def current_slot_size(self):
        if self.current_slot < self.slot_count - 1:
            return lwb_slot.max_data_payload
        else:
            return self.last_slot_size

    @property
    def next_period(self):
        return self.last_consumption + self.period

    def __copy__(self):
        return DataStream(self.id, self.node, self.master, self.priority, self.subpriority, self.period, service=None,
                          destination=self.destination, max_payload=self.max_payload, needs_ack=self.needs_ack)

    def get(self):
        return self.service.get_data()

    def available(self, timestamp=None):
        if timestamp is None:
            timestamp = self.service.node.network.global_timestamp

        if timestamp - self.last_consumption > self.period:
            if self.service is not None:
                return self.service.data_available()
            else:
                return True
        else:
            return None

    def success(self):
        self.ttl = MAX_TTL

        if self.current_slot < self.slot_count - 1:
            self.current_slot += 1
        else:
            self.last_consumption = self.node.network.global_timestamp
            self.current_slot = 0
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
    def __init__(self, id: str, node: 'sim_node.SimNode', master: 'sim_node.SimNode', priority: int, subpriority: int,
                 period, service: 'service.Service' = None, destination: 'sim_node.SimNode' = None, low_power=False,
                 needs_ack=True):
        self.id = id
        self.node = node
        self.master = master
        self.destination = destination
        self.service = service

        self.priority = priority
        self.subpriority = subpriority
        self.period = period

        self.low_power = low_power
        self.needs_ack = needs_ack

        self.stream_manager: LWBStreamManager = None
        self.last_consumption = self.node.local_timestamp - self.period
        self.ttl = MAX_TTL
        self.is_ack = True

        self.last_power_level = None
        self.last_modulation = None
        self.failed_request_counter = 0

    def check_request(self, modulation: int, power_level: int) -> bool:
        if self.last_power_level is not None and self.last_modulation is not None:
            if modulation >= modulation and power_level <= power_level:
                return True
            else:
                if self.failed_request_counter < MAX_FAILED_REQUESTS:
                    self.failed_request_counter += 1
                    return False
                else:
                    self.last_power_level = power_level
                    self.last_modulation = modulation
                    self.failed_request_counter = 0
                    return True
        else:
            self.last_power_level = power_level
            self.last_modulation = modulation
            return True

    def __copy__(self):
        return NotificationStream(self.id, self.node, self.master, self.priority, self.subpriority, self.period,
                                  service=None, destination=self.destination, low_power=self.low_power,
                                  needs_ack=self.needs_ack)

    @property
    def next_period(self):
        return self.last_consumption + self.period

    def get(self):
        return self.service.get_notification()

    def available(self, timestamp=None):
        if timestamp is None:
            timestamp = self.service.node.local_timestamp

        if timestamp - self.last_consumption > self.period:
            if self.service is not None:
                return self.service.notification_available()
            else:
                return True
        else:
            return None

    def success(self):
        self.ttl = MAX_TTL
        self.last_consumption = self.stream_manager.node.local_timestamp
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

    def register(self, stream: Union[DataStream, NotificationStream]):
        if stream.service is None:
            stream.is_ack = True

        if type(stream) is DataStream:
            self.register_data(stream)
        else:
            self.register_notification(stream)

    def register_data(self, datastream: DataStream):
        datastream.node = self.node
        datastream.stream_manager = self
        self.datastreams.append(datastream)


    def remove_data(self, datastream: DataStream):
        self.datastreams.remove(datastream)

    def register_notification(self, notification_stream: NotificationStream):
        notification_stream.node = self.node
        notification_stream.stream_manager = self
        self.notification_streams.append(notification_stream)

    def remove_notification(self, notification_stream: NotificationStream):
        self.notification_streams.remove(notification_stream)

    def select_data(self, slot_size: int = None, selection: List[DataStream] = None, timestamp=None):
        if selection is None:
            selection = self.datastreams.copy()

        best_match: DataStream = None

        if slot_size:
            stream: DataStream
            for stream in selection:
                if (stream.is_ack and stream.available(timestamp=timestamp)
                        and stream.current_slot_size <= slot_size - lwb_slot.data_header_length):
                    if best_match is None:
                        best_match = stream
                    else:
                        if best_match.priority >= stream.priority \
                                and best_match.subpriority >= stream.subpriority \
                                and best_match.available(timestamp)['payload'] < stream.available(timestamp)['payload'] \
                                and best_match.last_consumption > stream.last_consumption:
                            best_match = stream
        else:
            stream: DataStream
            for stream in selection:
                if stream.is_ack and stream.available(timestamp):
                    if best_match is None:
                        best_match = stream
                    else:
                        if best_match.priority >= stream.priority \
                                and best_match.subpriority >= stream.subpriority \
                                and best_match.available(timestamp)['payload'] < stream.available(timestamp)['payload'] \
                                and best_match.last_consumption > stream.last_consumption:
                            best_match = stream
        return best_match

    def select_notification(self, selection: List[NotificationStream] = None, low_power=False, timestamp=None):
        if selection is None:
            selection = self.notification_streams

        best_match: NotificationStream = None
        stream: NotificationStream
        for stream in selection:
            if stream.is_ack and stream.available(timestamp=timestamp) and (stream.low_power if low_power else True):
                if best_match is None:
                    best_match = stream
                else:
                    if best_match.priority >= stream.priority \
                            and best_match.subpriority > stream.subpriority:
                        best_match = stream

        return best_match

    def schedule_data(self, timestamp, slot_count: int, modulation: int):
        selection = self.datastreams.copy()
        streams: List[DataStream] = []
        count = 0

        while count < slot_count:
            stream = self.select_data(timestamp=timestamp, selection=selection)
            if stream is not None and stream.priority <= modulation:
                link = self.node.lwb.link_manager.get_link(stream.master)
                if link['modulation'] >= modulation:
                    for i in range(stream.slot_count):
                        streams.append(stream)
                        count += 1
                        if count >= slot_count:
                            break
                selection.remove(stream)
            else:
                break

        return streams

    def schedule_notification(self, timestamp, slot_count: int, modulation: int):
        selection = self.notification_streams.copy()
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
            return SimMessage(self.node.local_timestamp, self.node, lwb_slot.contention_header_length, 0,
                              self.node.lwb.base,
                              SimMessageType.ROUND_REQUEST)
        else:
            return None

    def get_data(self, slot_size: int) -> Tuple[DataStream, SimMessage]:
        stream = self.select_data(slot_size=slot_size-lwb_slot.data_header_length)

        if stream is not None:
            content = {'data': stream.get(), 'stream': copy(stream)}

            message = SimMessage(self.node.local_timestamp, self.node, lwb_slot.contention_header_length, 0,
                                 self.node.lwb.base,
                                 SimMessageType.DATA, content=content)

            return stream, message
        else:
            return None, None

    def get_notification(self, low_power=False) -> Tuple[Optional[NotificationStream], Optional[SimMessage]]:
        stream = self.select_notification(low_power=low_power)
        content = {'notification': stream.get(), 'stream': stream}

        message = SimMessage(self.node.local_timestamp, self.node, lwb_slot.contention_header_length, 0,
                             self.node.lwb.base,
                             SimMessageType.NOTIFICATION, content=content)

        return stream, message

    def get_stream_request(self, modulation: int, power_level: int) -> Tuple[Optional[Union[DataStream, NotificationStream]], Optional[SimMessage]]:
        for stream in self.notification_streams:
            if not stream.is_ack and stream.check_request(modulation, power_level):
                message = SimMessage(self.node.local_timestamp, self.node, lwb_slot.contention_header_length, 0,
                                     self.node.lwb.base,
                                     SimMessageType.STREAM_REQUEST,
                                     content={'type': 'notification', 'stream': copy(stream)})
                return stream, message

        for stream in self.datastreams:
            if not stream.is_ack and stream.check_request(modulation, power_level):
                message = SimMessage(self.node.local_timestamp, self.node, lwb_slot.contention_header_length, 0,
                                     self.node.lwb.base,
                                     SimMessageType.STREAM_REQUEST,
                                     content={'type': 'data', 'stream': copy(stream)})
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

    def tx_ack_stream_request(self, stream: Union[DataStream, NotificationStream]):
        return SimMessage(self.node.local_timestamp, self.node, lwb_slot.gloria_header_length, 0,
                          stream.master,
                          SimMessageType.ACK,
                          content={'type': ('data' if type(stream) is DataStream else 'notification'),
                                   'stream': copy(stream)})

    def tx_ack(self, stream: Union[DataStream, NotificationStream]):
        for local_stream in self.datastreams:
            if stream.id == local_stream.id:
                local_stream.success()
        for local_stream in self.notification_streams:
            if stream.id == local_stream.id:
                local_stream.success()

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

    def get_next_round_schedule_timestamp(self, modulation):
        next_period: int = None

        for stream in self.datastreams:
            if self.node.lwb.link_manager.get_link(stream.master)['modulation'] is modulation:
                if next_period is None:
                    next_period = stream.next_period
                elif stream.next_period < next_period:
                    next_period = stream.next_period

        for stream in self.notification_streams:
            if (not stream.low_power and
                    self.node.lwb.link_manager.get_link(stream.master)['modulation'] is modulation):
                if next_period is None:
                    next_period = stream.next_period
                elif stream.next_period < next_period:
                    next_period = stream.next_period

        if next_period is not None:
            return np.ceil(next_period / lwb_slot.SCHEDULE_GRANULARITY) * lwb_slot.SCHEDULE_GRANULARITY
        else:
            return None

    def get_next_lp_notifiaction_round_schedule_timestamp(self, modulation):
        next_period: int = None

        for stream in self.notification_streams:
            if (stream.low_power and
                    self.node.lwb.link_manager.get_acknowledged_link(stream.master)['modulation'] is modulation):
                if next_period is None:
                    next_period = stream.next_period
                elif stream.next_period < next_period:
                    next_period = stream.next_period

        return np.ceil(next_period / lwb_slot.SCHEDULE_GRANULARITY) * lwb_slot.SCHEDULE_GRANULARITY

    def retry_all_streams(self):
        for stream in self.datastreams:
            stream.retry()

        for stream in self.notification_streams:
            stream.retry()
