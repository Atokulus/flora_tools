import time
import datetime as dt
import pandas as pd
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from flora_tools.radio_configuration import RadioConfiguration
from flora_tools.radio_math import RadioMath
from flora_tools.oscilloscope import Oscilloscope
import flora_tools.utilities
from flora_tools.radio_configuration import RadioConfiguration
from flora_tools.radio_math import RadioMath
from copy import copy


class Experiment:
    def __init__(self, description):
        self.name = self.__class__.__name__
        self.description = description

    def run(self, bench):
        self.bench = bench
        print("\n\n[{}]: {}".format(self.name, self.description))

