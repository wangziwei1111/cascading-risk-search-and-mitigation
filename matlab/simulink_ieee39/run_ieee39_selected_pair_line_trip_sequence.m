function summary = run_ieee39_selected_pair_line_trip_sequence(manifestPath, outputDir, varargin)
%RUN_IEEE39_SELECTED_PAIR_LINE_TRIP_SEQUENCE Guarded selected-pair smoke entrypoint.
%
% This entrypoint is selected-32 guarded, but it only allows one selected pair
% to be executed in smoke mode after explicit manual approval. It does not run
% the full 1056 generation, does not export formal labels, does not save raw
% trajectory data, does not save full timeseries, does not save MAT files, and does
% not modify or save the source SLX model.
% Raw trajectory output remains forbidden in this entrypoint.
%
% phasor_RMS is not EMT. generator_speed_proxy is not direct frequency.
% beta * RATE_A is an audit-only proxy, not a real relay setting. Dynamic
% outputs are outputs/targets only, not input features.

parser = inputParser;
addRequired(parser, "manifestPath", @(x) ischar(x) || isstring(x));
addRequired(parser, "outputDir", @(x) ischar(x) || isstring(x));
addParameter(parser, "approved_selected_pairs_only", false, @(x) islogical(x) || isnumeric(x));
addParameter(parser, "execute", false, @(x) islogical(x) || isnumeric(x));
addParameter(parser, "execute_single_pair", false, @(x) islogical(x) || isnumeric(x));
addParameter(parser, "dry_run_only", true, @(x) islogical(x) || isnumeric(x));
addParameter(parser, "pair_id", "", @(x) ischar(x) || isstring(x));
addParameter(parser, "handwired_model_path", "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx", @(x) ischar(x) || isstring(x));
addParameter(parser, "validation_summary_csv", "../../results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_multi_handwired_breaker_validation_summary.csv", @(x) ischar(x) || isstring(x));
addParameter(parser, "provenance_manifest_path", "", @(x) ischar(x) || isstring(x));
addParameter(parser, "simulation_stop_time", 1.2, @(x) isnumeric(x) && isscalar(x) && x > 0);
addParameter(parser, "prior_trip_time", 0.5, @(x) isnumeric(x) && isscalar(x) && x >= 0);
addParameter(parser, "next_trip_time", 0.75, @(x) isnumeric(x) && isscalar(x) && x >= 0);
addParameter(parser, "timeout_s", 240, @(x) isnumeric(x) && isscalar(x) && x > 0);
parse(parser, manifestPath, outputDir, varargin{:});

approvedSelectedPairsOnly = logical(parser.Results.approved_selected_pairs_only);
executeRequested = logical(parser.Results.execute);
executeSinglePair = logical(parser.Results.execute_single_pair);
dryRunOnly = logical(parser.Results.dry_run_only);
manifestPath = char(parser.Results.manifestPath);
outputDir = char(parser.Results.outputDir);
pairId = string(parser.Results.pair_id);

if ~isfile(manifestPath)
    error("IEEE39SelectedPair:MissingManifest", "Selected pair manifest does not exist: %s", manifestPath);
end
if ~approvedSelectedPairsOnly
    error("IEEE39SelectedPair:ApprovalRequired", "approved_selected_pairs_only must be true.");
end

manifestText = fileread(manifestPath);
pairs = jsondecode(manifestText);
pairCount = numel(pairs);
if pairCount > 32
    error("IEEE39SelectedPair:TooManyPairs", "Selected-pair entrypoint refuses more than 32 pairs.");
end
if executeRequested && ~executeSinglePair
    error("IEEE39SelectedPair:BatchExecutionRefused", "Batch execution is refused. Use execute_single_pair=true with exactly one pair_id.");
end
if executeSinglePair && strlength(pairId) == 0
    error("IEEE39SelectedPair:PairIdRequired", "execute_single_pair requires pair_id.");
end

if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

selectedPair = struct([]);
if strlength(pairId) > 0
    selectedPair = findPairById(pairs, pairId);
    if isempty(selectedPair)
        error("IEEE39SelectedPair:PairNotFound", "Requested pair_id was not found in selected manifest: %s", pairId);
    end
else
    selectedPair = pairs(1);
end

validation = readValidation(parser.Results.validation_summary_csv);
row = buildBaseRow(selectedPair);
[priorReady, priorReason, priorCommand] = lineReady(validation, string(selectedPair.prior_outaged_branch));
[nextReady, nextReason, nextCommand] = lineReady(validation, string(selectedPair.candidate_next_branch));
entrypointReady = priorReady && nextReady && ~row.l12_special_case_flag;
[manifestReady, manifestReason, manifestPriorCommand, manifestNextCommand, manifestModel] = readProvenanceManifest(parser.Results.provenance_manifest_path);
if manifestReady
    priorCommand = manifestPriorCommand;
    nextCommand = manifestNextCommand;
end

