# IEEE118 adaptive probe policy selection

Probe count and promotion threshold are selected on eight validation operating scenarios. The frozen `20260708` test outcomes are not read during selection. Low-fidelity proxy scores are label-free policy inputs; high-fidelity validation labels are returned only after each selected probe in the retrospective oracle replay. Recall statistics cover only fully labeled validation S1 states; the output reports the subset coverage and must not be read as global IEEE118 recall.

Validation policy selection reads 108,410 high-fidelity path labels from the fully labeled validation S1 subset. These labels are a subset of the same validation labels already used for model selection and calibration, so they are reported separately but not double-counted in unique development-label cost.
