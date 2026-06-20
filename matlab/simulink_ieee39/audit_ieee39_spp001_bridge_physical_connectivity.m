function report = audit_ieee39_spp001_bridge_physical_connectivity(localBridgePath, l15SourcePath, l04SourcePath, outputJsonPath)
%AUDIT_IEEE39_SPP001_BRIDGE_PHYSICAL_CONNECTIVITY Static connectivity audit.
%
% This script loads the local SPP001 bridge and source lab models for static
% port/line inspection only. It never calls sim(), never exports labels, never
% saves models, and never writes raw trajectories, full timeseries, or MAT files.

arguments
    localBridgePath (1, :) char
    l15SourcePath (1, :) char
    l04SourcePath (1, :) char
    outputJsonPath (1, :) char
end

modelsToClose = strings(0, 1);
cleanup = onCleanup(@() closeLoadedModels(modelsToClose));

report = struct();
report.audit_scope = "spp001_bridge_physical_connectivity_matlab_static_audit";
report.sim_called = false;
report.update_diagram_called = false;
report.source_slx_modified = false;
report.local_bridge_path = string(localBridgePath);
report.l15_source_path = string(l15SourcePath);
report.l04_source_path = string(l04SourcePath);
report.local_bridge_loaded_for_static_audit = false;
report.matlab_error = "";

try
    [bridgeModel, modelsToClose] = loadModelStatic(localBridgePath, modelsToClose);
    [l15Model, modelsToClose] = loadModelStatic(l15SourcePath, modelsToClose);
    [l04Model, modelsToClose] = loadModelStatic(l04SourcePath, modelsToClose);
    report.local_bridge_loaded_for_static_audit = true;
    report.bridge_model = string(bridgeModel);
    report.l15_source_model = string(l15Model);
    report.l04_source_model = string(l04Model);

    report.l15_bridge = inspectLineInModel(bridgeModel, "L15");
    report.l04_bridge = inspectLineInModel(bridgeModel, "L04");
    report.l15_source = inspectLineInModel(l15Model, "L15");
    report.l04_source = inspectLineInModel(l04Model, "L04");
    report.bridge_unconnected_ports = findUnconnectedPorts(bridgeModel, ["L15_HandwiredTimedBreaker", "L04_HandwiredTimedBreaker", "L15_TripCommand", "L04_TripCommand"]);
    report.l15_topology_comparison = compareTopology(report.l15_bridge, report.l15_source);
    report.l04_topology_comparison = compareTopology(report.l04_bridge, report.l04_source);
catch ME
    report.matlab_error = string(ME.identifier) + ": " + string(ME.message);
end

writeJson(outputJsonPath, report);
end

function [modelName, modelsToClose] = loadModelStatic(modelPath, modelsToClose)
[~, modelName, ~] = fileparts(modelPath);
load_system(modelPath);
modelsToClose(end + 1, 1) = string(modelName);
end

function closeLoadedModels(modelsToClose)
for idx = numel(modelsToClose):-1:1
    try
        close_system(char(modelsToClose(idx)), 0);
    catch
    end
end
end

function info = inspectLineInModel(modelName, lineId)
breakerName = lineId + "_HandwiredTimedBreaker";
commandName = lineId + "_TripCommand";
breakerBlocks = find_system(modelName, "LookUnderMasks", "all", "FollowLinks", "on", "Name", char(breakerName));
commandBlocks = find_system(modelName, "LookUnderMasks", "all", "FollowLinks", "on", "Name", char(commandName));

info = struct();
info.model = string(modelName);
info.line_id = string(lineId);
info.breaker_name = breakerName;
info.command_name = commandName;
info.breaker_block_exists = ~isempty(breakerBlocks);
info.trip_command_block_exists = ~isempty(commandBlocks);
info.breaker_block_path = "";
info.trip_command_block_path = "";
info.trip_command_to_breaker_control_connected = false;
info.breaker_physical_ports_connected = false;
info.breaker_in_series_with_actual_branch = false;
info.breaker_physical_port_inventory = struct([]);
info.trip_command_signal_trace = struct([]);
info.breaker_neighbor_signature = strings(0, 1);
info.branch_name_matches_line_context = false;
info.unconnected_ports = struct([]);
info.audit_note = "static block-port and line-handle audit only; no sim()";

if info.breaker_block_exists
    info.breaker_block_path = string(breakerBlocks{1});
    [portsConnected, portInventory, neighbors] = inspectBreakerPhysicalPorts(breakerBlocks{1});
    info.breaker_physical_ports_connected = portsConnected;
    info.breaker_physical_port_inventory = portInventory;
    info.breaker_neighbor_signature = neighbors;
    info.branch_name_matches_line_context = any(contains(lower(neighbors), lower(lineId))) || any(contains(lower(neighbors), lineContextHint(lineId)));
    info.breaker_in_series_with_actual_branch = info.breaker_physical_ports_connected && info.branch_name_matches_line_context;
    info.unconnected_ports = findUnconnectedPortsForBlock(breakerBlocks{1});
end
if info.trip_command_block_exists
    info.trip_command_block_path = string(commandBlocks{1});
end
if info.trip_command_block_exists && info.breaker_block_exists
    [connected, trace] = traceSignalConnectivity(commandBlocks{1}, breakerBlocks{1});
    info.trip_command_to_breaker_control_connected = connected;
    info.trip_command_signal_trace = trace;
end
end

function hint = lineContextHint(lineId)
switch string(lineId)
    case "L04"
        hint = "b3";
    case "L15"
        hint = "b";
    otherwise
        hint = lower(string(lineId));
