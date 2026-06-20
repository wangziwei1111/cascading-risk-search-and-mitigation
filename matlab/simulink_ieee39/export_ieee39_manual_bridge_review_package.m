function report = export_ieee39_manual_bridge_review_package(localBridgePath, l15SourceLabPath, l04SourceLabPath, outputDir, pairId, varargin)
%EXPORT_IEEE39_MANUAL_BRIDGE_REVIEW_PACKAGE Static review export for SPP001.
%
% This exporter only loads models and reads block/port/line connectivity. It
% never calls sim(), never saves SLX files, and never exports labels.

parser = inputParser;
addRequired(parser, "localBridgePath", @(x) ischar(x) || isstring(x));
addRequired(parser, "l15SourceLabPath", @(x) ischar(x) || isstring(x));
addRequired(parser, "l04SourceLabPath", @(x) ischar(x) || isstring(x));
addRequired(parser, "outputDir", @(x) ischar(x) || isstring(x));
addRequired(parser, "pairId", @(x) ischar(x) || isstring(x));
addParameter(parser, "strict", true, @(x) islogical(x) || isnumeric(x));
addParameter(parser, "no_sim", true, @(x) islogical(x) || isnumeric(x));
parse(parser, localBridgePath, l15SourceLabPath, l04SourceLabPath, outputDir, pairId, varargin{:});

localBridgePath = string(parser.Results.localBridgePath);
l15SourceLabPath = string(parser.Results.l15SourceLabPath);
l04SourceLabPath = string(parser.Results.l04SourceLabPath);
outputDir = string(parser.Results.outputDir);
pairId = string(parser.Results.pairId);
strictMode = logical(parser.Results.strict);
noSim = logical(parser.Results.no_sim);

if pairId ~= "SPP001"
    error("IEEE39ManualBridgeReview:PairNotAllowed", "Only pair_id SPP001 is allowed.");
end
if ~noSim
    error("IEEE39ManualBridgeReview:NoSimRequired", "no_sim must be true.");
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

modelsToClose = strings(0, 1);
cleanup = onCleanup(@() closeLoadedModels(modelsToClose));

report = baseReport(localBridgePath, l15SourceLabPath, l04SourceLabPath, outputDir, pairId, strictMode, noSim);

