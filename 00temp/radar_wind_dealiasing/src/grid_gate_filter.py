#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""Gate filtering utilities for meteva_base grid data."""

from __future__ import annotations

import numpy as np
import xarray as xr

from ..utils.utils import check_for_meb_griddata


class GridGateFilter:
    """Build a boolean gate mask for meteva_base grid data.

    The class follows the useful parts of Py-ART ``GateFilter``: it keeps an
    internal excluded-gate mask and updates it through include/exclude rules.
    Radar-only concepts such as antenna transition gates are intentionally not
    implemented here.
    """

    def __init__(
        self,
        velocity: xr.DataArray,
        exclude_based: bool = True,
        gate_excluded: np.ndarray | None = None,
    ):
        self.velocity = check_for_meb_griddata(velocity, is_single=False)
        velocity_shape = self.velocity.shape
        plane_shape = velocity_shape[-2:]

        if gate_excluded is not None:
            gate_excluded = np.asarray(gate_excluded, dtype=bool)
            if gate_excluded.shape not in (plane_shape, velocity_shape):
                raise ValueError(
                    "gate_excluded shape must match the 2D plane or full grid shape"
                )
            self._gate_excluded = gate_excluded.copy()
        else:
            shape = plane_shape if _is_single_context(self.velocity) else velocity_shape
            if exclude_based:
                self._gate_excluded = np.zeros(shape, dtype=bool)
            else:
                self._gate_excluded = np.ones(shape, dtype=bool)

    @classmethod
    def from_mask(cls, velocity: xr.DataArray, mask) -> "GridGateFilter":
        """Create a filter from a boolean mask."""
        return cls(velocity, gate_excluded=np.asarray(mask, dtype=bool))

    def copy(self) -> "GridGateFilter":
        """Return a copy of the gate filter."""
        return GridGateFilter(self.velocity, gate_excluded=self._gate_excluded)

    @property
    def gate_included(self) -> np.ndarray:
        """Boolean array marking gates included in calculations."""
        return ~self._gate_excluded.copy()

    @property
    def gate_excluded(self) -> np.ndarray:
        """Boolean array marking gates excluded from calculations."""
        return self._gate_excluded.copy()

    @gate_excluded.setter
    def gate_excluded(self, value) -> None:
        value = np.asarray(value, dtype=bool)
        if value.shape != self._gate_excluded.shape:
            raise ValueError("gate_excluded shape must match the filter shape")
        self._gate_excluded = value.copy()

    def _merge(self, marked, op: str = "or", exclude_masked: bool = True):
        """Merge marked gates with the current excluded-gate mask."""
        if exclude_masked not in (True, False):
            raise ValueError("exclude_masked must be True or False")

        marked = np.ma.filled(marked, exclude_masked)
        marked = np.asarray(marked, dtype=bool)
        if marked.shape != self._gate_excluded.shape:
            raise ValueError("marked gate mask must match the filter shape")

        if op == "or":
            self._gate_excluded = np.logical_or(self._gate_excluded, marked)
        elif op == "and":
            self._gate_excluded = np.logical_and(self._gate_excluded, marked)
        elif op == "new":
            self._gate_excluded = marked
        else:
            raise ValueError("op must be one of 'or', 'and', or 'new'")

    def _get_fdata(self, grid_data) -> np.ndarray:
        """Return field data matching the filter shape."""
        normalized = check_for_meb_griddata(grid_data, is_single=False)
        if self._gate_excluded.ndim == 2:
            return _as_2d_array(normalized)
        if normalized.shape != self._gate_excluded.shape:
            raise ValueError("grid_data shape must match the full GridGateFilter shape")
        return normalized.values

    def exclude_below(
        self, grid_data, value, exclude_masked: bool = True, op: str = "or", inclusive: bool = False
    ):
        """Exclude gates where grid_data is below value."""
        data = self._get_fdata(grid_data)
        marked = data <= value if inclusive else data < value
        self._merge(marked, op, exclude_masked)

    def exclude_above(
        self, grid_data, value, exclude_masked: bool = True, op: str = "or", inclusive: bool = False
    ):
        """Exclude gates where grid_data is above value."""
        data = self._get_fdata(grid_data)
        marked = data >= value if inclusive else data > value
        self._merge(marked, op, exclude_masked)

    def exclude_inside(
        self,
        grid_data,
        v1,
        v2,
        exclude_masked: bool = True,
        op: str = "or",
        inclusive: bool = True,
    ):
        """Exclude gates where grid_data is inside an interval."""
        if v2 < v1:
            v1, v2 = v2, v1
        data = self._get_fdata(grid_data)
        marked = (data >= v1) & (data <= v2) if inclusive else (data > v1) & (data < v2)
        self._merge(marked, op, exclude_masked)

    def exclude_outside(
        self,
        grid_data,
        v1=None,
        v2=None,
        exclude_masked: bool = True,
        op: str = "or",
        inclusive: bool = False,
    ):
        """Exclude gates where grid_data is outside an interval."""
        if v1 is None and v2 is None:
            return
        if v1 is None:
            return self.exclude_above(grid_data, v2, exclude_masked, op, inclusive)
        if v2 is None:
            return self.exclude_below(grid_data, v1, exclude_masked, op, inclusive)
        if v2 < v1:
            v1, v2 = v2, v1
        data = self._get_fdata(grid_data)
        marked = (data <= v1) | (data >= v2) if inclusive else (data < v1) | (data > v2)
        self._merge(marked, op, exclude_masked)

    def exclude_equal(self, grid_data, value, exclude_masked: bool = True, op: str = "or"):
        """Exclude gates where grid_data equals value."""
        self._merge(self._get_fdata(grid_data) == value, op, exclude_masked)

    def exclude_not_equal(self, grid_data, value, exclude_masked: bool = True, op: str = "or"):
        """Exclude gates where grid_data does not equal value."""
        self._merge(self._get_fdata(grid_data) != value, op, exclude_masked)

    def exclude_all(self):
        """Exclude all gates."""
        self._gate_excluded = np.ones_like(self._gate_excluded)

    def exclude_none(self):
        """Exclude no gates."""
        self._gate_excluded = np.zeros_like(self._gate_excluded)

    def exclude_masked(self, grid_data, exclude_masked: bool = True, op: str = "or"):
        """Exclude gates where grid_data is masked."""
        self._merge(np.ma.getmaskarray(self._get_fdata(grid_data)), op, exclude_masked)

    def exclude_invalid(self, grid_data, exclude_masked: bool = True, op: str = "or"):
        """Exclude gates where grid_data is NaN or infinite."""
        self._merge(~np.isfinite(self._get_fdata(grid_data)), op, exclude_masked)

    def exclude_gates(self, mask, exclude_masked: bool = True, op: str = "or"):
        """Exclude gates where mask is True."""
        self._merge(np.asarray(mask, dtype=bool), op, exclude_masked)

    def include_below(
        self, grid_data, value, exclude_masked: bool = True, op: str = "and", inclusive: bool = False
    ):
        """Include gates where grid_data is below value."""
        data = self._get_fdata(grid_data)
        marked = data <= value if inclusive else data < value
        self._merge(~marked, op, exclude_masked)

    def include_above(
        self, grid_data, value, exclude_masked: bool = True, op: str = "and", inclusive: bool = False
    ):
        """Include gates where grid_data is above value."""
        data = self._get_fdata(grid_data)
        marked = data >= value if inclusive else data > value
        self._merge(~marked, op, exclude_masked)

    def include_inside(
        self,
        grid_data,
        v1,
        v2,
        exclude_masked: bool = True,
        op: str = "and",
        inclusive: bool = True,
    ):
        """Include gates where grid_data is inside an interval."""
        if v2 < v1:
            v1, v2 = v2, v1
        data = self._get_fdata(grid_data)
        marked = (data >= v1) & (data <= v2) if inclusive else (data > v1) & (data < v2)
        self._merge(~marked, op, exclude_masked)

    def include_outside(
        self,
        grid_data,
        v1=None,
        v2=None,
        exclude_masked: bool = True,
        op: str = "and",
        inclusive: bool = False,
    ):
        """Include gates where grid_data is outside an interval."""
        if v1 is None and v2 is None:
            return
        if v1 is None:
            return self.include_below(grid_data, v2, exclude_masked, op, inclusive)
        if v2 is None:
            return self.include_above(grid_data, v1, exclude_masked, op, inclusive)
        if v2 < v1:
            v1, v2 = v2, v1
        data = self._get_fdata(grid_data)
        marked = (data <= v1) | (data >= v2) if inclusive else (data < v1) | (data > v2)
        self._merge(~marked, op, exclude_masked)

    def include_equal(self, grid_data, value, exclude_masked: bool = True, op: str = "and"):
        """Include gates where grid_data equals value."""
        self._merge(~(self._get_fdata(grid_data) == value), op, exclude_masked)

    def include_not_equal(self, grid_data, value, exclude_masked: bool = True, op: str = "and"):
        """Include gates where grid_data does not equal value."""
        self._merge(~(self._get_fdata(grid_data) != value), op, exclude_masked)

    def include_all(self):
        """Include all gates."""
        self._gate_excluded = np.zeros_like(self._gate_excluded)

    def include_none(self):
        """Include no gates."""
        self._gate_excluded = np.ones_like(self._gate_excluded)

    def include_not_masked(self, grid_data, exclude_masked: bool = True, op: str = "and"):
        """Include gates where grid_data is not masked."""
        self._merge(np.ma.getmaskarray(self._get_fdata(grid_data)), op, exclude_masked)

    def include_valid(self, grid_data, exclude_masked: bool = True, op: str = "and"):
        """Include gates where grid_data is finite."""
        self._merge(~np.isfinite(self._get_fdata(grid_data)), op, exclude_masked)

    def include_gates(self, mask, exclude_masked: bool = True, op: str = "and"):
        """Include gates where mask is True."""
        self._merge(~np.asarray(mask, dtype=bool), op, exclude_masked)


def _as_2d_array(grid_data: xr.DataArray) -> np.ndarray:
    """Extract the 2D data plane from one meteva_base grid slice."""
    normalized = check_for_meb_griddata(grid_data, is_single=True)
    return normalized.values[0, 0, 0, 0, :, :]


def _is_single_context(grid_data: xr.DataArray) -> bool:
    """Return whether the first four dimensions identify one processing plane."""
    return all(size == 1 for size in grid_data.shape[:4])
