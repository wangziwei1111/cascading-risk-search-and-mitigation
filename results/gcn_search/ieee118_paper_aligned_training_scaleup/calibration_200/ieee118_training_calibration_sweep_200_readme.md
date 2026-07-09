# IEEE118 Paper-Aligned Training Calibration

- Target state samples per setting: 200
- Samples per scenario: 20
- Seeds: 20260701, 20260702, 20260703, 20260704, 20260705, 20260706, 20260707, 20260708, 20260709, 20260710
- Load scales: 1.0, 1.05, 1.1
- Flow-limit scales: 8.0, 10.0, 12.0
- Recommended row: {"load_scale": 1.1, "flow_limit_scale": 8.0, "min_rate_a": 1.0, "positive_label_ratio": 0.05270461471484545, "num_candidate_labels": 36752, "s0_positive_ratio": 0.0467741935483871, "s1_positive_ratio": 0.05302074974206122, "num_first_step_critical_lines_estimate": 87, "mean_candidate_labels_per_state": 183.76, "relay_cascade_positive_ratio": null, "error_count": 0, "recommended_setting": "candidate"}

Recommendation keeps the original-paper load setting when feasible, avoids overly dense labels, and avoids cases dominated by first-step critical lines. This calibration is for training-label density only; it does not modify search ordering logic.
