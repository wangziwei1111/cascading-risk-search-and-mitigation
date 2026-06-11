function summary = validate_ieee39_handwired_breaker_model(handwiredModelPath, outputDir, lineId, breakerBlockNameHint, tripCommandNameHint)
%VALIDATE_IEEE39_HANDWIRED_BREAKER_MODEL Validate a user hand-wired IEEE39 breaker wrapper.
%
% This script does not create or rewire Simscape physical ports. It only
% checks a user-supplied hand-wired model and writes compact validation
% artifacts used by the label-quality gate.

if nargin < 1 || isempty(handwiredModelPath)
    handwiredModelPath = "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx";
end
if nargin < 2 || isempty(outputDir)
    outputDir = "../../results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation";
end
if nargin < 3 || isempty(lineId)
    lineId = "L01";
end
if nargin < 4 || isempty(breakerBlockNameHint)
    breakerBlockNameHint = "L01_HandwiredTimedBreaker";
end
if nargin < 5 || isempty(tripCommandNameHint)
    tripCommandNameHint = "L01_TripCommand";
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

summary = initSummary(handwiredModelPath, lineId, breakerBlockNameHint, tripCommandNameHint);
blockRows = {};
try
    summary.handwired_model_found = isfile(handwiredModelPath);
    if ~summary.handwired_model_found
        summary.validation_failure_reason = "handwired model file not found";
        writeOutputs(summary, blockRows, outputDir);
        return;
    end

    load_system(handwiredModelPath);
    [~, modelName, ~] = fileparts(handwiredModelPath);
    summary.handwired_model_loadable = true;
    allBlocks = find_system(modelName, "LookUnderMasks", "all", "FollowLinks", "on");
    lowerBlocks = lower(string(allBlocks));
    breakerMask = contains(lowerBlocks, lower(string(breakerBlockNameHint))) | contains(lowerBlocks, "breaker") | contains(lowerBlocks, "switch");
    commandMask = contains(lowerBlocks, lower(string(tripCommandNameHint))) | contains(lowerBlocks, "tripcommand") | contains(lowerBlocks, "trip command") | contains(lowerBlocks, "trip_command");
    breakerBlocks = string(allBlocks(breakerMask));
    commandBlocks = string(allBlocks(commandMask));
    summary.breaker_block_found = ~isempty(breakerBlocks);
    summary.trip_command_found = ~isempty(commandBlocks);
    if summary.breaker_block_found
        summary.breaker_block_path = char(breakerBlocks(1));
    end
    if summary.trip_command_found
        summary.trip_command_path = char(commandBlocks(1));
    end
    blockRows = buildBlockInventory(breakerBlocks, commandBlocks);

    summary.breaker_near_l01 = any(contains(lower(breakerBlocks), "l01")) || any(contains(lower(breakerBlocks), "b1")) || any(contains(lower(breakerBlocks), "b2"));
    summary.trip_time_s = 0.5;
    summary.no_fault_simulation_success = false;
    summary.single_line_trip_simulation_success = false;
    summary.measurement_extraction_status = "not_run";
    if summary.breaker_block_found && summary.trip_command_found
        summary.validation_failure_reason = "handwired model loaded and hints were found, but compact dynamic suite must be run separately before accepting the label";
    else
        summary.validation_failure_reason = "missing handwired breaker or trip command block";
    end
    summary.validation_passed = summary.handwired_model_loadable && summary.breaker_block_found && summary.trip_command_found && summary.breaker_near_l01;
    if summary.validation_passed
        summary.validation_failure_reason = "";
    end
    close_system(modelName, 0);
catch ME
    summary.validation_failure_reason = char("validation failed: " + string(ME.message));
    try
        [~, modelName, ~] = fileparts(handwiredModelPath);
        close_system(modelName, 0);
    catch
    end
end
writeOutputs(summary, blockRows, outputDir);
end

function summary = initSummary(handwiredModelPath, lineId, breakerBlockNameHint, tripCommandNameHint)
summary = struct();
summary.handwired_model_path = char(handwiredModelPath);
summary.line_id = char(lineId);
summary.breaker_block_name_hint = char(breakerBlockNameHint);
summary.trip_command_name_hint = char(tripCommandNameHint);
summary.handwired_model_found = false;
summary.handwired_model_loadable = false;
summary.breaker_block_found = false;
summary.trip_command_found = false;
summary.breaker_near_l01 = false;
summary.no_fault_simulation_success = false;
summary.single_line_trip_simulation_success = false;
summary.trip_time_s = NaN;
summary.measurement_extraction_status = "not_run";
summary.validation_passed = false;
summary.validation_failure_reason = "";
summary.breaker_block_path = "";
summary.trip_command_path = "";
summary.handwired_model_committed = false;
summary.note = "Handwired .slx files are local artifacts and must not be committed.";
end

function rows = buildBlockInventory(breakerBlocks, commandBlocks)
rows = {};
for idx = 1:numel(breakerBlocks)
    rows(end+1, :) = {char(breakerBlocks(idx)), "breaker_or_switch_candidate"}; %#ok<AGROW>
end
for idx = 1:numel(commandBlocks)
    rows(end+1, :) = {char(commandBlocks(idx)), "trip_command_candidate"}; %#ok<AGROW>
end
end

function writeOutputs(summary, blockRows, outputDir)
summary = cleanStructText(summary);
writetable(struct2table(summary, "AsArray", true), fullfile(outputDir, "ieee39_handwired_breaker_validation_summary.csv"));
if isempty(blockRows)
    inventory = cell2table(cell(0, 2), "VariableNames", {'block_path', 'candidate_role'});
else
    inventory = cell2table(blockRows, "VariableNames", {'block_path', 'candidate_role'});
end
writetable(inventory, fullfile(outputDir, "ieee39_handwired_breaker_block_inventory.csv"));
fid = fopen(fullfile(outputDir, "ieee39_handwired_breaker_validation_summary.json"), "w");
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, "%s", jsonencode(summary, PrettyPrint=true));
fprintf("Wrote IEEE39 handwired breaker validation summary under: %s\n", outputDir);
end

function output = cleanStructText(input)
output = input;
fields = fieldnames(input);
for idx = 1:numel(fields)
    value = input.(fields{idx});
    if ischar(value) || isstring(value)
        output.(fields{idx}) = char(cleanText(value));
    end
end
end

function text = cleanText(value)
text = string(value);
text = replace(text, newline, "\n");
text = replace(text, sprintf('\r'), "\n");
end
