function [resultTable, trajectorySummary, lineLoadingSummary] = simulate_rts79_swing_case(basecasePath, eventTablePath, caseId, outputDir, saveTrajectories)
%SIMULATE_RTS79_SWING_CASE Run a simplified RTS-79 multi-machine swing simulation.
%
% This is a simplified electromechanical swing-equation prototype. It is not
% EMT, does not include renewable generation, and does not include detailed
% exciters, governors, or PSS. Missing dynamic parameters are assumed
% defaults exported by export_rts79_simulink_basecase.py.

if nargin < 4 || isempty(outputDir)
    outputDir = "../../results/gcn_search/simulink_dynamic_results";
end
if nargin < 5 || isempty(saveTrajectories)
    saveTrajectories = false;
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

[baseDir, ~, ~] = fileparts(basecasePath);
branches = readtable(fullfile(baseDir, "rts79_simulink_branches.csv"), "TextType", "string");
generators = readtable(fullfile(baseDir, "rts79_simulink_generators.csv"), "TextType", "string");
loads = readtable(fullfile(baseDir, "rts79_simulink_loads.csv"), "TextType", "string");
events = readtable(eventTablePath, "TextType", "string");
caseEvents = sortrows(events(events.case_id == string(caseId), :), "event_time");
if height(caseEvents) ~= 2
    error("Expected two trip events for case_id=%s, got %d", string(caseId), height(caseEvents));
end

systemBaseMva = readSystemBaseMvaLocal(basecasePath);
f0 = 50.0;
genBus = double(generators.bus_id);
ng = height(generators);
M = 2.0 * max(double(generators.H_s), 0.1);
D = max(double(generators.D_pu), 10.0);
delta0 = initialGeneratorAnglesLocal(branches, generators, loads, systemBaseMva);
omega0 = ones(ng, 1);
y0 = [delta0; omega0];
[Bbus0, ~] = buildBbusLocal(branches, strings(0, 1));
Bred0 = kronReduceToGeneratorsLocal(Bbus0, genBus);
Bred0 = normalizeCouplingLocal(Bred0);
Pm = electricalPowerLocal(delta0, Bred0);

allT = [];
allY = [];
lineRows = {};
offlineLines = strings(0, 1);
segmentStarts = [0; double(caseEvents.event_time(:))];
segmentEnds = [double(caseEvents.event_time(:)); max(double(caseEvents.simulation_end_time(1)), double(caseEvents.event_time(end)))];
currentY = y0;

for segIdx = 1:numel(segmentEnds)
    if segIdx > 1
        offlineLines(end + 1, 1) = caseEvents.event_line(segIdx - 1);
    end
    [Bbus, activeBranches] = buildBbusLocal(branches, offlineLines);
    Bred = kronReduceToGeneratorsLocal(Bbus, genBus);
    Bred = normalizeCouplingLocal(Bred);
    tStart = segmentStarts(segIdx);
    tEnd = segmentEnds(segIdx);
    if tEnd <= tStart
        continue;
    end
    ode = @(t, y) swingOdeLocal(t, y, Pm, M, D, Bred, f0);
    opts = odeset("RelTol", 1e-5, "AbsTol", 1e-7, "MaxStep", 0.05);
    [tSeg, ySeg] = ode45(ode, [tStart tEnd], currentY, opts);
    if ~isempty(allT) && abs(tSeg(1) - allT(end)) < 1e-9
        tSeg = tSeg(2:end);
        ySeg = ySeg(2:end, :);
    end
    allT = [allT; tSeg]; %#ok<AGROW>
    allY = [allY; ySeg]; %#ok<AGROW>
    currentY = ySeg(end, :)';
    lineRows = [lineRows; lineLoadingRowsLocal(tSeg, ySeg, activeBranches, genBus, systemBaseMva)]; %#ok<AGROW>
end

if isempty(allT)
    error("No integration segment was produced for case_id=%s", string(caseId));
end

omega = allY(:, ng + 1:end);
frequencyHz = f0 .* omega;
frequencyNadirHz = min(frequencyHz, [], "all");
frequencyZenithHz = max(frequencyHz, [], "all");
delta = allY(:, 1:ng);
maxRotorAngleSeparationDeg = max((max(delta, [], 2) - min(delta, [], 2)) * 180 / pi);
lineLoadingSummary = cell2table(lineRows, "VariableNames", ["time_s", "line_label", "loading_ratio"]);
maxLineLoadingRatio = max(double(lineLoadingSummary.loading_ratio));
[dynamicUnstable, unstableReason] = classifyDynamicStabilityLocal(frequencyNadirHz, maxRotorAngleSeparationDeg, maxLineLoadingRatio);

