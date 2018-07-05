import numpy as np

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

voltage = 3.3
proc_power = 48 * 120E-6 * voltage
rx_power = 5.5E-3 * voltage
tx_power = lambda power: power * (250 / 100) + 8E-3 * voltage

gap = 50E-6

gloria_ack_length = 2
preamble_pre_listening = 0.2


class GloriaMath():
    def __init__(self, safety_factor=2):
        self.safety_factor = safety_factor

    def calculate_total_rx_time(self, modulation, payload):
        config = RadioConfiguration(modulation, preamble=GloriaMath.preamble_len(modulation))
        math = RadioMath(config)
        toa = math.get_message_toa(payload_size=payload)
        toa_offset = self.calculate_rx_offset(modulation)
        return toa + toa_offset + rx_time_offsets[modulation][0] + rx_time_offsets[modulation][1] * self.safety_factor

    def calculate_rx_offset(self, modulation):
        config = RadioConfiguration(modulation, preamble=GloriaMath.preamble_len(modulation))
        math = RadioMath(config)
        return math.get_preamble_time() * preamble_pre_listening

    def calculate_total_tx_time(self, modulation, payload):
        config = RadioConfiguration(modulation, preamble=GloriaMath.preamble_len(modulation))
        math = RadioMath(config)
        toa = math.get_message_toa(payload_size=payload)
        return toa + tx_time_offsets[modulation][0] + tx_time_offsets[modulation][1] * self.safety_factor

    def calculate_slot_time(self, modulation, payload, rx_following=False):
        if rx_following:
            if rx_following:
                rx2ackrx = self.calculate_total_rx_time(modulation, payload) + \
                           self.rx_irq_time + \
                           self.rx_setup_time
                tx2ackrx = self.calculate_total_tx_time(modulation, payload) + \
                           self.calculate_rx_offset(modulation) + \
                           self.tx_irq_time + \
                           self.rx_setup_time

                period = np.max([rx2ackrx, tx2ackrx])
                return period + gap

        else:
            rx2tx = self.calculate_total_rx_time(modulation, payload) - self.calculate_rx_offset(
                modulation) + self.rx_irq_time + self.tx_setup_time
            tx2rx = self.calculate_total_tx_time(modulation,
                                                 payload) + self.tx_irq_time + self.rx_setup_time + self.calculate_rx_offset(
                modulation)
            period = np.max([rx2tx, tx2rx])
            return period + gap

    def calculate_flood(self, modulation, payload, repetitions, max_hops, ack=False, tx=True):
        overhead = self.wakeup_time + \
                   self.payload_set_time + \
                   np.max([self.tx_setup_time, self.rx_setup_time]) + \
                   8.52937941e-05 + 5.45332554e-08 * self.safety_factor + \
                   self.calculate_rx_offset(modulation) + \
                   self.payload_get_time + \
                   self.sleep_time
        total_time = (2 * repetitions + (max_hops - 1)) * (
                self.calculate_slot_time(modulation, payload, rx_following=ack) +
                (self.calculate_slot_time(modulation, payload=gloria_ack_length, rx_following=True) if ack else 0)
        ) + overhead

        slot_layout = []

        if tx:
            offset = self.wakeup_time + \
                     self.payload_set_time + \
                     np.max([self.tx_setup_time, self.rx_setup_time]) + \
                     8.52937941e-05 + 5.45332554e-08 * self.safety_factor + \
                     self.calculate_rx_offset(modulation)
        else:
            offset = self.wakeup_time + \
                     self.payload_set_time + \
                     np.max([self.tx_setup_time, self.rx_setup_time]) + \
                     8.52937941e-05 + 5.45332554e-08 * self.safety_factor

        slot_time = self.calculate_slot_time(modulation, payload, rx_following=ack)

        for i in range(2 * repetitions + (max_hops - 1)):
            if (i % 2) ^ tx:
                type = 'tx'
                activity_time = self.calculate_total_tx_time(modulation, payload)
            else:
                type = 'rx'
                activity_time = self.calculate_total_rx_time(modulation, payload)

            slot = {'offset': offset - (self.calculate_rx_offset(modulation) if type is 'rx' else 0),
                    'time': activity_time, 'type': type, 'marker': offset,
                    'rx_marker': self.calculate_rx_start(modulation, offset),
                    'rx_timeout_marker': self.calculate_rx_timeout(modulation, offset),
                    'rx_end_marker': offset + self.calculate_total_rx_time(modulation, payload)}
            slot_layout.append(slot)

            if ack:
                offset += slot_time
                ack_time = self.calculate_slot_time(modulation, gloria_ack_length, rx_following=True)
                activity_time = self.calculate_total_rx_time(modulation, gloria_ack_length)
                slot = {'offset': offset - self.calculate_rx_offset(modulation), 'time': activity_time,
                        'type': 'rx_ack', 'marker': offset, 'rx_marker': self.calculate_rx_start(modulation, offset),
                        'rx_timeout_marker': self.calculate_rx_timeout(modulation, offset),
                        'rx_end_marker': offset + self.calculate_total_rx_time(modulation, payload)}
                slot_layout.append(slot)

                offset += ack_time
            else:
                offset += slot_time

        return {'time': total_time, 'layout': slot_layout}

    def calculate_flood_energy(self, modulation, payload, repetitions, max_hops, ack=False, power=10E-3):
        overhead = self.wakeup_time + \
                   self.payload_set_time + \
                   np.max([self.tx_setup_time, self.rx_setup_time]) + \
                   8.52937941e-05 + 5.45332554e-08 * self.safety_factor + \
                   self.calculate_rx_offset(modulation) + \
                   self.payload_get_time + \
                   self.sleep_time

        total_time = (2 * repetitions + (max_hops - 1)) * (
                self.calculate_slot_time(modulation, payload, rx_following=ack) +
                (self.calculate_slot_time(modulation, payload=gloria_ack_length, rx_following=True) if ack else 0)
        ) + overhead

        tx_total = repetitions * self.calculate_total_tx_time(modulation, payload) * tx_power(power)
        rx_total = (repetitions + max_hops) * self.calculate_total_rx_time(modulation, payload) * rx_power / 2
        proc_total = total_time * proc_power

        return tx_total + rx_total + proc_total

    def calculate_flood_bitrate(self, modulation, payload, repetitions, max_hops, ack=False):
        flood_time = self.calculate_flood(modulation, payload, repetitions, max_hops)['time']
        return 8 * payload / flood_time

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

    @staticmethod
    def preamble_len(modulation):
        return 2 if modulation > 7 else 3

    def calculate_rx_start(self, modulation, tx_marker):
        return tx_marker - self.calculate_rx_offset(modulation)

    def calculate_rx_timeout(self, modulation, tx_marker):
        config = RadioConfiguration(modulation, preamble=GloriaMath.preamble_len(modulation))
        math = RadioMath(config)
        return tx_marker - self.calculate_rx_offset(modulation) + math.get_preamble_time()
