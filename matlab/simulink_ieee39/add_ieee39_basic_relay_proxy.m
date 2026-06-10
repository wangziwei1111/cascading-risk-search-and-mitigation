function relayStatus = add_ieee39_basic_relay_proxy(wrapperModelPath, outputDir, settings)
%ADD_IEEE39_BASIC_RELAY_PROXY Record a research-grade relay proxy.
%
% This does not claim engineering-grade relay coordination. It writes a
% reusable threshold specification and status file for the fault-test suite.

if nargin < 1 || isempty(wrapperModelPath)
    wrapperModelPath = "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper.slx";
end
if nargin < 2 || isempty(outputDir)
    outputDir = "../../results/gcn_search/ieee39_graphical_dynamic_model/protection";
end
if nargin < 3 || isempty(settings)
    settings = struct();
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

undervoltage = getOrDefault(settings, "undervoltage_threshold_pu", 0.8);
underfrequency = getOrDefault(settings, "underfrequency_threshold_hz", 49.0);
overcurrent = getOrDefault(settings, "overcurrent_threshold_pu", 1.5);
delay = getOrDefault(settings, "delay_s", 0.05);

settingTable = table( ...
    ["undervoltage"; "underfrequency"; "overcurrent"], ...
    [undervoltage; underfrequency; overcurrent], ...
    ["pu"; "Hz"; "pu"], ...
    [delay; delay; delay], ...
    ["basic proxy only"; "basic proxy only"; "used only if current proxy is available"], ...
    'VariableNames', {'relay_element', 'threshold', 'unit', 'delay_s', 'note'} ...
);
writetable(settingTable, fullfile(outputDir, "ieee39_basic_relay_settings.csv"));

relayStatus = struct();
relayStatus.wrapper_model_path = char(wrapperModelPath);
relayStatus.proxy_type = "basic relay proxy";
relayStatus.not_engineering_grade = true;
relayStatus.undervoltage_threshold_pu = undervoltage;
relayStatus.underfrequency_threshold_hz = underfrequency;
relayStatus.overcurrent_threshold_pu = overcurrent;
relayStatus.delay_s = delay;
relayStatus.trip_latch = true;
relayStatus.breaker_command_output = "logical proxy in fault-test suite";
relayStatus.note = "basic relay proxy, not engineering-grade relay coordination";
statusPath = fullfile(outputDir, "ieee39_basic_relay_status.json");
fid = fopen(statusPath, "w");
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, "%s", jsonencode(relayStatus, PrettyPrint=true));
fprintf("Wrote IEEE39 basic relay proxy settings under: %s\n", outputDir);
end

function value = getOrDefault(settings, name, defaultValue)
if isfield(settings, name)
    value = settings.(name);
else
    value = defaultValue;
end
end
