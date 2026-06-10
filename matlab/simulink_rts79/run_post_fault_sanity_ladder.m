function summaryTable = run_post_fault_sanity_ladder(basecasePath, inputRoot, outputDir, optionsJsonPath)
%RUN_POST_FAULT_SANITY_LADDER Run post-fault sanity ladder controls.
%
% This ladder checks whether post-fault dynamic responses have reasonable
% layers. It is a calibration sanity check, not EMT, not full OPF, and not an
% engineering-grade dynamic stability conclusion.

if nargin < 1 || isempty(basecasePath)
    basecasePath = "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json";
end
if nargin < 2 || isempty(inputRoot)
    inputRoot = "../../results/gcn_search/simulink_dynamic_negative_controls/inputs";
end
if nargin < 3 || isempty(outputDir)
    outputDir = "../../results/gcn_search/simulink_dynamic_post_fault_sanity";
end
if nargin < 4 || isempty(optionsJsonPath)
    optionsJsonPath = "../../results/gcn_search/simulink_dynamic_calibration/recommended_event_driven_options.json";
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

options = loadOptionsLadderLocal(optionsJsonPath);
groups = buildLadderCasesLocal(inputRoot, outputDir);
rows = {};
rowIdx = 0;
for g = 1:numel(groups)
    group = groups(g);
    resultDir = fullfile(outputDir, "case_results", char(group.name));
    if ~exist(resultDir, "dir")
        mkdir(resultDir);
    end
    resultParts = cell(numel(group.caseIds), 1);
    for idx = 1:numel(group.caseIds)
        [resultParts{idx}, ~, ~] = simulate_rts79_swing_case(basecasePath, group.eventCsv, group.caseIds(idx), resultDir, false, options);
    end
    results = vertcat(resultParts{:});
    rowIdx = rowIdx + 1;
    rows(rowIdx, :) = summarizeGroupLocal(group.name, results); %#ok<AGROW>
end
summaryTable = cell2table(rows, "VariableNames", ["case_group", "num_cases", "unstable_count", "unstable_fraction", ...
    "mean_frequency_nadir_hz", "min_frequency_nadir_hz", "mean_rotor_angle_separation_coi_deg", ...
    "max_rotor_angle_separation_coi_deg", "passive_trip_fraction", "security_action_fraction", ...
    "mean_dynamic_load_shed_mw", "mean_dynamic_stress_score", "sanity_level_passed"]);
writetable(summaryTable, fullfile(outputDir, "post_fault_sanity_ladder_summary.csv"));
payload = tableToStructLocal(summaryTable);
payload.overall_sanity_ladder_passed = all(logical(summaryTable.sanity_level_passed));
payload.note = "Post-fault sanity ladder; not a formal dynamic validation conclusion.";
fid = fopen(fullfile(outputDir, "post_fault_sanity_ladder_summary.json"), "w");
fprintf(fid, "%s", jsonencode(payload, "PrettyPrint", true));
fclose(fid);
writeBriefLocal(summaryTable, fullfile(outputDir, "post_fault_sanity_ladder_brief.md"));
end

function groups = buildLadderCasesLocal(inputRoot, outputDir)
groups = struct("name", {}, "eventCsv", {}, "caseIds", {});
groups(end + 1) = createGroupLocal("no_trip", strings(0, 1), outputDir);
groups(end + 1) = createGroupLocal("single_mild_trip", ["L01"], outputDir);
groups(end + 1) = createGroupFromInputLocal("low_risk_ordered_n2", fullfile(inputRoot, "low_score_top20_input_paths.csv"), 3, outputDir);
groups(end + 1) = createGroupFromInputLocal("random_ordered_n2", fullfile(inputRoot, "random_top20_input_paths.csv"), 3, outputDir);
groups(end + 1) = createGroupFromInputLocal("learned_high_risk_n2", fullfile(inputRoot, "learned_top20_input_paths.csv"), 3, outputDir);
end

function group = createGroupFromInputLocal(name, csvPath, maxCases, outputDir)
paths = ["L01->L02"; "L03->L04"; "L05->L06"];
if exist(csvPath, "file")
    tableIn = readtable(csvPath, "TextType", "string");
    if ismember("path", tableIn.Properties.VariableNames) && height(tableIn) > 0
        paths = string(tableIn.path(1:min(maxCases, height(tableIn))));
    end