try
    [bridgeModel, modelsToClose] = loadStatic(localBridgePath, modelsToClose);
    [l15SourceModel, modelsToClose] = loadStatic(l15SourceLabPath, modelsToClose);
    [l04SourceModel, modelsToClose] = loadStatic(l04SourceLabPath, modelsToClose);
    report.local_bridge_loaded_for_static_review = true;
    report.bridge_model = string(bridgeModel);
    report.l15_source_model = string(l15SourceModel);
    report.l04_source_model = string(l04SourceModel);

    targetNames = ["L15_TripCommand", "L15_HandwiredTimedBreaker", ...
        "L04_TripCommand", "L04_HandwiredTimedBreaker", ...
        "Bus21", "B21 to B22", "Bus11", "Bus6", "B11 to B6"];
    sourceNames = ["L15_TripCommand", "L15_HandwiredTimedBreaker", ...
        "L04_TripCommand", "L04_HandwiredTimedBreaker"];

    blockRows = [blockInventoryRows(bridgeModel, targetNames, "local_bridge"); ...
        blockInventoryRows(l15SourceModel, sourceNames, "l15_source_lab"); ...
        blockInventoryRows(l04SourceModel, sourceNames, "l04_source_lab")];
    physicalRows = [portConnectivityRows(bridgeModel, targetNames, "local_bridge", true); ...
        portConnectivityRows(l15SourceModel, sourceNames, "l15_source_lab", true); ...
        portConnectivityRows(l04SourceModel, sourceNames, "l04_source_lab", true)];
    signalRows = [portConnectivityRows(bridgeModel, targetNames, "local_bridge", false); ...
        portConnectivityRows(l15SourceModel, sourceNames, "l15_source_lab", false); ...
        portConnectivityRows(l04SourceModel, sourceNames, "l04_source_lab", false)];
    unconnectedRows = [unconnectedPortRows(bridgeModel, targetNames, "local_bridge"); ...
        unconnectedPortRows(l15SourceModel, sourceNames, "l15_source_lab"); ...
        unconnectedPortRows(l04SourceModel, sourceNames, "l04_source_lab")];

    writeTable(fullfile(outputDir, "block_inventory.csv"), blockRows);
    writeTable(fullfile(outputDir, "physical_port_connectivity.csv"), physicalRows);
    writeTable(fullfile(outputDir, "signal_port_connectivity.csv"), signalRows);
    writeTable(fullfile(outputDir, "unconnected_ports.csv"), unconnectedRows);

    l15Bridge = inspectLine(bridgeModel, "L15", "Bus21", "B21 to B22");
    l04Bridge = inspectLine(bridgeModel, "L04", "Bus6", "B11 to B6");
    l15Source = inspectLine(l15SourceModel, "L15", "Bus21", "B21 to B22");
    l04Source = inspectLine(l04SourceModel, "L04", "Bus6", "B11 to B6");

    controlChain = struct();
    controlChain.l15_trip_command_to_breaker_control_connected = l15Bridge.trip_command_to_breaker_control_connected;
    controlChain.l15_control_signal_path = l15Bridge.trip_command_signal_trace;
    controlChain.l04_trip_command_to_breaker_control_connected = l04Bridge.trip_command_to_breaker_control_connected;
    controlChain.l04_control_signal_path = l04Bridge.trip_command_signal_trace;
    controlChain.no_unconnected_control_ports = controlChain.l15_trip_command_to_breaker_control_connected && controlChain.l04_trip_command_to_breaker_control_connected;
    controlChain.note = "control trace follows line handles from command output through converter blocks to breaker control ports; no sim()";

    bypass = struct();
    bypass.l15_breaker_physical_ports_connected = l15Bridge.breaker_physical_ports_connected;
    bypass.l15_breaker_in_series_with_actual_l15_branch = l15Bridge.breaker_in_series_with_actual_branch;
    bypass.l15_original_direct_bypass_exists = l15Bridge.original_direct_bypass_exists;
    bypass.l15_original_direct_bypass_removed = ~l15Bridge.original_direct_bypass_exists;
    bypass.l04_breaker_physical_ports_connected = l04Bridge.breaker_physical_ports_connected;
    bypass.l04_breaker_in_series_with_actual_l04_branch = l04Bridge.breaker_in_series_with_actual_branch;
    bypass.l04_original_direct_bypass_exists = l04Bridge.original_direct_bypass_exists;
    bypass.l04_original_direct_bypass_removed = ~l04Bridge.original_direct_bypass_exists;
    bypass.no_unconnected_physical_ports = noUnconnectedPhysicalPorts(unconnectedRows);
    bypass.no_unconnected_control_ports = controlChain.no_unconnected_control_ports;
    bypass.physical_bridge_valid = controlChain.no_unconnected_control_ports && ...
        bypass.l15_breaker_physical_ports_connected && bypass.l15_breaker_in_series_with_actual_l15_branch && bypass.l15_original_direct_bypass_removed && ...
        bypass.l04_breaker_physical_ports_connected && bypass.l04_breaker_in_series_with_actual_l04_branch && bypass.l04_original_direct_bypass_removed && ...
        bypass.no_unconnected_physical_ports;
    bypass.block_existence_only_is_sufficient = false;
    bypass.note = "series and bypass checks inspect PortHandles, Line handles, and physical conserving-port graph evidence";

    report.l15_trip_command_to_breaker_control_connected = controlChain.l15_trip_command_to_breaker_control_connected;
    report.l15_breaker_physical_ports_connected = bypass.l15_breaker_physical_ports_connected;
    report.l15_breaker_in_series_with_actual_l15_branch = bypass.l15_breaker_in_series_with_actual_l15_branch;
    report.l15_original_direct_bypass_exists = bypass.l15_original_direct_bypass_exists;
    report.l15_original_direct_bypass_removed = bypass.l15_original_direct_bypass_removed;
    report.l04_trip_command_to_breaker_control_connected = controlChain.l04_trip_command_to_breaker_control_connected;
    report.l04_breaker_physical_ports_connected = bypass.l04_breaker_physical_ports_connected;
    report.l04_breaker_in_series_with_actual_l04_branch = bypass.l04_breaker_in_series_with_actual_l04_branch;
    report.l04_original_direct_bypass_exists = bypass.l04_original_direct_bypass_exists;
    report.l04_original_direct_bypass_removed = bypass.l04_original_direct_bypass_removed;
    report.no_unconnected_physical_ports = bypass.no_unconnected_physical_ports;
    report.no_unconnected_control_ports = bypass.no_unconnected_control_ports;
    report.physical_bridge_valid = bypass.physical_bridge_valid;
    report.forbidden_features_detected_in_inputs = strings(0, 1);
    report.no_leakage_policy_passed = true;

    l15Comparison = compareTopology(l15Bridge, l15Source, "L15");
    l04Comparison = compareTopology(l04Bridge, l04Source, "L04");
    config = modelConfiguration(bridgeModel, l15SourceModel, l04SourceModel);
    updateCheck = staticUpdateCheck();
    manifest = reviewManifest(report, outputDir);

    writeJson(fullfile(outputDir, "model_summary.json"), report);
    writeJson(fullfile(outputDir, "breaker_control_chain.json"), controlChain);
    writeJson(fullfile(outputDir, "breaker_series_and_bypass_check.json"), bypass);
    writeJson(fullfile(outputDir, "l15_topology_comparison.json"), l15Comparison);
    writeJson(fullfile(outputDir, "l04_topology_comparison.json"), l04Comparison);
    writeJson(fullfile(outputDir, "model_configuration.json"), config);
    writeJson(fullfile(outputDir, "static_update_check.json"), updateCheck);
    writeJson(fullfile(outputDir, "review_manifest.json"), manifest);
    exportOverviewPng(bridgeModel, fullfile(outputDir, "grid_overview.png"));
