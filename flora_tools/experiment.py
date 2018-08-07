import flora_tools.utilities as utilities
from flora_tools.radio_configuration import RadioConfiguration
from flora_tools.radio_math import RadioMath

import datetime as dt
import time
from copy import copy

import numpy as np
import pandas as pd

import matplotlib.pyplot as plt
import matplotlib
import matplotlib.cm

from mpl_toolkits.mplot3d import Axes3D


class Experiment:
    def __init__(self, description):
        self.name = self.__class__.__name__
        self.description = description
        self.bench = None

    def run(self, bench):
        self.bench = bench
        print("\n\n[{}]: {}".format(self.name, self.description))
