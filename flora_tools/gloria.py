from enum import Enum
from typing import List

import numpy as np

import flora_tools.lwb_slot as lwb_slot
from flora_tools.radio_configuration import RadioConfiguration, MCU_PROC_POWER, RADIO_TIMER_PERIOD
from flora_tools.radio_math import RadioMath

DEFAULT_BAND = 48
TIMER_FREQUENCY = 8E6  # 0.125 us
GLORIA_CLOCK_DRIFT = 40E-6  # +- 20ppm

GLORIA_MCU_TIMEOUT_MULTIPLE = 1.5

BLACK_BOX_SYNC_DELAY = 1.96501309E-6

RX_TIME_OFFSETS = [
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

TX_TIME_OFFSETS = [
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

RX2RF = [8.52937941e-05, 5.45332554e-08]
TX2RF = [0.000126195, 6.29292616e-07]
TX2SYNC = [  # Explicit Header mode, CRC, 4/5, Preamble Length 2 (LoRa) and 3 (FSK)
    0.759868118,
    0.379071358,
    0.188429554,
    0.094311664,
    0.047281829,
    0.023714271,
    0.01403183,
    0.00717021,
    0.000906055,
    0.000386149731,
]

GAP = 800E-6

GLORIA_ACK_LENGTH = 2
PREAMBLE_PRE_LISTENING = [3 / 14.25, 3 / 14.25, 3 / 14.25, 3 / 14.25, 3 / 14.25, 3 / 14.25, 5 / 16.25, 5 / 16.25, 4.0,
                          4.0]
PREAMBLE_POST_LISTENING = [3 / 14.25, 3 / 14.25, 3 / 14.25, 3 / 14.25, 3 / 14.25, 3 / 14.25, 5 / 16.25, 5 / 16.25, 4.0,
                           4.0]


class GloriaSlotType(Enum):
    TX = 1
    RX = 2
    RX_ACK = 3
    TX_ACK = 4


class GloriaSlot:
    def __init__(self, flood: 'GloriaFlood', slot_offset: float, type: GloriaSlotType = None, payload=None,
                 power=10):
        self.slot_offset = slot_offset
        self.flood = flood
        self.type = type
        self.power = power  # in dBm
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
        return self.tx_marker + self.total_toa

    @property
    def rx_marker(self):
        return self.tx_marker - self.flood.gloria_timings.rx_offset

    @property
    def rx_timeout_marker(self):
        return self.tx_marker + self.flood.gloria_timings.radio_math.get_preamble_time() * (
                1 + PREAMBLE_POST_LISTENING[self.flood.modulation])

    @property
    def rx_end_marker(self):
        return self.rx_marker + self.total_rx_time

    @property
    def total_rx_time(self):
        return self.flood.gloria_timings.rx_offset + self.total_toa + self.flood.gloria_timings.rx_end_offset

    @property
    def total_tx_time(self):
        return self.total_toa + self.flood.gloria_timings.tx_end_offset

    @property
    def total_toa(self):
        return self.flood.gloria_timings.radio_math.get_message_toa(payload_size=self.payload)

    @property
    def active_time(self):
        if self.type is GloriaSlotType.TX or self.type is GloriaSlotType.TX_ACK:
            return self.total_tx_time
        else:
            return self.total_rx_time

    @property
    def energy(self):
        if self.type is GloriaSlotType.TX or self.type is GloriaSlotType.TX_ACK:
            return RadioConfiguration(self.flood.modulation).tx_energy(self.power, self.active_time) + (
                    self.flood.gloria_timings.tx_setup_time + self.flood.gloria_timings.tx_irq_time) * MCU_PROC_POWER
        else:
            return RadioConfiguration(self.flood.modulation).rx_energy(self.active_time) + (
                    self.flood.gloria_timings.rx_setup_time + self.flood.gloria_timings.rx_irq_time) * MCU_PROC_POWER

    @property
    def slot_time(self):
        if self.flood.acked and (self.type is GloriaSlotType.TX or self.type is GloriaSlotType.RX):
            return self.flood.gloria_timings.slot_ack_overhead + self.total_toa
        else:
            return self.flood.gloria_timings.slot_overhead + self.total_toa


class GloriaFlood:
    def __init__(self, lwb_slot: 'lwb_slot.LWBSlot', modulation: int, payload: int, retransmission_count: int,
                 hop_count: int,
                 is_ack=False, safety_factor=2, is_master=True, power=10, band: int = None):
        if band is None:
            band = DEFAULT_BAND

        self.lwb_slot = lwb_slot
        self.modulation = modulation
        self.payload = payload
        self.retransmission_count = retransmission_count
        self.hop_count = hop_count
        self.acked = is_ack
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
    def data_slot_count(self):
        if self.lwb_slot.round.low_power:
            return 1
        else:
            return (2 * self.retransmission_count - 1) + (self.hop_count - 1)

    def generate(self):
        temp_slot = GloriaSlot(self, 0, type=GloriaSlotType.TX)
        temp_ack_slot = GloriaSlot(self, 0, type=GloriaSlotType.RX_ACK, payload=GLORIA_ACK_LENGTH)

        self.overhead = self.gloria_timings.flood_init_overhead + self.gloria_timings.sleep_time

        self.total_time = (
                self.overhead +
                self.data_slot_count * temp_slot.slot_time +
                (self.data_slot_count - 1) * (temp_ack_slot.slot_time if self.acked else 0)
        )

        offset = self.gloria_timings.flood_init_overhead

        for i in range(self.data_slot_count):
            if (i % 2) ^ self.is_master:
                slot = GloriaSlot(self, offset, type=GloriaSlotType.TX)
            else:
                slot = GloriaSlot(self, offset, type=GloriaSlotType.RX)

            self.slots.append(slot)

            if self.acked and i < self.data_slot_count - 1:  # No ACK required for last data slot
                offset += slot.slot_time
                ack_slot = GloriaSlot(self, offset, GloriaSlotType.RX_ACK, payload=GLORIA_ACK_LENGTH, power=self.power)
                self.slots.append(ack_slot)

                offset += ack_slot.slot_time
            else:
                offset += slot.slot_time
        return

    @property
    def energy(self):
        energy = self.overhead * MCU_PROC_POWER
        for slot in self.slots:
            energy += slot.energy

        return energy

    @property
    def bitrate(self):
        return self.payload * 8 / self.total_time


class GloriaTimings:
    def __init__(self, modulation: int, safety_factor: int = 2):
        self.modulation = modulation
        self.safety_factor = safety_factor

        self.radio_config = RadioConfiguration(self.modulation)
        self.radio_math = RadioMath(self.radio_config)

    @property
    def rx_setup_time(self):
        # delay_fsk_config_rx
        # delay_fsk_rx_boost
        # delay_rx_2_fs
        tmp = (
                0.000471490321 + 1.40729712e-05 * self.safety_factor +
                7.71854385e-05 + 1.18305852e-06 * self.safety_factor +
                RX2RF[0] + TX2RF[1] * self.safety_factor
        )
        return tmp

    @property
    def rx_irq_time(self):
        # irq_delay_finish
        # status_delay
        tmp = (
                5.92039801e-05 + 4.86421406e-07 * self.safety_factor +
                4.16382322e-05 + 1.03885748e-06 * self.safety_factor +
                self.payload_get_time
        )
        return tmp

    @property
    def tx_setup_time(self):
        # delay_config_tx
        # delay_fsk_tx
        # delay_tx_2_fs
        tmp = (
                0.000526660267 + 2.67004382e-05 * self.safety_factor +
                1.76468861e-05 + 1.90078286e-09 * self.safety_factor +
                TX2RF[0] + TX2RF[1] * self.safety_factor +
                self.payload_set_time
        )
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
        return self.radio_config.preamble_len

    @property
    def rx_offset(self):
        return self.radio_math.get_preamble_time() * (PREAMBLE_PRE_LISTENING[self.modulation])

    @property
    def rx_end_offset(self):
        return RX_TIME_OFFSETS[self.modulation][0] + RX_TIME_OFFSETS[self.modulation][1] * self.safety_factor

    @property
    def tx_end_offset(self):
        return TX_TIME_OFFSETS[self.modulation][0] + TX_TIME_OFFSETS[self.modulation][1] * self.safety_factor

    @property
    def slot_overhead(self):
        tx2rx_overhead = (
                self.tx_end_offset
                + self.tx_irq_time
                + self.rx_setup_time
                + self.rx_offset
                + GAP
        )

        rx2tx_overhead = (
                self.rx_end_offset
                + self.rx_irq_time + self.rx_setup_time
                + GAP
        )

        return np.max([tx2rx_overhead, rx2tx_overhead])

    @property
    def slot_ack_overhead(self):
        max_normal_overhead = self.slot_overhead

        rx2rx_overhead = (
                self.rx_end_offset
                + self.rx_irq_time
                + self.rx_setup_time
                + self.rx_offset
                + GAP
        )

        return np.max([max_normal_overhead, rx2rx_overhead])

    @property
    def flood_init_overhead(self):
        return self.wakeup_time + np.max([self.tx_setup_time, self.rx_setup_time + self.rx_offset])

    @property
    def flood_finish_overhead(self):
        return self.sleep_time

    def get_timings(self):
        return {
            'slot_overhead': GloriaTimings.timer_ticks(self.slot_overhead),
            'slot_ack_overhead': GloriaTimings.timer_ticks(self.slot_ack_overhead),
            'flood_init_overhead': GloriaTimings.timer_ticks(self.flood_init_overhead),
            'flood_finish_overhead': GloriaTimings.timer_ticks(self.flood_finish_overhead),
            'rx_offset': GloriaTimings.timer_ticks(self.rx_offset),
            'rx_trigger_delay': GloriaTimings.timer_ticks(RX2RF[0]),
            'tx_trigger_delay': GloriaTimings.timer_ticks(TX2RF[0]),
            'tx_sync': GloriaTimings.timer_ticks(TX2SYNC[self.modulation]),
            'rx_setup': GloriaTimings.timer_ticks(self.rx_setup_time),
            'tx_setup': GloriaTimings.timer_ticks(self.tx_setup_time),
            'preamble_timeout': GloriaTimings.radio_timer_ticks(self.radio_math.get_preamble_time() * (
                    1 + PREAMBLE_PRE_LISTENING[self.modulation] + PREAMBLE_POST_LISTENING[self.modulation])),
            'mcu_timeout': GloriaTimings.timer_ticks(
                (RX2RF[0] + RX2RF[1]
                 * self.safety_factor
                 + self.rx_offset
                 + TX2SYNC[self.modulation] * 1.5
                 + self.radio_math.get_preamble_time() * PREAMBLE_POST_LISTENING[self.modulation])),
        }

    @staticmethod
    def timer_ticks(time: float) -> int:
        return int(np.round(time * TIMER_FREQUENCY))

    @staticmethod
    def radio_timer_ticks(time: float) -> int:
        return int(np.round(time / RADIO_TIMER_PERIOD))
