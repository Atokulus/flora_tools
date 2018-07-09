import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from flora_tools.lwb_round import LWBRound
from flora_tools.lwb_slot import LWBSlot

class LWBVisualizer:
    @staticmethod
    def plot_round(round: 'LWBRound', enable_markers=True, track=0):

        boxes = []
        slot : LWBSlot
        for slot in round.slots:
            rect = Rectangle((slot.slot_marker, track), slot.total_time, 1, facecolor=LWBSlot.color,
                             edgecolor=round.color, linewidth=2)
            boxes.append(rect)

            for glossy_slot in slot.flood.slots:
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
