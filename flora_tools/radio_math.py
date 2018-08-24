import numpy as np
import pandas as pd

from flora_tools.radio_configuration import RadioConfiguration, RadioModem

LORA_SYMB_TIMES = [  # in ms
    [32.768, 16.384, 8.192, 4.096, 2.048, 1.024, 0.512, 0.256],  # 125 kHz
    [16.384, 8.192, 4.096, 2.048, 1.024, 0.512, 0.256, 0.128],  # 250 kHz
    [8.192, 4.096, 2.048, 1.024, 0.512, 0.256, 0.128, 0.064],  # 500 kHz
]

NOISE_FLOOR = -174.0
LORA_NOISE_FIGURE = 6  # Between 5-8 dB (based on SX1276 datasheet interpolation)

PATH_LOSS_EXPONENT_FACTOR = 1.5  # Cubic loss

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

RF_SWITCH_INSERTION_LOSS = 2.0  # Due to spectrum analyzer measurements. Officially 3.5 dB @ 1GHz, Peregrine Semi PE4259, based on datasheet, one-way

SENSITIVITIES = [  # Based on values in the SX1276 datasheet (Rev. 5) if not declared otherwise
    {'modem': RadioModem.FSK, 'fda': 800, 'bitrate': 600, 'bandwidth': 4000, 'sensitivity': -125},
    # SX1262 (1dB worse than SX1276)
    {'modem': RadioModem.FSK, 'fda': 5000, 'bitrate': 1200, 'bandwidth': 20000, 'sensitivity': -123},
    # HF-Switch improves sensitivity about 4 dB in comparison
    {'modem': RadioModem.FSK, 'fda': 5000, 'bitrate': 4800, 'bandwidth': 20000, 'sensitivity': -118},
    # SX1262 (1dB worse than SX1276)
    {'modem': RadioModem.FSK, 'fda': 40000, 'bitrate': 38400, 'bandwidth': 83000, 'sensitivity': -109},
    {'modem': RadioModem.FSK, 'fda': 20000, 'bitrate': 38400, 'bandwidth': 50000, 'sensitivity': -109},
    {'modem': RadioModem.FSK, 'fda': 62500, 'bitrate': 250000, 'bandwidth': 250000, 'sensitivity': -96},
    {'modem': RadioModem.FSK, 'fda': 125000, 'bitrate': 250000, 'bandwidth': 500000, 'sensitivity': -104},
    # SX1262

    {'modem': RadioModem.LORA, 'sf': 12, 'bandwidth': 10400, 'sensitivity': -148},  # SX1262 (1dB better than SX1276)
    {'modem': RadioModem.LORA, 'sf': 7, 'bandwidth': 10400, 'sensitivity': -135},

    {'modem': RadioModem.LORA, 'sf': 12, 'bandwidth': 125000, 'sensitivity': -137},  # SX1262 (1dB better than SX1276)
    {'modem': RadioModem.LORA, 'sf': 11, 'bandwidth': 125000, 'sensitivity': -133},
    {'modem': RadioModem.LORA, 'sf': 10, 'bandwidth': 125000, 'sensitivity': -132},
    {'modem': RadioModem.LORA, 'sf': 9, 'bandwidth': 125000, 'sensitivity': -129},
    {'modem': RadioModem.LORA, 'sf': 8, 'bandwidth': 125000, 'sensitivity': -126},
    {'modem': RadioModem.LORA, 'sf': 7, 'bandwidth': 125000, 'sensitivity': -124},  # SX1262 (1dB better than SX1276)
    {'modem': RadioModem.LORA, 'sf': 6, 'bandwidth': 125000, 'sensitivity': -118},
    {'modem': RadioModem.LORA, 'sf': 5, 'bandwidth': 125000, 'sensitivity': -115},
    # SX1262 only (estimation). As SF5 & SF6 changed it's coding, process gain might be better for both.

    {'modem': RadioModem.LORA, 'sf': 12, 'bandwidth': 250000, 'sensitivity': -134},  # SX1262 (1dB better than SX1276)
    {'modem': RadioModem.LORA, 'sf': 11, 'bandwidth': 250000, 'sensitivity': -130},
    {'modem': RadioModem.LORA, 'sf': 10, 'bandwidth': 250000, 'sensitivity': -128},
    {'modem': RadioModem.LORA, 'sf': 9, 'bandwidth': 250000, 'sensitivity': -125},
    {'modem': RadioModem.LORA, 'sf': 8, 'bandwidth': 250000, 'sensitivity': -123},
    {'modem': RadioModem.LORA, 'sf': 7, 'bandwidth': 250000, 'sensitivity': -121},  # SX1262 (1dB better than SX1276)
    {'modem': RadioModem.LORA, 'sf': 6, 'bandwidth': 250000, 'sensitivity': -115},
    {'modem': RadioModem.LORA, 'sf': 5, 'bandwidth': 250000, 'sensitivity': -112},  # SX1262 only (estimation)

    {'modem': RadioModem.LORA, 'sf': 12, 'bandwidth': 500000, 'sensitivity': -129},  # SX1262 (1dB worse than SX1276)
    {'modem': RadioModem.LORA, 'sf': 11, 'bandwidth': 500000, 'sensitivity': -128},
    {'modem': RadioModem.LORA, 'sf': 10, 'bandwidth': 500000, 'sensitivity': -125},
    {'modem': RadioModem.LORA, 'sf': 9, 'bandwidth': 500000, 'sensitivity': -122},
    {'modem': RadioModem.LORA, 'sf': 8, 'bandwidth': 500000, 'sensitivity': -119},
    {'modem': RadioModem.LORA, 'sf': 7, 'bandwidth': 500000, 'sensitivity': -117},  # SX1262 (1dB better than SX1276)
    {'modem': RadioModem.LORA, 'sf': 6, 'bandwidth': 500000, 'sensitivity': -111},
    {'modem': RadioModem.LORA, 'sf': 5, 'bandwidth': 500000, 'sensitivity': -108},  # SX1262 only (estimation)
]


