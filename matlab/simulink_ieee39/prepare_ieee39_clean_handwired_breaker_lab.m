function summary = prepare_ieee39_clean_handwired_breaker_lab(sourceWrapperPath, targetCleanLabPath, outputDir)
%PREPARE_IEEE39_CLEAN_HANDWIRED_BREAKER_LAB Copy a clean IEEE39 wrapper.
%
% This helper creates a local clean lab model for manual breaker wiring. It
% does not insert breakers, does not reconnect Simscape physical ports, and
% does not modify the source wrapper.

if nargin < 1 || isempty(sourceWrapperPath)
    sourceWrapperPath = "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper.slx";
end
if nargin < 2 || isempty(targetCleanLabPath)
    targetCleanLabPath = "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab.slx";
end
if nargin < 3 || isempty(outputDir)
    outputDir = "../../results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation";
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

configure_ieee39_short_filegen_paths();

sourceFound = isfile(sourceWrapperPath);
targetCreated = false;
targetLoadable = false;
note = "";
containsL01 = false;
containsL02 = false;
containsL03 = false;
containsL04 = false;

try
    if ~sourceFound
        note = "source wrapper not found";
    else
        [targetFolder, ~, ~] = fileparts(targetCleanLabPath);
        if strlength(string(targetFolder)) > 0 && ~exist(targetFolder, "dir")
            mkdir(targetFolder);
        end

        load_system(sourceWrapperPath);
        sourceModelName = bdroot;
        sourceContains = containsAnyHandwiredBreaker(sourceModelName);
        close_system(sourceModelName, 0);
        if sourceContains
            note = "source wrapper is not clean; existing L01-L04 handwired breaker blocks were found";
        else
            copyfile(sourceWrapperPath, targetCleanLabPath, "f");
            targetCreated = isfile(targetCleanLabPath);
            if targetCreated
                load_system(targetCleanLabPath);
                [~, targetModelName, ~] = fileparts(targetCleanLabPath);
                targetLoadable = true;
                containsL01 = hasNamedBlock(targetModelName, "L01_HandwiredTimedBreaker");
                containsL02 = hasNamedBlock(targetModelName, "L02_HandwiredTimedBreaker");
                containsL03 = hasNamedBlock(targetModelName, "L03_HandwiredTimedBreaker");
                containsL04 = hasNamedBlock(targetModelName, "L04_HandwiredTimedBreaker");
                callback = "Ts = 1/60; EnPSS = 1; addpath('C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/matlab/simulink_ieee39'); configure_ieee39_short_filegen_paths();";
                set_param(targetModelName, "PreLoadFcn", callback);
                set_param(targetModelName, "InitFcn", callback);
                save_system(targetModelName);
                close_system(targetModelName, 0);
                note = "clean breaker lab copied from source wrapper; no breaker was inserted";
            end
        end
    end
catch ME
    note = "prepare failed: " + string(ME.message);
    try
        close_system(bdroot, 0);
    catch
    end
end

summary = struct();
summary.source_wrapper_path = char(sourceWrapperPath);
summary.target_clean_lab_path = char(targetCleanLabPath);
summary.source_found = logical(sourceFound);
summary.target_created = logical(targetCreated);
summary.target_loadable = logical(targetLoadable);
summary.contains_existing_L01_HandwiredTimedBreaker = logical(containsL01);
summary.contains_existing_L02_HandwiredTimedBreaker = logical(containsL02);
summary.contains_existing_L03_HandwiredTimedBreaker = logical(containsL03);
summary.contains_existing_L04_HandwiredTimedBreaker = logical(containsL04);
summary.clean_lab_committed = false;
summary.note = char(note);

writeJson(summary, fullfile(outputDir, "ieee39_clean_breaker_lab_prepare_summary.json"));
fprintf("Wrote IEEE39 clean breaker lab prepare summary under: %s\n", outputDir);
end

function found = containsAnyHandwiredBreaker(modelName)
found = false;
for lineId = ["L01", "L02", "L03", "L04"]
    found = found || hasNamedBlock(modelName, lineId + "_HandwiredTimedBreaker");
end
end

function found = hasNamedBlock(modelName, blockName)
matches = find_system(modelName, "LookUnderMasks", "all", "FollowLinks", "on", "Name", char(blockName));
found = ~isempty(matches);
end

function writeJson(value, path)
fid = fopen(path, "w");
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, "%s", jsonencode(value, PrettyPrint=true));
end
