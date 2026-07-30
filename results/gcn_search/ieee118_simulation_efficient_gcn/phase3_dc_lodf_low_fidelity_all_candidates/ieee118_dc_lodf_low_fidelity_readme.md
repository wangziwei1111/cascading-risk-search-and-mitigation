# IEEE118 DC/LODF Low-Fidelity Targets

These targets are produced from topology, current branch flow, and thermal limits. They require one base DCOPF per load scenario and no additional N-1 or N-2 cascade calls inside this target builder. The source NPZ already contains S0/S1 graph states, so this incremental count does not reclaim their historical physical construction cost. All nine IEEE118 non-unity transformer taps are included in the DC branch susceptance used by the LODF calculation.

The target is suitable for pretraining or acquisition guidance only. It must not replace high-fidelity cascade labels in final evaluation.
