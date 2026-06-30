from __future__ import annotations

import numpy as np

from data import GridData, ScatterData


class FrequencyMatch:
    @staticmethod
    def _randomized_sorted(data: np.ndarray) -> np.ndarray:
        return np.sort(data.astype(float) + np.random.random(data.shape) / 1000.0)

    @staticmethod
    def _flatten_values(data):
        if len(data) == 0:
            return np.array([], dtype=float)
        if isinstance(data[0], GridData):
            return np.concatenate([item.val.flatten() for item in data])
        return np.array([p.val for item in data for p in item.sta_data], dtype=float)

    @staticmethod
    def get_used_model_level(model_data, fact_data, fact_level, fact_level_limit: int | None = None):
        model = FrequencyMatch._flatten_values(model_data)
        fact = FrequencyMatch._flatten_values(fact_data)
        if len(model) == 0 or len(fact) == 0:
            return np.array([], dtype=float), np.array([], dtype=float)
        array1 = FrequencyMatch._randomized_sorted(fact)
        array2 = FrequencyMatch._randomized_sorted(model)
        used_model = []
        used_fact = []
        has_limit = fact_level_limit is not None and fact_level_limit < 0.5 * (len(array1) - 1)
        lower_bound = fact_level_limit if has_limit else 0
        upper_bound = len(array1) - 1 - fact_level_limit if has_limit else len(array1) - 1
        for level in fact_level:
            if has_limit:
                if level >= array1[len(array1) - 1 - fact_level_limit] or level < array1[fact_level_limit]:
                    continue
                search_range = range(lower_bound, upper_bound)
            else:
                if level >= array1[-1] or level < array1[0]:
                    continue
                search_range = range(len(array1) - 1)
            for idx in search_range:
                in_range = array1[idx] < level <= array1[idx + 1] if has_limit else array1[idx] <= level < array1[idx + 1]
                if in_range:
                    idx2 = int((idx + 1) / len(array1) * len(array2)) - 1
                    if 0 <= idx2 < len(array2) - 1:
                        mapped = array2[idx2] + (array2[idx2 + 1] - array2[idx2]) * (level - array1[idx]) / (array1[idx + 1] - array1[idx])
                        used_model.append(mapped)
                        used_fact.append(level)
                    break
        return np.array(used_model, dtype=float), np.array(used_fact, dtype=float)

    @staticmethod
    def get_used_model_level_and_extend(model_data, fact_data, fact_level, fact_level_limit: int | None = None):
        used_model, used_fact = FrequencyMatch.get_used_model_level(model_data, fact_data, fact_level, fact_level_limit)
        if len(used_model) == 0 or len(used_model) >= len(fact_level):
            return used_model, used_fact
        for level in fact_level:
            if level > used_fact[-1]:
                extra_model = max(used_model[-1] * 2.0, level)
                used_model = np.append(used_model, extra_model)
                used_fact = np.append(used_fact, level)
                break
        return used_model, used_fact

    @staticmethod
    def correct_model_data(model_data: GridData, fact_level: np.ndarray, model_level: np.ndarray) -> GridData:
        output = model_data.copy_grid_data()
        if len(fact_level) == 0:
            return output
        flat = output.val.flatten()
        corrected = flat.copy()
        last = len(fact_level) - 1
        for idx, value in enumerate(flat):
            if value < model_level[0]:
                corrected[idx] = value * fact_level[0] / model_level[0] if model_level[0] != 0 else 0.0
            elif value < model_level[last]:
                for j in range(last):
                    if model_level[j] <= value < model_level[j + 1]:
                        corrected[idx] = fact_level[j] + (fact_level[j + 1] - fact_level[j]) * (value - model_level[j]) / (model_level[j + 1] - model_level[j])
                        break
            else:
                corrected[idx] = value * fact_level[last] / model_level[last] if model_level[last] != 0 else 0.0
        output.val = corrected.reshape(output.val.shape)
        return output
