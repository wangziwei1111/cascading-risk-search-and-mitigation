function inventoryTable = inventory_ieee39_simlog_tree(simOutOrNode, outputDir, maxDepth)
%INVENTORY_IEEE39_SIMLOG_TREE Inventory compact Simscape logging tree paths.
%
% The inventory is intentionally compact: it records node paths, whether a
% node has numeric series data, and a conservative candidate signal type.

if nargin < 2 || isempty(outputDir)
    outputDir = "../../results/gcn_search/ieee39_graphical_dynamic_model/fault_tests";
end
if nargin < 3 || isempty(maxDepth)
    maxDepth = 10;
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

rootNode = resolveRootNode(simOutOrNode);
rows = {};
rows = visitNode(rootNode, "simlog_IEEE39BusSystem", 0, maxDepth, rows);

if isempty(rows)
    inventoryTable = cell2table(cell(0, 8), "VariableNames", inventoryColumns());
else
    inventoryTable = cell2table(rows, "VariableNames", inventoryColumns());
end

csvPath = fullfile(outputDir, "ieee39_simlog_tree_inventory.csv");
jsonPath = fullfile(outputDir, "ieee39_simlog_tree_inventory.json");
writetable(inventoryTable, csvPath);

payload = struct();
payload.num_nodes = height(inventoryTable);
payload.num_series_nodes = sum(inventoryTable.has_series);
payload.num_voltage_candidates = sum(inventoryTable.candidate_signal_type == "voltage");
payload.num_speed_candidates = sum(inventoryTable.candidate_signal_type == "speed");
payload.num_rotor_angle_candidates = sum(inventoryTable.candidate_signal_type == "rotor_angle");
payload.num_current_candidates = sum(inventoryTable.candidate_signal_type == "current");
payload.top_candidate_paths = buildCandidateSummary(inventoryTable);
fid = fopen(jsonPath, "w");
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, "%s", jsonencode(payload, PrettyPrint=true));
fprintf("Wrote IEEE39 simlog tree inventory under: %s\n", outputDir);
end

function columns = inventoryColumns()
columns = {'node_path', 'node_name', 'node_class', 'depth', 'has_series', 'num_points', 'series_unit', 'candidate_signal_type'};
end

function rootNode = resolveRootNode(simOutOrNode)
rootNode = simOutOrNode;
try
    names = simOutOrNode.who;
    nameStrings = string(names);
    match = nameStrings(startsWith(nameStrings, "simlog_"));
    if ~isempty(match)
        rootNode = simOutOrNode.(char(match(1)));
    end
catch
end
end

function rows = visitNode(node, path, depth, maxDepth, rows)
[hasSeries, numPoints, unitText] = seriesInfo(node);
nodeName = lastPathToken(path);
rows(end+1, :) = {char(path), char(nodeName), char(class(node)), depth, hasSeries, numPoints, char(unitText), char(classifySignal(path))}; %#ok<AGROW>
if depth >= maxDepth
    return;
end
childNames = getChildNames(node);
for idx = 1:numel(childNames)
    childName = string(childNames(idx));
    try
        childNode = node.child(char(childName));
    catch
        try
            childNode = node.(childName);
        catch
            continue;
        end
    end
    rows = visitNode(childNode, path + "." + childName, depth + 1, maxDepth, rows);
end
end

function names = getChildNames(node)
names = strings(0, 1);
try
    raw = node.childIds;
    names = string(raw(:));
catch
    try
        raw = fieldnames(node);
        names = string(raw(:));
        names = setdiff(names, ["id"; "savable"; "exportable"; "series"], "stable");
    catch
    end
end
end

function [hasSeries, numPoints, unitText] = seriesInfo(node)
hasSeries = false;
numPoints = 0;
unitText = "";
try
    s = node.series;
    values = s.values;
    hasSeries = ~isempty(values);
    numPoints = numel(values);
    try
        unitText = string(s.unit);
    catch
        unitText = "";
    end
catch
end
end

function kind = classifySignal(path)
lowerPath = lower(string(path));
if contains(lowerPath, "terminal_voltage") || contains(lowerPath, "voltage") || contains(lowerPath, ".v")
    kind = "voltage";
elseif contains(lowerPath, "rotor_velocity") || contains(lowerPath, "speed") || contains(lowerPath, "omega")
    kind = "speed";
elseif contains(lowerPath, "rotor_electrical_angle") || contains(lowerPath, "rotor_angle") || contains(lowerPath, "angle")
    kind = "rotor_angle";
elseif contains(lowerPath, "current") || contains(lowerPath, ".i")
    kind = "current";
elseif contains(lowerPath, "frequency") || contains(lowerPath, "freq")
    kind = "frequency";
elseif contains(lowerPath, "power")
    kind = "electrical_power";
else
    kind = "unknown";
end
end

function token = lastPathToken(path)
parts = split(string(path), ".");
token = parts(end);
end

function summary = buildCandidateSummary(tableIn)
summary = struct();
for kind = ["voltage", "speed", "rotor_angle", "current", "frequency"]
    subset = tableIn(tableIn.candidate_signal_type == kind & tableIn.has_series, :);
    paths = string(subset.node_path);
    summary.(kind + "_paths") = cellstr(paths(1:min(20, numel(paths))));
end
end
