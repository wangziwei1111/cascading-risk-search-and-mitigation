function summary = build_ieee39_spp001_manual_physical_bridge(outputDir, varargin)
%BUILD_IEEE39_SPP001_MANUAL_PHYSICAL_BRIDGE Build local-only SPP001 bridge.
%
% This builder creates a local ignored SLX copy and attempts to reproduce the
% L15 clean-lab wiring pattern inside a wrapper that already contains L04. It
% performs static gate checks before any caller is allowed to run sim().

parser = inputParser;
addRequired(parser, "outputDir", @(x) ischar(x) || isstring(x));
addParameter(parser, "source_l04_wrapper_path", "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx", @(x) ischar(x) || isstring(x));
addParameter(parser, "source_l15_wrapper_path", "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15.slx", @(x) ischar(x) || isstring(x));
addParameter(parser, "build_local_copy", true, @(x) islogical(x) || isnumeric(x));
addParameter(parser, "run_update_diagram", true, @(x) islogical(x) || isnumeric(x));
parse(parser, outputDir, varargin{:});

outputDir = string(parser.Results.outputDir);
sourceL04 = string(parser.Results.source_l04_wrapper_path);
sourceL15 = string(parser.Results.source_l15_wrapper_path);
buildLocalCopy = logical(parser.Results.build_local_copy);
runUpdateDiagram = logical(parser.Results.run_update_diagram);
targetModelName = "IEEE39BusSystem_dynamic_experiment_wrapper_spp001_manual_physical_bridge";
targetPath = fullfile(outputDir, "local_bridge_copy", targetModelName + ".slx");

summary = baseSummary(targetPath, sourceL04, sourceL15);
modelsToClose = strings(0, 1);
cleanup = onCleanup(@() closeLoadedModels(modelsToClose));

try
    if ~exist(fullfile(outputDir, "local_bridge_copy"), "dir")
        mkdir(fullfile(outputDir, "local_bridge_copy"));
    end
    if ~isfile(sourceL04) || ~isfile(sourceL15)
        summary.blocker_if_any = "source L04 or L15 clean-lab model is missing";
        writeJson(fullfile(outputDir, "matlab_manual_bridge_build_raw.json"), summary);
        return;
    end
    if buildLocalCopy
        copyfile(sourceL04, targetPath, "f");
        modelsToClose(end + 1, 1) = targetModelName;
        load_system(targetPath);
        modelsToClose(end + 1, 1) = modelNameFromPath(sourceL15);
        load_system(sourceL15);
        sourceL15Model = modelNameFromPath(sourceL15);
        ensureNamedBlockCopied(sourceL15Model, targetModelName, "L15_TripCommand");
        ensureNamedBlockCopied(sourceL15Model, targetModelName, "Simulink-PS" + newline + "Converter", "L15_SimulinkPSConverter");
        ensureNamedBlockCopied(sourceL15Model, targetModelName, "L15_HandwiredTimedBreaker");
        summary.manual_bridge_build_attempted = true;
        summary.manual_bridge_built = isfile(targetPath);
        summary.l15_rebuild_attempted = true;
        summary.l04_preserved_from_source = true;
        try
            reconnectL15(targetModelName);
            summary.l15_rebuild_error = "";
        catch ME
            summary.l15_rebuild_error = string(ME.identifier) + ": " + string(ME.message);
        end
        if runUpdateDiagram
            try
                set_param(targetModelName, "SimulationCommand", "update");
                summary.update_diagram_passed = true;
            catch ME
                summary.update_diagram_passed = false;
                summary.update_diagram_error = string(ME.identifier) + ": " + string(ME.message);
            end
        end
        save_system(targetModelName);
    end
catch ME
    summary.blocker_if_any = string(ME.identifier) + ": " + string(ME.message);
end

try
    gate = auditManualBridge(targetPath, sourceL15, sourceL04, outputDir);
    summary = mergeGate(summary, gate);
catch ME
    summary.blocker_if_any = "static gate failed: " + string(ME.identifier) + ": " + string(ME.message);
end

if summary.physical_bridge_valid
    summary.blocker_if_any = "";
else
    if strlength(string(summary.blocker_if_any)) == 0
        summary.blocker_if_any = "manual physical bridge static gate did not pass";
    end
end
writeJson(fullfile(outputDir, "matlab_manual_bridge_build_raw.json"), summary);
end

