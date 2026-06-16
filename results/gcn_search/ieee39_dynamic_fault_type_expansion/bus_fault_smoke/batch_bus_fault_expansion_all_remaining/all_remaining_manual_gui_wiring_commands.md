# IEEE39 All-Remaining Bus-Fault Manual GUI Wiring Commands

This document is for manual GUI wiring only. Do not run Simulink. Use Update
Diagram only, then record evidence in the per-bus template.

## A. Target Summary

| bus | temp copy path | fault block name | template path | special handling |
| --- | --- | --- | --- | --- |
| B1 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B1_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B1_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B1.json` | `false` |
| B2 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B2_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B2_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B2.json` | `false` |
| B3 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B3_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B3_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B3.json` | `false` |
| B4 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B4_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B4_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B4.json` | `false` |
| B5 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B5_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B5_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B5.json` | `false` |
| B6 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B6_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B6_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B6.json` | `false` |
| B7 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B7_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B7_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B7.json` | `false` |
| B8 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B8_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B8_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B8.json` | `false` |
| B9 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B9_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B9_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B9.json` | `false` |
| B10 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B10_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B10_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B10.json` | `false` |
| B11 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B11_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B11_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B11.json` | `false` |
| B12 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B12_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B12_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B12.json` | `false` |
| B13 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B13_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B13_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B13.json` | `false` |
| B14 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B14_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B14_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B14.json` | `false` |
| B15 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B15_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B15_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B15.json` | `false` |
| B17 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B17_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B17_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B17.json` | `false` |
| B18 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B18_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B18_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B18.json` | `false` |
| B19 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B19_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B19_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B19.json` | `false` |
| B20 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B20_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B20_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B20.json` | `false` |
| B21 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B21_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B21_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B21.json` | `false` |
| B22 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B22_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B22_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B22.json` | `false` |
| B23 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B23_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B23_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B23.json` | `false` |
| B24 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B24_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B24_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B24.json` | `false` |
| B25 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B25_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B25_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B25.json` | `false` |
| B27 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B27_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B27_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B27.json` | `false` |
| B28 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B28_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B28_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B28.json` | `false` |
| B29 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B29_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B29_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B29.json` | `false` |
| B30 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B30_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B30_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B30.json` | `false` |
| B31 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B31_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B31_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B31.json` | `false` |
| B32 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B32_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B32_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B32.json` | `false` |
| B33 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B33_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B33_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B33.json` | `false` |
| B34 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B34_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B34_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B34.json` | `false` |
| B35 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B35_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B35_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B35.json` | `false` |
| B36 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B36_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B36_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B36.json` | `false` |
| B37 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B37_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B37_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B37.json` | `false` |
| B38 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B38_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B38_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B38.json` | `false` |
| B16 | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B16_TEMP_LOCAL_ONLY.slx` | `Grid/Fault_B16_TEMP` | `C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_B16.json` | `true` |

## B. Create Or Open Temporary Local Copies

```matlab
sourceModel = 'results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper.slx';
targetBuses = {'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B9', 'B10', 'B11', 'B12', 'B13', 'B14', 'B15', 'B17', 'B18', 'B19', 'B20', 'B21', 'B22', 'B23', 'B24', 'B25', 'B27', 'B28', 'B29', 'B30', 'B31', 'B32', 'B33', 'B34', 'B35', 'B36', 'B37', 'B38', 'B16'};
for k = 1:numel(targetBuses)
    bus = targetBuses{k};
    tempModel = sprintf('results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_{bus}_TEMP_LOCAL_ONLY.slx', bus);
    if exist(tempModel, 'file')
        fprintf('Temp copy exists, inspect before editing: %s\n', tempModel);
    else
        copyfile(sourceModel, tempModel);
        fprintf('Created ignored temp copy: %s\n', tempModel);
    end
    open_system(tempModel);
