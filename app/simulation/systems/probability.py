from __future__ import annotations

import numpy as np


def normalized_probabilities(values: np.ndarray | list[float]) -> np.ndarray:
    weights = np.asarray(values, dtype=np.float64)
    weights = np.where(np.isfinite(weights) & (weights > 0), weights, 0.0)
    total = float(weights.sum())
    if weights.size == 0:
        return weights
    if not np.isfinite(total) or total <= 0:
        return np.full(weights.size, 1.0 / weights.size, dtype=np.float64)
    return weights / total
