from flora_tools.sim.sim_message import SimMessage
from flora_tools.sim.sim_gloria_flood import SimGloriaFlood
from flora_tools.sim.sim_node import SimNode
import flora_tools.lwb_math as lwb_math
from flora_tools.lwb_math import LWBMath

scan_offset = 0.080

class SimLWBManager:
    def __init__(self, node: 'SimNode'):
        self.node = node

        self.rounds = []
        self.gloria_manager = SimGloriaFlood(self.node)

    def generate_initial_schedule(self):
        slot_times = LWBMath.calculate_sync_round(self.node.local_timestamp)


        self.rounds.append({'mod': lwb_math.modulations[0], 'offsets': slot_times})

        end_of_last_round = slot_times[-1]['offset']

        for i in reversed(range(len(lwb_math.modulations))):
            slots = [{'type': 'contention_slot'} for x in range(lwb_math.initial_contention_layout[i])]
            slot_times = LWBMath.calculate_round(lwb_math.modulations[i], slots)

            for offset in slot_times:
                offset['offset'] += end_of_last_round

            self.rounds.append({'mod': lwb_math.modulations[i], 'offsets': slot_times})

            end_of_last_round = slot_times[-1]['offset']

        return slot_times

    def scan_for_message(self):




    def update_rounds_schedule(self, schedule_msg: SimMessage):
        current_link = self.links[self.current_base]
        new_link = self.links[schedule_msg.source]
        if self.current_rounds_schedule is None \
                or (new_link['modulation'] > current_link['modulation']) \
                or (new_link['modulation'] == current_link['modulation'] and new_link['power'] < current_link['power']):

            self.current_base = schedule_msg.source
            self.current_rounds_schedule = schedule_msg.schedule