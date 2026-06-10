function [resultTable, trajectorySummary, lineLoadingSummary] = simulate_rts79_swing_case(basecasePath, eventTablePath, caseId, outputDir, saveTrajectories, options)
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
if nargin < 6 || isempty(options)
    options = defaultSwingOptionsLocal();
else
    options = mergeSwingOptionsLocal(options);
end
if ~exist(outputDir, "dir")
    mkdir(outputDir);
end

[baseDir, ~, ~] = fileparts(basecasePath);
branches = readtable(fullfile(baseDir, "rts79_simulink_branches.csv"), "TextType", "string");
generators = readtable(fullfile(baseDir, "rts79_simulink_generators.csv"), "TextType", "string");
loads = readtable(fullfile(baseDir, "rts79_simulink_loads.csv"), "TextType", "string");
events = readtable(eventTablePath, "TextType", "string");
if ~isstring(events.case_id)
    events.case_id = string(events.case_id);
end
if ~isstring(events.event_line)
    events.event_line = string(events.event_line);
end
caseEvents = sortrows(events(events.case_id == string(caseId), :), "event_time");
if height(caseEvents) > 2
    error("Expected zero, one, or two trip events for case_id=%s, got %d", string(caseId), height(caseEvents));
end

systemBaseMva = readSystemBaseMvaLocal(basecasePath);
f0 = 50.0;
genBus = double(generators.bus_id);
ng = height(generators);
M = options.inertia_scale * 2.0 * max(double(generators.H_s), 0.1);
D = options.damping_scale * max(double(generators.D_pu), 10.0);
equilibrium = initialize_swing_equilibrium(branches, generators, loads, systemBaseMva, options);
delta0 = equilibrium.delta0;
omega0 = equilibrium.omega0;
y0 = [delta0; omega0];
Pm = equilibrium.Pm0;

allT = [];
allY = [];
lineRows = {};
offlineLines = strings(0, 1);
if height(caseEvents) == 0
    simulationEndTime = options.simulation_end_time;
else
    simulationEndTime = max(double(caseEvents.simulation_end_time(1)), double(caseEvents.event_time(end)));
end
currentY = y0;
currentTime = 0.0;
currentLoads = loads;
eventRows = {};
eventRowIdx = 0;
cumulativeLoadShedMw = 0.0;
passiveRelayTripCount = 0;
securityRedispatchCount = 0;
maxSecurityViolationLoadingRatio = 0.0;
maxRelayViolationLoadingRatio = 0.0;
eventRound = 0;
lastPmUpdateSummary = struct("load_shed_mw", 0.0, "old_total_load_mw", sum(double(loads.pd_mw)), ...
    "new_total_load_mw", sum(double(loads.pd_mw)), "old_total_pm", sum(double(Pm)), ...
    "new_total_pm", sum(double(Pm)), "pm_update_mode", char(options.pm_update_mode));

