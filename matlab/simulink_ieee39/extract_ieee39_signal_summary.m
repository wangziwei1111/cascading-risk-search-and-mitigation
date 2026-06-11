function summary = extract_ieee39_signal_summary(simOut, testCase, outputDir)
%EXTRACT_IEEE39_SIGNAL_SUMMARY Extract compact IEEE39 signal diagnostics.
%
% This function does not use fixed 1.0 / 50.0 placeholders as measured
% values. Unavailable signals are returned as NaN with debug metadata.

if nargin < 2 || isempty(testCase)
    testCase = "unknown_case";
end
if nargin < 3 || isempty(outputDir)
    outputDir = "../../results/gcn_search/ieee39_graphical_dynamic_model/fault_tests";
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

missing = ["bus_voltage", "frequency", "generator_speed", "rotor_angle"];
status = "unavailable";
debug = struct();
debug.test_case = char(testCase);
debug.available_simulation_output_variables = {};
debug.note = "No fixed placeholder values are reported as measurements.";

if ~isempty(simOut)
    try
        debug.available_simulation_output_variables = simOut.who;
        status = "partial";
    catch
        debug.available_simulation_output_variables = {};
    end
end

summary = struct();
summary.test_case = char(testCase);
summary.min_voltage_pu = NaN;
summary.max_voltage_pu = NaN;
summary.min_frequency_hz = NaN;
summary.max_frequency_hz = NaN;
summary.max_speed_deviation = NaN;
summary.max_rotor_angle_separation_deg = NaN;
summary.measurement_extraction_status = status;
summary.missing_signal_list = strjoin(missing, ";");

debugPath = fullfile(outputDir, "ieee39_signal_extraction_debug.json");
existing = [];
if isfile(debugPath)
    try
        existing = jsondecode(fileread(debugPath));
    catch
        existing = [];
    end
end
record = summary;
record.debug = debug;
if isempty(existing)
    payload = record;
else
    payload = existing;
    if ~isstruct(payload) || ~isfield(payload, "records")
        payload = struct("records", payload);
    end
    payload.records(end+1) = record;
end
if ~isstruct(payload) || ~isfield(payload, "records")
    payload = struct("records", record);
end
fid = fopen(debugPath, "w");
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, "%s", jsonencode(payload, PrettyPrint=true));
end
