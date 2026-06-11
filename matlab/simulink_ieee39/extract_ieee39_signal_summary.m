function summary = extract_ieee39_signal_summary(simOut, testCase, outputDir)
%EXTRACT_IEEE39_SIGNAL_SUMMARY Extract compact IEEE39 signal diagnostics.
%
% This function reports only values extracted from simulation output. It does
% not fill missing measurements with fixed 1.0 / 50.0 placeholders.

if nargin < 2 || isempty(testCase)
    testCase = "unknown_case";
end
if nargin < 3 || isempty(outputDir)
    outputDir = "../../results/gcn_search/ieee39_graphical_dynamic_model/fault_tests";
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

debug = struct();
debug.test_case = char(testCase);
debug.available_simulation_output_variables = {};
debug.note = "No fixed placeholder values are reported as measurements.";
debug.extraction_errors = {};

voltageSeries = {};
speedSeries = {};
angleSeries = {};
currentSeries = {};
voltageSources = strings(0, 1);
speedSources = strings(0, 1);
angleSources = strings(0, 1);
currentSources = strings(0, 1);

if ~isempty(simOut)
    try
        debug.available_simulation_output_variables = simOut.who;
    catch
        debug.available_simulation_output_variables = {};
    end
    try
        inventory_ieee39_simlog_tree(simOut, outputDir, 10);
    catch ME
        debug.extraction_errors{end+1} = ["inventory_failed: " char(ME.message)];
    end
    try
        rootNode = getRootNode(simOut);
        [voltageSeries, voltageSources] = collectGeneratorLeafSeries(rootNode, "Terminal_voltage.pu_output");
        [speedSeries, speedSources] = collectGeneratorLeafSeries(rootNode, "Rotor_velocity.pu_output");
        [angleSeries, angleSources] = collectGeneratorLeafSeries(rootNode, "Rotor_electrical_angle.pu_output");
        [currentSeries, currentSources] = collectSeriesByKeyword(rootNode, "current", 8);
    catch ME
        debug.extraction_errors{end+1} = ["signal_extract_failed: " char(ME.message)];
    end
end

[minVoltage, maxVoltage] = minMaxAcrossSeries(voltageSeries);
[minSpeed, maxSpeed] = minMaxAcrossSeries(speedSeries);
maxSpeedDeviation = maxAbsDeviation(speedSeries, 1.0);
maxRotorAngleSeparation = maxSeparationAcrossSeries(angleSeries);

if ~isnan(minSpeed) && ~isnan(maxSpeed)
    minFrequency = minSpeed * 50.0;
    maxFrequency = maxSpeed * 50.0;
    frequencySource = "generator_speed_proxy";
else
    minFrequency = NaN;
    maxFrequency = NaN;
    frequencySource = "";
end

missing = strings(0, 1);
if isempty(voltageSeries); missing(end+1) = "bus_voltage"; end %#ok<AGROW>
if isempty(speedSeries); missing(end+1) = "frequency"; end %#ok<AGROW>
if isempty(speedSeries); missing(end+1) = "generator_speed"; end %#ok<AGROW>
if isempty(angleSeries); missing(end+1) = "rotor_angle"; end %#ok<AGROW>

status = measurementStatus(~isempty(voltageSeries), ~isempty(speedSeries), ~isempty(angleSeries));
summary = struct();
summary.test_case = char(testCase);
summary.min_voltage_pu = minVoltage;
summary.max_voltage_pu = maxVoltage;
summary.min_frequency_hz = minFrequency;
summary.max_frequency_hz = maxFrequency;
summary.max_speed_deviation = maxSpeedDeviation;
summary.max_rotor_angle_separation_deg = maxRotorAngleSeparation;
summary.measurement_extraction_status = char(status);
summary.missing_signal_list = strjoin(missing, ";");
summary.voltage_source = sourceText(voltageSources);
summary.frequency_source = char(frequencySource);
summary.speed_source = sourceText(speedSources);
summary.rotor_angle_source = sourceText(angleSources);
summary.current_source = sourceText(currentSources);
summary.num_voltage_signals_found = numel(voltageSeries);
summary.num_speed_signals_found = numel(speedSeries);
summary.num_rotor_angle_signals_found = numel(angleSeries);
summary.num_current_signals_found = numel(currentSeries);
summary.signal_source_summary = buildSourceSummary(summary);

writeDebugRecord(outputDir, summary, debug);
end

function rootNode = getRootNode(simOut)
names = simOut.who;
nameStrings = string(names);
match = nameStrings(startsWith(nameStrings, "simlog_"));
if isempty(match)
    error("No simlog_* variable found in SimulationOutput.");
end
rootNode = simOut.(char(match(1)));
end

function [seriesList, sourceList] = collectGeneratorLeafSeries(rootNode, relativePath)
seriesList = {};
sourceList = strings(0, 1);
if ~hasChildSafe(rootNode, "Generators")
    return;
end
generators = rootNode.child("Generators");
genIds = string(generators.childIds);
for idx = 1:numel(genIds)
    basePath = "Generators." + genIds(idx) + "." + relativePath;
    try
        node = nodeByPath(rootNode, basePath);
        values = numericSeries(node);
        if ~isempty(values)
            seriesList{end+1} = values(:); %#ok<AGROW>
            sourceList(end+1) = "simlog_IEEE39BusSystem." + basePath; %#ok<AGROW>
        end
    catch
    end
