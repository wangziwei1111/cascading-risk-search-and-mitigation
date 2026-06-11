function config = configure_ieee39_three_phase_fault_case(wrapperModelPath, faultStartS, faultClearS, outputDir)
%CONFIGURE_IEEE39_THREE_PHASE_FAULT_CASE Configure the existing fault block.

if nargin < 1 || isempty(wrapperModelPath)
    wrapperModelPath = "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper.slx";
end
if nargin < 2 || isempty(faultStartS)
    faultStartS = 0.5;
end
if nargin < 3 || isempty(faultClearS)
    faultClearS = 0.6;
end
if nargin < 4 || isempty(outputDir)
    outputDir = "../../results/gcn_search/ieee39_graphical_dynamic_model/wrapper";
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

config = struct();
config.wrapper_model_path = char(wrapperModelPath);
config.fault_start_s = faultStartS;
config.fault_clear_s = faultClearS;
config.fault_duration_s = max(0.05, faultClearS - faultStartS);
config.fault_configuration_status = "manual_required";
config.fault_block_path = "";

load_system(wrapperModelPath);
[~, modelName, ~] = fileparts(wrapperModelPath);
faultBlocks = find_system(modelName, "LookUnderMasks", "all", "FollowLinks", "on", "MaskType", "Fault (Three-Phase)");
if ~isempty(faultBlocks)
    faultBlock = string(faultBlocks{1});
    config.fault_block_path = char(faultBlock);
    params = getFaultParameterInventory(faultBlock);
    writetable(params, fullfile(outputDir, "ieee39_fault_block_parameter_inventory.csv"));
    try
        set_param(faultBlock, "enable_temporal_fault", "1");
        set_param(faultBlock, "fault_start_time", num2str(faultStartS));
        set_param(faultBlock, "fault_duration", num2str(config.fault_duration_s));
        config.fault_configuration_status = "configured";
    catch ME
        config.fault_configuration_status = "manual_required";
        config.error_message = ME.message;
    end
end
close_system(modelName, 0);

summaryPath = fullfile(outputDir, "ieee39_three_phase_fault_case_config.json");
fid = fopen(summaryPath, "w");
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, "%s", jsonencode(config, PrettyPrint=true));
fprintf("Wrote IEEE39 three-phase fault case config: %s\n", summaryPath);
end

function tableOut = getFaultParameterInventory(faultBlock)
params = get_param(faultBlock, "DialogParameters");
names = fieldnames(params);
values = strings(numel(names), 1);
for idx = 1:numel(names)
    try
        values(idx) = string(get_param(faultBlock, names{idx}));
    catch
        values(idx) = "<unreadable>";
    end
end
tableOut = table(string(names), values, 'VariableNames', {'parameter_name', 'parameter_value'});
end
