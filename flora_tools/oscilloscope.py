import time

import visa
import numpy as np
from struct import unpack

OSCILLOSCOPE_RECORDLENGTH_LOOKUP = [20E6, 10E6, 5E6, 1E6, 100E3, 10E3, 1E3]

OSCILLOSCOPE_SCALE_LOOKUP = [
    [1000,400,200,100,40,20,10,4,2,1,400E-3,200E-3,100E-3,40E-3,20E-3,8E-3,4E-3,2E-3,800E-6,400E-6,200E-6,100E-6,40E-6,20E-6,10E-6,4E-6,2E-6,1E-6,400E-9,200E-9,100E-9,40E-9,20E-9,10E-9,4E-9,2E-9,1E-9,400E-12],  # 20M
    [1000,400,200,100,40,20,10,4,2,1,400E-3,200E-3,100E-3,40E-3,20E-3,10E-3,4E-3,2E-3,1E-3,400E-6,200E-6,100E-6,40E-6,20E-6,10E-6,4E-6,2E-6,1E-6,400E-9,200E-9,100E-9,40E-9,20E-9,10E-9,4E-9,2E-9,1E-9,400E-12],  # 10M
    [1000,400,200,100,40,20,10,4,2,1,400E-3,200E-3,100E-3,40E-3,20E-3,10E-3,4E-3,2E-3,1E-3,400E-6,200E-6,100E-6,40E-6,20E-6,10E-6,4E-6,2E-6,1E-6,400E-9,200E-9,100E-9,40E-9,20E-9,10E-9,4E-9,2E-9,1E-9,400E-12],  # 5M
    [1000,400,200,100,40,20,10,4,2,1,400E-3,200E-3,100E-3,40E-3,20E-3,10E-3,4E-3,2E-3,1E-3,400E-6,200E-6,100E-6,40E-6,20E-6,10E-6,4E-6,2E-6,1E-6,400E-9,200E-9,100E-9,40E-9,20E-9,10E-9,4E-9,2E-9,1E-9,400E-12],  # 1M
    [1000,400,200,100,40,20,10,4,2,1,400E-3,200E-3,100E-3,40E-3,20E-3,10E-3,4E-3,2E-3,1E-3,400E-6,200E-6,100E-6,40E-6,20E-6,10E-6,4E-6,2E-6,1E-6,400E-9,200E-9,100E-9,40E-9,20E-9,10E-9,4E-9,2E-9,1E-9,400E-12],  # 100k
    [400,200,100,40,20,10,4,2,1,400E-3,200E-3,100E-3,40E-3,20E-3,10E-3,4E-3,2E-3,1E-3,400E-6,200E-6,100E-6,40E-6,20E-6,10E-6,4E-6,2E-6,1E-6,400E-9,200E-9,100E-9,40E-9,20E-9,10E-9,4E-9,2E-9,1E-9,400E-12],  # 10k
    [40,20,10,4,2,1,400E-3,200E-3,100E-3,40E-3,20E-3,10E-3,4E-3,2E-3,1E-3,400E-6,200E-6,100E-6,40E-6,20E-6,10E-6,4E-6,2E-6,1E-6,400E-9,200E-9,100E-9,40E-9,20E-9,10E-9,4E-9,2E-9,1E-9,400E-12],  # 1000
]

OSCILLOSCOPE_ADDRESS = "TCPIP0::ee-tik-dhcp-103-228.ethz.ch::inst0::INSTR"

SETUP = [
    #"*IDN?",

    "ACQUIRE:MODE SAMPLE",
    "HORIZONTAL:RECORDLENGTH 1000",
    "DATA:ENCDG SRIBINARY",
    "WFMOutpre:BYT_Nr 2",
    "TRIGger:A:MODe NORMAL",

    "CH1:LABEL 'NSS'",
    "CH1:IMPEDANCE MEG",
    "CH1:COUPLING DC",
    "CH1:SCALE 2.0",
    "CH1:POSITION 3.0",
    "SELECT:CH1 ON",
    "TRIGGER:A:LEVEL:CH1 1.65",

    "CH2:LABEL 'DIO1'",
    "CH2:IMPEDANCE MEG",
    "CH2:COUPLING DC",
    "CH2:SCALE 2.0",
    "CH2:POSITION 1.0",
    "SELECT:CH2 ON",
    "TRIGGER:A:LEVEL:CH2 1.65",

    "CH3:LABEL 'BUSY'",
    "CH3:IMPEDANCE MEG",
    "CH3:COUPLING DC",
    "CH3:SCALE 2.0",
    "CH3:POSITION -1.0",
    "SELECT:CH3 ON",
    "TRIGGER:A:LEVEL:CH3 1.65",

    "CH4:LABEL 'RF'",
    "CH4:DESKEW 2.0E-9", # 4.7 (Teflon-) - 5 ns/m (PE-Coax). I.e. 0.4 m -> 2 ns
    "CH4:IMPEDANCE FIFTY",
    "CH4:SCALE 0.005",
    "CH4:POSITION -3.0",
    "CH4:COUPLING DC",
    "SELECT:CH4 ON",
    "TRIGGER:A:LEVEL:CH4 0.0",
]