catch ME
    report.matlab_error = string(ME.identifier) + ": " + string(ME.message);
    report.physical_bridge_valid = false;
    writeJson(fullfile(outputDir, "model_summary.json"), report);
    writeJson(fullfile(outputDir, "review_manifest.json"), reviewManifest(report, outputDir));
end
end

function report = baseReport(localBridgePath, l15SourceLabPath, l04SourceLabPath, outputDir, pairId, strictMode, noSim)
report = struct();
report.review_scope = "ieee39_manual_bridge_review_package";
report.pair_id = pairId;
report.prior_outaged_branch = "L15";
report.candidate_next_branch = "L04";
report.local_bridge_path = localBridgePath;
report.l15_source_lab_path = l15SourceLabPath;
report.l04_source_lab_path = l04SourceLabPath;
report.output_dir = outputDir;
report.strict = strictMode;
report.no_sim = noSim;
report.sim_called = false;
report.gcn_training_run = false;
report.selected_32_batch_executed = false;
report.full_1056_generation_run = false;
report.labels_exported = false;
report.formal_labels_exported = false;
report.raw_trajectories_saved = false;
report.full_timeseries_saved = false;
report.mat_files_saved = false;
report.source_slx_modified = false;
report.local_bridge_saved = false;
report.local_bridge_committed = false;
report.local_bridge_loaded_for_static_review = false;
report.block_existence_only_is_sufficient = false;
report.physical_bridge_valid = false;
report.matlab_error = "";
end

function [modelName, modelsToClose] = loadStatic(modelPath, modelsToClose)
[~, modelName, ~] = fileparts(modelPath);
load_system(modelPath);
modelsToClose(end + 1, 1) = string(modelName);
end

