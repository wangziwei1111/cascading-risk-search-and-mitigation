function summary = configure_ieee39_pilot_line_trip_case(wrapperModelPath, lineId, outputDir)
%CONFIGURE_IEEE39_PILOT_LINE_TRIP_CASE Record pilot line-trip implementation.
%
% If no timed breaker/switch block exists, the current fallback is static
% topology disable. It is runnable but not a timed breaker and not a
% training-ready dynamic label.

if nargin < 1 || isempty(wrapperModelPath)
    wrapperModelPath = "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper.slx";
end
if nargin < 2 || isempty(lineId)
    lineId = "L01";
end
if nargin < 3 || isempty(outputDir)
    outputDir = "../../results/gcn_search/ieee39_graphical_dynamic_model/wrapper";
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

mapPath = fullfile(outputDir, "ieee39_line_breaker_map.csv");
if ~isfile(mapPath)
    map_ieee39_lines_and_breakers(wrapperModelPath, outputDir);
end
lineMap = readtable(mapPath, "TextType", "string", "Delimiter", ",", "VariableNamingRule", "preserve");
match = lineMap(lineMap.line_id == string(lineId), :);
breakerPath = "";
if ~isempty(match)
    breakerPath = string(match.breaker_block_path(1));
end
hasTimedBreaker = ~isempty(match) && strlength(breakerPath) > 0 && breakerPath ~= "missing" && breakerPath ~= "NaN";

if hasTimedBreaker
    implementation = "existing_breaker_control";
    physical = true;
    trainingReady = true;
    implementationStatus = "existing_breaker_found";
    insertedSwitchPath = "";
    controlSignalPath = breakerPath;
    note = "Existing breaker path found; timed control still requires parameter verification.";
else
    [inserted, insertedSwitchPath, controlSignalPath, insertNote] = tryRecordTimedSwitchCandidate(wrapperModelPath, match);
    if inserted
        implementation = "timed_controlled_switch";
        physical = true;
        trainingReady = true;
        implementationStatus = "timed_switch_candidate_recorded";
        note = insertNote;
    else
        implementation = "static_topology_disable";
        physical = false;
        trainingReady = false;
        implementationStatus = "manual_required";
        insertedSwitchPath = "";
        controlSignalPath = "";
        note = "No compatible breaker path found; pilot disables line block before simulation. Not timed breaker control. " + insertNote;
    end
end

summary = struct();
summary.wrapper_model_path = char(wrapperModelPath);
summary.line_id = char(lineId);
summary.line_block_path = "";
if ~isempty(match)
    summary.line_block_path = char(string(match.line_block_path(1)));
end
summary.inserted_switch_block_path = char(insertedSwitchPath);
summary.control_signal_block_path = char(controlSignalPath);
summary.trip_time_s = 0.5;
summary.trip_implementation = implementation;
summary.physical_fault_or_breaker_action_executed = physical;
summary.training_ready_candidate = trainingReady;
summary.implementation_status = implementationStatus;
summary.note = note;

summaryCsv = table(string(lineId), string(summary.line_block_path), string(insertedSwitchPath), string(controlSignalPath), 0.5, ...
    string(implementation), physical, trainingReady, string(implementationStatus), string(note), ...
    'VariableNames', {'line_id', 'line_block_path', 'inserted_switch_block_path', 'control_signal_block_path', 'trip_time_s', ...
    'trip_implementation', 'physical_fault_or_breaker_action_executed', 'training_ready_candidate', 'implementation_status', 'note'});
writetable(summaryCsv, fullfile(outputDir, "ieee39_pilot_trip_implementation_summary.csv"));
fid = fopen(fullfile(outputDir, "ieee39_pilot_trip_implementation_summary.json"), "w");
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, "%s", jsonencode(summary, PrettyPrint=true));
fprintf("Wrote IEEE39 pilot trip implementation summary under: %s\n", outputDir);
end

function [inserted, insertedSwitchPath, controlSignalPath, note] = tryRecordTimedSwitchCandidate(wrapperModelPath, match)
inserted = false;
insertedSwitchPath = "";
controlSignalPath = "";
note = "Automatic timed switch insertion was not attempted because no line mapping was available.";
if isempty(match) || strlength(string(match.line_block_path(1))) == 0
    return;
end
lineBlockPath = string(match.line_block_path(1));
try
    load_system(wrapperModelPath);
    try
        load_system("ee_lib");
    catch
    end
    params = get_param(lineBlockPath, "DialogParameters");
    portHandles = get_param(lineBlockPath, "PortHandles");
    hasLinePorts = isfield(portHandles, "LConn") && isfield(portHandles, "RConn") && numel(portHandles.LConn) == 2 && numel(portHandles.RConn) == 2;
    hasTransmissionParams = isfield(params, "R") && isfield(params, "L") && isfield(params, "Cl");
    if hasLinePorts && hasTransmissionParams
        note = "Compatible line block was found, but automatic Simscape physical-port rewiring is intentionally conservative in this round. Manual breaker insertion is still required before treating the line trip as training-ready.";
    else
        note = "Line block is not compatible with the pilot automatic timed switch insertion check.";
    end
    [~, modelName, ~] = fileparts(wrapperModelPath);
    close_system(modelName, 0);
catch ME
    note = "Timed switch insertion check failed: " + string(ME.message);
    try
        [~, modelName, ~] = fileparts(wrapperModelPath);
        close_system(modelName, 0);
    catch
    end
end
end
