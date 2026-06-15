# IEEE39 v2-plus-B39 Preview Interpretation

This round does not run new training. It only interprets the previous
v2-plus-B39 dynamic-aware reranker preview results and prepares the next manual
bus-fault sample workflow. It does not run Simulink, does not submit `.slx`,
does not train GCN, does not retrain the reranker, and does not export labels.

## Main Finding

The v2-plus-B39 preview suggests that bus-fault generalization is still weak.
The include-all and exclude-provenance metrics look good, but those modes use
compact dynamic measurements as input features. Since `dynamic_stress_score` is
also synthesized from compact dynamic measurements, those results have
target-feature leakage risk.

## Evidence

- include_all_41 RMSE: `0.043432407857356255`
- exclude_provenance RMSE: `0.04435709313621243`
- no_dynamic_measurement_features RMSE: `0.06101753319040434`
- label_family_holdout RMSE: `0.17926382339205915`
- B39 holdout true dynamic_stress_score: `0.6057813745060507`
- B39 holdout predicted dynamic_stress_score: `0.3941782648518122`
- B39 holdout absolute error: `0.2116031096542385`
- B39 holdout unstable probability: `0.9667234869320884`

The no_dynamic_measurement_features result is worse than include_all, which is
important evidence of leakage risk. The label_family_holdout result is much
harder. In the B39 holdout, the model assigns a high unstable probability, but
it clearly underestimates the dynamic_stress_score.

## Conservative Interpretation

B39 is only one bus-fault sample, so it cannot represent all bus faults. The
current result should be read as a warning: before connecting dynamic labels
back to the main GCN/reranker workflow, collect more independent bus-fault
samples. In short, collect more independent bus-fault samples first.

## Next Sample Priority

The next priority manual target is `B26`. The goal is not to run smoke in this
round. The goal is to guide a human Simulink GUI review to find a safe temporary
injection point.

## Boundaries

- B39 remains a candidate label, not a formal label.
- B26 is not verified.
- B26 is not smoke success.
- B26 candidate label has not been exported.
- The old formal gate remains `35 / 33 / 33`.
- The v2-plus-B39 count remains `41`.
- The model remains `phasor_RMS`, not EMT.
- `generator_speed_proxy` is not direct frequency.
- Temporary bus-fault injection is not engineering-grade protection.

## B26 Candidate Export Follow-Up

The next bus-fault candidate was added in a later export-only round: B26 was
exported as one candidate label after its temporary smoke quality review passed.
This does not retrain the preview model and does not change the old formal
gate.

- previous v2-plus-B39 count: `41`
- new v2-plus-B39+B26 count: `42`
- B26 dynamic_stress_score: `0.5314759474846006`
- B26 status: candidate label, not formal label
- B39 status: candidate label, not formal label

The next step remains no-training composition review. Do not train GCN or
retrain the reranker from the expanded table until that review is complete.
