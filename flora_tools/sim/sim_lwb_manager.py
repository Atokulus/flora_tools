from flora_tools.sim.sim_message import SimMessage
from flora_tools.sim.sim_lwb_slot_manager import SimLWBSlotManager
from flora_tools.sim.sim_node import SimNode
import flora_tools.lwb_math as lwb_math
from flora_tools.lwb_math import LWBMath

class SimLWBManager:
    def __init__(self, node: 'SimNode'):
        self.node = node
        self.rounds = []

    def generate_initial_schedule(self):
        slot_times = LWBMath.calculate_sync_round(lwb_math.modulations[0], self.node.local_timestamp, self.node)

        self.rounds.append({'offsets': slot_times, 'master': self.node})

        end_of_last_round = slot_times[-1]['offset']

        for i in reversed(range(len(lwb_math.modulations))):
            slots = [{'type': 'contention_slot'} for x in range(lwb_math.initial_contention_layout[i])]
            slot_times = LWBMath.calculate_round(lwb_math.modulations[i], slots, self.node)

            for offset in slot_times:
                offset['offset'] += end_of_last_round

            self.rounds.append({'modulation': lwb_math.modulations[i], 'offsets': slot_times, 'master': self.node})

            end_of_last_round = slot_times[-1]['offset']

        return slot_times

    def register_slot(self, slot):
        for round in self.rounds:
            if round[]



    def process_sync_slot(self, slot):

    def process_slot_schedule_slot(self, round, slot):
        if self.node.role is 'base':
            message = SimMessage(slot['modulation'], slot['tx_start'], self.node, slot['payload'], modulation=slot['modulation'], destination=None, type='slot_schedule', content=round, power_level=0)
            SimLWBSlotManager(self.node, slot, self.process_slot_schedule_slot_callback, tx_node=self.node, message=message)
        else:
            SimLWBSlotManager(self.node, slot, self.process_slot_schedule_slot_callback, tx_node=self.node.current_base, message=None)

    def process_slot_schedule_slot_callback(self, message: SimMessage):
        if not (self.node.role is 'base') and message is not None and message.type is 'slot_schedule':
            slots = message.content['offsets']
            for slot in slots[1:]:
                self.register_slot(slot)


