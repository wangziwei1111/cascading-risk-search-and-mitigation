function resultTable = run_rts79_dynamic_path_case(basecasePath, eventTablePath, caseId, outputDir, saveTrajectories)
%RUN_RTS79_DYNAMIC_PATH_CASE Run one simplified RTS-79 dynamic path case.
%
% This entry builds the Simulink scaffold and then calls a MATLAB ODE
% swing-equation engine to compute trajectory-based prototype metrics.

if nargin < 4 || isempty(outputDir)
    outputDir = "../../results/gcn_search/simulink_dynamic_results";
end
if nargin < 5 || isempty(saveTrajectories)
    saveTrajectories = false;
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

build_rts79_swing_simulink_model(basecasePath, eventTablePath, "../../results/gcn_search/simulink_dynamic_models");
[resultTable, ~, ~] = simulate_rts79_swing_case(basecasePath, eventTablePath, caseId, outputDir, saveTrajectories);
fprintf("Wrote swing-equation dynamic case result for case_id=%s\n", string(caseId));
end
