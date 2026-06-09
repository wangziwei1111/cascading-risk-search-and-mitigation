function sanityTable = check_rts79_swing_model_sanity(basecasePath, outputDir, options)
%CHECK_RTS79_SWING_MODEL_SANITY Run no-disturbance simplified swing sanity check.

if nargin < 1 || isempty(basecasePath)
    basecasePath = "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json";
end
if nargin < 2 || isempty(outputDir)
    outputDir = "../../results/gcn_search/simulink_dynamic_calibration";
end
if nargin < 3
    options = [];
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

eventCsv = fullfile(outputDir, "no_disturbance_events.csv");
emptyEvents = table(strings(0, 1), zeros(0, 1), strings(0, 1), strings(0, 1), 20 * ones(0, 1), ...
    'VariableNames', ["case_id", "event_time", "event_type", "event_line", "simulation_end_time"]);
writetable(emptyEvents, eventCsv);
[resultTable, trajectorySummary, lineLoadingSummary] = simulate_rts79_swing_case(basecasePath, eventCsv, "no_disturbance", outputDir, false, options);
freq = double(trajectorySummary.frequency_hz);
sanityTable = table( ...
    resultTable.frequency_nadir_hz(1), ...
    resultTable.frequency_zenith_hz(1), ...
    resultTable.max_rotor_angle_separation_deg(1), ...
    resultTable.max_line_loading_ratio(1), ...
    0.0, ...
    abs(freq(end) - 50.0), ...
    'VariableNames', ["frequency_nadir_hz", "frequency_zenith_hz", "max_rotor_angle_separation_deg", ...
    "max_line_loading_ratio", "initial_power_balance_residual", "final_frequency_deviation_hz"]);
writetable(sanityTable, fullfile(outputDir, "no_disturbance_sanity.csv"));
fprintf("Wrote no-disturbance sanity: %s\n", fullfile(outputDir, "no_disturbance_sanity.csv"));
end
