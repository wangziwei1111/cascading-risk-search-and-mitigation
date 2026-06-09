function gridTable = calibrate_rts79_swing_scales(basecasePath, matlabBatchInputCsv, outputDir)
%CALIBRATE_RTS79_SWING_SCALES Grid-search prototype scale parameters.

if nargin < 1 || isempty(basecasePath)
    basecasePath = "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json";
end
if nargin < 2 || isempty(matlabBatchInputCsv)
    matlabBatchInputCsv = "../../results/gcn_search/simulink_dynamic_cases/matlab_batch_input.csv";
end
if nargin < 3 || isempty(outputDir)
    outputDir = "../../results/gcn_search/simulink_dynamic_calibration";
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

couplingValues = [0.2, 0.5, 1.0, 2.0];
dampingValues = [0.5, 1.0, 2.0];
inertiaValues = [0.5, 1.0, 2.0];
loadingValues = [0.5, 1.0, 2.0];
rows = {};
rowIdx = 0;
batch = readtable(matlabBatchInputCsv, "TextType", "string");
demoCaseIds = unique(batch.case_id, "stable");
demoCaseIds = demoCaseIds(1:min(2, numel(demoCaseIds)));
for c = couplingValues
    for d = dampingValues
        for h = inertiaValues
            for l = loadingValues
                options = struct("coupling_scale", c, "damping_scale", d, "inertia_scale", h, "line_loading_scale", l);
                sanity = check_rts79_swing_model_sanity(basecasePath, outputDir, options);
                demoUnstable = 0;
                demoMaxLoading = 0;
                for idx = 1:numel(demoCaseIds)
                    tmpDir = fullfile(outputDir, "calibration_tmp");
                    result = run_rts79_dynamic_path_case(basecasePath, matlabBatchInputCsv, demoCaseIds(idx), tmpDir, false, options);
                    demoUnstable = demoUnstable + double(result.dynamic_unstable(1));
                    demoMaxLoading = max(demoMaxLoading, double(result.max_line_loading_ratio(1)));
                end
                freqDev = max(abs(double(sanity.frequency_nadir_hz(1)) - 50.0), abs(double(sanity.frequency_zenith_hz(1)) - 50.0));
                sanityPass = freqDev <= 0.25 && double(sanity.max_rotor_angle_separation_deg(1)) <= 45.0;
                score = freqDev + 0.001 * double(sanity.max_rotor_angle_separation_deg(1)) + 0.1 * abs(demoUnstable - 1);
                rowIdx = rowIdx + 1;
                rows(rowIdx, :) = {c, d, h, l, freqDev, double(sanity.max_rotor_angle_separation_deg(1)), ...
                    demoUnstable, demoMaxLoading, sanityPass, score}; %#ok<AGROW>
            end
        end
    end
end
gridTable = cell2table(rows, "VariableNames", ["coupling_scale", "damping_scale", "inertia_scale", "line_loading_scale", ...
    "no_disturbance_frequency_max_deviation_hz", "no_disturbance_max_rotor_angle_deg", ...
    "demo_unstable_count", "demo_max_line_loading_ratio", "sanity_pass", "selection_score"]);
gridTable = sortrows(gridTable, "selection_score");
writetable(gridTable, fullfile(outputDir, "swing_scale_grid.csv"));
recommended = table2struct(gridTable(1, ["coupling_scale", "damping_scale", "inertia_scale", "line_loading_scale"]));
recommended.frequency_unstable_threshold_hz = 49.0;
recommended.rotor_angle_unstable_threshold_deg = 180.0;
recommended.line_loading_unstable_threshold = 1.5;
fid = fopen(fullfile(outputDir, "recommended_swing_options.json"), "w");
fprintf(fid, "%s", jsonencode(recommended, "PrettyPrint", true));
fclose(fid);
fprintf("Wrote calibration grid and recommended options under %s\n", outputDir);
end

