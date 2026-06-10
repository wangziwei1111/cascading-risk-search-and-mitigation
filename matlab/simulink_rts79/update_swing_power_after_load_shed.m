function [updatedPm, pmUpdateSummary] = update_swing_power_after_load_shed(generators, oldLoads, newLoads, oldPm, delta, Bred, options)
%UPDATE_SWING_POWER_AFTER_LOAD_SHED Approximate Pm update after load shedding.
%
% This is a simplified prototype rule, not AGC and not OPF. It only keeps
% the swing-equation prototype from injecting a hidden system-wide power
% mismatch after approximate security load shedding.

if nargin < 7 || isempty(options)
    options = struct();
end
if ~isfield(options, "pm_update_mode")
    options.pm_update_mode = "rebalance_to_current_pe";
end

oldTotalLoad = sum(double(oldLoads.pd_mw));
newTotalLoad = sum(double(newLoads.pd_mw));
oldTotalPm = sum(double(oldPm));
loadShedMw = max(oldTotalLoad - newTotalLoad, 0.0);
mode = string(options.pm_update_mode);

switch mode
    case "proportional_total_load"
        if oldTotalLoad <= 1e-9
            updatedPm = oldPm;
        else
            updatedPm = oldPm * max(newTotalLoad / oldTotalLoad, 0.0);
        end
    case "subtract_load_shed_by_gen_weight"
        pg = max(double(generators.pg_mw), 0.0);
        if sum(pg) <= 1e-9
            weights = ones(numel(oldPm), 1) / numel(oldPm);
        else
            weights = pg(:) / sum(pg);
        end
        updatedPm = oldPm - weights * (loadShedMw / 100.0);
        updatedPm = updatedPm - mean(updatedPm - oldPm);
    case "keep_total_mechanical_power"
        updatedPm = oldPm;
    otherwise
        if nargin >= 6 && ~isempty(delta) && ~isempty(Bred)
            updatedPm = electricalPowerUpdateLocal(delta, Bred);
        else
            updatedPm = oldPm;
        end
end

if ~strcmp(mode, "keep_total_mechanical_power")
    mismatch = mean(updatedPm);
    updatedPm = updatedPm - mismatch;
end

pmUpdateSummary = struct();
pmUpdateSummary.load_shed_mw = loadShedMw;
pmUpdateSummary.old_total_load_mw = oldTotalLoad;
pmUpdateSummary.new_total_load_mw = newTotalLoad;
pmUpdateSummary.old_total_pm = oldTotalPm;
pmUpdateSummary.new_total_pm = sum(double(updatedPm));
pmUpdateSummary.pm_update_mode = char(mode);
end

function Pe = electricalPowerUpdateLocal(delta, Bred)
ng = numel(delta);
Pe = zeros(ng, 1);
for i = 1:ng
    for j = 1:ng
        Pe(i) = Pe(i) + Bred(i, j) * sin(delta(i) - delta(j));
    end
end
end
