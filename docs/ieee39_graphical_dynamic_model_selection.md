# IEEE39 Graphical Dynamic Model Selection

## Purpose

Round 26 pauses dynamic-aware reranker training and moves the dynamic-label backend from the RTS-79 simplified swing-equation prototype toward an existing IEEE 39-bus / New England 10-machine graphical Simulink model.

The goal is not to rebuild RTS-79 from scratch. The goal is to reuse a model that can be opened, inspected, wrapped, and later used to generate dynamic labels.

## Candidate Inventory

The local inventory found two IEEE39 graphical Simulink candidates:

| Candidate | Path | Opened in MATLAB | Source note |
|---|---|---:|---|
| MathWorks IEEE39BusSystem example | `C:/Users/24186/Documents/MATLAB/Examples/R2024b/simscapeelectrical/IEEE39BusSystemExample/IEEE39BusSystem.slx` | yes | Local MathWorks example; do not commit copied `.slx`. |
| Local user copy | `C:/Users/24186/Desktop/山东项目/IEEE39BusSystemExample/IEEE39BusSystem.slx` | yes | Local copy; license must be checked before committing. |

The MathWorks page describes `IEEE39BusSystem` as a 39-bus three-phase power-system example with four major subsystems: Generators, Grid, Loads, and Measurements. It also states that the generator subsystem includes ten generators with AVR, exciters, PSS, governors, and prime movers. See: <https://www.mathworks.com/help/sps/ug/ieee-39-bus-system.html>.

An additional open-source candidate exists on MATLAB Central File Exchange: "10-Machine New-England Power System IEEE benchmark", described as a SimPowerSystems model of the IEEE 39-bus / 10-machine New England system. See: <https://www.mathworks.com/matlabcentral/fileexchange/54771-10-machine-new-england-power-system-ieee-benchmark>.

## Primary Selection

Primary model:

`C:/Users/24186/Documents/MATLAB/Examples/R2024b/simscapeelectrical/IEEE39BusSystemExample/IEEE39BusSystem.slx`

Selection reasons:

- It is already installed locally with MATLAB examples.
- MATLAB verified that it can be opened.
- It contains generator, exciter, governor, load, line/grid, and measurement subsystems according to local inventory and MathWorks documentation.
- It avoids immediate dependence on a third-party downloaded `.slx`.
- It is suitable as a graphical dynamic-model backend for future label generation.

## Model Type

Current classification: `phasor_RMS`.

This is a conservative project-side classification for the current dynamic-label workflow. It must not be described as EMT unless the solver mode, network representation, and switching/fault blocks are explicitly verified for an EMT-level study.

## Component Status

| Component | Current status |
|---|---|
| Generators | present |
| Exciters / AVR | present |
| Governors / prime movers | present |
| PSS | present according to MathWorks documentation |
| Lines / grid | present |
| Loads | present |
| Measurements | present |
| Breakers | not yet verified by wrapper inventory |
| Protection | not yet a complete protection model |

## Selection Caveats

- The original `.slx` is not committed.
- The generated wrapper copy under `results/` is not committed.
- The protection interface is not engineering-grade.
- If real machine/protection settings are missing, later dynamic conclusions must remain preliminary.
- This round only establishes a reusable dynamic-label interface; it does not train a dynamic-aware reranker.

## Round 27 Caveat

Round 27 found an existing three-phase fault block and mapped pilot transmission lines, but automatic breaker discovery remains incomplete. The wrapper currently uses pilot line-block disabling for line outages and a basic relay proxy for relay status. This is a useful bridge toward dynamic labels, but it is still not a full protection model.
