import numpy as np

def smooth_values(values, window_size):
    """Applies a simple moving average to a list of values."""
    if len(values) < window_size:
        return np.mean(values) if values else 0
    return np.mean(values[-window_size:])