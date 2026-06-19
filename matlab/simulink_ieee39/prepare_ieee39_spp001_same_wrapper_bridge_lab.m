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
addParameter(parser, "dry_run_only", false, @(x) islogical(x) || isnumeric(x));
addParameter(parser, "prior_line", "L15", @(x) ischar(x) || isstring(x));
addParameter(parser, "next_line", "L04", @(x) ischar(x) || isstring(x));
addParameter(parser, "build_local_copy", false, @(x) islogical(x) || isnumeric(x));
addParameter(parser, "l15_source_lab_path", "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15.slx", @(x) ischar(x) || isstring(x));
parse(parser, pairId, sourceWrapperPath, outputDir, varargin{:});

pairId = string(parser.Results.pairId);
priorLine = upper(string(parser.Results.prior_line));
nextLine = upper(string(parser.Results.next_line));
dryRunOnly = logical(parser.Results.dry_run_only);
buildLocalCopy = logical(parser.Results.build_local_copy);
sourceWrapperPath = string(parser.Results.sourceWrapperPath);
outputDir = string(parser.Results.outputDir);
l15SourceLabPath = string(parser.Results.l15_source_lab_path);

if pairId ~= "SPP001" || priorLine ~= "L15" || nextLine ~= "L04"
    error("IEEE39SPP001Bridge:PairGuard", "Only SPP001 with prior L15 and next L04 is allowed.");
end
targetModelName = "IEEE39BusSystem_dynamic_experiment_wrapper_spp001_same_wrapper_bridge_lab";
targetPath = fullfile(outputDir, targetModelName + ".slx");
sourceFound = isfile(sourceWrapperPath);
l15SourceFound = isfile(l15SourceLabPath);
targetCreated = false;
sameWrapperConfirmed = false;
containsL15Command = false;
containsL04Command = false;
containsL15Breaker = false;
containsL04Breaker = false;
copiedL15Command = false;
copiedL15Breaker = false;
note = "local bridge lab copy was not built";

if buildLocalCopy && ~dryRunOnly
    if ~exist(outputDir, "dir")
        mkdir(outputDir);
    end
    if sourceFound
        copyfile(sourceWrapperPath, targetPath, "f");
        targetCreated = isfile(targetPath);
        if targetCreated
            try
                load_system(targetPath);
                if l15SourceFound
                    load_system(l15SourceLabPath);
                    [~, l15SourceModelName, ~] = fileparts(l15SourceLabPath);
                    copiedL15Command = copyNamedBlockIfMissing(l15SourceModelName, targetModelName, "L15_TripCommand");
                    copiedL15Breaker = copyNamedBlockIfMissing(l15SourceModelName, targetModelName, "L15_HandwiredTimedBreaker");
                    try
                        close_system(l15SourceModelName, 0);
                    catch
                    end
                end
                containsL15Command = hasNamedBlock(targetModelName, "L15_TripCommand");
                containsL04Command = hasNamedBlock(targetModelName, "L04_TripCommand");
                containsL15Breaker = hasNamedBlock(targetModelName, "L15_HandwiredTimedBreaker");
                containsL04Breaker = hasNamedBlock(targetModelName, "L04_HandwiredTimedBreaker");
                save_system(targetModelName);
                close_system(targetModelName, 0);
            catch ME
                try
                    close_system(targetModelName, 0);
                catch
                end
                try
                    if exist("l15SourceModelName", "var")
                        close_system(l15SourceModelName, 0);
                    end
                catch
                end
                note = "local bridge lab copy created, but compact validation failed: " + string(ME.message);
            end
        end
    end
    sameWrapperConfirmed = targetCreated && containsL15Command && containsL04Command && containsL15Breaker && containsL04Breaker;
    if sameWrapperConfirmed
        note = "local bridge lab copy contains L15/L04 TripCommand and breaker blocks in the same wrapper; no simulation was run";
    elseif ~l15SourceFound
        note = "L15 source clean-lab model was not found; no simulation was run";
    elseif strlength(note) == 0 || note == "local bridge lab copy was not built"
        note = "local bridge lab copy was created or attempted, but same-wrapper TripCommand validation did not pass; no simulation was run";
    end
elseif buildLocalCopy && dryRunOnly
    note = "dry_run_only=true; approved local build was not executed";
end

summary = struct();
summary.bridge_scope = "spp001_same_wrapper_bridge_lab_builder_skeleton";
summary.pair_id = char(pairId);
summary.prior_outaged_branch = char(priorLine);
summary.candidate_next_branch = char(nextLine);
summary.source_wrapper_path = char(sourceWrapperPath);
summary.l15_source_lab_path = char(l15SourceLabPath);
summary.output_dir = char(outputDir);
summary.target_local_lab_copy_path = char(targetPath);
summary.dry_run_only = dryRunOnly;
summary.build_local_copy_requested = buildLocalCopy;
summary.source_found = sourceFound;
summary.l15_source_found = l15SourceFound;
summary.target_created = targetCreated;
summary.copied_l15_trip_command = copiedL15Command;
summary.copied_l15_breaker = copiedL15Breaker;
summary.l15_trip_command_found_in_bridge = containsL15Command;
summary.l04_trip_command_found_in_bridge = containsL04Command;
summary.l15_breaker_found_in_bridge = containsL15Breaker;
summary.l04_breaker_found_in_bridge = containsL04Breaker;
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

function copied = copyNamedBlockIfMissing(sourceModelName, targetModelName, blockName)
copied = false;
if hasNamedBlock(targetModelName, blockName)
    copied = true;
    return;
end
sourceBlocks = find_system(sourceModelName, "LookUnderMasks", "all", "FollowLinks", "on", "Name", char(blockName));
if isempty(sourceBlocks)
    return;
end
targetGrid = targetModelName + "/Grid";
if isempty(find_system(targetModelName, "SearchDepth", 1, "Name", "Grid"))
    return;
end
destination = targetGrid + "/" + blockName;
try
    add_block(sourceBlocks{1}, char(destination), "MakeNameUnique", "off");
    copied = hasNamedBlock(targetModelName, blockName);
catch
    copied = false;
end
end

function found = hasNamedBlock(modelName, targetName)
found = false;
try
    blocks = find_system(modelName, "LookUnderMasks", "all", "FollowLinks", "on");
    for idx = 1:numel(blocks)
        try
            name = string(get_param(blocks{idx}, "Name"));
            if strcmpi(strtrim(name), strtrim(string(targetName)))
                found = true;
                return;
            end
        catch
        end
    end
catch
end
end
