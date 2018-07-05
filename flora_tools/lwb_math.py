import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrow

from flora_tools.gloria_math import GloriaMath
from flora_tools.radio_configuration import RadioConfiguration

sync_period = 1 / 8E6 * np.exp2(29)  # Sync every 67.108864 (~ 15 years of battery life)
schedule_granularity = sync_period / 256

modulations = [2, 4, 7, 9]
bands = [48, 50]
powers = [22, 10]

payloads = [8, 16, 32, 64, 128, 255]
repetitions = [1, 1, 1, 2, 2, 2, 2, 2, 2, 2]
max_hops = [2, 2, 2, 3, 3, 3, 3, 3, 3, 3]
max_slots = [2, 2, 4, 4, 6, 6, 16, 16, 32, 32]

gloria_header_length = 4
sync_header_length = gloria_header_length + 4
contention_length = gloria_header_length + 3

rounds_schedule_buffer_items = len(modulations) * 2
round_schedule_length = gloria_header_length + rounds_schedule_buffer_items * 4

slot_schedule_item_length = 3

max_contention_layout = [2, 4, 4, 8, 8]
initial_contention_layout = [1, 1, 1, 1, 8]
min_contention_layout = [0, 0, 0, 0, 0]


class LWBMath:
    @staticmethod
    def calculate_sync_round(modulation, round_offset=0):
        color = RadioConfiguration(modulation).color

        slots = [
            {'type': 'sync'},
            {'type': 'contention'},
        ]

        return LWBMath.calculate_round(modulation, custom_slots=slots, round_offset=round_offset, slot_schedule=False)

    @staticmethod
    def calculate_round(modulation, custom_slots=[], round_offset=0, slot_schedule=True):
        color = RadioConfiguration(modulation).color

        slots = []
        if slot_schedule:
            slots.append(
                {'offset': 0, 'slot': LWBMath.calculate_slot_schedule_slot(modulation),
                 'type': 'slot_schedule',
                 'facecolor': 'darkorchid',
                 'edgecolor': color})
        else:
            slots.append(
                {'offset': 0, 'slot': LWBMath.calculate_sync_slot(modulation),
                 'type': 'sync',
                 'facecolor': 'fuchsia',
                 'edgecolor': color})

        for slot in custom_slots:
            if slot['type'] == 'data':
                slots.append({'offset': slots[-1]['offset'] + slots[-1]['slot']['time'],
                              'slot': LWBMath.calculate_data_slot(modulation, slot['payload']),
                              'type': 'data', 'facecolor': 'deepskyblue', 'edgecolor': color})
            elif slot['type'] == 'ack':
                slots.append({'offset': slots[-1]['offset'] + slots[-1]['slot']['time'],
                              'slot': LWBMath.calculate_contention_ack_slot(modulation), 'type': 'ack',
                              'facecolor': 'mediumaquamarine', 'edgecolor': color})
            elif slot['type'] == 'contention':
                slots.append({'offset': slots[-1]['offset'] + slots[-1]['slot']['time'],
                              'slot': LWBMath.calculate_contention_slot(modulation), 'type': 'contention',
                              'facecolor': 'lightcoral', 'edgecolor': color})
                if 'acked' in slot and slot['acked'] is True:
                    slots.append({'offset': slots[-1]['offset'] + slots[-1]['slot']['time'],
                                  'slot': LWBMath.calculate_contention_ack_slot(modulation),
                                  'type': 'ack',
                                  'facecolor': 'mediumaquamarine', 'edgecolor': color})

        slots.append({
            'offset': slots[-1]['offset'] + slots[-1]['slot']['time'],
            'slot': LWBMath.calculate_round_schedule_slot(modulation),
            'type': 'round_schedule',
            'facecolor': 'rebeccapurple',
            'edgecolor': color
        })
        return slots

    @staticmethod
    def plot_round(modulation, slots=None, timestamp=0, enable_markers=True):
        if slots is None:
            slots = LWBMath.calculate_sync_round(modulation, timestamp)
        else:
            slots = LWBMath.calculate_round(modulation, slots, timestamp)
        boxes = []

        for slot in slots:
            rect = Rectangle((slot['offset'], 0), slot['slot']['time'], 1, facecolor=slot['facecolor'],
                             edgecolor=slot['edgecolor'], linewidth=2)
            boxes.append(rect)

            for glossy_slot in slot['slot']['layout']:
                offset = slot['offset'] + glossy_slot['offset']
                if glossy_slot['type'] is 'tx':
                    facecolor = 'r'
                elif glossy_slot['type'] is 'rx':
                    facecolor = 'b'
                else:
                    facecolor = 'g'

                rect = Rectangle(
                    (offset, 0),
                    glossy_slot['time'],
                    0.5,
                    facecolor=facecolor
                )

                if enable_markers:
                    offset = slot['offset'] + glossy_slot['marker']
                    plt.plot([offset, offset], [0.4, 0.6], c='white', linewidth=1)

                boxes.append(rect)

        return boxes

    @staticmethod
    def calculate_slot(modulation, payload, ack=True):
        return GloriaMath().calculate_flood(modulation, payload, repetitions[modulation], max_hops[modulation], ack=ack)

    @staticmethod
    def calculate_data_slot(modulation, payload):
        return LWBMath.calculate_slot(modulations[modulation], payload=(gloria_header_length + payload), ack=True)

    @staticmethod
    def calculate_sync_slot(modulation):
        return LWBMath.calculate_slot(modulation, payload=sync_header_length, ack=False)

    @staticmethod
    def calculate_round_schedule_slot(modulation):
        return LWBMath.calculate_slot(modulation, payload=round_schedule_length, ack=False)

    @staticmethod
    def calculate_slot_schedule_slot(modulation):
        return LWBMath.calculate_slot(modulation, payload=(
                sync_header_length + max_slots[modulation] * slot_schedule_item_length), ack=False)

    @staticmethod
    def calculate_contention_slot(modulation):
        return LWBMath.calculate_slot(modulation, payload=contention_length, ack=True)

    @staticmethod
    def calculate_contention_ack_slot(modulation):
        return LWBMath.calculate_slot(modulation, payload=gloria_header_length, ack=True)
