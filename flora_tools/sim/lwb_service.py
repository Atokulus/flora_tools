import abc

import flora_tools.sim.sim_node as sim_node
import flora_tools.sim.lwb_stream as stream


class Service:
    __metaclass__ = abc.ABCMeta

    def __init__(self, node: 'sim_node.SimNode', name=None):
        self.node = node
        self.name = name

    @abc.abstractmethod
    def get_data(self):
        return

    @abc.abstractmethod
    def data_available(self):
        return

    @abc.abstractmethod
    def get_notification(self):
        return

    @abc.abstractmethod
    def notification_available(self):
        return

    @abc.abstractmethod
    def ack_data_callback(self):
        return

    @abc.abstractmethod
    def ack_notification_callback(self):
        return

    @abc.abstractmethod
    def failed_datastream_callback(self, datastream: 'stream.DataStream'):
        return

    @abc.abstractmethod
    def failed_notification_callback(self, notification_stream: 'stream.NotificationStream'):
        return
