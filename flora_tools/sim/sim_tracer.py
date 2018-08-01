import json
import os
from typing import List

import flora_tools.sim.sim_network as sim_network
from flora_tools import lwb_slot
from flora_tools.radio_configuration import RadioConfiguration


class Event:
    def __init__(self, event_type, marker, node):
        self.event_type = event_type
        self.marker = marker
        self.node = node

    def json(self):
        return {
            'event_type': str(self.event_type),
            'marker': self.marker,
            'node': self.node.id,
        }


class Activity:
    def __init__(self, activity_type, start: float, end: float, node, energy=None, details=None):
        self.activity_type = activity_type
        self.start = start
        self.end = end
        self.node = node
        self.energy = energy
        self.details = details

    def json(self):
        return {
            'activity_type': self.activity_type.__qualname__,
            'start': self.start,
            'end': self.end,
            'node': self.node.id,
            'energy': self.energy,
            'details': self.details
        }


class TxActivity(Activity):
    def __init__(self, start, end, node, energy, power, modulation):
        super(TxActivity, self).__init__(type(self), start, end, node, energy=energy,
                                         details={'power': power, 'modulation': modulation})


class RxActivity(Activity):
    def __init__(self, start, end, node, energy, modulation, success):
        super(RxActivity, self).__init__(type(self), start, end, node, energy=energy,
                                         details={'modulation': modulation, 'success': success})


class CADActivity(Activity):
    def __init__(self, start, end, node, energy, modulation, success):
        super(CADActivity, self).__init__(type(self), start, end, node, energy=energy,
                                          details={'modulation': modulation, 'success': success})


class LWBSlotActivity(Activity):
    def __init__(self, start, end, node, slot_type, energy=None, payload=0):
        super(LWBSlotActivity, self).__init__(type(self), start, end, node, energy=energy,
                                              details={'slot_type': str(slot_type), 'payload': payload})


class LWBRoundActivity(Activity):
    def __init__(self, start, end, node, round_type, modulation, energy=None):
        super(LWBRoundActivity, self).__init__(type(self), start, end, node, energy=energy,
                                               details={'round_type': str(round_type), 'modulation': modulation})


class SimTracer:
    def __init__(self, network: 'sim_network.SimNetwork', output_path):
        self.activities: List[Activity] = []
        self.events: List[Event] = []
        self.output_path = output_path
        self.network = network

    def log_activity(self, activity: Activity):
        self.activities.append(activity)

    def log_event(self, event: Event):
        self.events.append(event)

    def describe_network(self):
        edges = [[edge[0], edge[1]] for edge in self.network.G.edges]

        return {
            'modulations': [{'modulation': modulation, 'gloria_modulation': lwb_slot.RADIO_MODULATIONS[modulation],
                             'color': RadioConfiguration(lwb_slot.RADIO_MODULATIONS[modulation]).color,
                             'name': RadioConfiguration(lwb_slot.RADIO_MODULATIONS[modulation]).modulation_name} for
                            modulation in
                            range(len(lwb_slot.RADIO_MODULATIONS))],
            'nodes': [{'id': node.id, 'role': str(node.role)} for node in self.network.nodes],
            'edges': edges,
            'pos': self.network.pos
        }

    def store(self):
        # timestr = time.strftime("%Y%m%d-%H%M%S")

        with open(
                os.path.join(self.output_path, "simulation_trace.json"),  # "simulation_trace-{}.json".format(timestr)),
                "w") as write_file:
            json.dump({
                'network': self.describe_network(),
                'activities': [activity.json() for activity in self.activities],
                'events': [event.json() for event in self.events]
            }, write_file, indent=4)
