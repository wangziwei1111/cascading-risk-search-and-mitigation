function resultTable = calibrate_event_driven_dynamic_scales(basecasePath, matlabBatchInputCsv, outputDir, maxGridRows)
%CALIBRATE_EVENT_DRIVEN_DYNAMIC_SCALES Small event-driven scale calibration grid.

if nargin < 1 || isempty(basecasePath)
    basecasePath = "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json";
end
if nargin < 2 || isempty(matlabBatchInputCsv)
    matlabBatchInputCsv = "../../results/gcn_search/simulink_dynamic_real_pipeline/dynamic_cases/matlab_batch_input.csv";
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

batch = readtable(matlabBatchInputCsv, "TextType", "string");
caseIds = unique(batch.case_id, "stable");
caseIds = caseIds(1:min(5, numel(caseIds)));
calibBatch = batch(ismember(batch.case_id, caseIds), :);
calibBatchPath = fullfile(outputDir, "event_driven_calibration_batch_input.csv");
writetable(calibBatch, calibBatchPath);

lineLoadingScales = [0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0];
couplingScales = [0.5, 1.0, 2.0];
dampingScales = [1.0, 2.0];
inertiaScales = [1.0, 2.0];
relayBetas = [1.2, 1.5];

rows = {};
rowIdx = 0;
gridCount = 0;
bestScore = -Inf;
bestOptions = struct();
for lineScale = lineLoadingScales
    for couplingScale = couplingScales
        for dampingScale = dampingScales
            for inertiaScale = inertiaScales
                for relayBeta = relayBetas
                    gridCount = gridCount + 1;
                    if gridCount > maxGridRows
                        continue;
                    end
                    options = struct();
                    options.line_loading_scale = lineScale;
                    options.coupling_scale = couplingScale;
                    options.damping_scale = dampingScale;
                    options.inertia_scale = inertiaScale;
                    options.relay_beta = relayBeta;
                    options.enable_passive_relay_trips = true;
                    runDir = fullfile(outputDir, sprintf("event_grid_%03d", gridCount));
                    results = run_rts79_dynamic_batch(basecasePath, calibBatchPath, runDir, false, options);
                    numCases = height(results);
                    precision = mean(logical(results.dynamic_unstable));
                    passiveFraction = mean(double(results.passive_relay_trip_count) > 0);
                    securityFraction = mean(double(results.security_redispatch_count) > 0);
                    meanNadir = mean(double(results.frequency_nadir_hz), "omitnan");
                    maxLoading = max(double(results.max_line_loading_ratio));
                    nondegenerateScore = 1.0 - abs(precision - 0.5) - 0.5 * passiveFraction + 0.25 * securityFraction;
                    if precision == 0 || precision == 1
                        nondegenerateScore = nondegenerateScore - 0.5;
                    end
                    if passiveFraction == 1
                        nondegenerateScore = nondegenerateScore - 0.5;
                    end
                    if nondegenerateScore > bestScore
                        bestScore = nondegenerateScore;
                        bestOptions = options;
                    end
                    rowIdx = rowIdx + 1;
                    rows(rowIdx, :) = {lineScale, couplingScale, dampingScale, inertiaScale, relayBeta, numCases, precision, passiveFraction, securityFraction, meanNadir, maxLoading, nondegenerateScore, false}; %#ok<AGROW>
                end
            end
        end
    end
end

resultTable = cell2table(rows, "VariableNames", ["line_loading_scale", "coupling_scale", "damping_scale", "inertia_scale", "relay_beta", "num_cases", "dynamic_precision", "passive_relay_trip_fraction", "security_redispatch_fraction", "mean_frequency_nadir_hz", "max_line_loading_ratio", "nondegenerate_score", "recommended"]);
if height(resultTable) > 0
    [~, bestIdx] = max(double(resultTable.nondegenerate_score));
    resultTable.recommended(bestIdx) = true;
end
writetable(resultTable, fullfile(outputDir, "event_driven_scale_grid.csv"));
fid = fopen(fullfile(outputDir, "recommended_event_driven_options.json"), "w");
fprintf(fid, "%s", jsonencode(bestOptions, "PrettyPrint", true));
fclose(fid);
summary = struct("num_grid_rows", height(resultTable), "max_grid_rows", maxGridRows, ...
    "recommended_event_driven_options", bestOptions, ...
    "warning", "Small calibration grid for preliminary smoke only; not an engineering-grade parameter identification.");
fid = fopen(fullfile(outputDir, "event_driven_calibration_summary.json"), "w");
fprintf(fid, "%s", jsonencode(summary, "PrettyPrint", true));
fclose(fid);
end
