function inventory = prepare_ieee39_bus_fault_temp_lab_copy(tempModelPath, targetBus, faultStartS, faultClearS, outputDir)
%PREPARE_IEEE39_BUS_FAULT_TEMP_LAB_COPY Inventory a temporary bus-fault lab copy.
%
% This helper only inspects a temporary local copy. It does not modify the
% source model and it does not claim an engineering-grade injection point.

if nargin < 3 || isempty(faultStartS)
    faultStartS = 0.5;
end
if nargin < 4 || isempty(faultClearS)
    faultClearS = 0.58;
end
if nargin < 5 || isempty(outputDir)
    outputDir = "../../results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans";
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

inventory = struct();
inventory.target_bus = char(targetBus);
inventory.temp_model_path = char(tempModelPath);
inventory.source_model_modified = false;
inventory.injection_point_found = false;
inventory.candidate_block_paths = {};
inventory.candidate_line_paths_or_handles = {};
inventory.proposed_fault_block_path = "";
inventory.fault_block_added_to_temp_copy = false;
inventory.fault_timing_configured = false;
inventory.compile_or_update_diagram_success = false;
inventory.error_or_warning = "";
inventory.manual_review_required = true;
inventory.safe_to_run_smoke = false;
inventory.fault_start_s = faultStartS;
inventory.fault_clear_s = faultClearS;
inventory.duration_s = max(0.0, faultClearS - faultStartS);

try
    if ~isfile(tempModelPath)
        error("Temporary model does not exist: %s", tempModelPath);
    end
    load_system(tempModelPath);
    [~, modelName, ~] = fileparts(tempModelPath);
    allBlocks = find_system(modelName, "LookUnderMasks", "all", "FollowLinks", "on", "Type", "Block");
    target = string(targetBus);
    targetNoB = erase(target, "B");
    blockStrings = string(allBlocks);
    blockNames = strings(numel(blockStrings), 1);
    for idx = 1:numel(blockStrings)
        try
            blockNames(idx) = string(get_param(blockStrings(idx), "Name"));
        catch
            blockNames(idx) = "";
        end
    end
    nameMatches = contains(blockNames, target, "IgnoreCase", true) | ...
        contains(blockNames, "Bus" + targetNoB, "IgnoreCase", true) | ...
        contains(blockNames, "Bus " + targetNoB, "IgnoreCase", true);
    candidateBlocks = blockStrings(nameMatches);
    if numel(candidateBlocks) > 80
        candidateBlocks = candidateBlocks(1:80);
    end
    lineLike = candidateBlocks(contains(candidateBlocks, " to ", "IgnoreCase", true) | contains(candidateBlocks, target, "IgnoreCase", true));
    faultBlocks = string(find_system(modelName, "LookUnderMasks", "all", "FollowLinks", "on", "MaskType", "Fault (Three-Phase)"));
    inventory.candidate_block_paths = cellstr(candidateBlocks);
    inventory.candidate_line_paths_or_handles = cellstr(lineLike);
    if ~isempty(faultBlocks)
        inventory.proposed_fault_block_path = char(faultBlocks(1));
    end
    inventory.injection_point_found = false;
    inventory.error_or_warning = "Candidate blocks were inventoried, but no safe automatic physical bus terminal wiring rule is verified.";
    try
        set_param(modelName, "SimulationCommand", "update");
        inventory.compile_or_update_diagram_success = true;
    catch ME
        inventory.compile_or_update_diagram_success = false;
        inventory.error_or_warning = char("Update diagram failed or partial: " + string(ME.message));
    end
    close_system(modelName, 0);
catch ME
    inventory.error_or_warning = char(string(ME.message));
    try
        [~, modelName, ~] = fileparts(tempModelPath);
        close_system(modelName, 0);
    catch
    end
end

jsonPath = fullfile(outputDir, "matlab_bus_fault_injection_inventory_" + string(targetBus) + ".json");
mdPath = fullfile(outputDir, "matlab_bus_fault_injection_inventory_" + string(targetBus) + ".md");
fid = fopen(jsonPath, "w");
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, "%s", jsonencode(inventory, PrettyPrint=true));

lines = [
    "# IEEE39 Bus-Fault Temporary Lab Inventory " + string(targetBus)
    ""
    "This inventory inspects a temporary lab copy only. It does not modify source `.slx` and does not prove final dynamic performance."
    ""
    "- source_model_modified: `" + string(inventory.source_model_modified) + "`"
    "- injection_point_found: `" + string(inventory.injection_point_found) + "`"
    "- fault_block_added_to_temp_copy: `" + string(inventory.fault_block_added_to_temp_copy) + "`"
    "- fault_timing_configured: `" + string(inventory.fault_timing_configured) + "`"
    "- compile_or_update_diagram_success: `" + string(inventory.compile_or_update_diagram_success) + "`"
    "- safe_to_run_smoke: `" + string(inventory.safe_to_run_smoke) + "`"
    "- manual_review_required: `" + string(inventory.manual_review_required) + "`"
    ""
    "The model remains phasor_RMS, not EMT. `generator_speed_proxy` is not direct frequency."
    ""
    "Warning: " + string(inventory.error_or_warning)
];
writelines(lines, mdPath);
fprintf("Wrote IEEE39 bus-fault temp lab inventory: %s\n", jsonPath);
end
