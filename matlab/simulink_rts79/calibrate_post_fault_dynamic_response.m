function gridTable = calibrate_post_fault_dynamic_response(basecasePath, inputRoot, outputDir, maxGridRows)
%CALIBRATE_POST_FAULT_DYNAMIC_RESPONSE Small post-fault sanity ladder grid.
%
% This searches for parameters that pass sanity controls, not parameters that
% make learned precision look good.

if nargin < 1 || isempty(basecasePath)
    basecasePath = "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json";
end
if nargin < 2 || isempty(inputRoot)
    inputRoot = "../../results/gcn_search/simulink_dynamic_negative_controls/inputs";
end
if nargin < 3 || isempty(outputDir)
    outputDir = "../../results/gcn_search/simulink_dynamic_calibration";
end
if nargin < 4 || isempty(maxGridRows)
    maxGridRows = 4;
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

dampingScales = [2, 5, 10];
inertiaScales = [2, 5];
couplingScales = [0.2, 0.5];
lineLoadingScales = [0.002, 0.005];
relayBetas = [1.5, 2.0];
loadShedSteps = [0.01, 0.02];
pmModes = ["rebalance_to_current_pe", "subtract_load_shed_by_gen_weight", "keep_total_mechanical_power"];

rows = {};
rowIdx = 0;
gridIdx = 0;
bestScore = -Inf;
bestOptions = struct();
for damping = dampingScales
    for inertia = inertiaScales
        for coupling = couplingScales
            for lineScale = lineLoadingScales
                for beta = relayBetas
                    for shedStep = loadShedSteps
                        for pmMode = pmModes
                            gridIdx = gridIdx + 1;
                            if gridIdx > maxGridRows
                                continue;
                            end
                            options = struct("damping_scale", damping, "inertia_scale", inertia, ...
                                "coupling_scale", coupling, "line_loading_scale", lineScale, ...
                                "relay_beta", beta, "load_shed_step_fraction", shedStep, ...
                                "pm_update_mode", pmMode, "simulation_end_time", 10.0, ...
                                "enable_passive_relay_trips", true, "enable_security_redispatch_approx", true);
                            optionsPath = fullfile(outputDir, sprintf("post_fault_grid_options_%03d.json", gridIdx));
                            fid = fopen(optionsPath, "w");
                            fprintf(fid, "%s", jsonencode(options, "PrettyPrint", true));
                            fclose(fid);
                            runDir = fullfile(outputDir, sprintf("post_fault_grid_%03d", gridIdx));
                            summary = run_post_fault_sanity_ladder(basecasePath, inputRoot, runDir, optionsPath);
                            metrics = metricsFromSummaryLocal(summary);
                            score = sanityScoreLocal(metrics);
                            if score > bestScore
                                bestScore = score;
                                bestOptions = options;
                            end
                            rowIdx = rowIdx + 1;
                            rows(rowIdx, :) = {damping, inertia, coupling, lineScale, beta, shedStep, pmMode, ...
                                metrics.no_trip_stable, metrics.single_mild_trip_stable, metrics.low_risk_unstable_fraction, ...
                                metrics.random_unstable_fraction, metrics.learned_unstable_fraction, metrics.mean_frequency_nadir_hz, ...
                                metrics.mean_coi_angle_deg, metrics.passive_trip_fraction, metrics.security_action_fraction, score, false}; %#ok<AGROW>
                        end
                    end
                end
            end
        end
    end
end

gridTable = cell2table(rows, "VariableNames", ["damping_scale", "inertia_scale", "coupling_scale", "line_loading_scale", ...
    "relay_beta", "load_shed_step_fraction", "pm_update_mode", "no_trip_stable", "single_mild_trip_stable", ...
    "low_risk_unstable_fraction", "random_unstable_fraction", "learned_unstable_fraction", "mean_frequency_nadir_hz", ...
    "mean_coi_angle_separation_deg", "passive_trip_fraction", "security_action_fraction", "sanity_ladder_score", "recommended"]);
if height(gridTable) > 0
    [~, bestIdx] = max(double(gridTable.sanity_ladder_score));
    gridTable.recommended(bestIdx) = true;
end
writetable(gridTable, fullfile(outputDir, "post_fault_calibration_grid.csv"));
fid = fopen(fullfile(outputDir, "recommended_post_fault_options.json"), "w");
fprintf(fid, "%s", jsonencode(bestOptions, "PrettyPrint", true));
fclose(fid);
summaryPayload = struct("num_grid_rows", height(gridTable), "max_grid_rows", maxGridRows, ...
    "recommended_post_fault_options", bestOptions, ...
    "warning", "Small post-fault sanity grid; not a formal dynamic validation conclusion.");
fid = fopen(fullfile(outputDir, "post_fault_calibration_summary.json"), "w");
fprintf(fid, "%s", jsonencode(summaryPayload, "PrettyPrint", true));
fclose(fid);
end

function metrics = metricsFromSummaryLocal(summary)
metrics = struct();
metrics.no_trip_stable = getGroupMetricLocal(summary, "no_trip", "unstable_fraction") == 0;
metrics.single_mild_trip_stable = getGroupMetricLocal(summary, "single_mild_trip", "unstable_fraction") == 0;
metrics.low_risk_unstable_fraction = getGroupMetricLocal(summary, "low_risk_ordered_n2", "unstable_fraction");
metrics.random_unstable_fraction = getGroupMetricLocal(summary, "random_ordered_n2", "unstable_fraction");
metrics.learned_unstable_fraction = getGroupMetricLocal(summary, "learned_high_risk_n2", "unstable_fraction");
metrics.mean_frequency_nadir_hz = mean(double(summary.mean_frequency_nadir_hz));
metrics.mean_coi_angle_deg = mean(double(summary.mean_rotor_angle_separation_coi_deg));
metrics.passive_trip_fraction = mean(double(summary.passive_trip_fraction));
metrics.security_action_fraction = mean(double(summary.security_action_fraction));
end

function value = getGroupMetricLocal(summary, groupName, metricName)
idx = find(string(summary.case_group) == string(groupName), 1);
if isempty(idx)
    value = 1.0;
else
    value = double(summary.(metricName)(idx));
end
end

function score = sanityScoreLocal(metrics)
score = 0.0;
if metrics.no_trip_stable
    score = score + 2.0;
end
if metrics.single_mild_trip_stable
    score = score + 1.0;
end
score = score + max(0.0, 1.0 - metrics.low_risk_unstable_fraction);
score = score + max(0.0, 1.0 - metrics.random_unstable_fraction);
score = score - 0.25 * metrics.passive_trip_fraction;
if metrics.low_risk_unstable_fraction == 0 && metrics.random_unstable_fraction == 0 && metrics.learned_unstable_fraction == 0
    score = score - 0.5;
end
end
