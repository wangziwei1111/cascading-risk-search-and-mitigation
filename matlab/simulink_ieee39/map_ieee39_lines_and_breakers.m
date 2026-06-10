function [lineMap, faultPoints] = map_ieee39_lines_and_breakers(wrapperModelPath, outputDir)
%MAP_IEEE39_LINES_AND_BREAKERS Build pilot IEEE39 line/fault mapping.
%
% The MathWorks IEEE39 example exposes transmission-line blocks and a
% three-phase fault block, but no explicit breaker blocks were found by the
% automatic inventory. Round 27 therefore records pilot line-outage mapping
% through line block disabling and marks breaker wiring as manual_required.

if nargin < 1 || isempty(wrapperModelPath)
    wrapperModelPath = "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper.slx";
end
if nargin < 2 || isempty(outputDir)
    outputDir = "../../results/gcn_search/ieee39_graphical_dynamic_model/wrapper";
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end
if ~isfile(wrapperModelPath)
    error("Wrapper model not found: %s", wrapperModelPath);
end

load_system(wrapperModelPath);
[~, modelName, ~] = fileparts(wrapperModelPath);
lineBlocks = find_system(modelName, "LookUnderMasks", "all", "FollowLinks", "on", "MaskType", "Transmission" + newline + "Line" + newline + "(Three-Phase)");
if isempty(lineBlocks)
    allBlocks = find_system(modelName, "LookUnderMasks", "all", "FollowLinks", "on", "Type", "Block");
    lineBlocks = allBlocks(contains(string(allBlocks), " to "));
end
lineBlocks = lineBlocks(1:min(5, numel(lineBlocks)));
faultBlocks = find_system(modelName, "LookUnderMasks", "all", "FollowLinks", "on", "MaskType", "Fault (Three-Phase)");

rows = cell(numel(lineBlocks), 10);
for idx = 1:numel(lineBlocks)
    blockPath = string(lineBlocks{idx});
    [fromBus, toBus] = parseLineBuses(blockPath);
    rows(idx, :) = {
        sprintf("L%02d", idx), char(fromBus), char(toBus), char(blockPath), "", "", "", ...
        char(fromBus), "pilot_line_block_disable", "No explicit breaker found; pilot trip disables the line block before simulation." ...
    };
end
lineMap = cell2table(rows, "VariableNames", { ...
    'line_id', 'from_bus', 'to_bus', 'line_block_path', 'breaker_block_path', ...
    'current_measurement_block_path', 'voltage_measurement_block_path', ...
    'fault_injection_bus_or_line', 'mapping_status', 'note' ...
});

faultRows = cell(max(1, numel(faultBlocks)), 4);
if isempty(faultBlocks)
    faultRows(1, :) = {"F01", "", "manual_required", "No existing fault block found."};
else
    for idx = 1:numel(faultBlocks)
        faultRows(idx, :) = {sprintf("F%02d", idx), char(faultBlocks{idx}), "existing_three_phase_fault_block", "Temporal fault parameters can be set on this block."};
    end
end
faultPoints = cell2table(faultRows, "VariableNames", {'fault_id', 'fault_block_path', 'mapping_status', 'note'});

writetable(lineMap, fullfile(outputDir, "ieee39_line_breaker_map.csv"));
writetable(lineMap, fullfile(outputDir, "ieee39_wrapper_line_breaker_map.csv"));
writetable(faultPoints, fullfile(outputDir, "ieee39_fault_injection_points.csv"));
close_system(modelName, 0);
fprintf("Wrote IEEE39 pilot line/breaker map under: %s\n", outputDir);
end

function [fromBus, toBus] = parseLineBuses(blockPath)
name = string(blockPath);
parts = split(name, "/");
leaf = parts(end);
tokens = regexp(char(leaf), 'B(\d+)\s+to\s+B(\d+)', 'tokens', 'once');
if isempty(tokens)
    fromBus = "";
    toBus = "";
else
    fromBus = "B" + string(tokens{1});
    toBus = "B" + string(tokens{2});
end
end
