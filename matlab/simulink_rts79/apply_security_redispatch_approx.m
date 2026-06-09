function [updatedLoads, loadShedMw, affectedBusId, reason] = apply_security_redispatch_approx(loads, branches, overloadedLineLabel, loadingRatio, options)
%APPLY_SECURITY_REDISPATCH_APPROX Approximate security redispatch/load shedding.
%
% This helper represents the distinction between security constraints and
% relay trips. A line with loading_ratio > 1.0 but <= relay_beta is not
% tripped here. Instead, a small load-shedding approximation is applied near
% the overloaded branch terminals. This is not a full OPF.

updatedLoads = loads;
loadShedMw = 0.0;
affectedBusId = NaN;
reason = "loading_ratio_above_lmax_below_relay_beta";

match = branches(string(branches.line_label) == string(overloadedLineLabel), :);
if isempty(match)
    reason = "overloaded_line_not_found";
    return;
end

terminalBuses = [double(match.from_bus(1)); double(match.to_bus(1))];
candidateLoads = loads(ismember(double(loads.bus_id), terminalBuses), :);
if isempty(candidateLoads) || max(double(candidateLoads.pd_mw)) <= 0
    positiveLoads = loads(double(loads.pd_mw) > 0, :);
    if isempty(positiveLoads)
        reason = "no_positive_load_available";
        return;
    end
    distances = min(abs(double(positiveLoads.bus_id) - terminalBuses'), [], 2);
    [~, pick] = min(distances);
    affectedBusId = double(positiveLoads.bus_id(pick));
else
    [~, pick] = max(double(candidateLoads.pd_mw));
    affectedBusId = double(candidateLoads.bus_id(pick));
end

loadIdx = find(double(updatedLoads.bus_id) == affectedBusId, 1);
if isempty(loadIdx)
    reason = "affected_bus_load_not_found";
    return;
end
currentLoad = double(updatedLoads.pd_mw(loadIdx));
maxShed = options.max_load_shed_fraction_per_bus * currentLoad;
targetReliefFraction = min(max(loadingRatio - options.overload_security_threshold, 0.0), options.load_shed_step_fraction);
loadShedMw = min(maxShed, max(currentLoad * options.load_shed_step_fraction, currentLoad * targetReliefFraction));
updatedLoads.pd_mw(loadIdx) = max(0.0, currentLoad - loadShedMw);
reason = "loading_ratio_above_lmax_below_relay_beta";
end
