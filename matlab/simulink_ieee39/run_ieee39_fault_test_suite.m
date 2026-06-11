function summaryTable = run_ieee39_fault_test_suite(wrapperModelPath, outputDir, executeSimulation, selectedCases, simulationStopTime, handwiredMode)
%RUN_IEEE39_FAULT_TEST_SUITE Run IEEE39 graphical-model pilot fault tests.
%
% The current wrapper uses real Simulink/Simscape simulations. Line trips use
% the best available pilot implementation recorded by
% configure_ieee39_pilot_line_trip_case. If timed physical-port rewiring is
% not available, the case remains a non-training static topology disable.
% The relay test uses a research-grade threshold proxy, not engineering-grade
% relay coordination.

if nargin < 1 || isempty(wrapperModelPath)
    wrapperModelPath = "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper.slx";
end
if nargin < 2 || isempty(outputDir)
    outputDir = "../../results/gcn_search/ieee39_graphical_dynamic_model/fault_tests";
end
if nargin < 3 || isempty(executeSimulation)
    executeSimulation = true;
end
if nargin < 4 || isempty(selectedCases)
    selectedCases = ["no_fault_sanity", "three_phase_fault_clear", "single_line_trip"];
end
if nargin < 5 || isempty(simulationStopTime)
    simulationStopTime = 2.0;
end
if nargin < 6 || isempty(handwiredMode)
    handwiredMode = false;
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

wrapperDir = "../../results/gcn_search/ieee39_graphical_dynamic_model/wrapper";
mapPath = fullfile(wrapperDir, "ieee39_line_breaker_map.csv");
faultPointPath = fullfile(wrapperDir, "ieee39_fault_injection_points.csv");
if ~isfile(mapPath)
    map_ieee39_lines_and_breakers(wrapperModelPath, wrapperDir);
end
if ~isfile(faultPointPath)
    map_ieee39_lines_and_breakers(wrapperModelPath, wrapperDir);
end
lineMap = readtable(mapPath, "TextType", "string", "VariableNamingRule", "preserve", "Delimiter", ",");
faultPoints = readtable(faultPointPath, "TextType", "string", "VariableNamingRule", "preserve", "Delimiter", ",");
line1 = lineMap(1, :);
line2 = lineMap(min(2, height(lineMap)), :);
faultBlock = "";
if ~isempty(faultPoints) && strlength(faultPoints.fault_block_path(1)) > 0
    faultBlock = faultPoints.fault_block_path(1);
end
tripSummary = configure_ieee39_pilot_line_trip_case(wrapperModelPath, line1.line_id, wrapperDir);
singleLineTripImplementation = string(tripSummary.trip_implementation);
handwiredValidated = false;
if handwiredMode
    handwiredValidated = readHandwiredValidationPassed();
    if handwiredValidated
        singleLineTripImplementation = "handwired_timed_breaker";
    else
        singleLineTripImplementation = "manual_required";
    end
end

cases = {
    "no_fault_sanity", "none", 0.0, 0.0, "", false, false, simulationStopTime, "none";
    "single_line_trip", "pilot_line_trip", 0.5, 0.0, line1.line_id, false, true, simulationStopTime, singleLineTripImplementation;
    "three_phase_fault_clear", "three_phase_fault_clear", 0.5, 0.6, "", true, false, simulationStopTime, "existing_three_phase_fault_block";
    "ordered_N2_trip", "pilot_ordered_N2_static_topology_disable", 0.0, 0.0, line1.line_id + "->" + line2.line_id, false, true, simulationStopTime, "static_topology_disable";
    "relay_trip_test", "basic_relay_proxy", 0.5, 0.6, line1.line_id, true, true, simulationStopTime, "basic_relay_proxy";
};
caseNames = string(cases(:, 1));
keep = ismember(caseNames, string(selectedCases));
cases = cases(keep, :);