end
end

function [seriesList, sourceList] = collectSeriesByKeyword(rootNode, keyword, maxDepth)
seriesList = {};
sourceList = strings(0, 1);
[seriesList, sourceList] = collectSeriesRecursive(rootNode, "simlog_IEEE39BusSystem", lower(keyword), 0, maxDepth, seriesList, sourceList);
end

function [seriesList, sourceList] = collectSeriesRecursive(node, path, keyword, depth, maxDepth, seriesList, sourceList)
if depth > maxDepth
    return;
end
if contains(lower(path), keyword)
    try
        values = numericSeries(node);
        if ~isempty(values)
            seriesList{end+1} = values(:); %#ok<AGROW>
            sourceList(end+1) = string(path); %#ok<AGROW>
        end
    catch
    end
end
try
    children = string(node.childIds);
catch
    children = strings(0, 1);
end
for idx = 1:numel(children)
    childName = children(idx);
    try
        childNode = node.child(char(childName));
        [seriesList, sourceList] = collectSeriesRecursive(childNode, path + "." + childName, keyword, depth + 1, maxDepth, seriesList, sourceList);
    catch
    end
end
end

function tf = hasChildSafe(node, childName)
try
    tf = node.hasChild(char(childName));
catch
    try
        node.child(char(childName));
        tf = true;
    catch
        tf = false;
    end
end
end

function node = nodeByPath(rootNode, path)
parts = split(string(path), ".");
parts = parts(:);
node = rootNode;
for idx = 1:numel(parts)
    node = node.child(char(parts(idx)));
end
end

function values = numericSeries(node)
values = [];
try
    s = node.series;
    raw = s.values;
    if isnumeric(raw)
        values = raw(:);
    end
catch
end
values = values(isfinite(values));
end

function [minValue, maxValue] = minMaxAcrossSeries(seriesList)
if isempty(seriesList)
    minValue = NaN;
    maxValue = NaN;
    return;
end
values = vertcat(seriesList{:});
if isempty(values)
    minValue = NaN;
    maxValue = NaN;
else
    minValue = min(values);
    maxValue = max(values);
end
end

function value = maxAbsDeviation(seriesList, nominal)
if isempty(seriesList)
    value = NaN;
    return;
end
values = vertcat(seriesList{:});
if isempty(values)
    value = NaN;
else
    value = max(abs(values - nominal));
end
end

function separation = maxSeparationAcrossSeries(seriesList)
if numel(seriesList) < 2
    separation = NaN;
    return;
end
minLength = min(cellfun(@numel, seriesList));
if minLength == 0
    separation = NaN;
    return;
end
matrix = zeros(minLength, numel(seriesList));
for idx = 1:numel(seriesList)
    matrix(:, idx) = seriesList{idx}(1:minLength);
end
spread = max(matrix, [], 2) - min(matrix, [], 2);
separation = max(abs(spread)) * 180.0 / pi;
end

function status = measurementStatus(hasVoltage, hasSpeed, hasAngle)
if hasVoltage && hasSpeed && hasAngle
    status = "voltage_speed_angle";
elseif hasVoltage && hasSpeed
    status = "voltage_and_speed";
elseif hasVoltage
    status = "voltage_only";
elseif hasSpeed || hasAngle
    status = "partial";
else
    status = "none";
end
end

function text = sourceText(sources)
if isempty(sources)
    text = "";
else
    text = char(strjoin(sources(1:min(5, numel(sources))), ";"));
end
end

function text = buildSourceSummary(summary)
parts = strings(0, 1);
if summary.num_voltage_signals_found > 0
    parts(end+1) = "voltage=generator_terminal_voltage_pu"; %#ok<AGROW>
end
if summary.num_speed_signals_found > 0
    parts(end+1) = "speed=generator_rotor_velocity_pu"; %#ok<AGROW>
    parts(end+1) = "frequency=generator_speed_proxy"; %#ok<AGROW>
end
if summary.num_rotor_angle_signals_found > 0
    parts(end+1) = "rotor_angle=generator_rotor_electrical_angle"; %#ok<AGROW>
end
if isempty(parts)
    text = "no_dynamic_measurement_series_found";
else
    text = char(strjoin(parts, ";"));
end
end

function writeDebugRecord(outputDir, summary, debug)
debugPath = fullfile(outputDir, "ieee39_signal_extraction_debug.json");
records = {};
if isfile(debugPath)
    try
        existing = jsondecode(fileread(debugPath));
        if isfield(existing, "records")
            if iscell(existing.records)
                records = existing.records;
            else
                for idx = 1:numel(existing.records)
                    records{end+1} = existing.records(idx); %#ok<AGROW>
                end
            end
        else
            records{end+1} = existing;
        end
    catch
        records = {};
    end
end
record = summary;
record.debug = debug;
records{end+1} = record;
payload = struct("records", {records});
fid = fopen(debugPath, "w");
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, "%s", jsonencode(payload, PrettyPrint=true));
end
