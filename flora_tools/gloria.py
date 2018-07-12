from enum import Enum
from typing import List

import numpy as np

import flora_tools.lwb_slot as lwb_slot
from flora_tools.lwb_slot import BANDS
from flora_tools.radio_configuration import RadioConfiguration
from flora_tools.radio_math import RadioMath

rx_time_offsets = [
    [0.359425231, 0.080458787],
    [0.182863757, 0.040771985],
    [0.089035287, 0.020060414],
    [0.044868022, 0.010087112],
    [0.023155864, 0.005082207],
    [0.01212482, 0.002489183],
    [0.005515929, 0.001180395],
    [0.00296378, 0.000603006],
    [0.000372544, 1.17E-06],
    [0.000308802, 1.47E-06],
]

tx_time_offsets = [
    [0.214534134, 0.076070831],
    [0.127697631, 0.017080405],
    [0.061834894, 0.012322289],
    [0.02956061, 0.007853842],
    [0.013441655, 0.004919127],
    [0.008188241, 0.001045395],
    [0.00229512, 0.001069851],
    [0.001502528, 0.000644286],
    [0.000310871, 6.28E-07],
    [0.000274632, 5.29E-07],
]

voltage = 3.7
proc_power = 48 * 120E-6 * voltage
rx_power = 5.5E-3 * voltage


def tx_power(power):
    return 8E-3 * voltage + power


gap = 50E-6

gloria_ack_length = 2
preamble_pre_listening = 0.2

preamble_lengths = [3, 3, 3, 3, 3, 3, 3, 3, 2, 2]


class GloriaSlotType(Enum):
    TX = 1
    RX = 2
    RX_ACK = 3
    TX_ACK = 4


class GloriaSlot:
    def __init__(self, flood: 'GloriaFlood', slot_offset: float, type: GloriaSlotType = None, payload=None,
                 power=10E-3):
        self.slot_offset = slot_offset
        self.flood = flood
        self.type = type
        self.power = power
        if payload is None:
            self.payload = self.flood.payload
        else:
            self.payload = payload

    @property
    def color(self):
        if self.type is GloriaSlotType.TX:
            return 'r'
        elif self.type is GloriaSlotType.RX:
            return 'b'
        else:
            return 'g'

    @property
    def active_marker(self):
        if self.type in [GloriaSlotType.RX, GloriaSlotType.RX_ACK]:
            return self.rx_marker
        else:
            return self.tx_marker

    @property
    def tx_marker(self):
        return self.flood.flood_marker + self.slot_offset

    @property
    def tx_done_marker(self):
        return self.tx_marker + self.total_tx_time

    @property
    def rx_marker(self):
        return self.tx_marker - self.rx_offset

    @property
    def rx_timeout_marker(self):
        return self.rx_marker + self.flood.gloria_timings.radio_math.get_preamble_time()

    @property
    def rx_end_marker(self):
        return self.rx_marker + self.total_rx_time

    @property
    def total_rx_time(self):
        toa = self.flood.gloria_timings.radio_math.get_message_toa(payload_size=self.payload)
        toa_offset = self.rx_offset
        return toa + toa_offset + rx_time_offsets[self.flood.modulation][0] + rx_time_offsets[self.flood.modulation][
            1] * self.flood.safety_factor

    @property
    def rx_offset(self):
        return self.flood.gloria_timings.radio_math.get_preamble_time() * preamble_pre_listening

    @property
    def total_tx_time(self):
        toa = self.flood.gloria_timings.radio_math.get_message_toa(payload_size=self.payload)
        return toa + tx_time_offsets[self.flood.modulation][0] + tx_time_offsets[self.flood.modulation][
            1] * self.flood.safety_factor

    @property
    def active_time(self):
        if self.type is GloriaSlotType.TX or self.type is GloriaSlotType.TX_ACK:
            return self.total_tx_time
        else:
            return self.total_rx_time

    @property
    def energy(self):
        if self.type is GloriaSlotType.TX or self.type is GloriaSlotType.TX_ACK:
            return self.active_time * tx_power(self.power) + (
                    self.flood.gloria_timings.tx_setup_time + self.flood.gloria_timings.tx_irq_time) * proc_power
        else:
            return self.active_time * rx_power + (
                    self.flood.gloria_timings.rx_setup_time + self.flood.gloria_timings.rx_irq_time) * proc_power

    @property
    def slot_time(self):
        if self.flood.acked and (self.type is GloriaSlotType.TX or self.type is GloriaSlotType.RX):
            rx2ackrx = self.total_rx_time + \
                       self.flood.gloria_timings.rx_irq_time + \
                       self.flood.gloria_timings.rx_setup_time
            tx2ackrx = self.total_tx_time + \
                       self.rx_offset + \
                       self.flood.gloria_timings.tx_irq_time + \
                       self.flood.gloria_timings.rx_setup_time

            period = np.max([rx2ackrx, tx2ackrx])
            return period + gap

        else:
            rx2tx = self.total_rx_time - self.rx_offset + self.flood.gloria_timings.rx_irq_time + self.flood.gloria_timings.tx_setup_time
            tx2rx = self.total_tx_time + self.flood.gloria_timings.tx_irq_time + self.flood.gloria_timings.rx_setup_time + self.rx_offset
            period = np.max([rx2tx, tx2rx])
            return period + gap