class Oscilloscope:
    def __init__(self):
        self.rm = visa.ResourceManager()
        if OSCILLOSCOPE_ADDRESS in self.rm.list_resources():
            self.inst = self.rm.open_resource(OSCILLOSCOPE_ADDRESS)
            #self.inst.timeout = 10000
            self.wait_busy()
            self.inst.write("*CLS")
            for cmd in SETUP:
                self.inst.write(cmd)
        else:
            raise ValueError("Oscilloscope {} not found. Check your configuration!".format(OSCILLOSCOPE_ADDRESS))

    def query(self, cmd):
        return self.inst.query(cmd)

    def wait_busy(self, timeout=30.0):
        try:
            if timeout:
                start = time.time()
                while ":BUSY 1" in self.inst.query("BUSY?"):
                    if (time.time() > start + timeout):
                        return False # Trigger did not work after 5 seconds
                    time.sleep(0.1)

                return True
            else:
                while ":BUSY 1" in self.inst.query("BUSY?"):
                    time.sleep(0.1)

                return True
        except (UnicodeDecodeError, visa.VisaIOError):
            time.sleep(0.2)
            if not timeout:
                self.wait_busy(timeout=0)
            else:
                return False

    def init_measurement(self, window, points=1000, trigger_channel="NSS", trigger_rise=True, start=0, text="", trigger_position=None):
        self.wait_busy(timeout=None)

        if text:
            self.inst.write("MESSage:SHOW '{}'".format(text))
            self.inst.write("SETUP:LABEL '{}'".format(text))

        self.start = start
        self.points = points
        self.window = window
        self.inst.write("TRIGGER:A:EDGE:SOURCE CH{}".format(self.get_channel_number(trigger_channel)))

        if trigger_rise:
            self.inst.write("TRIGGER:A:EDGE:SLOPE RISE")
        else:
            self.inst.write("TRIGGER:A:EDGE:SLOPE FALL")

        self.inst.write("HORIZONTAL:SCALE {:8E}".format(window / 10.0))
        self.inst.write("HORIZONTAL:DELAY:TIME {:8E}".format(trigger_position if trigger_position is not None else (0.4 * window)))
        self.inst.write("HORIZONTAL:RECORDLENGTH {}".format(points))
        self.inst.write("ACQUIRE:STOPAFTER SEQUENCE")
        self.inst.write("ACQUIRE:STATE RUN")


    def finish_measurement(self, channels=range(1,5)):
        if not self.wait_busy():
            return None

        self.inst.write("DATA:START {}".format(self.start + 1))
        self.inst.write("DATA:STOP {}".format(self.points))
        self.inst.write("CURVE BLOCK")

        data = np.empty((0, self.points - self.start), dtype=np.int16)

        for i in channels:
            self.inst.write("DATA:SOURCE CH{}".format(i))
            self.inst.write("CURVE?")
            reply = self.inst.read_raw()
            num_length = int(reply[7:8])
            length = int(reply[8:(8+num_length)])

            if int(length / 2) > self.points:
                self.points = length
                data = np.empty((0, self.points), dtype=np.int16)

            binary = reply[8+num_length:8+num_length+length]
            wave = np.fromstring(binary, dtype=np.int16)
            wave = np.int32(wave)

            data = np.append(data, [wave], axis=0)

        return data

    def measure(self, window, points=1000, channel="NSS", trigger_rise=True):
        self.init_measurement(window, points, channel, trigger_rise)
        return self.finish_measurement()

    def set_scale(self, channel, scale):
        self.inst.write("CH{}:SCALE {:.5E}".format(self.get_channel_number(channel), scale))

    def get_next_valid_window(self, window, precision):
        global OSCILLOSCOPE_RECORDLENGTH_LOOKUP, OSCILLOSCOPE_SCALE_LOOKUP

        fallback_scale = None

        for idx, record_len in enumerate(reversed(OSCILLOSCOPE_RECORDLENGTH_LOOKUP)):
            for scale in reversed(OSCILLOSCOPE_SCALE_LOOKUP[len(OSCILLOSCOPE_SCALE_LOOKUP) - idx - 1]):
                if scale * 10.0 >= window:
                    if not fallback_scale:
                        fallback_scale = scale

                    if (scale * 10.0 / (record_len-1)) <= precision:
                        return (scale * 10.0, int(record_len), scale * 10.0 / (record_len - 1))

                    break

        if fallback_scale:
            return (fallback_scale * 10.0, int(20E6), fallback_scale * 10.0 / (20E6 - 1))
        return None

    def get_channel_number(self, channel):
        if channel == "NSS":
            channel = 1
        elif channel == "DIO1":
            channel = 2
        elif channel == "BUSY":
            channel = 3
        elif channel == "COAX":
            channel = 4

        return channel

    def delay_acquisition_setup_time(self, window=0.0):
        time.sleep(np.max([0.6, window * 1.5]))

    @property
    def sample_period(self):
        return self.window / (self.points - 1)




