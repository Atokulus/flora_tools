import numpy as np
import random
import string


def get_random_text(length = None, max_length = 254):
    if length is None:
        length = np.random.randint(-1, max_length+1)
    if length < 0:
        return None
    else:
        text = ''.join(random.choices(string.ascii_letters + string.ascii_uppercase + string.digits, k=(length-1)))
        return text


def get_edges(wave):
    wave_min = np.amin(wave)
    wave_max = np.amax(wave)
    digital = np.digitize(wave, [(wave_min + wave_max) / 2.0])
    diff = np.diff(digital)
    indices = np.argwhere(diff)
    return indices