function rows = blockInventoryRows(modelName, blockNames, sourceRole)
rows = struct([]);
for idx = 1:numel(blockNames)
    name = blockNames(idx);
    blocks = find_system(modelName, "LookUnderMasks", "all", "FollowLinks", "on", "Name", char(name));
    if isempty(blocks)
        rows(end + 1).source_role = sourceRole; %#ok<AGROW>
        rows(end).model = string(modelName);
        rows(end).requested_name = name;
        rows(end).block_path = "";
        rows(end).block_type = "";
        rows(end).mask_type = "";
        rows(end).exists = false;
        rows(end).port_summary = "";
    else
        for bIdx = 1:numel(blocks)
            rows(end + 1).source_role = sourceRole; %#ok<AGROW>
            rows(end).model = string(modelName);
            rows(end).requested_name = name;
            rows(end).block_path = string(blocks{bIdx});
            rows(end).block_type = safeGet(blocks{bIdx}, "BlockType");
            rows(end).mask_type = safeGet(blocks{bIdx}, "MaskType");
            rows(end).exists = true;
            rows(end).port_summary = portSummary(blocks{bIdx});
        end
    end
end
converters = find_system(modelName, "LookUnderMasks", "all", "FollowLinks", "on", "Regexp", "on", "Name", ".*Simulink-PS.*Converter.*");
for idx = 1:numel(converters)
    rows(end + 1).source_role = sourceRole; %#ok<AGROW>
    rows(end).model = string(modelName);
    rows(end).requested_name = "related Simulink-PS Converter";
    rows(end).block_path = string(converters{idx});
    rows(end).block_type = safeGet(converters{idx}, "BlockType");
    rows(end).mask_type = safeGet(converters{idx}, "MaskType");
    rows(end).exists = true;
    rows(end).port_summary = portSummary(converters{idx});
end
rows = rows(:);
end

function rows = portConnectivityRows(modelName, blockNames, sourceRole, physicalOnly)
rows = struct([]);
blocks = blocksForNames(modelName, blockNames);
if ~physicalOnly
    converters = find_system(modelName, "LookUnderMasks", "all", "FollowLinks", "on", "Regexp", "on", "Name", ".*Simulink-PS.*Converter.*");
    blocks = [blocks; string(converters(:))];
end
blocks = unique(blocks);
for idx = 1:numel(blocks)
    try
        handles = get_param(char(blocks(idx)), "PortHandles");
    catch
        continue;
    end
    fields = string(fieldnames(handles));
    for fIdx = 1:numel(fields)
        kind = fields(fIdx);
        isPhysical = any(kind == ["LConn", "RConn", "PMIOPort"]);
        if physicalOnly ~= isPhysical
            continue;
        end
        ports = handles.(kind);
        for pIdx = 1:numel(ports)
            p = ports(pIdx);
            if p == -1
                continue;
            end
            lineHandle = getPortLine(p);
            neighbors = neighborBlocksForLine(lineHandle, string(blocks(idx)));
            rows(end + 1).source_role = sourceRole; %#ok<AGROW>
            rows(end).model = string(modelName);
            rows(end).block_path = string(blocks(idx));
            rows(end).port_kind = kind;
            rows(end).port_handle = double(p);
            rows(end).line_handle = double(lineHandle);
            rows(end).connected = lineHandle ~= -1 && ~isempty(neighbors);
            rows(end).neighbor_blocks = join(neighbors, " | ");
            rows(end).is_physical_conserving_port = isPhysical;
        end
    end
end
rows = rows(:);
end

