"""Synthetic fields for the scaling study: more wells and candidate sites than the case study.

Wells are drawn uniformly in a square; candidate manifold sites are the centres of
k-means clusters of the wells (the centroid idea of Silva & Guedes Soares 2025, applied to
groups of wells); the host lies ``host_distance`` north of the centre of the square.
Geometry only: costs, failure rates and weather come from the config in use.
"""
from __future__ import annotations

import numpy as np

from .layout import Field, build_field


def _kmeans(points: np.ndarray, k: int, rng: np.random.Generator, iterations: int = 100) -> np.ndarray:
    """Centres of k clusters (Lloyd's algorithm, k-means++ start)."""
    centres = [points[rng.integers(len(points))]]
    for _ in range(k - 1):
        d2 = np.min([((points - c) ** 2).sum(axis=1) for c in centres], axis=0)
        centres.append(points[rng.choice(len(points), p=d2 / d2.sum())])
    centres = np.array(centres, float)
    for _ in range(iterations):
        label = np.argmin(((points[:, None, :] - centres[None, :, :]) ** 2).sum(axis=2), axis=1)
        new = np.array([points[label == j].mean(axis=0) if (label == j).any() else centres[j] for j in range(k)])
        if np.allclose(new, centres):
            break
        centres = new
    return centres


def synthetic_field_data(n_wells: int, n_sites: int, side: float, host_distance: float, seed: int) -> dict:
    """Field dict (same structure as the field YAML) with ``n_wells`` wells and ``n_sites`` sites."""
    rng = np.random.default_rng(seed)
    wells = rng.uniform(0.0, side, size=(n_wells, 2))
    sites = _kmeans(wells, n_sites, rng)
    return {"name": f"synthetic field, {n_wells} wells, {n_sites} candidate sites (seed {seed})",
            "host": {"name": "HOST", "x": side / 2, "y": side / 2 + host_distance},
            "wells": [{"name": f"W{i + 1:02d}", "x": float(x), "y": float(y)} for i, (x, y) in enumerate(wells)],
            "manifold_sites": [{"name": f"M{j + 1:02d}", "x": float(x), "y": float(y)} for j, (x, y) in enumerate(sites)]}


def synthetic_field(n_wells: int, n_sites: int, side: float, host_distance: float, seed: int,
                    length_factor: float = 1.0) -> Field:
    return build_field(synthetic_field_data(n_wells, n_sites, side, host_distance, seed), length_factor)
