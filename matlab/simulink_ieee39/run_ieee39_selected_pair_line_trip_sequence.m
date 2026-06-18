function summary = run_ieee39_selected_pair_line_trip_sequence(manifestPath, outputDir, varargin)
%RUN_IEEE39_SELECTED_PAIR_LINE_TRIP_SEQUENCE Guarded selected-pair skeleton.
%
% This is a guarded entrypoint skeleton for future IEEE39 selected-32-only
% two-step line-trip evidence collection. It does not run the full 1056
% generation, does not export formal labels, does not save raw trajectory,
% does not save full timeseries, does not save MAT files, and does not modify
% the source SLX model.
%
% phasor_RMS is not EMT. beta * RATE_A is an audit-only proxy, not a real
% relay setting. Dynamic outputs are outputs/targets only, not input features.

parser = inputParser;
addRequired(parser, "manifestPath", @(x) ischar(x) || isstring(x));
addRequired(parser, "outputDir", @(x) ischar(x) || isstring(x));
addParameter(parser, "approved_selected_pairs_only", false, @(x) islogical(x) || isnumeric(x));
addParameter(parser, "execute", false, @(x) islogical(x) || isnumeric(x));
addParameter(parser, "timeout_s", 240, @(x) isnumeric(x) && isscalar(x) && x > 0);
parse(parser, manifestPath, outputDir, varargin{:});

approvedSelectedPairsOnly = logical(parser.Results.approved_selected_pairs_only);
executeRequested = logical(parser.Results.execute);
manifestPath = char(parser.Results.manifestPath);
outputDir = char(parser.Results.outputDir);

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

if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

rows = repmat(struct( ...
    "pair_id", "", ...
    "execution_status", "blocked", ...
    "pilot_label_value", [], ...
    "pilot_label_status", "blocked", ...
    "dynamic_stress_score_if_available", [], ...
    "unstable_flag_if_available", [], ...
    "timeout_or_failure_reason", "MATLAB entrypoint skeleton did not execute simulation", ...
    "evidence_source", "matlab_guarded_skeleton", ...
    "raw_trajectory_committed", false, ...
    "full_timeseries_committed", false, ...
    "mat_file_committed", false), pairCount, 1);

for idx = 1:pairCount
    prior = string(pairs(idx).prior_outaged_branch);
    next = string(pairs(idx).candidate_next_branch);
    if prior == "L12" || next == "L12"
        rows(idx).timeout_or_failure_reason = "L12 remains special/excluded";
    end
    rows(idx).pair_id = string(pairs(idx).pair_id);
end

summary = struct();
summary.execution_scope = "selected_pair_matlab_entrypoint_skeleton";
summary.approved_selected_pairs_only = approvedSelectedPairsOnly;
summary.execute_requested = executeRequested;
summary.selected_pair_count = pairCount;
summary.selected_pairs_executed = false;
summary.simulink_run = false;
summary.full_1056_generation_run = false;
summary.formal_labels_exported = false;
summary.raw_trajectories_saved = false;
summary.full_timeseries_saved = false;
summary.mat_files_saved = false;
summary.timeout_policy = "timeout remains timeout/unknown and is not converted to 0/1";
summary.unknown_policy = "blocked, failed, timeout, and unknown remain null";
summary.rows = rows;

summaryPath = fullfile(outputDir, "matlab_selected_pair_compact_evidence_summary.json");
fid = fopen(summaryPath, "w");
if fid < 0
    error("IEEE39SelectedPair:WriteFailed", "Cannot write compact evidence summary: %s", summaryPath);
end
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, "%s", jsonencode(summary, PrettyPrint=true));
clear cleanup;
end
