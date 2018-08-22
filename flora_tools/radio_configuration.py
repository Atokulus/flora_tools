from enum import Enum

import matplotlib
import matplotlib.cm
import numpy as np

HS_TIMER_SCHEDULE_MARGIN = 800  # 100 μs

RADIO_TIMER_PERIOD = 15.625E-6

RADIO_DEFAULT_BAND = 48
RADIO_DEFAULT_BAND_US915 = 0

BAND_FREQUENCIES = [
    # Duty-cycle in 1/1000
    # Subband 863.0 - 865.0 MHz (0)
    {'center_frequency': 863E6 + 1 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 1, 'max_power': 14},
    {'center_frequency': 863E6 + 3 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 1, 'max_power': 14},
    {'center_frequency': 863E6 + 5 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 1, 'max_power': 14},
    {'center_frequency': 863E6 + 7 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 1, 'max_power': 14},
    {'center_frequency': 863E6 + 9 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 1, 'max_power': 14},
    {'center_frequency': 863E6 + 11 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 1, 'max_power': 14},
    {'center_frequency': 863E6 + 13 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 1, 'max_power': 14},
    {'center_frequency': 863E6 + 15 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 1, 'max_power': 14},
    {'center_frequency': 863E6 + 17 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 1, 'max_power': 14},
    {'center_frequency': 863E6 + 19 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 1, 'max_power': 14},
    {'center_frequency': 863E6 + 21 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 1, 'max_power': 14},
    {'center_frequency': 863E6 + 23 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 1, 'max_power': 14},
    {'center_frequency': 863E6 + 25 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 1, 'max_power': 14},
    {'center_frequency': 863E6 + 27 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 1, 'max_power': 14},
    {'center_frequency': 863E6 + 29 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 1, 'max_power': 14},
    {'center_frequency': 863E6 + 31 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 1, 'max_power': 14},
    # Subband 865.0 - 868.0 MHz (16)
    {'center_frequency': 865E6 + 1 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 10, 'max_power': 14},
    {'center_frequency': 865E6 + 3 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 10, 'max_power': 14},
    {'center_frequency': 865E6 + 5 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 10, 'max_power': 14},
    {'center_frequency': 865E6 + 7 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 10, 'max_power': 14},
    {'center_frequency': 865E6 + 9 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 10, 'max_power': 14},
    {'center_frequency': 865E6 + 11 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 10, 'max_power': 14},
    {'center_frequency': 865E6 + 13 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 10, 'max_power': 14},
    {'center_frequency': 865E6 + 15 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 10, 'max_power': 14},
    {'center_frequency': 865E6 + 17 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 10, 'max_power': 14},
    {'center_frequency': 865E6 + 19 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 10, 'max_power': 14},
    {'center_frequency': 865E6 + 21 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 10, 'max_power': 14},
    {'center_frequency': 865E6 + 23 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 10, 'max_power': 14},
    {'center_frequency': 865E6 + 25 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 10, 'max_power': 14},
    {'center_frequency': 865E6 + 27 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 10, 'max_power': 14},
    {'center_frequency': 865E6 + 29 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 10, 'max_power': 14},
    {'center_frequency': 865E6 + 31 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 10, 'max_power': 14},
    {'center_frequency': 865E6 + 33 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 10, 'max_power': 14},
    {'center_frequency': 865E6 + 35 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 10, 'max_power': 14},
    {'center_frequency': 865E6 + 37 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 10, 'max_power': 14},
    {'center_frequency': 865E6 + 39 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 10, 'max_power': 14},
    {'center_frequency': 865E6 + 41 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 10, 'max_power': 14},
    {'center_frequency': 865E6 + 43 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 10, 'max_power': 14},
    {'center_frequency': 865E6 + 45 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 10, 'max_power': 14},
    {'center_frequency': 865E6 + 47 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 10, 'max_power': 14},
    # Subband 868.0  868.6 MHz (40)
    {'center_frequency': 868E6 + 1 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 10, 'max_power': 14},
    {'center_frequency': 868E6 + 3 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 10, 'max_power': 14},
    {'center_frequency': 868E6 + 5 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 10, 'max_power': 14},
    {'center_frequency': 868E6 + 7 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 10, 'max_power': 14},
    # Subband 868.7 - 869.2 MHz (44)
    {'center_frequency': 868.7E6 + 1 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 1, 'max_power': 14},
    {'center_frequency': 868.7E6 + 3 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 1, 'max_power': 14},
    {'center_frequency': 868.7E6 + 5 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 1, 'max_power': 14},
    {'center_frequency': 868.7E6 + 7 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 1, 'max_power': 14},
    # Subband 869.4 - 869.65 MHz (48)
    {'center_frequency': 869.4E6 + 1 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 100, 'max_power': 26},
    {'center_frequency': 869.4E6 + 3 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 100, 'max_power': 26},
    # Subband 869.7 - 870 MHz (50)
    {'center_frequency': 869.7E6 + 1 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 100, 'max_power': 7},
    {'center_frequency': 869.7E6 + 3 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 100, 'max_power': 7},
]

