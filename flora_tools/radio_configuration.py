import matplotlib
import matplotlib.cm
import numpy as np

BAND_FREQUENCIES = [
    863E6 + 1 * 125E3 / 2,
    863E6 + 3 * 125E3 / 2,
    863E6 + 5 * 125E3 / 2,
    863E6 + 7 * 125E3 / 2,
    863E6 + 9 * 125E3 / 2,
    863E6 + 11 * 125E3 / 2,
    863E6 + 13 * 125E3 / 2,
    863E6 + 15 * 125E3 / 2,
    863E6 + 17 * 125E3 / 2,
    863E6 + 19 * 125E3 / 2,
    863E6 + 21 * 125E3 / 2,
    863E6 + 23 * 125E3 / 2,
    863E6 + 25 * 125E3 / 2,
    863E6 + 27 * 125E3 / 2,
    863E6 + 29 * 125E3 / 2,
    863E6 + 31 * 125E3 / 2,
    865E6 + 1 * 125E3 / 2,
    865E6 + 3 * 125E3 / 2,
    865E6 + 5 * 125E3 / 2,
    865E6 + 7 * 125E3 / 2,
    865E6 + 9 * 125E3 / 2,
    865E6 + 11 * 125E3 / 2,
    865E6 + 13 * 125E3 / 2,
    865E6 + 15 * 125E3 / 2,
    865E6 + 17 * 125E3 / 2,
    865E6 + 19 * 125E3 / 2,
    865E6 + 21 * 125E3 / 2,
    865E6 + 23 * 125E3 / 2,
    865E6 + 25 * 125E3 / 2,
    865E6 + 27 * 125E3 / 2,
    865E6 + 29 * 125E3 / 2,
    865E6 + 31 * 125E3 / 2,
    865E6 + 33 * 125E3 / 2,
    865E6 + 35 * 125E3 / 2,
    865E6 + 37 * 125E3 / 2,
    865E6 + 39 * 125E3 / 2,
    865E6 + 41 * 125E3 / 2,
    865E6 + 43 * 125E3 / 2,
    865E6 + 45 * 125E3 / 2,
    865E6 + 47 * 125E3 / 2,
    868E6 + 1 * 125E3 / 2,
    868E6 + 3 * 125E3 / 2,
    868E6 + 5 * 125E3 / 2,
    868E6 + 7 * 125E3 / 2,
    868.7E6 + 1 * 125E3 / 2,
    868.7E6 + 3 * 125E3 / 2,
    868.7E6 + 5 * 125E3 / 2,
    868.7E6 + 7 * 125E3 / 2,
    869.4E6 + 1 * 125E3 / 2,
    869.4E6 + 3 * 125E3 / 2,
    869.7E6 + 1 * 125E3 / 2,
    869.7E6 + 3 * 125E3 / 2,
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
PROC_POWER = 48 * 120E-3 * VOLTAGE  # Based on ST application note regarding STM32L4 power modes
RX_POWER = 5.5 * VOLTAGE


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
        if self.modem == 'LoRa':
            return not self.implicit
        else:
            return not self.implicit

    @property
    def low_data_rate(self):
        if self.modem == 'LoRa':
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
            if self.modem == 'LoRa':
                if self.sf == 6 or self.sf == 5:
                    return 12
                else:
                    return 10
            else:
                return 8

    @property
    def header_len(self):
        if self.modem == 'LoRa':
            return 8
        else:
            return 3

    @property
    def bitrate(self):
        if self.modem == 'LoRa':
            return self.symbol_rate * (self.sf - (2 if self.low_data_rate else 0)) * (4 / (self.coderate % 4 + 4))
        else:
            if self.custom_bitrate:
                return self.custom_bitrate
            else:
                if self.modulation == 8:
                    return 125000
                if self.modulation == 9:
                    return 200000

    @property
    def bandwidth(self):

        if self.modem == 'LoRa':
            if self.custom_bandwidth is None:
                return 0
            else:
                return int(self.custom_bandwidth)
        elif self.modem == 'FSK':
            if self.custom_bandwidth is None:
                if self.modulation == 8:
                    return 250000
                if self.modulation == 9:
                    return 250000
            else:
                return self.custom_bandwidth

    @property
    def real_bandwidth(self):
        global LORA_BANDWIDTHS

        if self.modem == 'LoRa':
            return float(LORA_BANDWIDTHS[self.bandwidth])
        elif self.modem == 'FSK':
            return float(self.bandwidth)

    @property
    def modem(self):
        if 0 <= self.modulation < 8:
            return 'LoRa'
        elif 8 <= self.modulation < 10:
            return 'FSK'

    @property
    def sf(self):
        if self.modem == "LoRa":
            return 12 - self.modulation
        else:
            return 0

    @property
    def modulation_name(self, short=True):
        if short:
            if self.modem == "LoRa":
                return "SF{}".format(12 - self.modulation)
            elif self.modem == "FSK":
                if self.modulation == 8:
                    return "FSK\n{}".format("125k")
                if self.modulation == 9:
                    return "FSK\n{}".format("200k")
        else:
            if self.modem == "LoRa":
                return "LoRa SF{}@{}".format(12 - self.modulation, "125kHz")
            elif self.modem == "FSK":
                if self.modulation == 8:
                    return "GFSK {}@{} (h={})".format("125kBit/s", "250kHz", "2.0")
                if self.modulation == 9:
                    return "GFSK {}@{} (h={})".format("200kBit/s", "250kHz", "1.0")

    @staticmethod
    def get_modulation_name(modulation, short=True):
        return RadioConfiguration(modulation, 0, 0, short).modulation_name

    @property
    def coderate(self):
        if self.modem == "LoRa":
            return 5
        elif self.modem == "FSK":
            return 0

    @property
    def sync_word_length(self):
        if self.modem == "LoRa":
            return 0
        elif self.modem == "FSK":
            return 3

    @property
    def coderate_name(self):
        if self.modem == "LoRa":
            return "4/5"
        elif self.modem == "FSK":
            return "N/A"

    @staticmethod
    def get_random_configuration(tx=True, limit=None, bandwidth=False, power=np.arange(-17, 23), crc=True, implicit=0,
                                 modulation_range=np.arange(0, 10), irq_direct=False, preamble=False):
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
            if RadioConfiguration(modulation).modem == 'LoRa':
                preamble = np.random.randint(3, 13)
            else:
                preamble = np.random.randint(2, 13)

        if bandwidth is True:
            if RadioConfiguration(modulation).modem == 'LoRa':
                bandwidth = np.random.choice(np.arange(0, 3))
            elif RadioConfiguration(modulation).modem == 'FSK':
                bandwidth = np.random.choice(FSK_BANDWIDTHS)

        return RadioConfiguration(modulation, band, power, bandwidth=bandwidth, tx=tx, crc=crc, implicit=implicit,
                                  irq_direct=irq_direct, preamble=preamble)

    @property
    def color(self):
        if self.modem == "LoRa":
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
        if self.modem == 'LoRa':
            return np.square(self.real_bandwidth) / np.exp2(self.sf)
        else:
            return np.nan

    @property
    def symbol_rate(self):
        if self.modem == 'LoRa':
            return self.real_bandwidth / np.exp2(self.sf)
        else:
            return self.bitrate / 8.0

    @property
    def chips_per_symbol(self):
        if self.modem == 'LoRa':
            return np.exp2(self.sf)
        else:
            return np.nan

    @property
    def freq_deviation(self):
        if self.modem == 'LoRa':
            return np.nan
        else:
            if self.modulation == 8:
                return 50000.0
            else:
                return 10000.0

    @property
    def modulation_index(self):
        return 2 * self.freq_deviation / self.bitrate

    @staticmethod
    def rx_energy(duration):
        return RX_POWER * duration

    @staticmethod
    def tx_energy(power, duration):
        return (8 * VOLTAGE + np.power(10, power / 10) * 3) * duration  # 8 mA floor, 33% efficiency