end
```

`local_lab_copies` is an ignored local path. Do not commit `.slx`, `.slxc`,
`slprj`, `.mat`, raw trajectories, or full timeseries.

## C. Basic Inspection Commands

```matlab
targetBuses = {'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B9', 'B10', 'B11', 'B12', 'B13', 'B14', 'B15', 'B17', 'B18', 'B19', 'B20', 'B21', 'B22', 'B23', 'B24', 'B25', 'B27', 'B28', 'B29', 'B30', 'B31', 'B32', 'B33', 'B34', 'B35', 'B36', 'B37', 'B38', 'B16'};
for k = 1:numel(targetBuses)
    bus = targetBuses{k};
    tempModel = sprintf('results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_{bus}_TEMP_LOCAL_ONLY.slx', bus);
    open_system(tempModel);
    bd = bdroot;
    fprintf('\n=== %s ===\n', bus);
    busCandidates = find_system(bd, 'LookUnderMasks', 'all', 'FollowLinks', 'on', 'Name', ['*' bus '*']);
    oldFaults = find_system(bd, 'LookUnderMasks', 'all', 'FollowLinks', 'on', 'Name', '*Fault (Three-Phase)*');
    newFault = find_system(bd, 'LookUnderMasks', 'all', 'FollowLinks', 'on', 'Name', ['Fault_' bus '_TEMP']);
    disp(busCandidates);
    disp(oldFaults);
    disp(newFault);
    for n = 1:numel(busCandidates)
        try
            fprintf('%s | BlockType=%s | MaskType=%s\n', busCandidates{n}, get_param(busCandidates{n}, 'BlockType'), get_param(busCandidates{n}, 'MaskType'));
            disp(get_param(busCandidates{n}, 'PortConnectivity'));
        catch ME
            fprintf('Inspection warning for %s: %s\n', busCandidates{n}, ME.message);
        end
    end
end
```

## D. Post-Wiring Update-Diagram Checks

```matlab
targetBuses = {'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B9', 'B10', 'B11', 'B12', 'B13', 'B14', 'B15', 'B17', 'B18', 'B19', 'B20', 'B21', 'B22', 'B23', 'B24', 'B25', 'B27', 'B28', 'B29', 'B30', 'B31', 'B32', 'B33', 'B34', 'B35', 'B36', 'B37', 'B38', 'B16'};
for k = 1:numel(targetBuses)
    bus = targetBuses{k};
    tempModel = sprintf('results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_{bus}_TEMP_LOCAL_ONLY.slx', bus);
    open_system(tempModel);
    bd = bdroot;
    expectedFaultName = ['Fault_' bus '_TEMP'];
    newFault = find_system(bd, 'LookUnderMasks', 'all', 'FollowLinks', 'on', 'Name', expectedFaultName);
    if isempty(newFault)
        warning('Missing Grid/Fault_%s_TEMP in %s', bus, bd);
        continue;
    end
    disp(get_param(newFault{1}, 'PortConnectivity'));
    if strcmp(bus, 'B16')
        oldFaults = find_system(bd, 'LookUnderMasks', 'all', 'FollowLinks', 'on', 'Name', '*Fault (Three-Phase)*');
        disp(oldFaults);
    end
    set_param(bd, 'SimulationCommand', 'update');
    save_system(bd);
end
```

Do not press Run. Saving is allowed only for the ignored temporary local copy.

## E. Unified Fault Parameters

For every `Grid/Fault_<BUS>_TEMP`, set:

- fault_start_time: `0.5`
- fault_duration: `0.08`
- R_pn_fault: `1e-3`
- R_ng_fault: `1e-3`

Use `try/catch` because parameter names may differ by block mask.

```matlab
paramAttempts = {
    'SwitchTimes', '[0.5 0.58]';
    'FaultResistance', '1e-3';
    'GroundResistance', '1e-3';
    'Rpn', '1e-3';
    'Rng', '1e-3'
};
for p = 1:size(paramAttempts, 1)
    try
        set_param(newFault{1}, paramAttempts{p,1}, paramAttempts{p,2});
    catch ME
        fprintf('Parameter not accepted: %s (%s)\n', paramAttempts{p,1}, ME.message);
    end
end
```

## F. B16 Special Warning

- Do not rename old `Grid/Fault (Three-Phase)`.
- Do not move the old fault block.
- The new fault must be named only `Grid/Fault_B16_TEMP`.
- The old fault should remain near `Grid/Bus16_1` and `Grid/B16 to B17`.
- B16 evidence must be reviewed separately before smoke.