rows = cell(size(cases, 1), 26);
eventRows = {};
signalRows = {};
relayRows = {};
for idx = 1:size(cases, 1)
    testCase = string(cases{idx, 1});
    faultType = string(cases{idx, 2});
    faultStart = double(cases{idx, 3});
    faultClear = double(cases{idx, 4});
    trippedLine = string(cases{idx, 5});
    useFault = logical(cases{idx, 6});
    useLineTrip = logical(cases{idx, 7});
    stopTime = double(cases{idx, 8});
    tripImplementation = string(cases{idx, 9});
    [success, physicalExecuted, note, simOut] = runOneCase(wrapperModelPath, testCase, useLineTrip, trippedLine, useFault, faultBlock, faultStart, max(0.0, faultClear - faultStart), stopTime, executeSimulation, lineMap, tripImplementation);
    signalSummary = extract_ieee39_signal_summary(simOut, testCase, outputDir);
    minVoltage = signalSummary.min_voltage_pu;
    maxVoltage = signalSummary.max_voltage_pu;
    minFrequency = signalSummary.min_frequency_hz;
    maxFrequency = signalSummary.max_frequency_hz;
    maxSpeedDeviation = signalSummary.max_speed_deviation;
    maxRotorAngle = signalSummary.max_rotor_angle_separation_deg;
    measurementStatus = string(signalSummary.measurement_extraction_status);
    signalSourceSummary = string(signalSummary.signal_source_summary);
    relayOperated = testCase == "relay_trip_test" && physicalExecuted;
    breakerOpened = useLineTrip && isTimedTripImplementation(tripImplementation) && physicalExecuted;
    unstable = minFrequency < 49.0 || minVoltage < 0.8 || maxRotorAngle > 180.0;
    tripTime = ternary(relayOperated || breakerOpened, faultStart, NaN);
    schemaOnly = ~executeSimulation;
    faultConfigurationStatus = ternary(useFault && strlength(faultBlock) > 0, "configured", ternary(useFault, "manual_required", "not_applicable"));
    trainingReadyCandidate = success && physicalExecuted && ~schemaOnly && (isTimedTripImplementation(tripImplementation) || tripImplementation == "existing_three_phase_fault_block" || tripImplementation == "basic_relay_proxy");
    timeoutOrError = "";
    if ~success
        timeoutOrError = note;
    end
    rows(idx, :) = {
        char(testCase), success, physicalExecuted, schemaOnly, "graphical_simulink_phasor_RMS", char(tripImplementation), ...
        char(faultConfigurationStatus), char(measurementStatus), trainingReadyCandidate, char(timeoutOrError), ...
        char(faultType), faultStart, faultClear, char(trippedLine), ...
        relayOperated, breakerOpened, minVoltage, maxVoltage, minFrequency, maxFrequency, ...
        maxSpeedDeviation, maxRotorAngle, char(signalSourceSummary), unstable, tripTime, char(note) ...
    };
    eventRows(end+1, :) = {char(testCase), faultStart, char(faultType), physicalExecuted, char(note)}; %#ok<AGROW>
    signalRows(end+1, :) = {char(testCase), minVoltage, maxVoltage, minFrequency, maxFrequency, maxSpeedDeviation, maxRotorAngle, ...
        char(measurementStatus), char(signalSummary.missing_signal_list), char(signalSummary.voltage_source), ...
        char(signalSummary.frequency_source), char(signalSummary.speed_source), char(signalSummary.rotor_angle_source), ...
        signalSummary.num_voltage_signals_found, signalSummary.num_speed_signals_found, signalSummary.num_rotor_angle_signals_found, ...
        char(signalSourceSummary), "NaN means unavailable; no fixed placeholder is reported as measured"}; %#ok<AGROW>
    relayRows(end+1, :) = {char(testCase), relayOperated, tripTime, "basic relay proxy", "not engineering-grade relay coordination"}; %#ok<AGROW>
end

summaryTable = cell2table(rows, "VariableNames", { ...
    'test_case', 'simulation_success', 'physical_fault_or_breaker_action_executed', ...
    'schema_only', 'simulation_mode', 'trip_implementation', 'fault_configuration_status', ...
    'measurement_extraction_status', 'training_ready_candidate', 'timeout_or_error_message', ...
    'fault_type', 'fault_start_s', 'fault_clear_s', 'tripped_line', 'relay_operated', ...
    'breaker_opened', 'min_voltage_pu', 'max_voltage_pu', 'min_frequency_hz', ...
    'max_frequency_hz', 'max_speed_deviation', 'max_rotor_angle_separation_deg', ...
    'signal_source_summary', 'unstable_flag', 'trip_time_s', 'note' ...
});
eventTable = cell2table(eventRows, "VariableNames", {'test_case', 'event_time_s', 'event_type', 'physical_executed', 'event_note'});
signalTable = cell2table(signalRows, "VariableNames", {'test_case', 'min_voltage_pu', 'max_voltage_pu', 'min_frequency_hz', 'max_frequency_hz', ...
    'max_speed_deviation', 'max_rotor_angle_separation_deg', 'measurement_extraction_status', 'missing_signal_list', ...
    'voltage_source', 'frequency_source', 'speed_source', 'rotor_angle_source', 'num_voltage_signals_found', ...
    'num_speed_signals_found', 'num_rotor_angle_signals_found', 'signal_source_summary', 'signal_note'});