class GloriaFlood:
    def __init__(self, lwb_slot: 'lwb_slot.LWBSlot', modulation: int, payload: int, retransmission_count: int,
                 hop_count: int,
                 acked=False, safety_factor=2, is_master=True, power=10E-3, band: int = BANDS[0]):
        self.lwb_slot = lwb_slot
        self.modulation = modulation
        self.payload = payload
        self.retransmission_count = retransmission_count
        self.hop_count = hop_count
        self.acked = acked
        self.safety_factor = safety_factor
        self.is_master = is_master
        self.power = power
        self.gloria_timings = GloriaTimings(modulation=self.modulation)
        self.band = band

        self.total_time = None
        self.overhead = None

        self.slots: List[GloriaSlot] = []

    @property
    def flood_marker(self):
        return self.lwb_slot.slot_marker

    @property
    def slot_count(self):
        if self.lwb_slot.round.low_power:
            return 1
        else:
            return (2 * self.retransmission_count - 1) + (self.hop_count - 1)

    def generate(self):
        temp_slot = GloriaSlot(self, 0, type=GloriaSlotType.TX)
        temp_ack_slot = GloriaSlot(self, 0, type=GloriaSlotType.RX_ACK, payload=gloria_ack_length)

        self.overhead = (self.gloria_timings.wakeup_time +
                         self.gloria_timings.payload_set_time +
                         np.max([self.gloria_timings.tx_setup_time, self.gloria_timings.rx_setup_time]) +
                         8.52937941e-05 + 5.45332554e-08 * self.safety_factor +
                         temp_slot.rx_offset +
                         self.gloria_timings.payload_get_time +
                         self.gloria_timings.sleep_time)

        self.total_time = (self.slot_count * temp_slot.slot_time +
                           (self.slot_count - 1) * (temp_ack_slot.slot_time if self.acked else 0)
                           + self.overhead)

        offset = (self.gloria_timings.wakeup_time +
                  self.gloria_timings.payload_set_time +
                  np.max([self.gloria_timings.tx_setup_time, self.gloria_timings.rx_setup_time]) +
                  8.52937941e-05 + 5.45332554e-08 * self.safety_factor +
                  temp_slot.rx_offset)

        for i in range(self.slot_count):
            if (i % 2) ^ self.is_master:
                slot = GloriaSlot(self, offset, type=GloriaSlotType.TX)
            else:
                slot = GloriaSlot(self, offset, type=GloriaSlotType.RX)

            self.slots.append(slot)

            if self.acked and i < self.slot_count - 1:
                offset += slot.slot_time
                ack_slot = GloriaSlot(self, offset, GloriaSlotType.RX_ACK, payload=gloria_ack_length, power=self.power)
                self.slots.append(ack_slot)

                offset += ack_slot.slot_time
            else:
                offset += slot.slot_time

        return

    def energy(self):
        energy = self.overhead * proc_power
        for slot in self.slots:
            energy += slot.energy

        return energy

    def bitrate(self):
        return self.payload * 8 / self.total_time


class GloriaTimings:
    def __init__(self, modulation: int, safety_factor: int = 2):
        self.modulation = modulation
        self.safety_factor = safety_factor

        self.radio_config = RadioConfiguration(self.modulation, preamble=self.preamble_len)
        self.radio_math = RadioMath(self.radio_config)

    @property
    def rx_setup_time(self):
        # delay_fsk_config_rx
        # delay_fsk_rx_boost
        # delay_rx_2_fs
        tmp = \
            0.000471490321 + 1.40729712e-05 * self.safety_factor + \
            7.71854385e-05 + 1.18305852e-06 * self.safety_factor + \
            8.52937941e-05 + 5.45332554e-08 * self.safety_factor
        return tmp

    @property
    def rx_irq_time(self):
        # irq_delay_finish
        # status_delay
        ## payload_delay_lora
        # approx. payload_delay for 16 bytes
        tmp = \
            5.92039801e-05 + 4.86421406e-07 * self.safety_factor + \
            4.16382322e-05 + 1.03885748e-06 * self.safety_factor + \
            0.00025  # Get buffer
        return tmp

    @property
    def tx_setup_time(self): \
            # delay_config_tx
        # delay_fsk_tx
        # delay_tx_2_fs
        tmp = \
            0.000526660267 + 2.67004382e-05 * self.safety_factor + \
            1.76468861e-05 + 1.90078286e-09 * self.safety_factor + \
            0.000126364995 + 6.29292616e-07 * self.safety_factor
        return tmp

    @property
    def tx_irq_time(self):
        # irq_delay_finish
        tmp = 5.92039801e-05 + 4.86421406e-07 * self.safety_factor
        return tmp

    @property
    def sleep_time(self):
        return 1.52926223e-05 + 1.82871623e-06 * self.safety_factor

    @property
    def wakeup_time(self):
        # 14us for STM32L4 (Standby LPR SRAM2):
        # (http://www.st.com/content/ccc/resource/technical/document/application_note/9e/9b/ca/a3/92/5d/44/ff/DM00148033.pdf/files/DM00148033.pdf/jcr:content/translations/en.DM00148033.pdf)
        return 0.000488257072 + 1.01439514e-05 * self.safety_factor + 14E-6

    @property
    def payload_get_time(self):
        return 0.000528727308 + 1.63738628e-06 * self.safety_factor

    @property
    def payload_set_time(self):
        return 0.000528918379 + 3.12690783e-06 * self.safety_factor

    @property
    def wakeup_config(self):
        return 0.0008073303060942998

    @property
    def preamble_len(self):
        return 2 if self.modulation > 7 else 3
