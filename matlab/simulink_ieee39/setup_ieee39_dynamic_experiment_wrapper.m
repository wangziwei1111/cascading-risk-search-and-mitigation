function wrapperSummary = setup_ieee39_dynamic_experiment_wrapper(sourceModelPath, outputDir)
%SETUP_IEEE39_DYNAMIC_EXPERIMENT_WRAPPER Copy an IEEE39 graphical model for experiments.
%
% This wrapper preserves the source model. It creates a generated copy and a
% machine-readable interface plan for later fault injection, breaker trips,
% measurement export, and dynamic-label generation.

if nargin < 1 || isempty(sourceModelPath)
    sourceModelPath = "C:/Users/24186/Documents/MATLAB/Examples/R2024b/simscapeelectrical/IEEE39BusSystemExample/IEEE39BusSystem.slx";
end
if nargin < 2 || isempty(outputDir)
    outputDir = "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models";
end
if ~isfile(sourceModelPath)
    error("Source IEEE39 model not found: %s", sourceModelPath);
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

[~, modelName, ext] = fileparts(sourceModelPath);
generatedPath = fullfile(outputDir, modelName + "_dynamic_experiment_wrapper" + ext);
copyfile(sourceModelPath, generatedPath);

% Do not edit the source model in place. Round 26 records the wrapper
% interface plan in JSON; later rounds can add concrete fault/breaker blocks
% to this generated copy after path mapping is verified.

wrapperSummary = struct();
wrapperSummary.source_model_path = char(sourceModelPath);
wrapperSummary.generated_model_path = char(generatedPath);
wrapperSummary.original_model_preserved = true;
wrapperSummary.added_fault_injection_interface = "planned_wrapper_interface";
wrapperSummary.added_line_trip_interface = "planned_wrapper_interface";
wrapperSummary.added_measurement_outputs = ["bus_voltage", "generator_speed", "frequency", "rotor_angle", "line_loading_proxy", "relay_trip_signal"];
wrapperSummary.protection_status = "protection wrapper not engineering-grade; relay logic still preliminary";
wrapperSummary.result_export_status = "fault-test scripts export CSV summaries and event logs";
wrapperSummary.do_not_commit_generated_slx = true;

summaryPath = fullfile(outputDir, "ieee39_dynamic_experiment_wrapper_summary.json");
fid = fopen(summaryPath, "w");
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, "%s", jsonencode(wrapperSummary, PrettyPrint=true));
fprintf("Wrote IEEE39 wrapper summary: %s\n", summaryPath);
fprintf("Generated wrapper model copy: %s\n", generatedPath);
end
