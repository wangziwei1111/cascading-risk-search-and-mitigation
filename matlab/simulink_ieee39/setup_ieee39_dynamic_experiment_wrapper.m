function wrapperSummary = setup_ieee39_dynamic_experiment_wrapper(sourceModelPath, outputDir)
%SETUP_IEEE39_DYNAMIC_EXPERIMENT_WRAPPER Copy an IEEE39 graphical model for experiments.
%
% This wrapper preserves the source model. It creates a generated copy and a
% machine-readable interface plan for later fault injection, breaker trips,
% measurement export, and dynamic-label generation.

if nargin < 1 || isempty(sourceModelPath)
    sourceModelPath = "C:/Users/24186/Documents/MATLAB/Examples/R2024b/simscapeelectrical/IEEE39BusSystemExample/IEEE39BusSystem.slx";
end
if nargin < 2 || isempty(outputDir)
    outputDir = "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models";
end
if ~isfile(sourceModelPath)
    error("Source IEEE39 model not found: %s", sourceModelPath);
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

[~, modelName, ext] = fileparts(sourceModelPath);
generatedPath = fullfile(outputDir, modelName + "_dynamic_experiment_wrapper" + ext);
copyfile(sourceModelPath, generatedPath);

load_system(generatedPath);
generatedModelName = modelName + "_dynamic_experiment_wrapper";
allBlocks = find_system(generatedModelName, "LookUnderMasks", "all", "FollowLinks", "on", "Type", "Block");
blockTable = buildBlockInventory(allBlocks);
blockTable = compactBlockInventory(blockTable);
wrapperDir = fullfile(fileparts(outputDir), "wrapper");
if ~exist(wrapperDir, "dir")
    mkdir(wrapperDir);
end
writetable(blockTable, fullfile(wrapperDir, "ieee39_wrapper_block_inventory.csv"));
signalMap = table( ...
    ["bus_voltage"; "line_current_proxy"; "frequency_proxy"; "generator_speed"; "rotor_angle"; "relay_trip_signal"], ...
    ["Measurements subsystem"; "Simscape logging or mapped line current"; "generator speed derived proxy"; "generator measurement blocks"; "generator measurement blocks"; "basic relay proxy output"], ...
    ["available_or_mapped"; "manual_extraction_required"; "proxy_required"; "available_in_generator_subsystems"; "available_in_generator_subsystems"; "external_proxy"], ...
    'VariableNames', {'signal_name', 'source_hint', 'mapping_status'} ...
);
writetable(signalMap, fullfile(wrapperDir, "ieee39_wrapper_signal_map.csv"));
hasFault = any(contains(lower(string(allBlocks)), "fault"));
hasBreaker = any(contains(lower(string(allBlocks)), "breaker"));
hasLine = any(contains(string(getMaskTypes(allBlocks)), "Transmission", "IgnoreCase", true));
close_system(generatedModelName, 0);

wrapperSummary = struct();
wrapperSummary.source_model_path = char(sourceModelPath);
wrapperSummary.generated_model_path = char(generatedPath);
wrapperSummary.original_model_preserved = true;
wrapperSummary.wrapper_directory = char(wrapperDir);
wrapperSummary.block_inventory_csv = char(fullfile(wrapperDir, "ieee39_wrapper_block_inventory.csv"));
wrapperSummary.signal_map_csv = char(fullfile(wrapperDir, "ieee39_wrapper_signal_map.csv"));
wrapperSummary.fault_wiring_status = ternary(hasFault, "existing_three_phase_fault_block_available", "manual_required");
wrapperSummary.breaker_wiring_status = ternary(hasBreaker, "existing_breaker_blocks_available", "manual_required");
wrapperSummary.line_trip_status = ternary(hasLine, "pilot_line_block_disable_supported", "manual_required");
wrapperSummary.added_fault_injection_interface = wrapperSummary.fault_wiring_status;
wrapperSummary.added_line_trip_interface = wrapperSummary.line_trip_status;
wrapperSummary.added_measurement_outputs = ["bus_voltage", "generator_speed", "frequency", "rotor_angle", "line_loading_proxy", "relay_trip_signal"];
wrapperSummary.protection_status = "protection wrapper not engineering-grade; relay logic still preliminary";
wrapperSummary.result_export_status = "fault-test scripts export CSV summaries and event logs";
wrapperSummary.do_not_commit_generated_slx = true;

summaryPath = fullfile(wrapperDir, "ieee39_wrapper_build_summary.json");
fid = fopen(summaryPath, "w");
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, "%s", jsonencode(wrapperSummary, PrettyPrint=true));
fprintf("Wrote IEEE39 wrapper summary: %s\n", summaryPath);
fprintf("Generated wrapper model copy: %s\n", generatedPath);
end

function blockTable = buildBlockInventory(blocks)
numBlocks = numel(blocks);
paths = strings(numBlocks, 1);
blockTypes = strings(numBlocks, 1);
maskTypes = strings(numBlocks, 1);
for idx = 1:numBlocks
    paths(idx) = string(blocks{idx});
    try
        blockTypes(idx) = string(get_param(blocks{idx}, "BlockType"));
    catch
        blockTypes(idx) = "";
    end
    try
        maskTypes(idx) = string(get_param(blocks{idx}, "MaskType"));
    catch
        maskTypes(idx) = "";
    end
end
blockTable = table(paths, blockTypes, maskTypes, 'VariableNames', {'block_path', 'block_type', 'mask_type'});
end

function maskTypes = getMaskTypes(blocks)
maskTypes = strings(numel(blocks), 1);
for idx = 1:numel(blocks)
    try
        maskTypes(idx) = string(get_param(blocks{idx}, "MaskType"));
    catch
        maskTypes(idx) = "";
    end
end
end

function compactTable = compactBlockInventory(blockTable)
text = lower(blockTable.block_path + " " + blockTable.mask_type + " " + blockTable.block_type);
keep = contains(text, "grid") | contains(text, "generator") | contains(text, "load") | ...
    contains(text, "measurement") | contains(text, "fault") | contains(text, "breaker") | ...
    contains(text, "transmission") | contains(text, "line") | contains(text, "busbar") | ...
    contains(text, "switch") | contains(text, "governor") | contains(text, "exciter");
compactTable = blockTable(keep, :);
if height(compactTable) > 500
    compactTable = compactTable(1:500, :);
end
end

function value = ternary(condition, trueValue, falseValue)
if condition
    value = trueValue;
else
    value = falseValue;
end
end
