# B1 and Classification Diagnosis

```json
{
  "analysis_scope": "b1_and_classification_diagnosis",
  "target_bus": "B1",
  "scenario_id": "BF_B1_TEMP_SMOKE",
  "true_dynamic_stress_score": 0.19602585950733364,
  "gcn_predicted_dynamic_stress_score": 0.5078984498977661,
  "gcn_absolute_error": 0.31187259039043247,
  "gcn_unstable_probability": 1.0,
  "ridge_logistic_predicted_dynamic_stress_score": 0.5201847730493282,
  "ridge_logistic_absolute_error": 0.32415891354199455,
  "target_bus_only_predicted_dynamic_stress_score": 0.5057645215705512,
  "target_bus_only_absolute_error": 0.30973866206321754,
  "assumed_unstable_threshold": 0.5,
  "b1_true_unstable_by_score_threshold": false,
  "b1_predicted_unstable_by_probability_threshold": true,
  "b1_misclassified_by_probability_threshold": true,
  "b1_overconfident": true,
  "b1_regression_overprediction": 0.31187259039043247,
  "diagnosis": "B1 is a stable / low-stress marker but the GCN assigns unstable probability 1.0, so the audit exposes overconfident classification on this case."
}
```
