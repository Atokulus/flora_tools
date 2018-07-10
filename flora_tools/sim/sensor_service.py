from flora_tools.sim.service import Service
from flora_tools.sim.sim_message import SimMessage
from flora_tools.sim.sim_node import SimNode

from flora_tools.sim.stream import DataStream, NotificationStream


class SensorService(Service):
    def __init__(self, node: 'SimNode', name, datarate, slot_size=255, period=10, priority=3, subpriority=1):
        self.node = node
        self.name = name
        self.datarate = datarate
        self.slot_size = slot_size
        self.period = period
        self.priority = priority
        self.subpriority = subpriority

        self.slot_size = slot_size
        self.accumulated_data = 0.0
        self.last_timestamp = node.network.current_timestamp

        self.datastream = DataStream(self, self.priority, self.subpriority, self.datarate, self.period, self.slot_size)

    def get_data(self, modulation) -> SimMessage:
        message = self.data_available()
        if message is not None:
            self.accumulated_data -= message.payload

        return message

    def data_available(self) -> SimMessage:
        elapsed = self.node.network.current_timestamp - self.last_timestamp
        self.accumulated_data += elapsed * self.datarate
        self.last_timestamp = self.node.network.current_timestamp

        if self.accumulated_data >= self.slot_size:
            message = SimMessage(None,
                                 self.node,
                                 self.slot_size,
                                 None,
                                 destination=self.node.lwb_manager.base,
                                 type='data',
                                 content={'node': self.node,
                                          'timestamp': self.node.local_timestamp,
                                          'payload': self.slot_size})
            return message
        else:
            return None

    def get_notification(self, modulation) -> SimMessage:
        return None

    def notification_available(self) -> SimMessage:
        return None

    def failed_datastream_callback(self, datastream: DataStream):
        datastream.retry()

    def failed_notification_callback(self, notification_stream: NotificationStream):
        notification_stream.retry()
