from flora_tools.sim.service import Service
import flora_tools.sim.sim_node as sim_node

from flora_tools.sim.stream import DataStream, NotificationStream


class SensorService(Service):
    def __init__(self, node: 'sim_node.SimNode', name, datarate, slot_size=255, period=10, priority=3, subpriority=1):
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

    def get_data(self):
        data = self.data_available()
        return data

    def data_available(self):
        elapsed = self.node.network.current_timestamp - self.last_timestamp
        self.accumulated_data += elapsed * self.datarate
        self.last_timestamp = self.node.network.current_timestamp

        if self.accumulated_data >= self.slot_size:
            data = {'node': self.node,'timestamp': self.node.local_timestamp,'payload': self.slot_size}
            return data
        else:
            return None

    def get_notification(self):
        return None

    def notification_available(self):
        return None

    def failed_datastream_callback(self, datastream: DataStream):
        datastream.retry()

    def failed_notification_callback(self, notification_stream: NotificationStream):
        notification_stream.retry()

    def ack_data_callback(self):
        self.accumulated_data -= self.slot_size

    def ack_notification_callback(self):
        return