while currentTime < simulationEndTime && eventRound < options.max_event_rounds
    futureEvents = caseEvents(double(caseEvents.event_time) > currentTime + options.min_event_separation_s, :);
    if isempty(futureEvents)
        nextScheduledTime = simulationEndTime;
    else
        nextScheduledTime = min(double(futureEvents.event_time));
    end
    nextCheckTime = min(currentTime + options.loading_check_interval_s, simulationEndTime);
    tEnd = min(nextScheduledTime, nextCheckTime);
    if tEnd <= currentTime + options.min_event_separation_s
        tEnd = min(currentTime + options.loading_check_interval_s, simulationEndTime);
    end
    [Bbus, activeBranches] = buildBbusLocal(branches, offlineLines);
    Bred = kronReduceToGeneratorsLocal(Bbus, genBus);
    Bred = normalizeCouplingLocal(Bred, options.coupling_scale);
    if tEnd <= currentTime
        continue;
    end
    ode = @(t, y) swingOdeLocal(t, y, Pm, M, D, Bred, f0);
    opts = odeset("RelTol", 1e-5, "AbsTol", 1e-7, "MaxStep", options.max_step_s);
    [tSeg, ySeg] = ode45(ode, [currentTime tEnd], currentY, opts);
    if ~isempty(allT) && abs(tSeg(1) - allT(end)) < 1e-9
        tSeg = tSeg(2:end);
        ySeg = ySeg(2:end, :);
    end
    allT = [allT; tSeg]; %#ok<AGROW>
    allY = [allY; ySeg]; %#ok<AGROW>
    currentY = ySeg(end, :)';
    segmentRows = lineLoadingRowsLocal(tSeg, ySeg, activeBranches, genBus, systemBaseMva);
    lineRows = [lineRows; segmentRows]; %#ok<AGROW>
    currentTime = tEnd;

    scheduledNow = caseEvents(abs(double(caseEvents.event_time) - currentTime) <= options.min_event_separation_s, :);
    for evIdx = 1:height(scheduledNow)
        lineLabel = string(scheduledNow.event_line(evIdx));
        if ~ismember(lineLabel, offlineLines)
            offlineLines(end + 1, 1) = lineLabel; %#ok<AGROW>
        end
        eventRound = eventRound + 1;
        if evIdx == 1 && sum(double(caseEvents.event_time) <= currentTime + options.min_event_separation_s) == 1
            eventType = "active_trip_first_line";
        else
            eventType = "active_trip_second_line";
        end
        eventRowIdx = eventRowIdx + 1;
        eventRows(eventRowIdx, :) = {string(caseId), currentTime, eventType, strjoin(offlineLines, ";"), lineLabel, NaN, options.relay_beta, NaN, 0.0, cumulativeLoadShedMw, "scheduled_active_trip"}; %#ok<AGROW>
    end

    if ~isempty(segmentRows)
        segmentTable = cell2table(segmentRows, "VariableNames", ["time_s", "line_label", "loading_ratio"]);
        segmentTable.loading_ratio = double(segmentTable.loading_ratio) * options.line_loading_scale;
        [maxLoadingRatio, maxIdx] = max(double(segmentTable.loading_ratio));
        maxLineLabel = string(segmentTable.line_label(maxIdx));
        if maxLoadingRatio > options.relay_beta && options.enable_passive_relay_trips && passiveRelayTripCount < options.max_passive_trip_rounds
            if ~ismember(maxLineLabel, offlineLines)
                offlineLines(end + 1, 1) = maxLineLabel; %#ok<AGROW>
            end
            passiveRelayTripCount = passiveRelayTripCount + 1;
            maxRelayViolationLoadingRatio = max(maxRelayViolationLoadingRatio, maxLoadingRatio);
            eventRound = eventRound + 1;
            eventRowIdx = eventRowIdx + 1;
            eventRows(eventRowIdx, :) = {string(caseId), currentTime + options.relay_trip_delay_s, "passive_relay_trip", strjoin(offlineLines, ";"), maxLineLabel, maxLoadingRatio, options.relay_beta, NaN, 0.0, cumulativeLoadShedMw, "loading_ratio_above_beta"}; %#ok<AGROW>
            continue;
        elseif maxLoadingRatio > options.overload_security_threshold && maxLoadingRatio <= options.relay_beta && options.enable_security_redispatch_approx
            oldLoads = currentLoads;
            oldPm = Pm;
            [currentLoads, loadShedMw, affectedBusId, reason] = apply_security_redispatch_approx(currentLoads, branches, maxLineLabel, maxLoadingRatio, options);
            if options.redispatch_updates_pm
                [Pm, lastPmUpdateSummary] = update_swing_power_after_load_shed(generators, oldLoads, currentLoads, oldPm, currentY(1:ng), Bred, options);
            end
            cumulativeLoadShedMw = cumulativeLoadShedMw + loadShedMw;
            securityRedispatchCount = securityRedispatchCount + 1;
            maxSecurityViolationLoadingRatio = max(maxSecurityViolationLoadingRatio, maxLoadingRatio);
            eventRound = eventRound + 1;
            eventRowIdx = eventRowIdx + 1;
            eventRows(eventRowIdx, :) = {string(caseId), currentTime, "security_redispatch_or_load_shed", strjoin(offlineLines, ";"), maxLineLabel, maxLoadingRatio, options.relay_beta, affectedBusId, loadShedMw, cumulativeLoadShedMw, reason}; %#ok<AGROW>
            continue;
        end
    end
end

if isempty(allT)
    error("No integration segment was produced for case_id=%s", string(caseId));
end

omega = allY(:, ng + 1:end);
frequencyHz = f0 .* omega;
frequencyNadirHz = min(frequencyHz, [], "all");
frequencyZenithHz = max(frequencyHz, [], "all");
meanFrequencyHz = mean(frequencyHz, "all");
finalMeanFrequencyHz = mean(frequencyHz(end, :));
if numel(allT) >= 2
    frequencyDriftHzPerS = (mean(frequencyHz(end, :)) - mean(frequencyHz(1, :))) / max(allT(end) - allT(1), eps);
