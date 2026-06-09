function modelName = build_rts79_swing_simulink_model(basecasePath, eventTablePath, outputDir)
%BUILD_RTS79_SWING_SIMULINK_MODEL Generate a simplified RTS-79 dynamic prototype.
%
% This script creates a reproducible Simulink model scaffold. The current
% implementation uses a Simulink scaffold plus the MATLAB ODE engine in
% simulate_rts79_swing_case.m for trajectory-based metrics. This is not EMT,
% not a detailed generator/governor/PSS model, and not a renewable model.

if nargin < 1 || isempty(basecasePath)
    basecasePath = "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json";
end
if nargin < 2 || isempty(eventTablePath)
    eventTablePath = "../../results/gcn_search/simulink_dynamic_cases/matlab_batch_input.csv";
end
if nargin < 3 || isempty(outputDir)
    outputDir = "../../results/gcn_search/simulink_dynamic_models";
end

if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

modelName = "rts79_swing_dynamic_autogen";
if bdIsLoaded(modelName)
    close_system(modelName, 0);
end

new_system(modelName);
open_system(modelName);
set_param(modelName, "StopTime", "20.0");
set_param(modelName, "Solver", "ode45");
set_param(modelName, "Description", ...
    "simplified swing-equation prototype; not EMT; no renewable; no detailed controls; MATLAB ODE engine computes metrics");

add_block("simulink/Sources/Constant", modelName + "/BasecasePathMarker", "Value", "0");
add_block("simulink/Sources/Constant", modelName + "/EventTablePathMarker", "Value", "0");
add_block("simulink/User-Defined Functions/MATLAB Function", modelName + "/SimplifiedSwingPrototype");
add_block("simulink/Sinks/To Workspace", modelName + "/DynamicMetrics", "VariableName", "rts79_dynamic_metrics");
annotationText = sprintf("Simplified swing-equation prototype\\nNot EMT\\nNo renewable generation\\nNo detailed exciter/governor/PSS\\nMetrics computed by simulate_rts79_swing_case.m");
add_block("simulink/Ports & Subsystems/Subsystem", modelName + "/PrototypeScopeNote", "Position", [360 40 600 140]);
set_param(modelName + "/PrototypeScopeNote", "AttributesFormatString", annotationText);

try
    Simulink.BlockDiagram.arrangeSystem(modelName);
catch
    % arrangeSystem is cosmetic only; keep the generated model usable.
end

savePath = fullfile(outputDir, modelName + ".slx");
save_system(modelName, savePath);
fprintf("Generated Simulink prototype: %s\n", savePath);
fprintf("The generated .slx is an output artifact and should not be committed.\n");
end
