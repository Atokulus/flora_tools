import flora_tools.lwb_round as lwb_round
import flora_tools.lwb_slot as lwb_slot
import flora_tools.sim.sim_node as sim_node


class LWBScheduleManager:
    def __init__(self, node: 'sim_node.SimNode'):
        self.node = node

        self.rounds = []
        self.round_count = []

        self.stream_contention_layout = lwb_round.initial_contention_layout

        if self.node.role is 'base':
            self.base = self.node
            self.generate_initial_schedule()
        else:
            self.base = None

    def increment_contention(self, modulation):
        if self.stream_contention_layout[modulation] < lwb_round.max_contention_layout:
            self.stream_contention_layout[modulation] += 1

    def decrement_contention(self, modulation):
        if self.stream_contention_layout[modulation] > lwb_round.min_contention_layout:
            self.stream_contention_layout[modulation] -= 1

    def generate_initial_schedule(self):
        slot_times = lwb_round.LWBRound.create_sync_round(self.lwb_slot.modulations[0], self.node.local_timestamp,
                                                          self.node)

        self.rounds.append({'offsets': slot_times, 'master': self.node})

        end_of_last_round = slot_times[-1]['offset']

        for i in reversed(range(len(lwb_slot.MODULATIONS))):
            slots = [{'type': 'contention_slot'} for x in range(lwb_math.initial_contention_layout[i])]
            slot_times = LWBVisualizer.calculate_round(lwb_math.modulations[i], slots, self.node)

            for offset in slot_times:
                offset['offset'] += end_of_last_round

            self.rounds.append({'modulation': lwb_math.modulations[i], 'offsets': slot_times, 'master': self.node})

            end_of_last_round = slot_times[-1]['offset']

        self.schedule = slot_times

    def select_data_slot_message(self):
        pass

    def get_next_epoch(self):
        self
