function summary = inspect_ieee39_line_ports(wrapperModelPath, lineId, lineBlockPath, outputDir)
%INSPECT_IEEE39_LINE_PORTS Inventory a pilot IEEE39 transmission-line block.

if nargin < 1 || isempty(wrapperModelPath)
    wrapperModelPath = "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper.slx";
end
if nargin < 2 || isempty(lineId)
    lineId = "L01";
end
if nargin < 3 || isempty(lineBlockPath)
    lineBlockPath = "IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B1 to B2";
end
if nargin < 4 || isempty(outputDir)
    outputDir = "../../results/gcn_search/ieee39_graphical_dynamic_model/wrapper";
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

summary = struct();
summary.line_id = char(lineId);
summary.line_block_path = char(lineBlockPath);
summary.block_type = "";
summary.mask_type = "";
summary.reference_block = "";
summary.dialog_parameters = "";
summary.port_handles = "";
summary.port_connectivity = "";
summary.physical_port_count = 0;
summary.lconn_count = 0;
summary.rconn_count = 0;
summary.inport_count = 0;
summary.outport_count = 0;
summary.connected_source_blocks = "";
summary.connected_destination_blocks = "";
summary.port_domain_guess = "unknown";
summary.switch_insertion_feasible = false;
summary.note = "";

try
    load_system(wrapperModelPath);
    summary.block_type = char(string(get_param(lineBlockPath, "BlockType")));
    summary.mask_type = char(string(get_param(lineBlockPath, "MaskType")));
    try
        summary.reference_block = char(string(get_param(lineBlockPath, "ReferenceBlock")));
    catch
        summary.reference_block = "";
    end
    dialogParams = get_param(lineBlockPath, "DialogParameters");
    summary.dialog_parameters = char(strjoin(string(fieldnames(dialogParams)), ";"));
    ports = get_param(lineBlockPath, "PortHandles");
    summary.lconn_count = countPort(ports, "LConn");
    summary.rconn_count = countPort(ports, "RConn");
    summary.inport_count = countPort(ports, "Inport");
    summary.outport_count = countPort(ports, "Outport");
    summary.physical_port_count = summary.lconn_count + summary.rconn_count;
    summary.port_handles = compactPortHandleText(ports);
    connectivity = get_param(lineBlockPath, "PortConnectivity");
    summary.port_connectivity = compactConnectivityText(connectivity);
    [summary.connected_source_blocks, summary.connected_destination_blocks] = connectedBlockText(connectivity);
    if summary.physical_port_count > 0
        summary.port_domain_guess = "simscape_physical";
    end
    summary.switch_insertion_feasible = summary.physical_port_count == 4 && contains(summary.mask_type, "Transmission");
    if summary.switch_insertion_feasible
        summary.note = "L01 exposes four Simscape physical ports. Timed breaker insertion may be possible but requires compatible physical-port rewiring.";
    else
        summary.note = "Line block does not expose the expected four physical ports for automatic insertion.";
    end
    [~, modelName, ~] = fileparts(wrapperModelPath);
    close_system(modelName, 0);
catch ME
    summary.note = char("line port inventory failed: " + string(ME.message));
    try
        [~, modelName, ~] = fileparts(wrapperModelPath);
        close_system(modelName, 0);
    catch
    end
end

summary = cleanStructText(summary);
summaryTable = struct2table(summary, "AsArray", true);
writetable(summaryTable, fullfile(outputDir, "ieee39_line_port_inventory.csv"));
fid = fopen(fullfile(outputDir, "ieee39_line_port_inventory.json"), "w");
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, "%s", jsonencode(summary, PrettyPrint=true));
fprintf("Wrote IEEE39 line port inventory under: %s\n", outputDir);
end

function output = cleanStructText(input)
output = input;
fields = fieldnames(input);
for idx = 1:numel(fields)
    value = input.(fields{idx});
    if ischar(value) || isstring(value)
        output.(fields{idx}) = char(cleanText(value));
    end
end
end

function text = cleanText(value)
text = string(value);
text = replace(text, newline, "\n");
text = replace(text, sprintf('\r'), "\n");
end

function n = countPort(ports, fieldName)
n = 0;
if isfield(ports, fieldName)
    n = numel(ports.(fieldName));
end
end

function text = compactPortHandleText(ports)
names = fieldnames(ports);
parts = strings(0, 1);
for idx = 1:numel(names)
    value = ports.(names{idx});
    parts(end+1) = string(names{idx}) + "=" + mat2str(size(value)) + ":" + string(numel(value)); %#ok<AGROW>
end
text = char(strjoin(parts, ";"));
end

function text = compactConnectivityText(connectivity)
parts = strings(0, 1);
for idx = 1:numel(connectivity)
    item = connectivity(idx);
    parts(end+1) = string(item.Type) + "|src=" + mat2str(item.SrcBlock) + "|dst=" + mat2str(item.DstBlock); %#ok<AGROW>
end
text = char(strjoin(parts, ";"));
end

function [sources, destinations] = connectedBlockText(connectivity)
src = strings(0, 1);
dst = strings(0, 1);
for idx = 1:numel(connectivity)
    if ~isempty(connectivity(idx).SrcBlock)
        src(end+1) = mat2str(connectivity(idx).SrcBlock); %#ok<AGROW>
    end
    if ~isempty(connectivity(idx).DstBlock)
        dst(end+1) = mat2str(connectivity(idx).DstBlock); %#ok<AGROW>
    end
end
sources = char(strjoin(unique(src), ";"));
destinations = char(strjoin(unique(dst), ";"));
end