BAND_GROUPS = [
    {'lower': 0, 'upper': 15},
    {'lower': 16, 'upper': 39},
    {'lower': 40, 'upper': 43},
    {'lower': 44, 'upper': 47},
    {'lower': 48, 'upper': 49},
    {'lower': 50, 'upper': 51},
]

BAND_FREQUENCIES_US915 = [
    {'center_frequency': 915E6 - 3 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 100, 'max_power': 26},
    {'center_frequency': 915E6 - 1 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 100, 'max_power': 26},
    {'center_frequency': 915E6 + 1 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 100, 'max_power': 26},
    {'center_frequency': 915E6 + 3 * 125E3 / 2, 'bandwidth': 125E3, 'duty_cycle': 100, 'max_power': 26},
]

BAND_GROUPS_US915 = [
    {'lower': 0, 'upper': 3},
]

LORA_BANDWIDTHS = [
    125000,
    250000,
    500000,
]

FSK_BANDWIDTHS = [
    234300,
    312000,
    373600,
    467000,
]

VOLTAGE = 3.3
MCU_PROC_POWER = 48 * 120E-3 * VOLTAGE  # Based on ST application note regarding STM32L4 power modes
RX_POWER_LORA = 4.6 * VOLTAGE  # Boost
RX_POWER_FSK = 4.2 * VOLTAGE  # Boost
RX_POWER_BOOST_LORA = 5.3 * VOLTAGE  # Boost
RX_POWER_BOOST_FSK = 4.8 * VOLTAGE  # Boost

TX_CURRENT_LOOKUP_TABLE = [  # X: dBm, Y: mA. SX1262 datasheet, page 30, Figure 4-9, 3.3 V
    list(range(-9, 23)),
    [
        23,  # -9 dBm
        24,  # -8
        26,
        27,
        29,
        31,
        32,
        35,
        38,
        40,  # 0 dBm
        42,
        45,
        47,
        51,
        54,
        56,
        60,
        63,
        66,
        69,  # 10 dBm
        74,
        79,
        83,
        87,
        92,
        93,
        95,
        97,
        101,
        105,  # 20 dBm
        109,
        120,  # 22 dBm
    ],
]


class RadioModem(Enum):
    LORA = 1
    FSK = 2

    @property
    def c_name(self):
        if self is RadioModem.LORA:
            return 'MODEM_LORA'
        elif self is RadioModem.FSK:
            return 'MODEM_FSK'


RADIO_CONFIGURATIONS = [
    {'modem': RadioModem.LORA, 'bandwidth': 0, 'datarate': 12, 'coderate': 5, 'preamble_len': 10},
    {'modem': RadioModem.LORA, 'bandwidth': 0, 'datarate': 11, 'coderate': 5, 'preamble_len': 10},
    {'modem': RadioModem.LORA, 'bandwidth': 0, 'datarate': 10, 'coderate': 5, 'preamble_len': 10},
    {'modem': RadioModem.LORA, 'bandwidth': 0, 'datarate': 9, 'coderate': 5, 'preamble_len': 10},
    {'modem': RadioModem.LORA, 'bandwidth': 0, 'datarate': 8, 'coderate': 5, 'preamble_len': 10},
    {'modem': RadioModem.LORA, 'bandwidth': 0, 'datarate': 7, 'coderate': 5, 'preamble_len': 10},
    {'modem': RadioModem.LORA, 'bandwidth': 0, 'datarate': 6, 'coderate': 5, 'preamble_len': 12},
    {'modem': RadioModem.LORA, 'bandwidth': 0, 'datarate': 5, 'coderate': 5, 'preamble_len': 12},
    {'modem': RadioModem.FSK, 'bandwidth': 234300, 'datarate': 125000, 'preamble_len': 2, 'fdev': 50000},
    {'modem': RadioModem.FSK, 'bandwidth': 234300, 'datarate': 200000, 'preamble_len': 2, 'fdev': 10000},
]


