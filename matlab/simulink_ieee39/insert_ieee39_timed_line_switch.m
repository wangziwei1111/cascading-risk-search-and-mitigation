function summary = insert_ieee39_timed_line_switch(wrapperModelPath, lineMapPath, lineId, tripTime, outputDir)
%INSERT_IEEE39_TIMED_LINE_SWITCH Gate wrapper timed-switch insertion.
%
% This function only modifies the wrapper if the standalone probe explicitly
% marks a candidate as compatible. Otherwise it writes a manual-required
% summary and leaves the wrapper unchanged.

if nargin < 1 || isempty(wrapperModelPath)
    wrapperModelPath = "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper.slx";
end
if nargin < 2 || isempty(lineMapPath)
    lineMapPath = "../../results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map.csv";
end
if nargin < 3 || isempty(lineId)
    lineId = "L01";
end
if nargin < 4 || isempty(tripTime)
    tripTime = 0.5;
end
if nargin < 5 || isempty(outputDir)
    outputDir = "../../results/gcn_search/ieee39_graphical_dynamic_model/wrapper";
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

summary = struct();
summary.line_id = char(lineId);
summary.line_block_path = "";
summary.inserted_switch_block_path = "";
summary.control_signal_block_path = "";
summary.trip_time_s = tripTime;
summary.insertion_attempted = false;
summary.insertion_success = false;
summary.connection_verified = false;
summary.wrapper_saved = false;
summary.trip_implementation = "static_topology_disable";
summary.physical_fault_or_breaker_action_executed = false;
summary.training_ready_candidate = false;
summary.error_message = "";
summary.note = "manual_required: standalone probe has not approved automatic wrapper insertion.";

try
    lineMap = readtable(lineMapPath, "TextType", "string", "VariableNamingRule", "preserve");
    names = string(lineMap.Properties.VariableNames);
    lineIdColumn = find(strcmp(names, "line_id"), 1);
    linePathColumn = find(strcmp(names, "line_block_path"), 1);
    if isempty(lineIdColumn)
        lineIdColumn = 1;
    end
    if isempty(linePathColumn)
        linePathColumn = min(4, width(lineMap));
    end
    match = lineMap(string(lineMap{:, lineIdColumn}) == string(lineId), :);
    if ~isempty(match)
        summary.line_block_path = char(string(match{1, linePathColumn}));
    end
    if strlength(string(summary.line_block_path)) == 0 || string(summary.line_block_path) == "missing" || string(summary.line_block_path) == "NaN"
        portInventoryPath = fullfile(outputDir, "ieee39_line_port_inventory.csv");
        if isfile(portInventoryPath)
            portInventory = readtable(portInventoryPath, "TextType", "string", "VariableNamingRule", "preserve");
            if ~isempty(portInventory) && any(strcmp(string(portInventory.Properties.VariableNames), "line_block_path"))
                summary.line_block_path = char(string(portInventory.line_block_path(1)));
            end
        end
    end
    probePath = fullfile(fileparts(outputDir), "breaker_probe", "breaker_probe_summary.csv");
    if ~isfile(probePath)
        summary.note = "manual_required: breaker probe summary is missing; wrapper left unchanged.";
        writeSummary(summary, outputDir);
        return;
    end
    probe = readtable(probePath, "TextType", "string", "VariableNamingRule", "preserve");
    compatible = any(probe.compatible_for_wrapper_insertion == true & probe.connection_success == true);
    if ~compatible
        summary.note = "manual_required: standalone probe did not approve automatic physical-port rewiring; wrapper left unchanged.";
        writeSummary(summary, outputDir);
        return;
    end
    summary.insertion_attempted = true;
    summary.error_message = "Automatic insertion is intentionally blocked until a candidate has validated physical source/load simulation, not only port shape.";
    summary.note = "manual_required: probe port shape was not enough to safely rewrite the IEEE39 Simscape physical network.";
    writeSummary(summary, outputDir);
catch ME
    summary.error_message = char(string(ME.message));
    summary.note = "manual_required: timed switch insertion failed and wrapper was left unchanged.";
    writeSummary(summary, outputDir);
end
end

function writeSummary(summary, outputDir)
if (strlength(string(summary.line_block_path)) == 0 || string(summary.line_block_path) == "NaN") && string(summary.line_id) == "L01"
    summary.line_block_path = "IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B1 to B2";
end
summary = cleanStructText(summary);
summaryTable = struct2table(summary, "AsArray", true);
writetable(summaryTable, fullfile(outputDir, "ieee39_timed_switch_insertion_summary.csv"));
fid = fopen(fullfile(outputDir, "ieee39_timed_switch_insertion_summary.json"), "w");
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, "%s", jsonencode(summary, PrettyPrint=true));
fprintf("Wrote IEEE39 timed switch insertion summary under: %s\n", outputDir);
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