if executeSinglePair
    if dryRunOnly
        row.execution_status = "blocked";
        row.pilot_label_status = "blocked";
        row.timeout_or_failure_reason = "dry_run_only=true; single-pair smoke execution was not run";
        row.evidence_source = "matlab_selected_pair_entrypoint_dry_run";
    elseif ~entrypointReady
        row.execution_status = "blocked";
        row.pilot_label_status = "blocked";
        row.timeout_or_failure_reason = "single-pair smoke not ready: " + priorReason + "; " + nextReason;
        row.evidence_source = "matlab_selected_pair_entrypoint_readiness_blocked";
    elseif ~sameWrapperProvenance(parser.Results.handwired_model_path, priorCommand, nextCommand, manifestReady, manifestModel)
        row.execution_status = "failed";
        row.pilot_label_status = "failed";
        row.timeout_or_failure_reason = "single-pair smoke failed provenance check before set_param: " + manifestReason + "; prior model=" + commandModelName(priorCommand) + "; next model=" + commandModelName(nextCommand);
        row.evidence_source = "matlab_selected_pair_entrypoint_provenance_mismatch";
    else
        row = executeOnePair(row, parser.Results.handwired_model_path, outputDir, validation, priorCommand, nextCommand, parser.Results);
    end
else
    if entrypointReady
        row.execution_status = "execution_ready";
        row.pilot_label_status = "unknown";
        row.timeout_or_failure_reason = "single-pair smoke mode is ready but execute_single_pair=false";
        row.evidence_source = "matlab_selected_pair_entrypoint_readiness";
    else
        row.execution_status = "blocked";
        row.pilot_label_status = "blocked";
        row.timeout_or_failure_reason = "single-pair smoke not ready: " + priorReason + "; " + nextReason;
        row.evidence_source = "matlab_selected_pair_entrypoint_readiness_blocked";
    end
end

summary = struct();
summary.execution_scope = "selected_pair_matlab_entrypoint_single_pair_smoke";
summary.approved_selected_pairs_only = approvedSelectedPairsOnly;
summary.execute_requested = executeRequested;
summary.execute_single_pair = executeSinglePair;
summary.dry_run_only = dryRunOnly;
summary.selected_pair_count = pairCount;
summary.pair_id = row.pair_id;
summary.selected_32_pairs_executed = false;
summary.single_pair_executed = strcmp(row.execution_status, "succeeded");
summary.simulink_run = summary.single_pair_executed;
summary.full_1056_generation_run = false;
summary.formal_labels_exported = false;
summary.raw_trajectories_saved = false;
summary.full_timeseries_saved = false;
summary.mat_files_saved = false;
summary.source_slx_modified = false;
summary.timeout_policy = "timeout remains timeout/unknown and is not converted to 0/1";
summary.unknown_policy = "blocked, failed, timeout, and unknown remain null";
summary.rows = row;

summaryPath = fullfile(outputDir, "matlab_selected_pair_compact_evidence_summary.json");
fid = fopen(summaryPath, "w");
if fid < 0
    error("IEEE39SelectedPair:WriteFailed", "Cannot write compact evidence summary: %s", summaryPath);
end
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, "%s", jsonencode(summary, PrettyPrint=true));
clear cleanup;
end

function selected = findPairById(pairs, pairId)
selected = struct([]);
for idx = 1:numel(pairs)
    if string(pairs(idx).pair_id) == pairId
        selected = pairs(idx);
        return;
    end
end
end

function validation = readValidation(validationSummaryCsv)
validationPath = char(validationSummaryCsv);
if isfile(validationPath)
    validation = readtable(validationPath, "TextType", "string", "VariableNamingRule", "preserve", "Delimiter", ",");
else
    validation = table( ...
        strings(0, 1), false(0, 1), strings(0, 1), strings(0, 1), ...
        "VariableNames", {'line_id', 'validation_passed', 'trip_command_path', 'validation_failure_reason'});
end
end

function [ready, reason, commandPath] = lineReady(validation, lineId)
ready = false;
reason = "";
commandPath = "";
if lineId == "L12"
    reason = "L12 remains special/excluded";
    return;
end
if isempty(validation) || height(validation) == 0 || ~any(validation.line_id == lineId)
    reason = "validation missing for " + lineId;
    return;
end
match = validation(validation.line_id == lineId, :);
commandPath = string(match.trip_command_path(1));
ready = boolFromValidationValue(match.validation_passed(1)) && strlength(commandPath) > 0;
if ready
    reason = lineId + " validation passed";
else
    reason = lineId + " validation failed: " + string(match.validation_failure_reason(1));
end
end

function value = boolFromValidationValue(rawValue)
if islogical(rawValue)
    value = rawValue;
    return;
end
if isnumeric(rawValue)
    value = rawValue ~= 0;
    return;
end
textValue = lower(strtrim(string(rawValue)));
value = any(textValue == ["true", "1", "yes", "y"]);
end

