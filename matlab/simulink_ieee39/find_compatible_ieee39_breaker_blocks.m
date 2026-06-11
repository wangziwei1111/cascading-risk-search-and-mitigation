function candidateTable = find_compatible_ieee39_breaker_blocks(outputDir)
%FIND_COMPATIBLE_IEEE39_BREAKER_BLOCKS Search installed breaker/switch blocks.

if nargin < 1 || isempty(outputDir)
    outputDir = "../../results/gcn_search/ieee39_graphical_dynamic_model/wrapper";
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

libraries = ["ee_lib", "powerlib", "fl_lib", "sps_lib"];
rows = {};
for lib = libraries
    try
        load_system(lib);
        found = find_system(lib, "LookUnderMasks", "all", "FollowLinks", "on", ...
            "RegExp", "on", "Name", ".*Breaker.*|.*Switch.*");
        for idx = 1:numel(found)
            blockPath = string(found{idx});
            if blockPath == lib
                continue;
            end
            [maskType, portText, physicalCount, inCount, outCount, likelyCompatible, requiresControl, note] = inspectLibraryCandidate(blockPath);
            rows(end+1, :) = {char(cleanText(blockPath)), char(cleanText(lastPathToken(blockPath))), char(cleanText(maskType)), char(cleanText(portText)), ...
                physicalCount, inCount, outCount, likelyCompatible, requiresControl, char(cleanText(note))}; %#ok<AGROW>
        end
    catch ME
        rows(end+1, :) = {char(cleanText(lib)), char(cleanText(lib)), "", "", 0, 0, 0, false, false, char(cleanText("library search failed: " + string(ME.message)))}; %#ok<AGROW>
    end
end

if isempty(rows)
    candidateTable = cell2table(cell(0, 10), "VariableNames", candidateColumns());
else
    candidateTable = cell2table(rows, "VariableNames", candidateColumns());
end
candidateTable = sortrows(candidateTable, ["likely_compatible_with_l01", "physical_port_count"], ["descend", "descend"]);
writetable(candidateTable, fullfile(outputDir, "ieee39_compatible_breaker_candidates.csv"));
payload = struct();
payload.num_candidates = height(candidateTable);
payload.num_likely_compatible = sum(candidateTable.likely_compatible_with_l01);
payload.top_candidates = table2struct(candidateTable(1:min(10, height(candidateTable)), :));
fid = fopen(fullfile(outputDir, "ieee39_compatible_breaker_candidates.json"), "w");
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, "%s", jsonencode(payload, PrettyPrint=true));
fprintf("Wrote IEEE39 compatible breaker candidates under: %s\n", outputDir);
end

function columns = candidateColumns()
columns = {'library_path', 'block_name', 'mask_type', 'port_structure', 'physical_port_count', ...
    'inport_count', 'outport_count', 'likely_compatible_with_l01', 'requires_control_input', 'note'};
end

function [maskType, portText, physicalCount, inCount, outCount, likelyCompatible, requiresControl, note] = inspectLibraryCandidate(blockPath)
maskType = "";
portText = "";
physicalCount = 0;
inCount = 0;
outCount = 0;
likelyCompatible = false;
requiresControl = false;
note = "";
tmpModel = "tmp_ieee39_breaker_candidate_probe";
try
    if bdIsLoaded(tmpModel)
        close_system(tmpModel, 0);
    end
    new_system(tmpModel);
    add_block(char(blockPath), tmpModel + "/candidate", "MakeNameUnique", "on");
    candidatePath = tmpModel + "/candidate";
    try
        maskType = string(get_param(candidatePath, "MaskType"));
    catch
        maskType = "";
    end
    ports = get_param(candidatePath, "PortHandles");
    physicalCount = countPort(ports, "LConn") + countPort(ports, "RConn");
    inCount = countPort(ports, "Inport");
    outCount = countPort(ports, "Outport");
    portText = compactPortText(ports);
    lowerText = lower(blockPath + " " + maskType);
    requiresControl = inCount > 0 || contains(lowerText, "controlled");
    likelyCompatible = physicalCount >= 3 && (contains(lowerText, "breaker") || contains(lowerText, "switch"));
    if likelyCompatible
        note = "Candidate has physical ports and breaker/switch naming; standalone probe still required before wrapper insertion.";
    else
        note = "Candidate is not clearly compatible with the four-port IEEE39 line block.";
    end
    close_system(tmpModel, 0);
catch ME
    note = "candidate inspection failed: " + string(ME.message);
    try
        close_system(tmpModel, 0);
    catch
    end
end
end

function n = countPort(ports, fieldName)
n = 0;
if isfield(ports, fieldName)
    n = numel(ports.(fieldName));
end
end

function text = compactPortText(ports)
fields = fieldnames(ports);
parts = strings(0, 1);
for idx = 1:numel(fields)
    parts(end+1) = string(fields{idx}) + ":" + string(numel(ports.(fields{idx}))); %#ok<AGROW>
end
text = char(strjoin(parts, ";"));
end

function token = lastPathToken(path)
parts = split(string(path), "/");
token = parts(end);
end

function text = cleanText(value)
text = string(value);
text = replace(text, newline, "\n");
text = replace(text, sprintf('\r'), "\n");
end