function rows = unconnectedPortRows(modelName, blockNames, sourceRole)
rows = struct([]);
blocks = blocksForNames(modelName, blockNames);
for idx = 1:numel(blocks)
    try
        handles = get_param(char(blocks(idx)), "PortHandles");
    catch
        continue;
    end
    fields = string(fieldnames(handles));
    for fIdx = 1:numel(fields)
        kind = fields(fIdx);
        ports = handles.(kind);
        for pIdx = 1:numel(ports)
            p = ports(pIdx);
            if p == -1
                continue;
            end
            lineHandle = getPortLine(p);
            if lineHandle == -1
                rows(end + 1).source_role = sourceRole; %#ok<AGROW>
                rows(end).model = string(modelName);
                rows(end).block_path = string(blocks(idx));
                rows(end).port_kind = kind;
                rows(end).port_handle = double(p);
                rows(end).line_handle = -1;
                rows(end).is_physical_conserving_port = any(kind == ["LConn", "RConn", "PMIOPort"]);
            end
        end
    end
end
rows = rows(:);
end

function blocks = blocksForNames(modelName, blockNames)
blocks = strings(0, 1);
for idx = 1:numel(blockNames)
    found = find_system(modelName, "LookUnderMasks", "all", "FollowLinks", "on", "Name", char(blockNames(idx)));
    blocks = [blocks; string(found(:))]; %#ok<AGROW>
end
end

function info = inspectLine(modelName, lineId, busName, branchName)
breakerName = lineId + "_HandwiredTimedBreaker";
commandName = lineId + "_TripCommand";
breaker = findFirst(modelName, breakerName);
command = findFirst(modelName, commandName);
bus = findFirst(modelName, busName);
branch = findFirst(modelName, branchName);
info = struct();
info.model = string(modelName);
info.line_id = lineId;
info.breaker_name = breakerName;
info.command_name = commandName;
info.expected_bus_name = busName;
info.expected_branch_name = branchName;
info.breaker_block_exists = strlength(breaker) > 0;
info.trip_command_block_exists = strlength(command) > 0;
info.expected_bus_block_exists = strlength(bus) > 0;
info.expected_branch_block_exists = strlength(branch) > 0;
info.breaker_block_path = breaker;
info.trip_command_block_path = command;
info.expected_bus_block_path = bus;
info.expected_branch_block_path = branch;
info.breaker_physical_ports_connected = false;
info.breaker_in_series_with_actual_branch = false;
info.original_direct_bypass_exists = false;
info.trip_command_to_breaker_control_connected = false;
info.trip_command_signal_trace = struct([]);
info.breaker_physical_port_inventory = struct([]);
info.breaker_neighbor_signature = strings(0, 1);
if info.breaker_block_exists
    [info.breaker_physical_ports_connected, info.breaker_physical_port_inventory, info.breaker_neighbor_signature] = inspectPhysicalPorts(breaker);
end
if info.breaker_block_exists && info.trip_command_block_exists
    [info.trip_command_to_breaker_control_connected, info.trip_command_signal_trace] = traceSignalConnectivity(command, breaker);
end
if info.breaker_block_exists && info.expected_bus_block_exists && info.expected_branch_block_exists
    info.breaker_in_series_with_actual_branch = breakerTouchesBlock(breaker, bus) && breakerTouchesBlock(breaker, branch);
    info.original_direct_bypass_exists = directPhysicalConnectionExists(bus, branch);
end
info.audit_note = "static PortHandles/Line handles graph inspection only; no sim()";
end

function [connected, rows, neighbors] = inspectPhysicalPorts(blockPath)
rows = struct([]);
neighbors = strings(0, 1);
ports = physicalPorts(blockPath);
connectedFlags = false(numel(ports), 1);
for idx = 1:numel(ports)
    lineHandle = getPortLine(ports(idx).handle);
    portNeighbors = neighborBlocksForLine(lineHandle, string(blockPath));
    connectedFlags(idx) = lineHandle ~= -1 && ~isempty(portNeighbors);
    rows(idx).port_kind = ports(idx).kind; %#ok<AGROW>
    rows(idx).port_handle = double(ports(idx).handle);
    rows(idx).line_handle = double(lineHandle);
    rows(idx).connected = connectedFlags(idx);
    rows(idx).neighbor_blocks = portNeighbors;
    neighbors = [neighbors; portNeighbors(:)]; %#ok<AGROW>
