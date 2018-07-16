import flora_tools.sim.sim_node as sim_node
import flora_tools.lwb_slot as lwb_slot
from flora_tools.sim.service import Service
from flora_tools.sim.stream import DataStream, NotificationStream


class SensorService(Service):
    def __init__(self, node: 'sim_node.SimNode', name, datarate, payload_size=None, period=10, priority=3,
                 subpriority=1):
        self.node = node
        self.name = name
        self.datarate = datarate
        self.payload_size = payload_size
        self.period = period
        self.priority = priority
        self.subpriority = subpriority

        if payload_size is None:
            payload_size = lwb_slot.max_data_payload

        self.payload_size = payload_size
        self.accumulated_data = 0.0
        self.last_timestamp = node.network.current_timestamp

        self.datastream = DataStream('sensor{}'.format(self.node.id), self.node, self.node, self.priority,
                                     self.subpriority, self.period, self, max_payload=self.payload_size)

    def get_data(self):
        data = self.data_available()
        return data

    def data_available(self):
        elapsed = self.node.network.current_timestamp - self.last_timestamp
        self.accumulated_data += elapsed * self.datarate
        self.last_timestamp = self.node.network.current_timestamp

        if self.accumulated_data >= self.payload_size:
            data = {'node': self.node, 'timestamp': self.node.local_timestamp, 'payload': self.payload_size}
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
        self.accumulated_data -= self.payload_size

    def ack_notification_callback(self):
        return
