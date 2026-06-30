from __future__ import annotations

import numpy as np

from data import GridData


class Ensemble:
    @staticmethod
    def similarity_score_by_ts_and_bias(
        gd_model: GridData,
        gd_fact: GridData,
        rain_limit: float = 0.0,
        smooth_num: int = 0,
        check_limit: float = 0.1,
    ) -> float:
        model = gd_model.copy_grid_data()
        fact = gd_fact.copy_grid_data()
        model.clear_to_num_less_than(0.0, rain_limit)
        fact.clear_to_num_less_than(0.0, rain_limit)
        model.smooth9(smooth_num)
        fact.smooth9(smooth_num)
        fact_hit = fact.val >= check_limit
        model_hit = model.val >= check_limit
        hit = float(np.count_nonzero(fact_hit & model_hit))
        miss = float(np.count_nonzero(fact_hit & ~model_hit))
        false_alarm = float(np.count_nonzero(~fact_hit & model_hit))
        ts_den = hit + miss + false_alarm
        hm_den = hit + miss
        ts = hit / ts_den if ts_den != 0.0 else 0.0
        bias = (hit + false_alarm) / hm_den if hm_den != 0.0 else 0.0
        return ts + 0.2 / (abs(9.0 * (bias - 1.0)) + 1.0) if (bias != 0.0 or ts != 0.0) else -1.0

    @staticmethod
    def get_similarity_index_by_ts_and_bias(
        gd_model: list[GridData],
        gd_fact: GridData,
        choose_num: int,
        check_limit: np.ndarray | list[float] | None = None,
        rain_limit: float = 0.0,
        smooth_num: int = 0,
    ) -> tuple[np.ndarray, np.ndarray]:
        scores = np.zeros(len(gd_model), dtype=float)
        if check_limit is None:
            check_limits = np.array([0.1], dtype=float)
        else:
            check_limits = np.asarray(check_limit, dtype=float)
        for idx, item in enumerate(gd_model):
            valid_scores = []
            for limit in check_limits:
                score = Ensemble.similarity_score_by_ts_and_bias(item, gd_fact, rain_limit, smooth_num, float(limit))
                if score >= 0.0:
                    valid_scores.append(score)
            scores[idx] = float(np.mean(valid_scores)) if valid_scores else 0.0
        order = np.argsort(scores)[::-1][:choose_num]
        return order.astype(int), scores[order].astype(float)
