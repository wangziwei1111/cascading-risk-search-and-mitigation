function updatedPm = update_swing_power_after_load_shed(~, oldLoads, newLoads, oldPm)
%UPDATE_SWING_POWER_AFTER_LOAD_SHED Approximate Pm update after load shedding.
%
% This is a simplified prototype rule, not AGC and not OPF. It scales the
% generator mechanical-power reference according to the total load change so
% subsequent swing-equation segments feel the security action.

oldTotalLoad = sum(double(oldLoads.pd_mw));
newTotalLoad = sum(double(newLoads.pd_mw));
if oldTotalLoad <= 1e-9
    updatedPm = oldPm;
    return;
end
scale = max(newTotalLoad / oldTotalLoad, 0.0);
updatedPm = oldPm * scale;
end
