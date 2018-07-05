import numpy as np
import pandas as pd
from flora_tools.radio_configuration import RadioConfiguration

LORA_SYMB_TIMES = [  # in ms
    [32.768, 16.384, 8.192, 4.096, 2.048, 1.024, 0.512, 0.256],  # 125 kHz
    [16.384, 8.192,  4.096, 2.048, 1.024, 0.512, 0.256, 0.128],  # 250 kHz
    [8.192,  4.096,  2.048, 1.024, 0.512, 0.256, 0.128, 0.064],  # 500 kHz
]


NOISE_FLOOR = -174.0
LORA_NOISE_FIGURE = 6  # Between 5-8 dB (based on SX1276 datasheet interpolation)

PATH_LOSS_CORRECTION_FACTOR = 1.5

RADIO_SNR = [  # Based on http://www.rfwireless-world.com/calculators/LoRa-Sensitivity-Calculator.html
    -20.0,
    -17.5,
    -15.0,
    -12.5,
    -10.0,
    -7.5,
    -5.0,
    -2.5,
    0.0,
    2.0,
]

RF_SWITCH_INSERTION_LOSS = 2.0  # Due to spectrum analyzer measurements. 3.5 dB @ 1GHz, Peregrine Semi PE4259, based on datasheet, one-way

SENSITIVITIES = [  # Based on values in the SX1276 datasheet (Rev. 5) if not declared otherwise
    {'modem': 'FSK', 'fda': 800, 'bitrate': 600, 'bandwidth': 4000, 'sensitivity': -125},  # SX1262 (1dB worse than SX1276)
    {'modem': 'FSK', 'fda': 5000, 'bitrate': 1200, 'bandwidth': 20000, 'sensitivity': -123}, # HF-Switch improves sensitivity about 4 dB in comparison
    {'modem': 'FSK', 'fda': 5000, 'bitrate': 4800, 'bandwidth': 20000, 'sensitivity': -118},  # SX1262 (1dB worse than SX1276)
    {'modem': 'FSK', 'fda': 40000, 'bitrate': 38400, 'bandwidth': 83000, 'sensitivity': -109},
    {'modem': 'FSK', 'fda': 20000, 'bitrate': 38400, 'bandwidth': 50000, 'sensitivity': -109},
    {'modem': 'FSK', 'fda': 62500, 'bitrate': 250000, 'bandwidth': 250000, 'sensitivity': -96},
    {'modem': 'FSK', 'fda': 125000, 'bitrate': 250000, 'bandwidth': 500000, 'sensitivity': -104},  # SX1262

    {'modem': 'LoRa', 'sf': 12, 'bandwidth': 125000, 'sensitivity': -137},  # SX1262 (1dB better than SX1276)
    {'modem': 'LoRa', 'sf': 11, 'bandwidth': 125000, 'sensitivity': -133},
    {'modem': 'LoRa', 'sf': 10, 'bandwidth': 125000, 'sensitivity': -132},
    {'modem': 'LoRa', 'sf': 9,  'bandwidth': 125000, 'sensitivity': -129},
    {'modem': 'LoRa', 'sf': 8,  'bandwidth': 125000, 'sensitivity': -126},
    {'modem': 'LoRa', 'sf': 7,  'bandwidth': 125000, 'sensitivity': -124},  # SX1262 (1dB better than SX1276)
    {'modem': 'LoRa', 'sf': 6,  'bandwidth': 125000, 'sensitivity': -118},
    {'modem': 'LoRa', 'sf': 5,  'bandwidth': 125000, 'sensitivity': -115},  # SX1262 only (estimation). As SF5 & SF6 changed it's coding, process gain might be better for both.

    {'modem': 'LoRa', 'sf': 12, 'bandwidth': 250000, 'sensitivity': -134},  # SX1262 (1dB better than SX1276)
    {'modem': 'LoRa', 'sf': 11, 'bandwidth': 250000, 'sensitivity': -130},
    {'modem': 'LoRa', 'sf': 10, 'bandwidth': 250000, 'sensitivity': -128},
    {'modem': 'LoRa', 'sf': 9, 'bandwidth': 250000, 'sensitivity': -125},
    {'modem': 'LoRa', 'sf': 8, 'bandwidth': 250000, 'sensitivity': -123},
    {'modem': 'LoRa', 'sf': 7, 'bandwidth': 250000, 'sensitivity': -121},  # SX1262 (1dB better than SX1276)
    {'modem': 'LoRa', 'sf': 6, 'bandwidth': 250000, 'sensitivity': -115},
    {'modem': 'LoRa', 'sf': 5, 'bandwidth': 250000, 'sensitivity': -112},  # SX1262 only (estimation)

    {'modem': 'LoRa', 'sf': 12, 'bandwidth': 500000, 'sensitivity': -129},  # SX1262 (1dB worse than SX1276)
    {'modem': 'LoRa', 'sf': 11, 'bandwidth': 500000, 'sensitivity': -128},
    {'modem': 'LoRa', 'sf': 10, 'bandwidth': 500000, 'sensitivity': -125},
    {'modem': 'LoRa', 'sf': 9, 'bandwidth': 500000, 'sensitivity': -122},
    {'modem': 'LoRa', 'sf': 8, 'bandwidth': 500000, 'sensitivity': -119},
    {'modem': 'LoRa', 'sf': 7, 'bandwidth': 500000, 'sensitivity': -117},  # SX1262 (1dB better than SX1276)
    {'modem': 'LoRa', 'sf': 6, 'bandwidth': 500000, 'sensitivity': -111},
    {'modem': 'LoRa', 'sf': 5, 'bandwidth': 500000, 'sensitivity': -108},  # SX1262 only (estimation)
]