end
end

function [portsConnected, portInventory, neighbors] = inspectBreakerPhysicalPorts(blockPath)
handles = get_param(blockPath, "PortHandles");
physicalPorts = [];
portKinds = strings(0, 1);
for fieldName = ["LConn", "RConn", "PMIOPort"]
    if isfield(handles, fieldName)
        values = handles.(fieldName);
        physicalPorts = [physicalPorts, values(:)']; %#ok<AGROW>
        portKinds = [portKinds; repmat(fieldName, numel(values), 1)]; %#ok<AGROW>
    end
end
portInventory = struct([]);
neighbors = strings(0, 1);
if isempty(physicalPorts)
    portsConnected = false;
    return;
end
connectedFlags = false(numel(physicalPorts), 1);
for idx = 1:numel(physicalPorts)
    lineHandle = get_param(physicalPorts(idx), "Line");
    neighborBlocks = neighborBlocksForPortLine(lineHandle, blockPath);
    connectedFlags(idx) = lineHandle ~= -1 && ~isempty(neighborBlocks);
    portInventory(idx).port_kind = portKinds(idx);
    portInventory(idx).port_handle = double(physicalPorts(idx));
    portInventory(idx).line_handle = double(lineHandle);
    portInventory(idx).connected = connectedFlags(idx);
    portInventory(idx).neighbor_blocks = neighborBlocks;
    neighbors = [neighbors; string(neighborBlocks(:))]; %#ok<AGROW>
end
portsConnected = all(connectedFlags);
neighbors = unique(neighbors);
end

function neighbors = neighborBlocksForPortLine(lineHandle, ownBlock)
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
        if strlength(parent) > 0 && parent ~= string(ownBlock)
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
while ~isempty(queue) && depth < 12
    current = queue(1);
    queue(1) = [];
    if any(visited == current)
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
        continue;
    end
    outports = [];
    for fieldName = ["Outport", "RConn", "LConn"]
        if isfield(handles, fieldName)
            outports = [outports, handles.(fieldName)(:)']; %#ok<AGROW>
        end
    end
    for pIdx = 1:numel(outports)
        try
            lineHandle = get_param(outports(pIdx), "Line");
        catch
            lineHandle = -1;
        end
        destinations = destinationBlocksForLine(lineHandle);
        for dIdx = 1:numel(destinations)
            nextBlock = destinations(dIdx);
            step = numel(trace) + 1;
            trace(step).from_block = current;
            trace(step).to_block = nextBlock;
            trace(step).line_handle = double(lineHandle);
            if nextBlock == string(breakerBlock)
                connected = true;
            end
            if ~any(visited == nextBlock)
                queue(end + 1, 1) = nextBlock; %#ok<AGROW>
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

function ports = findUnconnectedPorts(modelName, blockNames)
ports = struct([]);
for bIdx = 1:numel(blockNames)
    blocks = find_system(modelName, "LookUnderMasks", "all", "FollowLinks", "on", "Name", char(blockNames(bIdx)));
    if isempty(blocks)
        continue;
    end
    blockPorts = findUnconnectedPortsForBlock(blocks{1});
    for idx = 1:numel(blockPorts)
        next = numel(ports) + 1;
        ports(next).block = string(blockPorts(idx).block); %#ok<AGROW>
        ports(next).port_kind = string(blockPorts(idx).port_kind);
        ports(next).port_handle = double(blockPorts(idx).port_handle);
        ports(next).line_handle = double(blockPorts(idx).line_handle);
    end
end
end

function ports = findUnconnectedPortsForBlock(blockPath)
ports = struct([]);
try
    handles = get_param(blockPath, "PortHandles");
catch
    return;
end
fields = string(fieldnames(handles));
for fIdx = 1:numel(fields)
    fieldName = fields(fIdx);
    values = handles.(fieldName);
    for vIdx = 1:numel(values)
        portHandle = values(vIdx);
        if portHandle == -1
            continue;
        end
        try
            lineHandle = get_param(portHandle, "Line");
        catch
            lineHandle = -1;
        end
        if isempty(lineHandle) || lineHandle == -1
            next = numel(ports) + 1;
            ports(next).block = string(blockPath);
            ports(next).port_kind = fieldName;
            ports(next).port_handle = double(portHandle);
            ports(next).line_handle = -1;
        end
    end
end
end

function comparison = compareTopology(bridgeInfo, sourceInfo)
bridgeSig = sort(string(bridgeInfo.breaker_neighbor_signature));
sourceSig = sort(string(sourceInfo.breaker_neighbor_signature));
comparison = struct();
comparison.line_id = bridgeInfo.line_id;
comparison.bridge_neighbors = bridgeSig;
comparison.source_neighbors = sourceSig;
comparison.same_neighbor_count = numel(bridgeSig) == numel(sourceSig);
comparison.shared_neighbor_count = numel(intersect(bridgeSig, sourceSig));
comparison.topology_signature_matches_source = comparison.same_neighbor_count && comparison.shared_neighbor_count == numel(sourceSig) && sourceInfo.breaker_physical_ports_connected;
comparison.audit_note = "name-normalized graph comparison is conservative; mismatch blocks execution";
end

function writeJson(path, payload)
folder = fileparts(path);
if ~exist(folder, "dir")
    mkdir(folder);
end
fid = fopen(path, "w");
if fid < 0
    error("IEEE39SPP001ConnectivityAudit:WriteFailed", "Cannot write %s", path);
end
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, "%s", jsonencode(payload, PrettyPrint=true));
clear cleanup;
end
