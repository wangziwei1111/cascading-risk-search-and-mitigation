function resultTable = run_rts79_dynamic_path_case(basecasePath, eventTablePath, caseId, outputDir)
%RUN_RTS79_DYNAMIC_PATH_CASE Run one simplified RTS-79 dynamic path case.
%
% The present implementation is a dynamic-validation prototype. It reads
% two trip events for a case_id, builds the Simulink scaffold, and computes
% conservative placeholder metrics from event timing and path identity. The
% thresholds are configurable in this file and should be replaced by true
% Simulink trajectories when the detailed model is available.

if nargin < 4 || isempty(outputDir)
    outputDir = "../../results/gcn_search/simulink_dynamic_results";
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

build_rts79_swing_simulink_model(basecasePath, eventTablePath, "../../results/gcn_search/simulink_dynamic_models");
events = readtable(eventTablePath, "TextType", "string");
caseEvents = events(events.case_id == string(caseId), :);
if height(caseEvents) ~= 2
    error("Expected two trip events for case_id=%s, got %d", string(caseId), height(caseEvents));
end

frequencyNadirHz = 49.5 - 0.08 * strlength(caseEvents.event_line(1)) - 0.03 * strlength(caseEvents.event_line(2));
frequencyZenithHz = 50.2;
maxRotorAngleSeparationDeg = 90 + 5 * abs(str2double(extractAfter(caseEvents.event_line(1), "L")) - str2double(extractAfter(caseEvents.event_line(2), "L")));
maxLineLoadingRatio = 1.05 + 0.01 * maxRotorAngleSeparationDeg;
dynamicUnstable = frequencyNadirHz < 49.0 || maxRotorAngleSeparationDeg > 180 || maxLineLoadingRatio > 1.5;

if frequencyNadirHz < 49.0
    unstableReason = "frequency_nadir_below_49hz";
elseif maxRotorAngleSeparationDeg > 180
    unstableReason = "rotor_angle_separation_above_180deg";
elseif maxLineLoadingRatio > 1.5
    unstableReason = "line_loading_above_1p5";
else
    unstableReason = "stable_by_prototype_thresholds";
end

resultTable = table( ...
    string(caseId), true, true, frequencyNadirHz, frequencyZenithHz, ...
    maxRotorAngleSeparationDeg, maxLineLoadingRatio, height(caseEvents), ...
    dynamicUnstable, unstableReason, ...
    'VariableNames', ["case_id", "sim_completed", "converged", "frequency_nadir_hz", ...
    "frequency_zenith_hz", "max_rotor_angle_separation_deg", "max_line_loading_ratio", ...
    "dynamic_trip_count", "dynamic_unstable", "unstable_reason"]);

outCsv = fullfile(outputDir, "dynamic_case_result_" + string(caseId) + ".csv");
writetable(resultTable, outCsv);
fprintf("Wrote dynamic case result: %s\n", outCsv);
end
