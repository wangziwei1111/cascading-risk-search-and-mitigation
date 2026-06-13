function inventoryTable = inspect_ieee39_wrapper_grid_line_blocks(wrapperPath, outputDir)
%INSPECT_IEEE39_WRAPPER_GRID_LINE_BLOCKS Inventory line-like blocks under Grid.
%
% This read-only helper opens the generated IEEE39 wrapper, scans the Grid
% subsystem for line-like blocks, writes CSV/JSON inventory files, and closes
% the model without saving.

if nargin < 1 || isempty(wrapperPath)
    wrapperPath = "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper.slx";
end
if nargin < 2 || isempty(outputDir)
    outputDir = "../../results/gcn_search/ieee39_graphical_dynamic_model/wrapper";
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

configure_ieee39_short_filegen_paths();

modelName = "";
try
    load_system(wrapperPath);
    [~, modelName, ~] = fileparts(wrapperPath);
    gridPath = modelName + "/Grid";
    if isempty(find_system(modelName, "SearchDepth", 1, "Name", "Grid"))
        error("Grid subsystem not found in %s", modelName);
    end

    blocks = find_system(gridPath, "LookUnderMasks", "all", "FollowLinks", "on", "Type", "Block");
    rows = {};
    inventoryIndex = 0;
    for idx = 1:numel(blocks)
        blockPath = string(blocks{idx});
        if blockPath == gridPath
            continue;
        end
        blockName = string(get_param(blockPath, "Name"));
        blockType = safeGetParam(blockPath, "BlockType");
        maskType = safeGetParam(blockPath, "MaskType");
        [busFrom, busTo, nameLike] = parseBusPair(blockName);
        typeLike = isTypeLineLike(blockName, blockType, maskType);
        isCandidate = nameLike || typeLike;
        if ~isCandidate
            continue;
        end
        inventoryIndex = inventoryIndex + 1;
        parentPath = string(get_param(blockPath, "Parent"));
        note = "line-like candidate from Grid scan";
        if nameLike
            note = note + "; bus pair parsed from block name";
        end
        if typeLike
            note = note + "; type or mask suggests line/branch";
        end
        rows(end + 1, :) = {inventoryIndex, char(blockName), char(blockPath), char(parentPath), ...
            char(blockType), char(maskType), char(busFrom), char(busTo), logical(isCandidate), char(note)}; %#ok<AGROW>
    end

    inventoryTable = cell2table(rows, "VariableNames", { ...
        'inventory_index', 'block_name', 'block_path', 'parent_path', ...
        'block_type', 'mask_type', 'bus_from_candidate', 'bus_to_candidate', ...
        'is_line_like_candidate', 'note' ...
    });
    writetable(inventoryTable, fullfile(outputDir, "ieee39_wrapper_grid_line_block_inventory.csv"));
    writeJsonTable(inventoryTable, fullfile(outputDir, "ieee39_wrapper_grid_line_block_inventory.json"));
    fprintf("Wrote IEEE39 wrapper Grid line inventory under: %s\n", outputDir);
catch ME
    try
        if strlength(string(modelName)) > 0
            close_system(modelName, 0);
        end
    catch
    end
    rethrow(ME);
end

try
    close_system(modelName, 0);
catch
end
end

function value = safeGetParam(blockPath, paramName)
try
    value = cleanText(string(get_param(blockPath, paramName)));
catch
    value = "";
end
end

function value = cleanText(value)
value = regexprep(string(value), "[\r\n]+", " ");
value = strtrim(value);
end

function [busFrom, busTo, matched] = parseBusPair(blockName)
busFrom = "";
busTo = "";
matched = false;
patterns = [
    "^(B\d+)\s+to\s+(B\d+)$"
    "^(Bus\d+)\s+to\s+(Bus\d+)$"
    "^(B\d+)\s*-\s*(B\d+)$"
    "^(Bus\d+)\s*-\s*(Bus\d+)$"
];
for idx = 1:numel(patterns)
    tokens = regexp(char(blockName), char(patterns(idx)), "tokens", "once", "ignorecase");
    if ~isempty(tokens)
        busFrom = string(tokens{1});
        busTo = string(tokens{2});
        matched = true;
        return;
    end
end
end

function tf = isTypeLineLike(blockName, blockType, maskType)
text = lower(strjoin([string(blockName), string(blockType), string(maskType)], " "));
tf = contains(text, "branch") || contains(text, "line") || contains(text, "pi section") || contains(text, "transmission");
end

function writeJsonTable(tableValue, path)
records = table2struct(tableValue);
fid = fopen(path, "w");
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, "%s", jsonencode(records, PrettyPrint=true));
end