class RadioMath:
    def __init__(self, configuration: RadioConfiguration):
        self.configuration = configuration

    def get_symbol_time(self):
        if self.configuration.modem.value is RadioModem.LORA.value:
            ts = LORA_SYMB_TIMES[self.configuration.bandwidth][int(self.configuration.modulation)] / 1000.0
        elif self.configuration.modem.value is RadioModem.FSK.value:
            ts = 8 / self.configuration.bitrate
        else:
            ts = None
        return ts

    def get_preamble_time(self, preamble_length=0):
        if not preamble_length:
            preamble_length = self.configuration.preamble_len
        ts = self.get_symbol_time()
        if self.configuration.modem.value is RadioModem.LORA.value:
            time_preamble = ts * (preamble_length + (6.25 if self.configuration.sf in [6, 5] else 4.25))
        else:
            time_preamble = ts * preamble_length

        return time_preamble

    def get_message_toa(self, payload_size=0, preamble_length=0, sync=False, ceil_overhead=True):
        if not preamble_length:
            preamble_length = self.configuration.preamble_len

        if self.configuration.modem.value is RadioModem.LORA.value:
            ts = self.get_symbol_time()
            preamble_time = self.get_preamble_time(preamble_length)

            if ceil_overhead:
                tmp = (
                        np.ceil(
                            (
                                    8 * payload_size
                                    - 4 * self.configuration.sf
                                    + 28
                                    + (16 if self.configuration.crc and not sync else 0) -
                                    - (0 if self.configuration.explicit_header else 20)
                            )
                            / (4 * (self.configuration.sf - (2 if self.configuration.low_data_rate else 0)))
                        ) * (self.configuration.coderate % 4 + 4)
                )
            else:
                tmp = (
                        (
                                8 * payload_size
                                - 4 * self.configuration.sf
                                + 28
                                + (16 if self.configuration.crc and not sync else 0) -
                                - (0 if self.configuration.explicit_header else 20)
                        )
                        / (4 * (self.configuration.sf - (2 if self.configuration.low_data_rate else 0)))
                        * (self.configuration.coderate % 4 + 4)
                )

            n_payload = 8 + (tmp if tmp > 0 else 0)
            t_payload = n_payload * ts
            time_on_air = preamble_time + t_payload

            return time_on_air
        else:
            return 8 * (
                    preamble_length
                    + self.configuration.sync_word_length
                    + (1.0 if self.configuration.explicit_header else 0.0)
                    + payload_size
                    + (2.0 if self.configuration.crc and not sync else 0.0)
            ) / self.configuration.bitrate

    @property
    def sync_time(self, preamble_length=0):
        return self.get_message_toa(0, preamble_length, sync=True)

    @staticmethod
    def get_sync_time(modulation):
        return RadioMath(RadioConfiguration(modulation)).sync_time

    def get_datarate(self, payload_size=255):
        pass

    @property
    def sensitivity(self):
        global SENSITIVITIES
        if self.configuration.modem.value is RadioModem.LORA.value:
            df = pd.DataFrame(SENSITIVITIES)
            sensitivity = df[(df.sf == self.configuration.sf) & (
                    df.bandwidth == self.configuration.real_bandwidth)].sensitivity.sort_values().iloc[0]
            return sensitivity + RF_SWITCH_INSERTION_LOSS
        else:
            df = pd.DataFrame(SENSITIVITIES)
            sensitivity = df[(df.bitrate >= self.configuration.bitrate) & (
                    df.bandwidth >= self.configuration.real_bandwidth)].sensitivity.sort_values().iloc[0]
            return sensitivity + RF_SWITCH_INSERTION_LOSS

    def link_budget(self, power=22):
        return -(self.sensitivity - power + RF_SWITCH_INSERTION_LOSS)

    @staticmethod
    def get_theoretical_max_distance(modulation):
        # No antenna losses, no antenna gain, no Tx or Rx losses (connectors, coax). In meters [m].
        # The RF_SWITCH_INSERTION_LOSS is already included on the Rx side in the datasheet sensitivity values.
        MAX_POWER = 22  # dBm
        WAVELENGTH = 1.0 / 868E6 * 300E6
        link_budget = -(modulation.sensitivity - MAX_POWER + RF_SWITCH_INSERTION_LOSS)
        distance = np.power(10, link_budget / 10.0 / 2.0 / PATH_LOSS_EXPONENT_FACTOR) / np.sqrt(4 * np.pi) * WAVELENGTH
        return distance

    @staticmethod
    def get_bitrate(modulation):
        if modulation.modem == RadioModem.LORA:
            if modulation.bandwidth == 125000:
                bandwidth = 0
            elif modulation.bandwidth == 250000:
                bandwidth = 1
            elif modulation.bandwidth == 500000:
                bandwidth = 2
            else:
                bandwidth = 0
            config = RadioConfiguration(int(12 - modulation.sf), bandwidth=bandwidth)
            return config.symbol_rate * (config.sf - (2 if config.low_data_rate else 0)) * (
                    4 / (config.coderate % 4 + 4))
        else:
            return modulation.bitrate

    @staticmethod
    def get_energy_per_bit(modulation):
        MAX_PACKET = 255 * 8

        if modulation.modem.value is RadioModem.LORA.value:

            if modulation.bandwidth == 125000:
                bandwidth = 0
            elif modulation.bandwidth == 250000:
                bandwidth = 1
            elif modulation.bandwidth == 500000:
                bandwidth = 2
            else:
                bandwidth = 0
            config = RadioConfiguration(int(12 - modulation.sf), bandwidth=bandwidth)
        else:
            config = RadioConfiguration(8, bandwidth=modulation.bandwidth, bitrate=modulation.bitrate)

        math = RadioMath(config)
        return config.tx_energy(22, math.get_message_toa(MAX_PACKET)) / (MAX_PACKET * 8)
