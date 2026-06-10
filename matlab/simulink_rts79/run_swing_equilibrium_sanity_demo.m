function summary = run_swing_equilibrium_sanity_demo(basecasePath, outputDir)
%RUN_SWING_EQUILIBRIUM_SANITY_DEMO Run no-trip and low-risk swing sanity cases.
%
% These cases are a prototype sanity check only. They are not EMT, not a full
% OPF redispatch validation, and not an engineering-grade dynamic stability
% conclusion.

if nargin < 1 || isempty(basecasePath)
    basecasePath = "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json";
end
if nargin < 2 || isempty(outputDir)
    outputDir = "../../results/gcn_search/simulink_dynamic_equilibrium_sanity";
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

options = loadRecommendedOptionsLocal();
options.enable_passive_relay_trips = false;
options.enable_security_redispatch_approx = false;
options.simulation_end_time = 10.0;
options.pm_update_mode = "rebalance_to_current_pe";

noTripEvents = table(string.empty(0, 1), zeros(0, 1), string.empty(0, 1), zeros(0, 1), ...
    'VariableNames', ["case_id", "event_time", "event_line", "simulation_end_time"]);
noTripPath = fullfile(outputDir, "no_trip_events.csv");
writetable(noTripEvents, noTripPath);
[noTripResult, ~, ~] = simulate_rts79_swing_case(basecasePath, noTripPath, "no_trip", outputDir, false, options);
writetable(noTripResult, fullfile(outputDir, "no_trip_result.csv"));

singleEvents = table("single_mild_trip", 1.0, "L01", 10.0, ...
    'VariableNames', ["case_id", "event_time", "event_line", "simulation_end_time"]);
singlePath = fullfile(outputDir, "single_mild_trip_events.csv");
writetable(singleEvents, singlePath);
[singleResult, ~, ~] = simulate_rts79_swing_case(basecasePath, singlePath, "single_mild_trip", outputDir, false, options);
writetable(singleResult, fullfile(outputDir, "single_mild_trip_result.csv"));

[firstLine, secondLine] = lowRiskLinesLocal();
lowRiskEvents = table(["low_risk_ordered_n2"; "low_risk_ordered_n2"], [1.0; 3.0], [firstLine; secondLine], [10.0; 10.0], ...
    'VariableNames', ["case_id", "event_time", "event_line", "simulation_end_time"]);
lowRiskPath = fullfile(outputDir, "low_risk_ordered_n2_events.csv");
writetable(lowRiskEvents, lowRiskPath);
[lowRiskResult, ~, ~] = simulate_rts79_swing_case(basecasePath, lowRiskPath, "low_risk_ordered_n2", outputDir, false, options);
writetable(lowRiskResult, fullfile(outputDir, "low_risk_n2_result.csv"));

noTripUnstable = logical(noTripResult.dynamic_unstable(1));
singleUnstable = logical(singleResult.dynamic_unstable(1));
lowRiskUnstable = logical(lowRiskResult.dynamic_unstable(1));
noTripNadir = double(noTripResult.frequency_nadir_hz(1));
noTripAngle = double(noTripResult.max_rotor_angle_separation_coi_deg(1));
sanityPassed = ~noTripUnstable && noTripNadir >= 49.8 && noTripAngle <= 60.0;

summary = struct();
summary.no_trip_dynamic_unstable = noTripUnstable;
summary.no_trip_frequency_nadir_hz = noTripNadir;
summary.no_trip_frequency_zenith_hz = double(noTripResult.frequency_zenith_hz(1));
summary.no_trip_final_mean_frequency_hz = double(noTripResult.final_mean_frequency_hz(1));
summary.no_trip_max_rotor_angle_separation_deg = double(noTripResult.max_rotor_angle_separation_deg(1));
summary.no_trip_max_rotor_angle_separation_coi_deg = noTripAngle;
summary.pre_event_frequency_drift_hz_per_s = double(noTripResult.frequency_drift_hz_per_s(1));
summary.initial_pm_pe_residual_norm = double(noTripResult.initial_pm_pe_residual_norm(1));
summary.initial_pm_pe_max_abs_residual = double(noTripResult.initial_pm_pe_max_abs_residual(1));
summary.mean_pm = double(noTripResult.mean_pm(1));
summary.mean_pe = double(noTripResult.mean_pe(1));
summary.total_load_mw = double(noTripResult.total_load_mw(1));
summary.total_generation_mw = double(noTripResult.total_generation_mw(1));
summary.single_mild_trip_dynamic_unstable = singleUnstable;
summary.low_risk_n2_dynamic_unstable = lowRiskUnstable;
summary.sanity_passed = sanityPassed;
summary.dynamic_model_equilibrium_failed = ~sanityPassed;
summary.note = "No-trip sanity must pass before interpreting Top-K dynamic precision.";

fid = fopen(fullfile(outputDir, "swing_equilibrium_sanity_summary.json"), "w");
fprintf(fid, "%s", jsonencode(summary, "PrettyPrint", true));
fclose(fid);
end

function options = loadRecommendedOptionsLocal()
optionsPath = "../../results/gcn_search/simulink_dynamic_calibration/recommended_event_driven_options.json";
if exist(optionsPath, "file")
    options = jsondecode(fileread(optionsPath));
else
    options = struct();
    options.line_loading_scale = 0.005;
    options.coupling_scale = 0.5;
    options.damping_scale = 1.0;
    options.inertia_scale = 1.0;
    options.relay_beta = 1.2;
end
end

function [firstLine, secondLine] = lowRiskLinesLocal()
inputPath = "../../results/gcn_search/simulink_dynamic_negative_controls/inputs/low_score_top20_input_paths.csv";
firstLine = "L01";
secondLine = "L02";
if ~exist(inputPath, "file")
    return;
end
tableIn = readtable(inputPath, "TextType", "string");
if height(tableIn) < 1 || ~ismember("path", tableIn.Properties.VariableNames)
    return;
end
parts = split(string(tableIn.path(1)), "->");
if numel(parts) >= 2
    firstLine = strtrim(parts(1));
    secondLine = strtrim(parts(2));
end
end
