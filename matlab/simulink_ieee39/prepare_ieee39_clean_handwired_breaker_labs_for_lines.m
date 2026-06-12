function summaryTable = prepare_ieee39_clean_handwired_breaker_labs_for_lines(lineIds, sourceWrapperPath, outputDir)
%PREPARE_IEEE39_CLEAN_HANDWIRED_BREAKER_LABS_FOR_LINES Copy per-line clean labs.
%
% This batch helper copies the original clean generated wrapper into one
% local .slx per target line. It does not insert breakers, reconnect Simscape
% physical ports, or save changes to the source wrapper.

if nargin < 1 || isempty(lineIds)
    lineIds = ["L04", "L05"];
end
if nargin < 2 || isempty(sourceWrapperPath)
    sourceWrapperPath = "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper.slx";
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
sourceFound = isfile(sourceWrapperPath);
sourceHasHandwired = false;
if sourceFound
    try
        load_system(sourceWrapperPath);
        sourceModelName = bdroot;
        sourceHasHandwired = containsAnyHandwiredBreaker(sourceModelName, ["L01", "L02", "L03", "L04", "L05"]);
        close_system(sourceModelName, 0);
    catch
        sourceHasHandwired = true;
        try
            close_system(bdroot, 0);
        catch
        end
    end
end

rows = cell(numel(lineIds), 10);
for idx = 1:numel(lineIds)
    lineId = lineIds(idx);
    lineBlockPath = linePathFor(lineMap, lineId);
    targetCleanLabPath = "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_" + lineId + ".slx";
    targetCreated = false;
    targetLoadable = false;
    status = "not_started";
    note = "";

    if ~sourceFound
        status = "source_missing";
        note = "source wrapper not found";
    elseif sourceHasHandwired
        status = "source_not_clean";
        note = "source wrapper contains existing L01-L05 handwired breaker blocks";
    else
        try
            [targetFolder, ~, ~] = fileparts(targetCleanLabPath);
            if strlength(string(targetFolder)) > 0 && ~exist(targetFolder, "dir")
                mkdir(targetFolder);
            end
            copyfile(sourceWrapperPath, targetCleanLabPath, "f");
            targetCreated = isfile(targetCleanLabPath);
            if targetCreated
                load_system(targetCleanLabPath);
                [~, targetModelName, ~] = fileparts(targetCleanLabPath);
                callback = "Ts = 1/60; EnPSS = 1; addpath('C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/matlab/simulink_ieee39'); configure_ieee39_short_filegen_paths();";
                set_param(targetModelName, "PreLoadFcn", callback);
                set_param(targetModelName, "InitFcn", callback);
                targetLoadable = true;
                save_system(targetModelName);
                close_system(targetModelName, 0);
                status = "prepared";
                note = "per-line clean breaker lab copied from source wrapper; no breaker was inserted";
            end
        catch ME
            status = "prepare_failed";
            note = string(ME.message);
            try
                close_system(bdroot, 0);
            catch
            end
        end
    end

    rows(idx, :) = {
        char(lineId), char(lineBlockPath), char(targetCleanLabPath), logical(sourceFound), logical(targetCreated), ...
        logical(targetLoadable), logical(sourceHasHandwired), false, char(status), char(note) ...
    };
end

summaryTable = cell2table(rows, "VariableNames", { ...
    'line_id', 'line_block_path', 'target_clean_lab_path', 'source_found', ...
    'target_created', 'target_loadable', 'existing_handwired_breaker_found', ...
    'clean_lab_committed', 'status', 'note' ...
});
writetable(summaryTable, fullfile(outputDir, "ieee39_clean_breaker_lab_batch_prepare_summary.csv"));
writeJsonTable(summaryTable, fullfile(outputDir, "ieee39_clean_breaker_lab_batch_prepare_summary.json"));
fprintf("Wrote IEEE39 batch clean breaker lab prepare summary under: %s\n", outputDir);
end

function found = containsAnyHandwiredBreaker(modelName, lineIds)
found = false;
for lineId = string(lineIds)
    found = found || hasNamedBlock(modelName, lineId + "_HandwiredTimedBreaker");
end
end

function found = hasNamedBlock(modelName, blockName)
matches = find_system(modelName, "LookUnderMasks", "all", "FollowLinks", "on", "Name", char(blockName));
found = ~isempty(matches);
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
