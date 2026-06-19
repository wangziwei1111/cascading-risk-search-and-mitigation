function summary = prepare_ieee39_spp001_same_wrapper_bridge_lab(pairId, sourceWrapperPath, outputDir, varargin)
%PREPARE_IEEE39_SPP001_SAME_WRAPPER_BRIDGE_LAB Guarded local lab-copy builder.
%
% This helper is a skeleton for a future manually approved SPP001-only
% same-wrapper bridge lab. It defaults to dry_run_only=true, does not run
% simulation, does not export formal labels, does not save raw trajectories,
% does not save full timeseries, does not save MAT files, and does not modify
% the source SLX model. Any generated bridge SLX must be a local lab copy and
% must not be committed.
%
% phasor_RMS is not EMT. generator_speed_proxy is not direct frequency.

parser = inputParser;
addOptional(parser, "pairId", "SPP001", @(x) ischar(x) || isstring(x));
addOptional(parser, "sourceWrapperPath", "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper.slx", @(x) ischar(x) || isstring(x));
addOptional(parser, "outputDir", "../../results/gcn_search/ieee39_spp001_same_wrapper_bridge_dry_run/local_lab_copy", @(x) ischar(x) || isstring(x));
addParameter(parser, "dry_run_only", true, @(x) islogical(x) || isnumeric(x));
addParameter(parser, "prior_line", "L15", @(x) ischar(x) || isstring(x));
addParameter(parser, "next_line", "L04", @(x) ischar(x) || isstring(x));
addParameter(parser, "build_local_copy", false, @(x) islogical(x) || isnumeric(x));
parse(parser, pairId, sourceWrapperPath, outputDir, varargin{:});

pairId = string(parser.Results.pairId);
priorLine = upper(string(parser.Results.prior_line));
nextLine = upper(string(parser.Results.next_line));
dryRunOnly = logical(parser.Results.dry_run_only);
buildLocalCopy = logical(parser.Results.build_local_copy);
sourceWrapperPath = string(parser.Results.sourceWrapperPath);
outputDir = string(parser.Results.outputDir);

if pairId ~= "SPP001" || priorLine ~= "L15" || nextLine ~= "L04"
    error("IEEE39SPP001Bridge:PairGuard", "Only SPP001 with prior L15 and next L04 is allowed.");
end
if buildLocalCopy && dryRunOnly
    error("IEEE39SPP001Bridge:DryRunOnly", "build_local_copy requires a separate approved non-dry-run call.");
end

targetModelName = "IEEE39BusSystem_dynamic_experiment_wrapper_spp001_same_wrapper_bridge_lab";
targetPath = fullfile(outputDir, targetModelName + ".slx");
sourceFound = isfile(sourceWrapperPath);
targetCreated = false;
sameWrapperConfirmed = false;
note = "dry_run_only=true; local bridge lab copy was not built";

if buildLocalCopy && ~dryRunOnly
    if ~exist(outputDir, "dir")
        mkdir(outputDir);
    end
    % Future approved implementation should copy sourceWrapperPath to targetPath,
    % insert or import L15/L04 handwired breaker controls into the same model,
    % and then inspect only compact readiness evidence. It must not run sim().
    note = "local bridge lab copy build skeleton reached; implementation intentionally guarded";
end

summary = struct();
summary.bridge_scope = "spp001_same_wrapper_bridge_lab_builder_skeleton";
summary.pair_id = char(pairId);
summary.prior_outaged_branch = char(priorLine);
summary.candidate_next_branch = char(nextLine);
summary.source_wrapper_path = char(sourceWrapperPath);
summary.output_dir = char(outputDir);
summary.target_local_lab_copy_path = char(targetPath);
summary.dry_run_only = dryRunOnly;
summary.build_local_copy_requested = buildLocalCopy;
summary.source_found = sourceFound;
summary.target_created = targetCreated;
summary.same_wrapper_confirmed = sameWrapperConfirmed;
summary.simulink_run = false;
summary.formal_labels_exported = false;
summary.raw_trajectories_saved = false;
summary.full_timeseries_saved = false;
summary.mat_files_saved = false;
summary.source_slx_modified = false;
summary.local_lab_copy_committed = false;
summary.note = char(note);
end