class RadioMath:
    def __init__(self, configuration: RadioConfiguration):
        self.configuration = configuration

    def get_symbol_time(self):
        if self.configuration.modem is 'LoRa':
            ts = LORA_SYMB_TIMES[self.configuration.bandwidth][int(self.configuration.modulation)] / 1000.0
        elif self.configuration.modem is 'FSK':
            ts = 8 / self.configuration.bitrate
        return ts

    def get_preamble_time(self, preamble_length=0):
        if not preamble_length:
            preamble_length = self.configuration.preamble_len
        ts = self.get_symbol_time()
        if self.configuration.modem is 'LoRa':
            time_preamble = ts * (preamble_length + (6.25 if self.configuration.sf in [6, 5] else 4.25))
        else:
            time_preamble = ts * preamble_length

        return time_preamble

    def get_message_toa(self, payload_size=0, preamble_length=0, sync=False):
        global LORA_SYMB_TIMES

        if not preamble_length:
            preamble_length = self.configuration.preamble_len

        if self.configuration.modem == "LoRa":
            ts = self.get_symbol_time()
            tPreamble = self.get_preamble_time(preamble_length)
            tmp = np.ceil(
                (
                    8 * payload_size -
                    4 * self.configuration.sf +
                    28 +
                    16 * (1 if self.configuration.crc and not sync else 0) -
                    (0 if self.configuration.explicit_header else 20)
                ) / ( 4 * (
                    self.configuration.sf - (2 if self.configuration.low_data_rate else 0)
                ))
            ) * (
                self.configuration.coderate % 4 + 4
            )

            nPayload = ( tmp if tmp > 0 else 0)
            tPayload = nPayload * ts
            tOnAir = tPreamble + tPayload

            return tOnAir
        else:
            return (8 * (
                        preamble_length +
                        (self.configuration.sync_word_length) +
                        (1.0 if self.configuration.explicit_header else 0.0) +
                        payload_size +
                        (2.0 if self.configuration.crc and not sync else 0.0) )
                    ) / self.configuration.bitrate

    @property
    def sync_time(self, preamble_length=0):
        return self.get_message_toa(0, preamble_length, sync=True)

    @staticmethod
    def get_sync_time(modulation):
        return RadioMath(RadioConfiguration(modulation)).sync_time

    def get_datarate(self, payload_size = 255):
        pass

    @property
    def sensitivity(self):
        global SENSITIVITIES
        if self.configuration.modem is 'LoRa':
            #global LORA_NOISE_FIGURE, LORA_SNR, RF_SWITCH_INSERTION_LOSS, NOISE_FLOOR
            #return NOISE_FLOOR + 10 * np.log10(self.configuration.real_bandwidth) + LORA_NOISE_FIGURE + LORA_SNR[self.configuration.sf] + RF_SWITCH_INSERTION_LOSS

            df = pd.DataFrame(SENSITIVITIES)
            sensitivity = df[(df.sf == self.configuration.sf) & (df.bandwidth == self.configuration.real_bandwidth)].sensitivity.sort_values().iloc[0]
            return sensitivity + RF_SWITCH_INSERTION_LOSS
        else:
            df = pd.DataFrame(SENSITIVITIES)
            sensitivity = df[(df.bitrate >= self.configuration.bitrate) & (df.bandwidth >= self.configuration.real_bandwidth)].sensitivity.sort_values().iloc[0]
            return sensitivity + RF_SWITCH_INSERTION_LOSS

    def link_budget(self, power=22):
        global RF_SWITCH_INSERTION_LOSS
        return self.sensitivity - power + RF_SWITCH_INSERTION_LOSS

    @staticmethod
    def get_theoretical_max_distance(modulation):  # No antenna losses, no antenna gain, no Tx or Rx losses (connectors, coax). In meters [m].
        global RF_SWITCH_INSERTION_LOSS, PATH_LOSS_CORRECTION_FACTOR
        MAX_POWER = 22  # dBm
        WAVELENGTH = 1.0 / 868E6 * 300E6
        #ESTIMATED_LOSS = 20.0
        #MARGIN = 20.0
        link_budget = modulation.sensitivity - 30.0 - MAX_POWER
        distance = np.power(10, -link_budget / 20.0 / PATH_LOSS_CORRECTION_FACTOR) / (4 * np.pi) * WAVELENGTH
        return distance

    @staticmethod
    def get_bitrate(modulation):  # No antenna losses, no antenna gain, no Tx or Rx losses (connectors, coax). In meters [m].
        if modulation.modem == 'LoRa':

            if modulation.bandwidth == 125000:
                bandwidth = 0
            elif modulation.bandwidth == 250000:
                bandwidth = 1
            elif modulation.bandwidth == 500000:
                bandwidth = 2
            else:
                bandwidth = 0
            config = RadioConfiguration(12 - modulation.sf, bandwidth=bandwidth)
            return config.symbol_rate * (config.sf - (2 if config.low_data_rate else 0)) * (
                        4 / (config.coderate % 4 + 4))
        else:
            return modulation.bitrate

    @staticmethod
    def get_energy_per_bit(modulation):  # No antenna losses, no antenna gain, no Tx or Rx losses (connectors, coax). In meters [m].
        MAX_PACKET = 255 * 8

        if modulation.modem == 'LoRa':

            if modulation.bandwidth == 125000:
                bandwidth = 0
            elif modulation.bandwidth == 250000:
                bandwidth = 1
            elif modulation.bandwidth == 500000:
                bandwidth = 2
            else:
                bandwidth = 0
            config = RadioConfiguration(12 - modulation.sf, bandwidth=bandwidth)
        else:
            config = RadioConfiguration(8, bandwidth=modulation.bandwidth, bitrate=modulation.bitrate)

        math = RadioMath(config)
        return math.get_message_toa(MAX_PACKET, 3) / (MAX_PACKET * 8)










