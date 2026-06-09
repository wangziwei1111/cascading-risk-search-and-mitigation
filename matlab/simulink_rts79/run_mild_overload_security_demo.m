function summary = run_mild_overload_security_demo(basecasePath, outputDir)
%RUN_MILD_OVERLOAD_SECURITY_DEMO Demonstrate security action without relay trip.

if nargin < 1 || isempty(basecasePath)
    basecasePath = "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json";
end
if nargin < 2 || isempty(outputDir)
    outputDir = "../../results/gcn_search/simulink_dynamic_mild_overload_demo";
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end
eventCsv = fullfile(outputDir, "mild_overload_events.csv");
events = table(strings(0, 1), zeros(0, 1), strings(0, 1), strings(0, 1), 20 * ones(0, 1), ...
    'VariableNames', ["case_id", "event_time", "event_type", "event_line", "simulation_end_time"]);
writetable(events, eventCsv);
options = struct();
options.line_loading_scale = 0.75;
options.relay_beta = 1.2;
options.loading_check_interval_s = 0.2;
options.max_event_rounds = 3;
[resultTable, ~, ~] = simulate_rts79_swing_case(basecasePath, eventCsv, "mild_overload", outputDir, false, options);
eventLog = readtable(fullfile(outputDir, "dynamic_case_event_log_mild_overload.csv"), "TextType", "string");
copyfile(fullfile(outputDir, "dynamic_case_result_mild_overload.csv"), fullfile(outputDir, "mild_overload_dynamic_results.csv"));
hasSecurity = any(eventLog.event_type == "security_redispatch_or_load_shed");
hasRelay = any(eventLog.event_type == "passive_relay_trip");
summary = struct();
summary.has_security_redispatch_or_load_shed = logical(hasSecurity);
summary.has_passive_relay_trip = logical(hasRelay);
summary.max_loading_ratio = double(resultTable.max_security_violation_loading_ratio(1));
summary.relay_beta = double(resultTable.relay_beta(1));
summary.dynamic_load_shed_mw = double(resultTable.dynamic_load_shed_mw(1));
summary.note = "Demo only; validates security action in 1.0 < loading_ratio <= beta.";
fid = fopen(fullfile(outputDir, "mild_overload_summary.json"), "w");
fprintf(fid, "%s", jsonencode(summary, "PrettyPrint", true));
fclose(fid);
end
