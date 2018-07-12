import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from flora_tools.gloria import GloriaSlot
from flora_tools.lwb_round import LWBRound
from flora_tools.lwb_slot import LWBSlot


class LWBVisualizer:
    @staticmethod
    def plot_round(round: 'LWBRound', ax, enable_markers=True, track: int = 0):
        boxes = []

        rect = Rectangle((round.round_marker, track), round.total_time, 0.8,
                         edgecolor=round.color, linewidth=4)
        boxes.append(rect)

        slot: LWBSlot
        for slot in round.slots:
            rect = Rectangle((slot.slot_marker, track), slot.total_time, 0.8, facecolor=slot.color, linewidth=2)
            boxes.append(rect)

            gloria_slot: GloriaSlot
            for gloria_slot in slot.flood.slots:
                rect = Rectangle(
                    (gloria_slot.active_marker, track),
                    gloria_slot.active_time,
                    0.4,
                    facecolor=gloria_slot.color
                )

                if enable_markers:
                    plt.plot([gloria_slot.tx_marker, gloria_slot.tx_marker], [0.2 + track, 0.4 + track], c='white',
                             linewidth=1)

                boxes.append(rect)

            ax.text(slot.slot_marker + slot.total_time / 2, 0.6 + track, slot.type,
                    horizontalalignment='center',
                    verticalalignment='center', color='white', rotation=90, fontsize=6)

        for box in boxes:
            ax.add_patch(box)

        ax.text(round.round_marker + round.total_time / 2, 0.82 + track, round.type, horizontalalignment='center',
                verticalalignment='bottom')

        return boxes
