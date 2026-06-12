function summaryTable = run_ieee39_multi_handwired_line_trip_suite(handwiredModelPath, outputDir, lineIds, simulationStopTime, validationSummaryCsv, perLineTimeoutSeconds)
%RUN_IEEE39_MULTI_HANDWIRED_LINE_TRIP_SUITE Run compact validated line trips.
%
% The suite does not insert or save breakers. It only simulates line trip
% cases whose handwired breaker and trip command passed validation.

if nargin < 1 || isempty(handwiredModelPath)
    handwiredModelPath = "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx";
end
if nargin < 2 || isempty(outputDir)
    outputDir = "../../results/gcn_search/ieee39_graphical_dynamic_model/fault_tests";
end
if nargin < 3 || isempty(lineIds)
    lineIds = ["L01", "L02", "L03", "L04"];
end
if nargin < 4 || isempty(simulationStopTime)
    simulationStopTime = 1.0;
end
if nargin < 5 || isempty(validationSummaryCsv)
    validationSummaryCsv = "../../results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_multi_handwired_breaker_validation_summary.csv";
end
if nargin < 6 || isempty(perLineTimeoutSeconds)
    perLineTimeoutSeconds = 180;
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end
configure_ieee39_short_filegen_paths();

lineIds = string(lineIds);
validation = readtable(validationSummaryCsv, "TextType", "string", "VariableNamingRule", "preserve", "Delimiter", ",");
rows = cell(numel(lineIds), 26);
eventRows = {};
signalRows = {};
for idx = 1:numel(lineIds)
    lineId = lineIds(idx);
    testCase = "handwired_line_trip_" + lineId;
    match = validation(validation.line_id == lineId, :);
    passed = ~isempty(match) && logical(match.validation_passed(1));
    if passed
        commandPath = string(match.trip_command_path(1));
        [success, note, simOut] = simulateOneLine(handwiredModelPath, validation, lineId, commandPath, simulationStopTime, perLineTimeoutSeconds);
        physicalExecuted = success;
        tripImplementation = "handwired_timed_breaker";
        trainingReady = success;
    else
        success = false;
        physicalExecuted = false;
        simOut = [];
        tripImplementation = "manual_required";
        trainingReady = false;
        if isempty(match)
            note = "validation missing for " + lineId;
        else
            note = "validation failed: " + string(match.validation_failure_reason(1));
        end
    end
    signalSummary = extract_ieee39_signal_summary(simOut, testCase, outputDir);
    rows(idx, :) = {
        char(testCase), success, physicalExecuted, false, "graphical_simulink_phasor_RMS", char(tripImplementation), ...
        "not_applicable", char(signalSummary.measurement_extraction_status), trainingReady, char(ternary(success, "", note)), ...
        "pilot_line_trip", 0.5, 0.0, char(lineId), false, success, ...
        signalSummary.min_voltage_pu, signalSummary.max_voltage_pu, signalSummary.min_frequency_hz, signalSummary.max_frequency_hz, ...
        signalSummary.max_speed_deviation, signalSummary.max_rotor_angle_separation_deg, char(signalSummary.signal_source_summary), false, 0.5, char(note) ...
    };
    eventRows(end+1, :) = {char(testCase), 0.5, "pilot_line_trip", physicalExecuted, char(note)}; %#ok<AGROW>
    signalRows(end+1, :) = {char(testCase), signalSummary.min_voltage_pu, signalSummary.max_voltage_pu, signalSummary.min_frequency_hz, signalSummary.max_frequency_hz, ...
        signalSummary.max_speed_deviation, signalSummary.max_rotor_angle_separation_deg, char(signalSummary.measurement_extraction_status), ...
        char(signalSummary.missing_signal_list), char(signalSummary.voltage_source), char(signalSummary.frequency_source), ...
        char(signalSummary.speed_source), char(signalSummary.rotor_angle_source), signalSummary.num_voltage_signals_found, ...
        signalSummary.num_speed_signals_found, signalSummary.num_rotor_angle_signals_found, char(signalSummary.signal_source_summary), ...
        "frequency_source must remain generator_speed_proxy"}; %#ok<AGROW>
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
writetable(summaryTable, fullfile(outputDir, "ieee39_multi_handwired_line_trip_summary.csv"));
writetable(eventTable, fullfile(outputDir, "ieee39_multi_handwired_event_log.csv"));
writetable(signalTable, fullfile(outputDir, "ieee39_multi_handwired_signal_summary.csv"));
fprintf("Wrote IEEE39 multi-handwired line trip suite under: %s\n", outputDir);
end

function [success, note, simOut] = simulateOneLine(modelPath, validation, lineId, commandPath, stopTime, perLineTimeoutSeconds)
success = false;
note = "not executed";
simOut = [];
try
    load_system(modelPath);
    [~, modelName, ~] = fileparts(modelPath);
    for idx = 1:height(validation)
        otherCommand = string(validation.trip_command_path(idx));
        if strlength(otherCommand) > 0
            try
                if string(validation.line_id(idx)) == string(lineId)
                    set_param(otherCommand, "Time", "0.5");
                else
                    set_param(otherCommand, "Time", "1000");
                end
            catch
            end
        end
    end
    try
        set_param(commandPath, "Time", "0.5");
    catch
    end
    simOut = sim(modelName, "StopTime", num2str(stopTime), "TimeOut", perLineTimeoutSeconds);
    success = true;
    note = "handwired timed breaker validated and compact simulation completed";
    close_system(modelName, 0);
catch ME
    success = false;
    if contains(lower(string(ME.message)), "timeout") || contains(lower(string(ME.message)), "time out")
        note = "simulation timeout after " + string(perLineTimeoutSeconds) + " seconds: " + string(ME.message);
    else
        note = "simulation failed: " + string(ME.message);
    end
    try
        [~, modelName, ~] = fileparts(modelPath);
        close_system(modelName, 0);
    catch
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
