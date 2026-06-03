# Figure 1 Cascade Flow Trace

This is a same-environment trace for the paper cascade mitigation flow.

System: `ieee14_pypower_case14`
Policy: `do_nothing`
Initial outages: `[6, 9]`

## Paper Flow Steps

1. initialize generation and load scenario
2. sample initial N-k outage
3. identify islands
4. balance generation and load inside each island
5. run power flow
6. terminate if power flow fails
7. agent selects action
8. apply proactive line opening
9. process islands again
10. run power flow again
11. detect overloaded lines
12. sample overload trips with paper beta rule
13. terminate if no new trip occurs
14. advance to next generation if new trips occur

## Episode Trace

- generation 1: action=0, valid=True, opened=None, new trips=[3, 7, 8], pf_converged=False, terminal_reason=powerflow_failed, reward=-102.9554