else
    frequencyDriftHzPerS = 0.0;
end
delta = allY(:, 1:ng);
rawRotorAngleSeparationDeg = max((max(delta, [], 2) - min(delta, [], 2)) * 180 / pi);
coiDelta = centerOfInertiaDeltaLocal(delta, M);
coiRotorAngleSeparationDeg = max(max(abs(coiDelta), [], 2) * 180 / pi);
finalRotorAngleSeparationCoiDeg = max(abs(coiDelta(end, :))) * 180 / pi;
maxRotorAngleSeparationDeg = coiRotorAngleSeparationDeg;
lineLoadingSummary = cell2table(lineRows, "VariableNames", ["time_s", "line_label", "loading_ratio"]);
lineLoadingSummary.loading_ratio = double(lineLoadingSummary.loading_ratio) * options.line_loading_scale;
maxLineLoadingRatio = max(double(lineLoadingSummary.loading_ratio));
if isempty(eventRows)
    eventLog = cell2table(cell(0, numel(eventLogColumnsLocal())), "VariableNames", eventLogColumnsLocal());
else
    eventLog = cell2table(eventRows, "VariableNames", eventLogColumnsLocal());
end
dynamicLoadShedMw = cumulativeLoadShedMw;
[dynamicUnstable, unstableReason] = classifyDynamicStabilityLocal( ...
    frequencyNadirHz, maxRotorAngleSeparationDeg, maxLineLoadingRatio, maxRelayViolationLoadingRatio, passiveRelayTripCount, options);

resultTable = table( ...
    string(caseId), true, true, frequencyNadirHz, frequencyZenithHz, ...
    maxRotorAngleSeparationDeg, rawRotorAngleSeparationDeg, coiRotorAngleSeparationDeg, ...
    finalRotorAngleSeparationCoiDeg, meanFrequencyHz, finalMeanFrequencyHz, frequencyDriftHzPerS, ...
    equilibrium.residual_norm, equilibrium.max_abs_residual, equilibrium.mean_pm, equilibrium.mean_pe, ...
    equilibrium.total_load_mw, equilibrium.total_generation_mw, ...
    lastPmUpdateSummary.load_shed_mw, lastPmUpdateSummary.old_total_load_mw, ...
    lastPmUpdateSummary.new_total_load_mw, lastPmUpdateSummary.old_total_pm, ...
    lastPmUpdateSummary.new_total_pm, string(lastPmUpdateSummary.pm_update_mode), ...
    maxLineLoadingRatio, height(caseEvents), ...
    dynamicUnstable, string(unstableReason), passiveRelayTripCount, securityRedispatchCount, ...
    dynamicLoadShedMw, maxSecurityViolationLoadingRatio, maxRelayViolationLoadingRatio, options.relay_beta, ...
    "simulink_swing_prototype", ...
    'VariableNames', ["case_id", "sim_completed", "converged", "frequency_nadir_hz", ...
    "frequency_zenith_hz", "max_rotor_angle_separation_deg", ...
    "max_rotor_angle_separation_raw_deg", "max_rotor_angle_separation_coi_deg", ...
    "final_rotor_angle_separation_coi_deg", "mean_frequency_hz", "final_mean_frequency_hz", ...
    "frequency_drift_hz_per_s", "initial_pm_pe_residual_norm", "initial_pm_pe_max_abs_residual", ...
    "mean_pm", "mean_pe", "total_load_mw", "total_generation_mw", ...
    "pm_update_load_shed_mw", "pm_update_old_total_load_mw", "pm_update_new_total_load_mw", ...
    "pm_update_old_total_pm", "pm_update_new_total_pm", "pm_update_mode", ...
    "max_line_loading_ratio", ...
    "dynamic_trip_count", "dynamic_unstable", "unstable_reason", "passive_relay_trip_count", ...
    "security_redispatch_count", "dynamic_load_shed_mw", "max_security_violation_loading_ratio", ...
    "max_relay_violation_loading_ratio", "relay_beta", "result_source"]);

trajectorySummary = trajectorySummaryTableLocal(allT, allY, generators, f0, M);
writetable(resultTable, fullfile(outputDir, "dynamic_case_result_" + string(caseId) + ".csv"));
writetable(trajectorySummary, fullfile(outputDir, "dynamic_case_trajectory_summary_" + string(caseId) + ".csv"));
writetable(eventLog, fullfile(outputDir, "dynamic_case_event_log_" + string(caseId) + ".csv"));

