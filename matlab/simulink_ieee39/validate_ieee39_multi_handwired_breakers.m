function summaryTable = validate_ieee39_multi_handwired_breakers(handwiredModelPath, outputDir, lineIds, breakerNamePattern, tripCommandPattern)
%VALIDATE_IEEE39_MULTI_HANDWIRED_BREAKERS Validate user hand-wired line breakers.
%
% This function only inspects a user-supplied handwired model. It does not
% create, insert, reconnect, or save Simscape physical-port blocks.

if nargin < 1 || isempty(handwiredModelPath)
    handwiredModelPath = "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx";
end
if nargin < 2 || isempty(outputDir)
    outputDir = "../../results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation";
end
if nargin < 3 || isempty(lineIds)
    lineIds = ["L01", "L02", "L03", "L04"];
end
if nargin < 4 || isempty(breakerNamePattern)
    breakerNamePattern = "%s_HandwiredTimedBreaker";
end
if nargin < 5 || isempty(tripCommandPattern)
    tripCommandPattern = "%s_TripCommand";
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end
configure_ieee39_short_filegen_paths();

lineIds = string(lineIds);
lineMap = readLineMap();
rows = cell(numel(lineIds), 15);
inventoryRows = {};
modelFound = isfile(handwiredModelPath);
modelLoadable = false;
modelName = "";
allBlocks = strings(0, 1);
blockNames = strings(0, 1);
try
    if modelFound
        load_system(handwiredModelPath);
        [~, modelName, ~] = fileparts(handwiredModelPath);
        modelLoadable = true;
        [allBlocks, blockNames] = listBlocks(modelName);
    end
catch ME
    modelLoadable = false;
    loadFailure = "model load failed: " + string(ME.message);
end
if ~exist("loadFailure", "var")
    loadFailure = "";
end

for idx = 1:numel(lineIds)
    lineId = lineIds(idx);
    breakerName = string(sprintf(char(breakerNamePattern), char(lineId)));
    commandName = string(sprintf(char(tripCommandPattern), char(lineId)));
    lineBlockPath = linePathFor(lineMap, lineId);
    breakerBlocks = findNamedBlocks(allBlocks, blockNames, breakerName);
    commandBlocks = findNamedBlocks(allBlocks, blockNames, commandName);
    breakerFound = ~isempty(breakerBlocks);
    commandFound = ~isempty(commandBlocks);
    breakerPath = "";
    commandPath = "";
    if breakerFound
        breakerPath = breakerBlocks(1);
        inventoryRows(end+1, :) = {char(lineId), char(breakerPath), "breaker"}; %#ok<AGROW>
    end
    if commandFound
        commandPath = commandBlocks(1);
        inventoryRows(end+1, :) = {char(lineId), char(commandPath), "trip_command"}; %#ok<AGROW>
    end
    nearLine = breakerFound && (contains(lower(breakerPath), lower(lineId)) || contains(lower(breakerPath), "grid"));
    passed = modelFound && modelLoadable && breakerFound && commandFound && nearLine;
    reason = "";
    if ~modelFound
        reason = "handwired model file not found";
    elseif ~modelLoadable
        reason = loadFailure;
    elseif ~breakerFound
        reason = "missing breaker block named " + breakerName;
    elseif ~commandFound
        reason = "missing trip command named " + commandName;
    elseif ~nearLine
        reason = "breaker block found but not near expected line naming context";
    end
    rows(idx, :) = {
        char(lineId), char(lineBlockPath), modelFound, modelLoadable, char(breakerName), breakerFound, char(breakerPath), ...
        char(commandName), commandFound, char(commandPath), nearLine, 0.5, passed, char(reason), false ...
    };
end

if modelLoadable
    try
        close_system(modelName, 0);
    catch
    end
end

summaryTable = cell2table(rows, "VariableNames", { ...
    'line_id', 'line_block_path', 'handwired_model_found', 'handwired_model_loadable', ...
    'breaker_block_name', 'breaker_block_found', 'breaker_block_path', ...
    'trip_command_name', 'trip_command_found', 'trip_command_path', ...
    'breaker_near_line', 'trip_time_s', 'validation_passed', ...
    'validation_failure_reason', 'handwired_model_committed' ...
});
if isempty(inventoryRows)
    inventoryTable = cell2table(cell(0, 3), "VariableNames", {'line_id', 'block_path', 'candidate_role'});
else
    inventoryTable = cell2table(inventoryRows, "VariableNames", {'line_id', 'block_path', 'candidate_role'});
end
writetable(summaryTable, fullfile(outputDir, "ieee39_multi_handwired_breaker_validation_summary.csv"));
writetable(inventoryTable, fullfile(outputDir, "ieee39_multi_handwired_breaker_block_inventory.csv"));
writeJsonTable(summaryTable, fullfile(outputDir, "ieee39_multi_handwired_breaker_validation_summary.json"));
fprintf("Wrote IEEE39 multi-handwired breaker validation under: %s\n", outputDir);
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
path = "";
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
