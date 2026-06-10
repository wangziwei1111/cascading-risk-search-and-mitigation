function run_dynamic_method_comparison_batch(basecasePath, casesRoot, outputRoot, optionsJsonPath, maxCases)
%RUN_DYNAMIC_METHOD_COMPARISON_BATCH Run learned/PIO/LODF Top-K dynamic batches.
%
% This is a simplified swing-equation preliminary diagnostic, not EMT and
% not an engineering-grade dynamic stability conclusion.

if nargin < 1 || isempty(basecasePath)
    basecasePath = "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json";
end
if nargin < 2 || isempty(casesRoot)
    casesRoot = "../../results/gcn_search/simulink_dynamic_method_comparison_cases";
end
if nargin < 3 || isempty(outputRoot)
    outputRoot = "../../results/gcn_search/simulink_dynamic_method_comparison_results";
end
if nargin < 4 || isempty(optionsJsonPath)
    optionsJsonPath = "../../results/gcn_search/simulink_dynamic_calibration/recommended_post_fault_options.json";
end
if nargin < 5 || isempty(maxCases)
    maxCases = 100;
end
if ~exist(outputRoot, "dir")
    mkdir(outputRoot);
end

options = struct();
if exist(optionsJsonPath, "file")
    options = jsondecode(fileread(optionsJsonPath));
end
groups = ["learned_mlp_top50", "learned_mlp_top100", "pio_gcn_top50", "pio_gcn_top100", "lodf_top50", "lodf_top100"];
for idx = 1:numel(groups)
    group = groups(idx);
    inputCsv = fullfile(casesRoot, group, "matlab_batch_input.csv");
    if ~exist(inputCsv, "file")
        fprintf("Skipping %s because matlab_batch_input.csv is missing.\n", group);
        continue;
    end
    batch = readtable(inputCsv, "TextType", "string");
    caseIds = unique(batch.case_id, "stable");
    keepIds = caseIds(1:min(maxCases, numel(caseIds)));
    limited = batch(ismember(batch.case_id, keepIds), :);
    outDir = fullfile(outputRoot, group);
    if ~exist(outDir, "dir")
        mkdir(outDir);
    end
    limitedCsv = fullfile(outDir, "matlab_batch_input.csv");
    writetable(limited, limitedCsv);
    run_rts79_dynamic_batch(basecasePath, limitedCsv, outDir, false, options);
end
end