function summary = baseSummary(targetPath, sourceL04, sourceL15)
summary = struct();
summary.build_scope = "spp001_manual_physical_bridge_matlab_builder";
summary.pair_id = "SPP001";
summary.prior_outaged_branch = "L15";
summary.candidate_next_branch = "L04";
summary.source_l04_wrapper_path = sourceL04;
summary.source_l15_wrapper_path = sourceL15;
summary.target_local_bridge_path = string(targetPath);
summary.manual_bridge_build_attempted = false;
summary.manual_bridge_built = false;
summary.l15_rebuild_attempted = false;
summary.l04_preserved_from_source = false;
summary.l15_rebuild_error = "";
summary.update_diagram_passed = false;
summary.update_diagram_error = "";
summary.physical_bridge_valid = false;
summary.source_slx_modified = false;
summary.sim_called = false;
summary.blocker_if_any = "";
end

function reconnectL15(modelName)
grid = modelName + "/Grid";
bus21 = findOne(modelName, "Bus21");
lineBlock = findOne(modelName, "B21 to B22");
breaker = findOne(modelName, "L15_HandwiredTimedBreaker");
command = findOne(modelName, "L15_TripCommand");
converter = findOne(modelName, "L15_SimulinkPSConverter");

[busPort, linePort, directLine] = findConnectionBetween(bus21, lineBlock);
if directLine == -1
    error("IEEE39SPP001ManualBridge:NoDirectL15Path", "Cannot find original Bus21 to B21 to B22 direct physical path.");
end
try
    delete_line(directLine);
catch
end

bh = get_param(breaker, "PortHandles");
ch = get_param(command, "PortHandles");
vh = get_param(converter, "PortHandles");
if numel(bh.LConn) < 2 || numel(bh.RConn) < 1
    error("IEEE39SPP001ManualBridge:BreakerPorts", "L15 breaker does not expose expected physical ports.");
end
safeDeletePortLine(bh.LConn(1));
safeDeletePortLine(bh.LConn(2));
safeDeletePortLine(bh.RConn(1));
safeDeletePortLine(vh.Inport(1));
safeDeletePortLine(vh.RConn(1));
add_line(grid, ch.Outport(1), vh.Inport(1), "autorouting", "on");
add_line(grid, vh.RConn(1), bh.LConn(1), "autorouting", "on");
add_line(grid, busPort, bh.LConn(2), "autorouting", "on");
add_line(grid, bh.RConn(1), linePort, "autorouting", "on");
end

function safeDeletePortLine(portHandle)
try
    lineHandle = get_param(portHandle, "Line");
    if ~isempty(lineHandle) && lineHandle ~= -1
        delete_line(lineHandle);
    end
catch
end
end

function block = findOne(modelName, blockName)
blocks = find_system(modelName, "LookUnderMasks", "all", "FollowLinks", "on", "Name", char(blockName));
if isempty(blocks)
    error("IEEE39SPP001ManualBridge:MissingBlock", "Missing block %s", blockName);
end
block = string(blocks{1});
end

function [portA, portB, lineHandle] = findConnectionBetween(blockA, blockB)
portA = -1;
portB = -1;
lineHandle = -1;
portsA = physicalPorts(blockA);
for idx = 1:numel(portsA)
    try
        lh = get_param(portsA(idx), "Line");
    catch
        lh = -1;
    end
    if isempty(lh) || lh == -1
        continue;
    end
    neighbors = neighborBlocksForPortLine(lh, blockA);
    if any(neighbors == string(blockB))
        portA = portsA(idx);
        portB = portOnBlockForLine(blockB, lh);
        lineHandle = lh;
        return;
    end
end
end