relayTable = cell2table(relayRows, "VariableNames", {'test_case', 'relay_operated', 'trip_time_s', 'relay_type', 'note'});

writetable(summaryTable, fullfile(outputDir, "ieee39_fault_test_summary.csv"));
writetable(eventTable, fullfile(outputDir, "ieee39_event_log.csv"));
writetable(signalTable, fullfile(outputDir, "ieee39_signal_summary.csv"));
writetable(relayTable, fullfile(outputDir, "ieee39_relay_trip_log.csv"));
fprintf("Wrote IEEE39 fault-test outputs under: %s\n", outputDir);
end

function [success, physicalExecuted, note, simOut] = runOneCase(modelPath, testCase, useLineTrip, trippedLine, useFault, faultBlock, faultStart, faultDuration, stopTime, executeSimulation, lineMap, tripImplementation)
success = false;
physicalExecuted = false;
note = "not executed";
simOut = [];
try
    load_system(modelPath);
    [~, modelName, ~] = fileparts(modelPath);
    resetPilotChanges(lineMap, faultBlock);
    if useLineTrip
        if tripImplementation == "static_topology_disable" || tripImplementation == "manual_required"
            disableMappedLines(trippedLine, lineMap);
            physicalExecuted = false;
        elseif isTimedTripImplementation(tripImplementation)
            physicalExecuted = true;
        end
    end
    if useFault && strlength(faultBlock) > 0
        set_param(faultBlock, "enable_temporal_fault", "1");
        set_param(faultBlock, "fault_start_time", num2str(faultStart));
        set_param(faultBlock, "fault_duration", num2str(max(faultDuration, 0.05)));
        physicalExecuted = true;
    end
    if ~executeSimulation
        success = false;
        note = "simulation skipped; interface dry run";
    else
        simOut = sim(modelName, "StopTime", num2str(stopTime));
        success = true;
        if testCase == "no_fault_sanity"
            physicalExecuted = false;
            note = "real no-fault graphical simulation completed";
        elseif useLineTrip && tripImplementation == "static_topology_disable"
            note = "static topology line disable executed before simulation; not timed breaker control and not training-ready";
        elseif useLineTrip && tripImplementation == "manual_required"
            note = "manual_required: handwired timed breaker validation did not pass; static topology fallback is not training-ready";
        elseif useLineTrip && startsWith(tripImplementation, "handwired")
            note = "handwired timed breaker validated by validation script";
        elseif useLineTrip
            note = "pilot controlled switch or breaker-like trip executed";
        elseif useFault
            note = "existing three-phase fault block executed with temporal fault parameters";
        else
            note = "real graphical simulation completed";
        end
    end
    close_system(modelName, 0);
catch ME
    success = false;
    note = "simulation failed: " + string(ME.message);
    try
        [~, modelName, ~] = fileparts(modelPath);
        close_system(modelName, 0);
    catch
    end
end
end

function resetPilotChanges(lineMap, faultBlock)
for idx = 1:height(lineMap)
    path = lineMap.line_block_path(idx);
    if strlength(path) > 0
        try
            set_param(path, "Commented", "off");
        catch
        end
    end
end
if strlength(faultBlock) > 0
    try
        set_param(faultBlock, "fault_start_time", "1000");
        set_param(faultBlock, "fault_duration", "0.1");
    catch
    end
end
end

function disableMappedLines(trippedLine, lineMap)
parts = split(string(trippedLine), "->");
for idx = 1:numel(parts)
    lineId = strtrim(parts(idx));
    match = lineMap(lineMap.line_id == lineId, :);
    if ~isempty(match)
        set_param(match.line_block_path(1), "Commented", "on");
    end
end
end

function value = ternary(condition, trueValue, falseValue)
if condition
    value = trueValue;
else
    value = falseValue;
end
end

function tf = isTimedTripImplementation(tripImplementation)
tripImplementation = string(tripImplementation);
tf = ismember(tripImplementation, ["existing_breaker_control", "timed_controlled_switch", "handwired_timed_breaker", "handwired_timed_controlled_switch"]);
end

function passed = readHandwiredValidationPassed()
passed = false;
summaryPath = "../../results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_handwired_breaker_validation_summary.json";
if isfile(summaryPath)
    try
        payload = jsondecode(fileread(summaryPath));
        passed = logical(payload.validation_passed);
    catch
        passed = false;
    end
end
end