resultTable = table( ...
    string(caseId), true, true, frequencyNadirHz, frequencyZenithHz, ...
    maxRotorAngleSeparationDeg, maxLineLoadingRatio, height(caseEvents), ...
    dynamicUnstable, string(unstableReason), "simulink_swing_prototype", ...
    'VariableNames', ["case_id", "sim_completed", "converged", "frequency_nadir_hz", ...
    "frequency_zenith_hz", "max_rotor_angle_separation_deg", "max_line_loading_ratio", ...
    "dynamic_trip_count", "dynamic_unstable", "unstable_reason", "result_source"]);

trajectorySummary = trajectorySummaryTableLocal(allT, allY, generators, f0);
writetable(resultTable, fullfile(outputDir, "dynamic_case_result_" + string(caseId) + ".csv"));
writetable(trajectorySummary, fullfile(outputDir, "dynamic_case_trajectory_summary_" + string(caseId) + ".csv"));

if saveTrajectories
    rawDir = fullfile(outputDir, "raw_trajectories");
    if ~exist(rawDir, "dir")
        mkdir(rawDir);
    end
    writetable(trajectorySummary, fullfile(rawDir, "dynamic_case_trajectory_" + string(caseId) + ".csv"));
    writetable(lineLoadingSummary, fullfile(rawDir, "dynamic_case_line_loading_" + string(caseId) + ".csv"));
end
end

function systemBaseMva = readSystemBaseMvaLocal(basecasePath)
systemBaseMva = 100.0;
try
    raw = jsondecode(fileread(basecasePath));
    if isfield(raw, "system_base_mva")
        systemBaseMva = double(raw.system_base_mva);
    elseif isfield(raw, "base_mva")
        systemBaseMva = double(raw.base_mva);
    end
catch
    systemBaseMva = 100.0;
end
end

function [Bbus, activeBranches] = buildBbusLocal(branches, offlineLines)
busIds = unique([double(branches.from_bus); double(branches.to_bus)]);
nb = max(busIds);
Bbus = zeros(nb, nb);
isOffline = ismember(upper(string(branches.line_label)), upper(string(offlineLines)));
isActive = double(branches.status) ~= 0 & ~isOffline;
activeBranches = branches(isActive, :);
for idx = 1:height(activeBranches)
    i = double(activeBranches.from_bus(idx));
    j = double(activeBranches.to_bus(idx));
    x = abs(double(activeBranches.x_pu(idx)));
    if x < 1e-6
        continue;
    end
    b = 1.0 / x;
    Bbus(i, i) = Bbus(i, i) + b;
    Bbus(j, j) = Bbus(j, j) + b;
    Bbus(i, j) = Bbus(i, j) - b;
    Bbus(j, i) = Bbus(j, i) - b;
end
end