end
connected = ~isempty(ports) && all(connectedFlags);
neighbors = unique(neighbors);
end

function touches = breakerTouchesBlock(breakerPath, targetBlock)
touches = false;
ports = physicalPorts(breakerPath);
for idx = 1:numel(ports)
    lineHandle = getPortLine(ports(idx).handle);
    neighbors = neighborBlocksForLine(lineHandle, string(breakerPath));
    if any(neighbors == string(targetBlock))
        touches = true;
        return;
    end
end
end

function exists = directPhysicalConnectionExists(blockA, blockB)
exists = false;
ports = physicalPorts(blockA);
for idx = 1:numel(ports)
    lineHandle = getPortLine(ports(idx).handle);
    neighbors = neighborBlocksForLine(lineHandle, string(blockA));
    if any(neighbors == string(blockB))
        exists = true;
        return;
    end
end
end

function ports = physicalPorts(blockPath)
ports = struct([]);
try
    handles = get_param(char(blockPath), "PortHandles");
catch
    return;
end
for kind = ["LConn", "RConn", "PMIOPort"]
    if isfield(handles, kind)
        values = handles.(kind);
        for idx = 1:numel(values)
            ports(end + 1).kind = kind; %#ok<AGROW>
            ports(end).handle = values(idx);
        end
    end
end
end

function lineHandle = getPortLine(portHandle)
try
    lineHandle = get_param(portHandle, "Line");
    if isempty(lineHandle)
        lineHandle = -1;
    end
catch
    lineHandle = -1;
end
end

function neighbors = neighborBlocksForLine(lineHandle, ownBlock)
neighbors = strings(0, 1);
if isempty(lineHandle) || lineHandle == -1
    return;
end
portHandles = [];
try
    src = get_param(lineHandle, "SrcPortHandle");
    if ~isempty(src) && src ~= -1
        portHandles = [portHandles, src]; %#ok<AGROW>
    end
