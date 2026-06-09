function summary = run_severe_overload_relay_demo(basecasePath, outputDir)
%RUN_SEVERE_OVERLOAD_RELAY_DEMO Demonstrate passive relay trip above beta.

if nargin < 1 || isempty(basecasePath)
    basecasePath = "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json";
end
if nargin < 2 || isempty(outputDir)
    outputDir = "../../results/gcn_search/simulink_dynamic_severe_overload_demo";
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end
eventCsv = fullfile(outputDir, "severe_overload_events.csv");
events = table("severe_overload", 1.0, "trip_first_line", "L10", 20.0, ...
    'VariableNames', ["case_id", "event_time", "event_type", "event_line", "simulation_end_time"]);
events = [events; table("severe_overload", 5.0, "trip_second_line", "L05", 20.0, ...
    'VariableNames', ["case_id", "event_time", "event_type", "event_line", "simulation_end_time"])];
writetable(events, eventCsv);
options = struct();
options.relay_beta = 1.2;
[resultTable, ~, ~] = simulate_rts79_swing_case(basecasePath, eventCsv, "severe_overload", outputDir, false, options);
copyfile(fullfile(outputDir, "dynamic_case_result_severe_overload.csv"), fullfile(outputDir, "severe_overload_dynamic_results.csv"));
summary = struct();
summary.has_passive_relay_trip = double(resultTable.passive_relay_trip_count(1)) >= 1;
summary.max_relay_violation_loading_ratio = double(resultTable.max_relay_violation_loading_ratio(1));
summary.relay_beta = double(resultTable.relay_beta(1));
summary.passive_relay_trip_count = double(resultTable.passive_relay_trip_count(1));
summary.note = "Demo only; validates passive relay trip when loading_ratio > beta.";
fid = fopen(fullfile(outputDir, "severe_overload_summary.json"), "w");
fprintf(fid, "%s", jsonencode(summary, "PrettyPrint", true));
fclose(fid);
end
