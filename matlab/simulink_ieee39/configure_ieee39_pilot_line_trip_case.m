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
    note = "Existing breaker path found; timed control still requires parameter verification.";
else
    implementation = "static_topology_disable";
    physical = false;
    trainingReady = false;
    note = "No breaker path found; pilot disables line block before simulation. Not timed breaker control.";
end

summary = struct();
summary.wrapper_model_path = char(wrapperModelPath);
summary.line_id = char(lineId);
summary.trip_implementation = implementation;
summary.physical_fault_or_breaker_action_executed = physical;
summary.training_ready_candidate = trainingReady;
summary.note = note;

summaryCsv = table(string(lineId), string(implementation), physical, trainingReady, string(note), ...
    'VariableNames', {'line_id', 'trip_implementation', 'physical_fault_or_breaker_action_executed', 'training_ready_candidate', 'note'});
writetable(summaryCsv, fullfile(outputDir, "ieee39_pilot_trip_implementation_summary.csv"));
fid = fopen(fullfile(outputDir, "ieee39_pilot_trip_implementation_summary.json"), "w");
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, "%s", jsonencode(summary, PrettyPrint=true));
fprintf("Wrote IEEE39 pilot trip implementation summary under: %s\n", outputDir);
end
