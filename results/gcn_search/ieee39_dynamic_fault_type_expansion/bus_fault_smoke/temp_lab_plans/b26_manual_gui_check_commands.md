# B26 Manual GUI Check Commands

These snippets are for the user to copy into MATLAB while manually reviewing
the B26 temporary local copy. Do not Run simulation from these snippets. Use
Update Diagram only.

```matlab
modelPath = 'results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B26_TEMP_LOCAL_ONLY.slx';
open_system(modelPath);
bd = bdroot;
```

Inspect `Bus26_1` and `Bus26_2`:

```matlab
blocks = {'Grid/Bus26_1', 'Grid/Bus26_2'};
for k = 1:numel(blocks)
    blk = [bd '/' blocks{k}];
    fprintf('\n=== %s ===\n', blk);
    disp(get_param(blk, 'BlockType'));
    try, disp(get_param(blk, 'MaskType')); end
    try, disp(get_param(blk, 'MaskNames')); end
    try, disp(get_param(blk, 'MaskValues')); end
    try, disp(get_param(blk, 'PortConnectivity')); end
end
```

Check whether the old `Fault (Three-Phase)` is still near B16:

```matlab
faults = find_system(bd, 'LookUnderMasks', 'all', 'FollowLinks', 'on', ...
    'Name', 'Fault (Three-Phase)');
disp(faults);
```

Check whether `Fault_B26_TEMP` already exists:

```matlab
tempFault = find_system(bd, 'LookUnderMasks', 'all', 'FollowLinks', 'on', ...
    'Name', 'Fault_B26_TEMP');
disp(tempFault);
```

After manual wiring, inspect `Fault_B26_TEMP` connectivity:

```matlab
blk = [bd '/Grid/Fault_B26_TEMP'];
if ~isempty(find_system(bd, 'SearchDepth', 2, 'Name', 'Fault_B26_TEMP'))
    disp(get_param(blk, 'PortConnectivity'));
end
```

Update Diagram only:

```matlab
set_param(bd, 'SimulationCommand', 'update');
```

Do not run simulation in this manual verification step. Record the result in:

```text
results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_bus_fault_injection_review_template_B26.json
```