if saveTrajectories
    rawDir = fullfile(outputDir, "raw_trajectories");
    if ~exist(rawDir, "dir")
        mkdir(rawDir);
    end
    writetable(trajectorySummary, fullfile(rawDir, "dynamic_case_trajectory_" + string(caseId) + ".csv"));
    writetable(lineLoadingSummary, fullfile(rawDir, "dynamic_case_line_loading_" + string(caseId) + ".csv"));
end
end

function options = defaultSwingOptionsLocal()
options = struct();
options.coupling_scale = 2.0;
options.damping_scale = 1.0;
options.inertia_scale = 1.0;
options.line_loading_scale = 1.0;
options.frequency_unstable_threshold_hz = 49.0;
options.rotor_angle_unstable_threshold_deg = 180.0;
options.line_loading_unstable_threshold = 1.5;
options.simulation_end_time = 20.0;
options.max_step_s = 0.05;
options.relay_beta = 1.2;
options.enable_passive_relay_trips = true;
options.enable_security_redispatch_approx = true;
options.overload_security_threshold = 1.0;
options.relay_trip_delay_s = 0.2;
options.max_passive_trip_rounds = 5;
options.load_shed_step_fraction = 0.05;
options.max_load_shed_fraction_per_bus = 0.5;
options.max_event_rounds = 20;
options.loading_check_interval_s = 0.2;
options.min_event_separation_s = 1e-3;
options.redispatch_updates_pm = true;
options.pm_update_mode = "rebalance_to_current_pe";
options.equilibrium_residual_warning_threshold = 1e-4;
end

function options = mergeSwingOptionsLocal(optionsIn)
options = defaultSwingOptionsLocal();
fields = fieldnames(optionsIn);
for idx = 1:numel(fields)
    options.(fields{idx}) = optionsIn.(fields{idx});
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

function Bscaled = normalizeCouplingLocal(Bred, couplingScale)
scale = max(abs(Bred), [], "all");
if scale < 1e-9
    Bscaled = Bred;
else
    Bscaled = couplingScale * Bred / scale;
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

function trajectorySummary = trajectorySummaryTableLocal(allT, allY, generators, f0, inertiaWeights)
ng = height(generators);
delta = allY(:, 1:ng);
coiDelta = centerOfInertiaDeltaLocal(delta, inertiaWeights);
rows = cell(numel(allT) * ng, 7);
rowIdx = 0;
for tIdx = 1:numel(allT)
    for genIdx = 1:ng
        rowIdx = rowIdx + 1;
        omega = allY(tIdx, ng + genIdx);
        rows(rowIdx, :) = {
            double(allT(tIdx)), ...
            string(generators.gen_id(genIdx)), ...
            double(allY(tIdx, genIdx)), ...
            double(coiDelta(tIdx, genIdx)), ...
            double(abs(coiDelta(tIdx, genIdx)) * 180 / pi), ...
            double(omega), ...
            double(f0 * omega)};
    end
end
trajectorySummary = cell2table(rows, "VariableNames", ["time_s", "gen_id", "raw_delta_rad", "coi_delta_rad", "rotor_angle_separation_coi_deg", "omega_pu", "frequency_hz"]);
end

function [eventLog, passiveRelayTripCount, securityRedispatchCount, dynamicLoadShedMw, maxSecurityViolationLoadingRatio, maxRelayViolationLoadingRatio] = classifyRelayAndSecurityEventsLocal(caseId, caseEvents, lineLoadingSummary, branches, loads, offlineLines, options)
eventRows = {};
rowIdx = 0;
cumulativeLoadShedMw = 0.0;

for idx = 1:height(caseEvents)
    if idx == 1
        eventType = "active_trip_first_line";
    else
        eventType = "active_trip_second_line";
    end
    rowIdx = rowIdx + 1;
    offlineText = strjoin(offlineLines, ";");
    eventRows(rowIdx, :) = {string(caseId), double(caseEvents.event_time(idx)), eventType, offlineText, string(caseEvents.event_line(idx)), NaN, options.relay_beta, NaN, 0.0, cumulativeLoadShedMw, "scheduled_active_trip"}; %#ok<AGROW>
end

if isempty(lineLoadingSummary)
    eventLog = cell2table(eventRows, "VariableNames", eventLogColumnsLocal());
    passiveRelayTripCount = 0;
    securityRedispatchCount = 0;
    dynamicLoadShedMw = 0.0;
    maxSecurityViolationLoadingRatio = 0.0;
    maxRelayViolationLoadingRatio = 0.0;
    return;
