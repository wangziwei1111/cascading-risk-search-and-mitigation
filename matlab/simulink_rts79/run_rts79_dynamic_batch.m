function resultTable = run_rts79_dynamic_batch(basecasePath, matlabBatchInputCsv, outputDir, saveTrajectories)
%RUN_RTS79_DYNAMIC_BATCH Run simplified dynamic validation for exported cases.

if nargin < 1 || isempty(basecasePath)
    basecasePath = "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json";
end
if nargin < 2 || isempty(matlabBatchInputCsv)
    matlabBatchInputCsv = "../../results/gcn_search/simulink_dynamic_cases/matlab_batch_input.csv";
end
if nargin < 3 || isempty(outputDir)
    outputDir = "../../results/gcn_search/simulink_dynamic_results";
end
if nargin < 4 || isempty(saveTrajectories)
    saveTrajectories = false;
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

batch = readtable(matlabBatchInputCsv, "TextType", "string");
caseIds = unique(batch.case_id, "stable");
parts = cell(numel(caseIds), 1);
for idx = 1:numel(caseIds)
    parts{idx} = run_rts79_dynamic_path_case(basecasePath, matlabBatchInputCsv, caseIds(idx), outputDir, saveTrajectories);
end
resultTable = vertcat(parts{:});
outCsv = fullfile(outputDir, "simulink_dynamic_simulation_results.csv");
writetable(resultTable, outCsv);
fprintf("Wrote batch dynamic results: %s\n", outCsv);
end