function ports = physicalPorts(blockPath)
handles = get_param(blockPath, "PortHandles");
ports = [];
for fieldName = ["LConn", "RConn", "PMIOPort"]
    if isfield(handles, fieldName)
        ports = [ports, handles.(fieldName)(:)']; %#ok<AGROW>
    end
end
end

function port = portOnBlockForLine(blockPath, lineHandle)
port = -1;
ports = physicalPorts(blockPath);
for idx = 1:numel(ports)
    try
        if get_param(ports(idx), "Line") == lineHandle
            port = ports(idx);
            return;
        end
    catch
    end
end
end

function neighbors = neighborBlocksForPortLine(lineHandle, ownBlock)
neighbors = strings(0, 1);
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

function ensureNamedBlockCopied(sourceModel, targetModel, sourceName, varargin)
if nargin >= 4
    targetName = string(varargin{1});
else
    targetName = string(sourceName);
end
targetPath = targetModel + "/Grid/" + targetName;
existing = find_system(targetModel, "LookUnderMasks", "all", "FollowLinks", "on", "Name", char(targetName));
if ~isempty(existing)
    return;
end
sourceBlocks = find_system(sourceModel, "LookUnderMasks", "all", "FollowLinks", "on", "Name", char(sourceName));
if isempty(sourceBlocks)
    error("IEEE39SPP001ManualBridge:MissingSourceBlock", "Missing source block %s", sourceName);
end
add_block(sourceBlocks{1}, char(targetPath), "MakeNameUnique", "off");
end

function gate = auditManualBridge(targetPath, sourceL15, sourceL04, outputDir)
rawPath = fullfile(outputDir, "manual_bridge_static_raw.json");
audit_ieee39_spp001_bridge_physical_connectivity(char(targetPath), ...
    char(sourceL15), ...
    char(sourceL04), ...
    rawPath);
raw = jsondecode(fileread(rawPath));
gate = struct();
gate.l15_trip_command_block_exists = logical(raw.l15_bridge.trip_command_block_exists);
gate.l15_breaker_block_exists = logical(raw.l15_bridge.breaker_block_exists);
gate.l15_trip_command_to_breaker_control_connected = logical(raw.l15_bridge.trip_command_to_breaker_control_connected);
gate.l15_breaker_physical_ports_connected = logical(raw.l15_bridge.breaker_physical_ports_connected);
gate.l15_breaker_in_series_with_actual_l15_branch = logical(raw.l15_bridge.breaker_in_series_with_actual_branch);
gate.l15_original_direct_bypass_removed = ~directConnectionExists(raw.bridge_model, "Bus21", "B21 to B22");
gate.l04_trip_command_block_exists = logical(raw.l04_bridge.trip_command_block_exists);
gate.l04_breaker_block_exists = logical(raw.l04_bridge.breaker_block_exists);
gate.l04_trip_command_to_breaker_control_connected = logical(raw.l04_bridge.trip_command_to_breaker_control_connected);
gate.l04_breaker_physical_ports_connected = logical(raw.l04_bridge.breaker_physical_ports_connected);
gate.l04_breaker_in_series_with_actual_l04_branch = l04SeriesValid(raw.l04_bridge);
gate.l04_original_direct_bypass_removed = l04BypassRemoved(raw.bridge_model, raw.l04_bridge);
gate.no_unconnected_physical_ports = isempty(raw.bridge_unconnected_ports);
gate.no_unconnected_control_ports = gate.l15_trip_command_to_breaker_control_connected && gate.l04_trip_command_to_breaker_control_connected;
gate.physical_bridge_valid = gate.l15_trip_command_to_breaker_control_connected && gate.l15_breaker_physical_ports_connected && gate.l15_breaker_in_series_with_actual_l15_branch && gate.l15_original_direct_bypass_removed && gate.l04_trip_command_to_breaker_control_connected && gate.l04_breaker_physical_ports_connected && gate.l04_breaker_in_series_with_actual_l04_branch && gate.l04_original_direct_bypass_removed && gate.no_unconnected_physical_ports && gate.no_unconnected_control_ports;
end

function valid = l04SeriesValid(info)
neighbors = string(info.breaker_neighbor_signature);
valid = logical(info.breaker_physical_ports_connected) && any(contains(neighbors, "B11 to B6")) && (any(contains(neighbors, "Bus6")) || any(contains(neighbors, "Bus11")));
end

function removed = l04BypassRemoved(modelName, info)
neighbors = string(info.breaker_neighbor_signature);
if any(contains(neighbors, "Bus6"))
    breakerSideBus = "Bus6";
elseif any(contains(neighbors, "Bus11"))
    breakerSideBus = "Bus11";
else
    removed = false;
    return;
end
removed = ~directConnectionExists(modelName, breakerSideBus, "B11 to B6");
end

function exists = directConnectionExists(modelName, blockAName, blockBName)
try
    blockA = findOne(modelName, blockAName);
    blockB = findOne(modelName, blockBName);
    [~, ~, lh] = findConnectionBetween(blockA, blockB);
    exists = lh ~= -1;
catch
    exists = false;
end
end

function summary = mergeGate(summary, gate)
fields = fieldnames(gate);
for idx = 1:numel(fields)
    summary.(fields{idx}) = gate.(fields{idx});
end
end

function name = modelNameFromPath(path)
[~, name, ~] = fileparts(path);
name = string(name);
end

function closeLoadedModels(modelsToClose)
for idx = numel(modelsToClose):-1:1
    try
        close_system(char(modelsToClose(idx)), 0);
    catch
    end
end
end

function writeJson(path, payload)
folder = fileparts(path);
if ~exist(folder, "dir")
    mkdir(folder);
end
fid = fopen(path, "w");
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, "%s", jsonencode(payload, PrettyPrint=true));
end
