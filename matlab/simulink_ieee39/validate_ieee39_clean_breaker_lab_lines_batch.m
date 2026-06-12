function summaryTable = validate_ieee39_clean_breaker_lab_lines_batch(lineIds, modelPathPattern, outputDir)
%VALIDATE_IEEE39_CLEAN_BREAKER_LAB_LINES_BATCH Validate per-line clean labs.
%
% This function only inspects user-handwired per-line clean lab models. It
% does not insert breakers, reconnect physical ports, or save models.

if nargin < 1 || isempty(lineIds)
    lineIds = ["L04", "L05"];
end
if nargin < 2 || isempty(modelPathPattern)
    modelPathPattern = "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_%s.slx";
end
if nargin < 3 || isempty(outputDir)
    outputDir = "../../results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation";
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

configure_ieee39_short_filegen_paths();

lineIds = upper(string(lineIds));
lineMap = readLineMap();
rows = cell(numel(lineIds), 16);
inventoryRows = {};
for idx = 1:numel(lineIds)
    lineId = lineIds(idx);
    modelPath = string(sprintf(modelPathPattern, lineId));
    lineBlockPath = linePathFor(lineMap, lineId);
    breakerName = lineId + "_HandwiredTimedBreaker";
    commandName = lineId + "_TripCommand";
    modelFound = isfile(modelPath);
    modelLoadable = false;
    breakerFound = false;
    commandFound = false;
    breakerPath = "";
    commandPath = "";
    reason = "";
    try
        if modelFound
            load_system(modelPath);
            [~, modelName, ~] = fileparts(modelPath);
            modelLoadable = true;
            [allBlocks, blockNames] = listBlocks(modelName);
            breakerBlocks = findNamedBlocks(allBlocks, blockNames, breakerName);
            commandBlocks = findNamedBlocks(allBlocks, blockNames, commandName);
            breakerFound = ~isempty(breakerBlocks);
            commandFound = ~isempty(commandBlocks);
            if breakerFound
                breakerPath = breakerBlocks(1);
                inventoryRows(end+1, :) = {char(lineId), char(modelPath), char(breakerPath), "breaker"}; %#ok<AGROW>
            end
            if commandFound
                commandPath = commandBlocks(1);
                inventoryRows(end+1, :) = {char(lineId), char(modelPath), char(commandPath), "trip_command"}; %#ok<AGROW>
            end
            close_system(modelName, 0);
        end
    catch ME
        reason = "model load failed: " + string(ME.message);
        try
            [~, modelName, ~] = fileparts(modelPath);
            close_system(modelName, 0);
        catch
        end
    end
    nearLine = breakerFound && contains(lower(breakerPath), "grid");
    passed = modelFound && modelLoadable && breakerFound && commandFound && nearLine;
    if strlength(reason) == 0
        if ~modelFound
            reason = "clean lab model file not found";
        elseif ~modelLoadable
            reason = "model not loadable";
        elseif ~breakerFound
            reason = "missing breaker block named " + breakerName;
        elseif ~commandFound
            reason = "missing trip command named " + commandName;
        elseif ~nearLine
            reason = "breaker block found but not in Grid context";
        end
    end
    rows(idx, :) = {
        char(lineId), char(lineBlockPath), char(modelPath), modelFound, modelLoadable, char(breakerName), breakerFound, char(breakerPath), ...
        char(commandName), commandFound, char(commandPath), nearLine, 0.5, passed, char(reason), false ...
    };
end

summaryTable = cell2table(rows, "VariableNames", { ...
    'line_id', 'line_block_path', 'clean_lab_model_path', 'clean_lab_model_found', 'clean_lab_model_loadable', ...
    'breaker_block_name', 'breaker_block_found', 'breaker_block_path', ...
    'trip_command_name', 'trip_command_found', 'trip_command_path', ...
    'breaker_near_line', 'trip_time_s', 'validation_passed', ...
    'validation_failure_reason', 'clean_lab_model_committed' ...
});
if isempty(inventoryRows)
    inventoryTable = cell2table(cell(0, 4), "VariableNames", {'line_id', 'clean_lab_model_path', 'block_path', 'candidate_role'});
else
    inventoryTable = cell2table(inventoryRows, "VariableNames", {'line_id', 'clean_lab_model_path', 'block_path', 'candidate_role'});
end
writetable(summaryTable, fullfile(outputDir, "ieee39_clean_breaker_lab_batch_validation_summary.csv"));
writetable(inventoryTable, fullfile(outputDir, "ieee39_clean_breaker_lab_batch_block_inventory.csv"));
writeJsonTable(summaryTable, fullfile(outputDir, "ieee39_clean_breaker_lab_batch_validation_summary.json"));
fprintf("Wrote IEEE39 batch clean breaker lab validation under: %s\n", outputDir);
end

function [allBlocks, blockNames] = listBlocks(modelName)
allBlocks = string(find_system(modelName, "LookUnderMasks", "all", "FollowLinks", "on"));
blockNames = strings(size(allBlocks));
for idx = 1:numel(allBlocks)
    try
        blockNames(idx) = string(get_param(allBlocks(idx), "Name"));
    catch
        blockNames(idx) = "";
    end
end
isRoot = allBlocks == string(modelName);
allBlocks = allBlocks(~isRoot);
blockNames = blockNames(~isRoot);
end

function blocks = findNamedBlocks(allBlocks, blockNames, targetName)
mask = strcmpi(strtrim(blockNames), strtrim(string(targetName)));
blocks = allBlocks(mask);
end

function lineMap = readLineMap()
mapPath = "../../results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map.csv";
if isfile(mapPath)
    lineMap = readtable(mapPath, "TextType", "string", "VariableNamingRule", "preserve", "Delimiter", ",");
else
    lineMap = table(string.empty(0, 1), string.empty(0, 1), "VariableNames", {'line_id', 'line_block_path'});
end
end

function path = linePathFor(lineMap, lineId)
path = "not_in_current_line_map";
if ~isempty(lineMap) && any(lineMap.line_id == lineId)
    match = lineMap(lineMap.line_id == lineId, :);
    path = string(match.line_block_path(1));
end
end

function writeJsonTable(tableValue, path)
records = table2struct(tableValue);
fid = fopen(path, "w");
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, "%s", jsonencode(records, PrettyPrint=true));
end