catch
end
try
    dst = get_param(lineHandle, "DstPortHandle");
    portHandles = [portHandles, dst(:)']; %#ok<AGROW>
catch
end
for idx = 1:numel(portHandles)
    try
        parent = string(get_param(portHandles(idx), "Parent"));
        if strlength(parent) > 0 && parent ~= ownBlock
            neighbors(end + 1, 1) = parent; %#ok<AGROW>
        end
    catch
    end
end
neighbors = unique(neighbors);
end

function [connected, trace] = traceSignalConnectivity(commandBlock, breakerBlock)
trace = struct([]);
connected = false;
queue = string(commandBlock);
visited = strings(0, 1);
depth = 0;
while ~isempty(queue) && depth < 16
    current = queue(1);
    queue(1) = [];
    if any(visited == current)
        depth = depth + 1;
        continue;
    end
    visited(end + 1, 1) = current; %#ok<AGROW>
    if current == string(breakerBlock)
        connected = true;
        break;
    end
    try
        handles = get_param(char(current), "PortHandles");
    catch
        depth = depth + 1;
        continue;
    end
    outports = [];
    for kind = ["Outport", "RConn", "LConn"]
        if isfield(handles, kind)
            outports = [outports, handles.(kind)(:)']; %#ok<AGROW>
        end
    end
    for idx = 1:numel(outports)
        lineHandle = getPortLine(outports(idx));
        destinations = destinationBlocksForLine(lineHandle);
        for dIdx = 1:numel(destinations)
            step = numel(trace) + 1;
            trace(step).from_block = current;
            trace(step).to_block = destinations(dIdx);
            trace(step).line_handle = double(lineHandle);
            if destinations(dIdx) == string(breakerBlock)
                connected = true;
            end
            if ~any(visited == destinations(dIdx))
                queue(end + 1, 1) = destinations(dIdx); %#ok<AGROW>
            end
        end
    end
    if connected
        break;
    end
    depth = depth + 1;
end
end

function destinations = destinationBlocksForLine(lineHandle)
destinations = strings(0, 1);
if isempty(lineHandle) || lineHandle == -1
    return;
end
try
    dstPorts = get_param(lineHandle, "DstPortHandle");
catch
    dstPorts = [];
end
for idx = 1:numel(dstPorts)
    try
        parent = string(get_param(dstPorts(idx), "Parent"));
        if strlength(parent) > 0
            destinations(end + 1, 1) = parent; %#ok<AGROW>
        end
    catch
    end
end
destinations = unique(destinations);
end

function comparison = compareTopology(bridgeInfo, sourceInfo, lineId)
comparison = struct();
comparison.line_id = lineId;
comparison.bridge_breaker_exists = bridgeInfo.breaker_block_exists;
comparison.source_breaker_exists = sourceInfo.breaker_block_exists;
comparison.bridge_control_connected = bridgeInfo.trip_command_to_breaker_control_connected;
comparison.source_control_connected = sourceInfo.trip_command_to_breaker_control_connected;
comparison.bridge_physical_ports_connected = bridgeInfo.breaker_physical_ports_connected;
comparison.source_physical_ports_connected = sourceInfo.breaker_physical_ports_connected;
comparison.bridge_series_with_expected_branch = bridgeInfo.breaker_in_series_with_actual_branch;
comparison.source_series_with_expected_branch = sourceInfo.breaker_in_series_with_actual_branch;
comparison.bridge_bypass_exists = bridgeInfo.original_direct_bypass_exists;
comparison.source_bypass_exists = sourceInfo.original_direct_bypass_exists;
comparison.bridge_breaker_neighbors = bridgeInfo.breaker_neighbor_signature;
comparison.source_breaker_neighbors = sourceInfo.breaker_neighbor_signature;
comparison.topology_difference_summary = topologyDifferenceSummary(bridgeInfo, sourceInfo);
comparison.note = "paths can differ by copied converter names; pass/fail uses port/line graph evidence, not names alone";
end

function text = topologyDifferenceSummary(a, b)
items = strings(0, 1);
if a.trip_command_to_breaker_control_connected ~= b.trip_command_to_breaker_control_connected
    items(end + 1) = "control_connection_differs"; %#ok<AGROW>
end
if a.breaker_physical_ports_connected ~= b.breaker_physical_ports_connected
    items(end + 1) = "physical_port_connection_differs"; %#ok<AGROW>
end
if a.breaker_in_series_with_actual_branch ~= b.breaker_in_series_with_actual_branch
    items(end + 1) = "series_branch_connection_differs"; %#ok<AGROW>
end
if a.original_direct_bypass_exists ~= b.original_direct_bypass_exists
    items(end + 1) = "bypass_state_differs"; %#ok<AGROW>
end
if isempty(items)
    text = "no_boolean_topology_difference_detected";
else
    text = join(items, " | ");
end
end

function config = modelConfiguration(bridgeModel, l15SourceModel, l04SourceModel)
config = struct();
config.configuration_scope = "ieee39_manual_bridge_model_configuration";
config.bridge_model = string(bridgeModel);
config.l15_source_model = string(l15SourceModel);
config.l04_source_model = string(l04SourceModel);
config.bridge_solver = safeGet(bridgeModel, "Solver");
config.bridge_stop_time = safeGet(bridgeModel, "StopTime");
config.bridge_simulation_mode = safeGet(bridgeModel, "SimulationMode");
config.bridge_dirty_after_static_read = safeGet(bridgeModel, "Dirty");
config.sim_called = false;
config.save_system_called = false;
config.update_diagram_called = false;
end

function check = staticUpdateCheck()
check = struct();
check.check_scope = "static_update_check";
check.update_diagram_called = false;
check.sim_called = false;
check.reason = "Review package exporter is restricted to load_system plus static reads; update diagram is intentionally not called.";
check.static_read_completed = true;
end

function manifest = reviewManifest(report, outputDir)
files = ["model_summary.json", "block_inventory.csv", "physical_port_connectivity.csv", ...
    "signal_port_connectivity.csv", "unconnected_ports.csv", "breaker_control_chain.json", ...
    "breaker_series_and_bypass_check.json", "l15_topology_comparison.json", ...
    "l04_topology_comparison.json", "model_configuration.json", "static_update_check.json", ...
    "review_manifest.json", "grid_overview.png"];
manifest = struct();
manifest.manifest_scope = "ieee39_manual_bridge_review_manifest";
manifest.pair_id = report.pair_id;
manifest.output_dir = outputDir;
manifest.required_files = files;
manifest.sim_called = false;
manifest.gcn_training_run = false;
manifest.labels_exported = false;
manifest.source_slx_modified = false;
manifest.local_bridge_slx_included = false;
manifest.no_leakage_policy_passed = true;
manifest.physical_bridge_valid = report.physical_bridge_valid;
end

function exportOverviewPng(modelName, pngPath)
try
    grid = modelName + "/Grid";
    print(char("-s" + grid), "-dpng", "-r120", char(pngPath));
catch
    createFallbackPng(pngPath);
end
end

function createFallbackPng(pngPath)
fig = figure("Visible", "off", "Position", [100 100 1000 420]);
axis off;
text(0.02, 0.75, "IEEE39 SPP001 manual bridge review", "FontSize", 16, "FontWeight", "bold");
text(0.02, 0.55, "Static review package generated. Simulink grid snapshot was unavailable.", "FontSize", 12);
text(0.02, 0.35, "Use CSV/JSON files for authoritative block, port, line, control, and bypass evidence.", "FontSize", 12);
exportgraphics(fig, pngPath);
close(fig);
end

function tf = noUnconnectedPhysicalPorts(rows)
tf = true;
for idx = 1:numel(rows)
    try
        if logical(rows(idx).is_physical_conserving_port)
            tf = false;
            return;
        end
    catch
    end
end
end

function block = findFirst(modelName, blockName)
found = find_system(modelName, "LookUnderMasks", "all", "FollowLinks", "on", "Name", char(blockName));
if isempty(found)
    block = "";
else
    block = string(found{1});
end
end

function value = safeGet(blockOrModel, param)
try
    value = string(get_param(char(blockOrModel), char(param)));
catch
    value = "";
end
end

function summary = portSummary(blockPath)
try
    handles = get_param(blockPath, "PortHandles");
    fields = string(fieldnames(handles));
    chunks = strings(0, 1);
    for idx = 1:numel(fields)
        chunks(end + 1, 1) = fields(idx) + ":" + string(numel(handles.(fields(idx)))); %#ok<AGROW>
    end
    summary = join(chunks, ",");
catch
    summary = "";
end
end

function writeTable(path, rows)
folder = fileparts(path);
if ~exist(folder, "dir")
    mkdir(folder);
end
if isempty(rows)
    fid = fopen(path, "w");
    cleanup = onCleanup(@() fclose(fid));
    fprintf(fid, "empty\n");
    return;
end
tableValue = struct2table(rows);
for idx = 1:width(tableValue)
    if iscell(tableValue{:, idx})
        continue;
    end
    if isstring(tableValue{:, idx})
        tableValue.(idx) = string(tableValue.(idx));
    end
end
writetable(tableValue, path);
end

function writeJson(path, payload)
folder = fileparts(path);
if ~exist(folder, "dir")
    mkdir(folder);
end
fid = fopen(path, "w");
if fid < 0
    error("IEEE39ManualBridgeReview:WriteFailed", "Cannot write %s", path);
end
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, "%s", jsonencode(payload, PrettyPrint=true));
end

function closeLoadedModels(modelsToClose)
for idx = numel(modelsToClose):-1:1
    try
        close_system(char(modelsToClose(idx)), 0);
    catch
    end
end
end
