function summary = probe_ieee39_breaker_insertion_standalone(candidateCsvPath, outputDir)
%PROBE_IEEE39_BREAKER_INSERTION_STANDALONE Conservative breaker probe.
%
% The probe inspects whether a candidate can be instantiated and whether its
% port structure is close enough to the IEEE39 line block for wrapper
% insertion. It does not treat a candidate as wrapper-compatible unless the
% port structure is unambiguous.

if nargin < 1 || isempty(candidateCsvPath)
    candidateCsvPath = "../../results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_compatible_breaker_candidates.csv";
end
if nargin < 2 || isempty(outputDir)
    outputDir = "../../results/gcn_search/ieee39_graphical_dynamic_model/breaker_probe";
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

errorLogPath = fullfile(outputDir, "breaker_probe_error_log.txt");
fidLog = fopen(errorLogPath, "w");
cleanupLog = onCleanup(@() fclose(fidLog));

summary = struct();
summary.probe_model_created = false;
summary.candidate_block = "";
summary.connection_success = false;
summary.simulation_success = false;
summary.timed_open_signal_applied = false;
summary.compatible_for_wrapper_insertion = false;
summary.error_message = "";
summary.note = "";

try
    candidates = readtable(candidateCsvPath, "TextType", "string", "VariableNamingRule", "preserve");
    if isempty(candidates)
        error("Candidate table is empty.");
    end
    likely = candidates(candidates.likely_compatible_with_l01 == true, :);
    if isempty(likely)
        likely = candidates;
    end
    candidate = likely(1, :);
    candidateBlock = restorePath(candidate.library_path);
    summary.candidate_block = char(cleanText(candidate.library_path));
    tmpModel = "tmp_ieee39_breaker_standalone_probe";
    if bdIsLoaded(tmpModel)
        close_system(tmpModel, 0);
    end
    new_system(tmpModel);
    summary.probe_model_created = true;
    add_block(char(candidateBlock), tmpModel + "/candidate_breaker", "MakeNameUnique", "on");
    add_block("simulink/Sources/Step", tmpModel + "/trip_step", "Time", "0.5", "Before", "1", "After", "0");
    summary.timed_open_signal_applied = true;
    ports = get_param(tmpModel + "/candidate_breaker", "PortHandles");
    physicalCount = countPort(ports, "LConn") + countPort(ports, "RConn");
    inCount = countPort(ports, "Inport");
    hasControl = inCount > 0;
    if hasControl
        try
            add_line(tmpModel, "trip_step/1", "candidate_breaker/1", "autorouting", "on");
        catch ME
            fprintf(fidLog, "Control connection failed: %s\n", ME.message);
        end
    end
    summary.connection_success = physicalCount == 4 && hasControl;
    if summary.connection_success
        summary.compatible_for_wrapper_insertion = true;
        summary.simulation_success = false;
        summary.note = "Candidate has four physical ports and a control input. Wrapper insertion may be attempted by insert_ieee39_timed_line_switch.";
    else
        summary.compatible_for_wrapper_insertion = false;
        summary.simulation_success = false;
        summary.note = "Standalone probe did not find an unambiguous four-physical-port controlled breaker compatible with the L01 line block.";
    end
    fprintf(fidLog, "No MATLAB exception. Probe gate result: compatible_for_wrapper_insertion=%d\n", summary.compatible_for_wrapper_insertion);
    close_system(tmpModel, 0);
catch ME
    summary.error_message = char(string(ME.message));
    summary.note = "standalone probe failed; wrapper insertion is blocked";
    fprintf(fidLog, "%s\n", getReport(ME, "extended", "hyperlinks", "off"));
    try
        close_system("tmp_ieee39_breaker_standalone_probe", 0);
    catch
    end
end

summary = cleanStructText(summary);
summaryTable = struct2table(summary, "AsArray", true);
writetable(summaryTable, fullfile(outputDir, "breaker_probe_summary.csv"));
fid = fopen(fullfile(outputDir, "breaker_probe_summary.json"), "w");
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, "%s", jsonencode(summary, PrettyPrint=true));
fprintf("Wrote IEEE39 breaker probe summary under: %s\n", outputDir);
end

function path = restorePath(value)
path = replace(string(value), "\n", newline);
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
