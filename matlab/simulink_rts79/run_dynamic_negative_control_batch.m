function run_dynamic_negative_control_batch(basecasePath, controlCasesRootDir, outputRootDir, optionsJsonPath, maxCases)
%RUN_DYNAMIC_NEGATIVE_CONTROL_BATCH Run event-driven dynamic validation for control groups.

if nargin < 1 || isempty(basecasePath)
    basecasePath = "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json";
end
if nargin < 2 || isempty(controlCasesRootDir)
    controlCasesRootDir = "../../results/gcn_search/simulink_dynamic_negative_controls/cases";
end
if nargin < 3 || isempty(outputRootDir)
    outputRootDir = "../../results/gcn_search/simulink_dynamic_negative_controls/results";
end
if nargin < 4
    optionsJsonPath = "";
end
if nargin < 5 || isempty(maxCases)
    maxCases = 20;
end
if strlength(string(optionsJsonPath)) > 0 && exist(optionsJsonPath, "file")
    options = jsondecode(fileread(optionsJsonPath));
else
    options = struct();
end
groups = ["learned_top20", "low_score_top20", "random_top20", "line_order_top20"];
for idx = 1:numel(groups)
    group = groups(idx);
    batchPath = fullfile(controlCasesRootDir, group, "matlab_batch_input.csv");
    if ~exist(batchPath, "file")
        warning("Missing batch input for group %s: %s", group, batchPath);
        continue;
    end
    batch = readtable(batchPath, "TextType", "string");
    caseIds = unique(batch.case_id, "stable");
    keepIds = caseIds(1:min(maxCases, numel(caseIds)));
    batch = batch(ismember(batch.case_id, keepIds), :);
    groupOutput = fullfile(outputRootDir, group);
    if ~exist(groupOutput, "dir")
        mkdir(groupOutput);
    end
    limitedBatchPath = fullfile(groupOutput, "matlab_batch_input.csv");
    writetable(batch, limitedBatchPath);
    run_rts79_dynamic_batch(basecasePath, limitedBatchPath, groupOutput, false, options);
end
end