function [ready, reason, priorCommand, nextCommand, selectedModel] = readProvenanceManifest(manifestPath)
ready = false;
reason = "no provenance manifest supplied";
priorCommand = "";
nextCommand = "";
selectedModel = "";
if strlength(string(manifestPath)) == 0
    return;
end
if ~isfile(manifestPath)
    reason = "provenance manifest missing: " + string(manifestPath);
    return;
end
payload = jsondecode(fileread(manifestPath));
if isfield(payload, "same_wrapper_confirmed") && logical(payload.same_wrapper_confirmed)
    priorCommand = string(payload.prior_trip_command_path);
    nextCommand = string(payload.next_trip_command_path);
    selectedModel = string(payload.selected_wrapper_model);
    ready = strlength(priorCommand) > 0 && strlength(nextCommand) > 0 && strlength(selectedModel) > 0;
    reason = "provenance manifest confirms same wrapper";
else
    if isfield(payload, "blocker_if_any")
        reason = "provenance manifest not ready: " + string(payload.blocker_if_any);
    else
        reason = "provenance manifest does not confirm same wrapper";
    end
end
end

function ok = sameWrapperProvenance(handwiredModelPath, priorCommand, nextCommand, manifestReady, manifestModel)
[~, loadedModel, ~] = fileparts(handwiredModelPath);
priorModel = commandModelName(priorCommand);
nextModel = commandModelName(nextCommand);
ok = strlength(priorModel) > 0 && priorModel == nextModel && priorModel == string(loadedModel);
if manifestReady
    ok = ok && string(manifestModel) == string(loadedModel);
end
end

function modelName = commandModelName(commandPath)
parts = split(string(commandPath), "/");
if numel(parts) == 0
    modelName = "";
else
    modelName = parts(1);
end
end

function row = buildBaseRow(pair)
row = struct();
row.pair_id = string(pair.pair_id);
row.state_id = string(pair.state_id);
row.prior_outaged_branch = string(pair.prior_outaged_branch);
row.candidate_next_branch = string(pair.candidate_next_branch);
row.planned_contingency_sequence = pair.planned_contingency_sequence;
row.selection_bucket = string(pair.selection_bucket);
row.execution_status = "blocked";
row.pilot_label_value = [];
row.pilot_label_status = "blocked";
row.dynamic_stress_score_if_available = [];
row.unstable_flag_if_available = [];
row.instability_or_risk_reason = "";
row.timeout_or_failure_reason = "not executed";
row.evidence_source = "matlab_selected_pair_entrypoint";
row.raw_trajectory_committed = false;
row.full_timeseries_committed = false;
row.mat_file_committed = false;
row.bus_fault_label_used = false;
row.l12_special_case_flag = row.prior_outaged_branch == "L12" || row.candidate_next_branch == "L12";
row.notes = "single-pair compact evidence only; not a formal training label";
end

function row = executeOnePair(row, handwiredModelPath, outputDir, validation, priorCommand, nextCommand, options)
try
    configure_ieee39_short_filegen_paths();
catch
end
try
    load_system(handwiredModelPath);
    [~, modelName, ~] = fileparts(handwiredModelPath);
    for idx = 1:height(validation)
        commandPath = string(validation.trip_command_path(idx));
        if strlength(commandPath) > 0
            try
                set_param(commandPath, "Time", "1000");
            catch
            end
        end
    end
    set_param(priorCommand, "Time", num2str(options.prior_trip_time));
    set_param(nextCommand, "Time", num2str(options.next_trip_time));
    simOut = sim(modelName, "StopTime", num2str(options.simulation_stop_time), "TimeOut", options.timeout_s);
    signalSummary = extract_ieee39_signal_summary(simOut, "selected_pair_" + row.pair_id, outputDir);
    row.execution_status = "succeeded";
    row.pilot_label_status = "unknown";
    row.timeout_or_failure_reason = "";
    row.evidence_source = "matlab_single_pair_smoke_compact_simulation";
    row.dynamic_stress_score_if_available = [];
    row.unstable_flag_if_available = [];
    row.instability_or_risk_reason = "compact signal status: " + string(signalSummary.measurement_extraction_status);
    close_system(modelName, 0);
catch ME
    row.pilot_label_value = [];
    row.evidence_source = "matlab_single_pair_smoke_failed";
    if contains(lower(string(ME.message)), "timeout") || contains(lower(string(ME.message)), "time out")
        row.execution_status = "timeout";
        row.pilot_label_status = "timeout";
        row.timeout_or_failure_reason = "single-pair smoke timeout: " + string(ME.message);
    else
        row.execution_status = "failed";
        row.pilot_label_status = "failed";
        row.timeout_or_failure_reason = "single-pair smoke failed: " + string(ME.message);
    end
    try
        [~, modelName, ~] = fileparts(handwiredModelPath);
        close_system(modelName, 0);
    catch
    end
end
end
