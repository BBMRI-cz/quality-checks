#!/usr/bin/env python3

import numpy as np

def add_laplace_noise(count, epsilon, sensitivity=1):
    """Add Laplace noise to a count for differential privacy."""
    scale = sensitivity / epsilon
    noise = np.random.laplace(0, scale)
    noisy_count = max(0, round(count + noise))  # Ensure non-negative and round
    return noisy_count