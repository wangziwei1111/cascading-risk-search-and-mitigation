function resultTable = run_real_topk_event_driven_dynamic_validation(basecasePath, matlabBatchInputCsv, outputDir, optionsJsonPath, saveTrajectories)
%RUN_REAL_TOPK_EVENT_DRIVEN_DYNAMIC_VALIDATION Run real Top-K closed-loop dynamic validation.

if nargin < 1 || isempty(basecasePath)
    basecasePath = "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json";
end
if nargin < 2 || isempty(matlabBatchInputCsv)
    matlabBatchInputCsv = "../../results/gcn_search/simulink_dynamic_real_cases/matlab_batch_input.csv";
end
if nargin < 3 || isempty(outputDir)
    outputDir = "../../results/gcn_search/simulink_dynamic_real_results";
end
if nargin < 4
    optionsJsonPath = "";
end
if nargin < 5 || isempty(saveTrajectories)
    saveTrajectories = false;
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end
if strlength(string(optionsJsonPath)) > 0 && exist(optionsJsonPath, "file")
    options = jsondecode(fileread(optionsJsonPath));
else
    options = struct();
end
resultTable = run_rts79_dynamic_batch(basecasePath, matlabBatchInputCsv, outputDir, saveTrajectories, options);
config = struct("basecasePath", string(basecasePath), "matlabBatchInputCsv", string(matlabBatchInputCsv), ...
    "outputDir", string(outputDir), "optionsJsonPath", string(optionsJsonPath), ...
    "saveTrajectories", logical(saveTrajectories), "engine", "event_driven_closed_loop");
fid = fopen(fullfile(outputDir, "real_topk_event_driven_run_config.json"), "w");
fprintf(fid, "%s", jsonencode(config, "PrettyPrint", true));
fclose(fid);
end