end

summary = groupsummary(lineLoadingSummary, "line_label", "max", "loading_ratio");
summary.Properties.VariableNames(end) = "max_loading_ratio";
passiveRelayTripCount = 0;
securityRedispatchCount = 0;
maxSecurityViolationLoadingRatio = 0.0;
maxRelayViolationLoadingRatio = 0.0;
for idx = 1:height(summary)
    lineLabel = string(summary.line_label(idx));
    loadingRatio = double(summary.max_loading_ratio(idx));
    eventTime = min(double(lineLoadingSummary.time_s(lineLoadingSummary.line_label == lineLabel)));
    if loadingRatio > options.relay_beta && options.enable_passive_relay_trips && passiveRelayTripCount < options.max_passive_trip_rounds
        passiveRelayTripCount = passiveRelayTripCount + 1;
        maxRelayViolationLoadingRatio = max(maxRelayViolationLoadingRatio, loadingRatio);
        offlineLines(end + 1, 1) = lineLabel; %#ok<AGROW>
        rowIdx = rowIdx + 1;
        eventRows(rowIdx, :) = {string(caseId), eventTime + options.relay_trip_delay_s, "passive_relay_trip", strjoin(offlineLines, ";"), lineLabel, loadingRatio, options.relay_beta, NaN, 0.0, cumulativeLoadShedMw, "loading_ratio_above_beta"}; %#ok<AGROW>
    elseif loadingRatio > options.overload_security_threshold && loadingRatio <= options.relay_beta && options.enable_security_redispatch_approx
        securityRedispatchCount = securityRedispatchCount + 1;
        maxSecurityViolationLoadingRatio = max(maxSecurityViolationLoadingRatio, loadingRatio);
        [~, loadShedMw, affectedBusId, reason] = apply_security_redispatch_approx(loads, branches, lineLabel, loadingRatio, options);
        cumulativeLoadShedMw = cumulativeLoadShedMw + loadShedMw;
        rowIdx = rowIdx + 1;
        eventRows(rowIdx, :) = {string(caseId), eventTime, "security_redispatch_or_load_shed", strjoin(offlineLines, ";"), lineLabel, loadingRatio, options.relay_beta, affectedBusId, loadShedMw, cumulativeLoadShedMw, reason}; %#ok<AGROW>
    end
end
dynamicLoadShedMw = cumulativeLoadShedMw;
if isempty(eventRows)
    eventLog = cell2table(cell(0, numel(eventLogColumnsLocal())), "VariableNames", eventLogColumnsLocal());
else
    eventLog = cell2table(eventRows, "VariableNames", eventLogColumnsLocal());
end
end

function columns = eventLogColumnsLocal()
columns = ["case_id", "time_s", "event_type", "offlineLines", "line_label", "loading_ratio", "relay_beta", "affected_bus_id", "load_shed_mw", "cumulative_load_shed_mw", "reason"];
end

function [dynamicUnstable, unstableReason] = classifyDynamicStabilityLocal(frequencyNadirHz, maxRotorAngleSeparationDeg, maxLineLoadingRatio, maxRelayViolationLoadingRatio, passiveRelayTripCount, options)
reasons = strings(0, 1);
if frequencyNadirHz < options.frequency_unstable_threshold_hz
    reasons(end + 1, 1) = "frequency_nadir_below_49hz";
end
if maxRotorAngleSeparationDeg > options.rotor_angle_unstable_threshold_deg
    reasons(end + 1, 1) = "rotor_angle_separation_above_180deg";
end
if maxRelayViolationLoadingRatio > options.relay_beta && passiveRelayTripCount == 0
    reasons(end + 1, 1) = "relay_violation_not_eliminated";
end
dynamicUnstable = ~isempty(reasons);
if dynamicUnstable
    unstableReason = strjoin(reasons, ";");
else
    unstableReason = "stable_by_swing_prototype_thresholds";
end
end

function coiDelta = centerOfInertiaDeltaLocal(delta, inertiaWeights)
weights = double(inertiaWeights(:));
if isempty(weights) || sum(weights) <= 1e-9
    weights = ones(size(delta, 2), 1);
end
weights = weights / sum(weights);
coi = delta * weights;
relative = delta - coi;
coiDelta = atan2(sin(relative), cos(relative));
end