function Bred = kronReduceToGeneratorsLocal(Bbus, genBus)
nb = size(Bbus, 1);
genBus = double(genBus(:));
loadBus = setdiff((1:nb)', unique(genBus), "stable");
if isempty(loadBus)
    BredBus = Bbus;
else
    Bgg = Bbus(unique(genBus), unique(genBus));
    Bgl = Bbus(unique(genBus), loadBus);
    Blg = Bbus(loadBus, unique(genBus));
    Bll = Bbus(loadBus, loadBus);
    BredBus = Bgg - Bgl * pinv(Bll) * Blg;
end
[uniqueGenBus, ~, busGroup] = unique(genBus, "stable");
BredUnique = BredBus(1:numel(uniqueGenBus), 1:numel(uniqueGenBus));
ng = numel(genBus);
Bred = zeros(ng, ng);
for i = 1:ng
    for j = 1:ng
        Bred(i, j) = BredUnique(busGroup(i), busGroup(j));
    end
end
end

function Bscaled = normalizeCouplingLocal(Bred)
scale = max(abs(Bred), [], "all");
if scale < 1e-9
    Bscaled = Bred;
else
    Bscaled = 2.0 * Bred / scale;
end
end

function delta0 = initialGeneratorAnglesLocal(branches, generators, loads, systemBaseMva)
[Bbus, ~] = buildBbusLocal(branches, strings(0, 1));
nb = size(Bbus, 1);
Pinj = zeros(nb, 1);
for idx = 1:height(generators)
    Pinj(double(generators.bus_id(idx))) = Pinj(double(generators.bus_id(idx))) + double(generators.pg_mw(idx)) / systemBaseMva;
end
for idx = 1:height(loads)
    Pinj(double(loads.bus_id(idx))) = Pinj(double(loads.bus_id(idx))) - double(loads.pd_mw(idx)) / systemBaseMva;
end
Pinj = Pinj - mean(Pinj);
theta = pinv(Bbus + 1e-6 * eye(nb)) * Pinj;
delta0 = theta(double(generators.bus_id));
delta0 = delta0 - mean(delta0);
end

function dydt = swingOdeLocal(~, y, Pm, M, D, Bred, f0)
ng = numel(Pm);
delta = y(1:ng);
omega = y(ng + 1:end);
    Pe = electricalPowerLocal(delta, Bred);
dDelta = 2 * pi * f0 * (omega - 1.0);
dOmega = (Pm - Pe - D .* (omega - 1.0)) ./ M;
dydt = [dDelta; dOmega];
end

function Pe = electricalPowerLocal(delta, Bred)
ng = numel(delta);
Pe = zeros(ng, 1);
for i = 1:ng
    for j = 1:ng
        Pe(i) = Pe(i) + Bred(i, j) * sin(delta(i) - delta(j));
    end
end
end

function rows = lineLoadingRowsLocal(tSeg, ySeg, activeBranches, genBus, systemBaseMva)
ng = numel(genBus);
rows = cell(height(activeBranches) * numel(tSeg), 3);
rowIdx = 0;
genBus = double(genBus(:));
for tIdx = 1:numel(tSeg)
    delta = ySeg(tIdx, 1:ng)';
    for brIdx = 1:height(activeBranches)
        fromBus = double(activeBranches.from_bus(brIdx));
        toBus = double(activeBranches.to_bus(brIdx));
        fromAngle = busAngleFromGeneratorsLocal(fromBus, genBus, delta);
        toAngle = busAngleFromGeneratorsLocal(toBus, genBus, delta);
        x = max(abs(double(activeBranches.x_pu(brIdx))), 1e-6);
        flowMw = abs((fromAngle - toAngle) / x) * systemBaseMva;
        rateMva = max(abs(double(activeBranches.rate_mva(brIdx))), 1e-6);
        rowIdx = rowIdx + 1;
        rows(rowIdx, :) = {double(tSeg(tIdx)), string(activeBranches.line_label(brIdx)), double(flowMw / rateMva)};
    end
end
rows = rows(1:rowIdx, :);
end

function angle = busAngleFromGeneratorsLocal(busId, genBus, delta)
matches = find(genBus == busId);
if isempty(matches)
    [~, nearest] = min(abs(genBus - busId));
    angle = delta(nearest);
else
    angle = mean(delta(matches));
end
end

function trajectorySummary = trajectorySummaryTableLocal(allT, allY, generators, f0)
ng = height(generators);
rows = cell(numel(allT) * ng, 5);
rowIdx = 0;
for tIdx = 1:numel(allT)
    for genIdx = 1:ng
        rowIdx = rowIdx + 1;
        omega = allY(tIdx, ng + genIdx);
        rows(rowIdx, :) = {
            double(allT(tIdx)), ...
            string(generators.gen_id(genIdx)), ...
            double(allY(tIdx, genIdx)), ...
            double(omega), ...
            double(f0 * omega)};
    end
end
trajectorySummary = cell2table(rows, "VariableNames", ["time_s", "gen_id", "delta_rad", "omega_pu", "frequency_hz"]);
end

function [dynamicUnstable, unstableReason] = classifyDynamicStabilityLocal(frequencyNadirHz, maxRotorAngleSeparationDeg, maxLineLoadingRatio)
reasons = strings(0, 1);
if frequencyNadirHz < 49.0
    reasons(end + 1, 1) = "frequency_nadir_below_49hz";
end
if maxRotorAngleSeparationDeg > 180.0
    reasons(end + 1, 1) = "rotor_angle_separation_above_180deg";
end
if maxLineLoadingRatio > 1.5
    reasons(end + 1, 1) = "line_loading_above_1p5";
end
dynamicUnstable = ~isempty(reasons);
if dynamicUnstable
    unstableReason = strjoin(reasons, ";");
else
    unstableReason = "stable_by_swing_prototype_thresholds";
end
end