class RadioConfiguration:
    def __init__(self, modulation=0, band=48, power=0, bandwidth=None, tx=True, crc=True, implicit=0, irq_direct=False,
                 preamble=None, bitrate=None):
        self.modulation = modulation
        self.band = band
        self.power = power
        if tx:
            self.tx = True
        else:
            self.tx = False

        self.preamble = preamble

        self.irq_direct = irq_direct

        self.custom_bandwidth = bandwidth
        self.custom_bitrate = bitrate

        self.crc = crc
        self.implicit = implicit

    def __copy__(self):
        return RadioConfiguration(modulation=self.modulation, band=self.band, power=self.power, tx=self.tx,
                                  crc=self.crc, implicit=self.implicit, irq_direct=self.irq_direct,
                                  preamble=self.preamble, bitrate=self.bitrate)

    @property
    def cmd(self):
        if self.tx:
            cmd = "radio config {} {} {}".format(self.modulation, self.band, self.power)
        else:
            cmd = "radio config {} {}".format(self.modulation, self.band)

        if self.custom_bandwidth:
            cmd += " -w {:d}".format(self.custom_bandwidth)

        if not self.crc:
            cmd += " -c false"

        if self.implicit:
            cmd += " -i {:d}".format(self.implicit)

        if self.preamble:
            cmd += " -p {:d}".format(self.preamble)

        if self.irq_direct:
            cmd += " --irq"

        return cmd

    def print(self, end=None):
        print(str(self), end=end)

    def __str__(self):
        return "{},{},{}".format(self.modulation, self.band, self.power)

    @property
    def explicit_header(self):
        if self.modem is RadioModem.LORA:
            return not self.implicit
        else:
            return not self.implicit

    @property
    def low_data_rate(self):
        if self.modem is RadioModem.LORA:
            if self.bandwidth == 0 and (self.sf == 11 or self.sf == 12):
                return True
            elif self.bandwidth == 1 and (self.sf == 11 or self.sf == 12):
                return True
            else:
                return False
        else:
            return False

    @property
    def preamble_len(self):
        if self.preamble:
            return self.preamble
        else:
            return RADIO_CONFIGURATIONS[self.modulation]['preamble_len']

    @property
    def header_len(self):
        if self.modem is RadioModem.LORA:
            return 8
        else:
            return 3

    @property
    def bitrate(self):
        if self.modem is RadioModem.LORA:
            return self.symbol_rate * (self.sf - (2 if self.low_data_rate else 0)) * (4 / (self.coderate % 4 + 4))
        else:
            if self.custom_bitrate:
                return self.custom_bitrate
            else:
                return RADIO_CONFIGURATIONS[self.modulation]['datarate']

    @property
    def bandwidth(self):

        if self.modem is RadioModem.LORA:
            if self.custom_bandwidth is None:
                return RADIO_CONFIGURATIONS[self.modulation]['bandwidth']
            else:
                return int(self.custom_bandwidth)
        elif self.modem is RadioModem.FSK:
            if self.custom_bandwidth is None:
                return RADIO_CONFIGURATIONS[self.modulation]['bandwidth']
            else:
                return self.custom_bandwidth

    @property
    def real_bandwidth(self):
        if self.modem is RadioModem.LORA:
            return float(LORA_BANDWIDTHS[self.bandwidth])
        elif self.modem is RadioModem.FSK:
            return float(self.bandwidth)

    @property
    def modem(self):
        return RADIO_CONFIGURATIONS[self.modulation]['modem']

    @property
    def sf(self):
        if self.modem is RadioModem.LORA:
            return RADIO_CONFIGURATIONS[self.modulation]['datarate']
        else:
            return None

    @property
    def modulation_name(self, short=True):
        if short:
            if self.modem is RadioModem.LORA:
                return "SF{}".format(self.sf)
            elif self.modem is RadioModem.FSK:
                return "FSK {:d}k".format(int(self.bitrate / 1000))
        else:
            if self.modem is RadioModem.LORA:
                return "LoRa SF{}@{}kHz".format(self.sf, self.real_bandwidth / 1000)
            elif self.modem is RadioModem.FSK:
                return "FSK {:d}kBit/s@{}kHz".format(int(self.bitrate / 1000), self.real_bandwidth / 1000)

    @staticmethod
    def get_modulation_name(modulation, short=True):
        return RadioConfiguration(modulation, 0, 0, short).modulation_name

    @property
    def coderate(self):
        if self.modem is RadioModem.LORA:
            return RADIO_CONFIGURATIONS[self.modulation]['coderate']
        else:
            return None

    @property
    def sync_word_length(self):
        if self.modem is RadioModem.LORA:
            return None
        elif self.modem is RadioModem.FSK:
            return 3

    @property
    def coderate_name(self):
        if self.modem is RadioModem.LORA:
            return "4/{}".format(RADIO_CONFIGURATIONS[self.modulation]['coderate'])
        else:
            return "N/A"

    @staticmethod
    def get_random_configuration(tx=True, limit=None, bandwidth=False, power=np.arange(-17, 23), crc=True, implicit=0,
                                 modulation_range=np.arange(0, 10), irq_direct=False, preamble=None):
        global FSK_BANDWIDTHS

        band_count = 52

        if limit == "LoRa":
            modulation_range = np.arange(0, 8)
        elif limit == "FSK":
            modulation_range = np.arange(8, 10)

        modulation = np.random.choice(modulation_range)

        if tx == "randomize":
            tx = np.random.choice([True, False])

        if crc == "randomize":
            crc = np.random.choice([True, False])

        band = np.random.randint(0, band_count)
        power = np.random.choice(power)

        if preamble is True:
            if RadioConfiguration(modulation).modem is RadioModem.LORA:
                preamble = np.random.randint(3, 13)
            else:
                preamble = np.random.randint(2, 13)

        if bandwidth is True:
            if RadioConfiguration(modulation).modem is RadioModem.LORA:
                bandwidth = np.random.choice(np.arange(0, 3))
            elif RadioConfiguration(modulation).modem is RadioModem.FSK:
                bandwidth = np.random.choice(FSK_BANDWIDTHS)

        return RadioConfiguration(modulation, band, power, bandwidth=bandwidth, tx=tx, crc=crc, implicit=implicit,
                                  irq_direct=irq_direct, preamble=preamble)

    @property
    def color(self):
        if self.modem is RadioModem.LORA:
            cmap = matplotlib.cm.get_cmap('plasma')
            return cmap(self.modulation / 12)
        else:
            cmap = matplotlib.cm.get_cmap('summer')
            return cmap((self.modulation - 8) / 2)

    @staticmethod
    def get_color(modulation):
        return RadioConfiguration(modulation).color

    @property
    def frequency(self):
        global BAND_FREQUENCIES

        return BAND_FREQUENCIES[self.band]

    @property
    def chirp_rate(self):
        if self.modem is RadioModem.LORA:
            return np.square(self.real_bandwidth) / np.exp2(self.sf)
        else:
            return np.nan

    @property
    def symbol_rate(self):
        if self.modem is RadioModem.LORA:
            return self.real_bandwidth / np.exp2(self.sf)
        else:
            return self.bitrate / 8.0

    @property
    def chips_per_symbol(self):
        if self.modem is RadioModem.LORA:
            return np.exp2(self.sf)
        else:
            return np.nan

    @property
    def freq_deviation(self):
        if self.modem is RadioModem.LORA:
            return np.nan
        else:
            return RADIO_CONFIGURATIONS[self.modulation]['fdev']

    @property
    def modulation_index(self):
        return 2 * self.freq_deviation / self.bitrate

    @staticmethod
    def rx_energy(duration):
        return RX_POWER_BOOST_LORA * duration

    @staticmethod
    def tx_energy(power, duration):
        current = np.interp(power, TX_CURRENT_LOOKUP_TABLE[0], TX_CURRENT_LOOKUP_TABLE[1])
        return VOLTAGE + current * duration