end
caseRows = {};
rowIdx = 0;
caseIds = strings(numel(paths), 1);
for idx = 1:numel(paths)
    caseId = string(name) + "_" + sprintf("%04d", idx);
    caseIds(idx) = caseId;
    parts = split(paths(idx), "->");
    firstLine = strtrim(parts(1));
    secondLine = strtrim(parts(min(2, numel(parts))));
    rowIdx = rowIdx + 1;
    caseRows(rowIdx, :) = {caseId, 1.0, firstLine, 10.0}; %#ok<AGROW>
    rowIdx = rowIdx + 1;
    caseRows(rowIdx, :) = {caseId, 3.0, secondLine, 10.0}; %#ok<AGROW>
end
eventCsv = fullfile(outputDir, string(name) + "_events.csv");
eventTable = cell2table(caseRows, "VariableNames", ["case_id", "event_time", "event_line", "simulation_end_time"]);
writetable(eventTable, eventCsv);
group = struct("name", string(name), "eventCsv", eventCsv, "caseIds", caseIds);
end

function group = createGroupLocal(name, lines, outputDir)
caseId = string(name) + "_0001";
caseRows = {};
for idx = 1:numel(lines)
    caseRows(idx, :) = {caseId, 1.0 + 2.0 * (idx - 1), string(lines(idx)), 10.0}; %#ok<AGROW>
end
if isempty(caseRows)
    eventTable = table(string.empty(0, 1), zeros(0, 1), string.empty(0, 1), zeros(0, 1), ...
        'VariableNames', ["case_id", "event_time", "event_line", "simulation_end_time"]);
else
    eventTable = cell2table(caseRows, "VariableNames", ["case_id", "event_time", "event_line", "simulation_end_time"]);
end
eventCsv = fullfile(outputDir, string(name) + "_events.csv");
writetable(eventTable, eventCsv);
group = struct("name", string(name), "eventCsv", eventCsv, "caseIds", caseId);
end

function row = summarizeGroupLocal(name, results)
unstable = logical(results.dynamic_unstable);
numCases = height(results);
freq = double(results.frequency_nadir_hz);
if ismember("max_rotor_angle_separation_coi_deg", results.Properties.VariableNames)
    angle = double(results.max_rotor_angle_separation_coi_deg);
else
    angle = double(results.max_rotor_angle_separation_deg);
end
passive = double(results.passive_relay_trip_count) > 0;
security = double(results.security_redispatch_count) > 0;
shed = double(results.dynamic_load_shed_mw);
stress = (49.5 - freq);
stress(stress < 0) = 0;
stress = stress + max(angle / 180.0 - 1.0, 0) + max(double(results.max_line_loading_ratio) - 1.0, 0) + passive;
unstableFraction = mean(unstable);
switch string(name)
    case "no_trip"
        passed = unstableFraction == 0;
    case "single_mild_trip"
        passed = unstableFraction == 0;
    case {"low_risk_ordered_n2", "random_ordered_n2"}
        passed = unstableFraction < 1.0;
    otherwise
        passed = true;
end
row = {string(name), numCases, sum(unstable), unstableFraction, mean(freq), min(freq), mean(angle), max(angle), ...
    mean(passive), mean(security), mean(shed), mean(stress), passed};
end

function options = loadOptionsLadderLocal(optionsJsonPath)
if exist(optionsJsonPath, "file")
    options = jsondecode(fileread(optionsJsonPath));
else
    options = struct();
end
options.simulation_end_time = 10.0;
if ~isfield(options, "pm_update_mode")
    options.pm_update_mode = "rebalance_to_current_pe";
end
end

function payload = tableToStructLocal(tableIn)
payload = struct();
for idx = 1:height(tableIn)
    key = matlab.lang.makeValidName(char(tableIn.case_group(idx)));
    payload.(key) = table2struct(tableIn(idx, :));
end
end

function writeBriefLocal(summaryTable, path)
fid = fopen(path, "w");
fprintf(fid, "# Post-Fault Sanity Ladder Brief\n\n");
fprintf(fid, "| case_group | unstable_fraction | passive_trip_fraction | mean_stress | passed |\n");
fprintf(fid, "| --- | ---: | ---: | ---: | --- |\n");
for idx = 1:height(summaryTable)
    fprintf(fid, "| %s | %.4f | %.4f | %.4f | %s |\n", string(summaryTable.case_group(idx)), ...
        double(summaryTable.unstable_fraction(idx)), double(summaryTable.passive_trip_fraction(idx)), ...
        double(summaryTable.mean_dynamic_stress_score(idx)), string(summaryTable.sanity_level_passed(idx)));
end
fprintf(fid, "\nNo dynamic recall is reported because no full dynamic truth is available.\n");
fclose(fid);
end
