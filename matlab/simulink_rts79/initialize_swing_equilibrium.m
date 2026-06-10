function equilibrium = initialize_swing_equilibrium(branches, generators, loads, systemBaseMva, options)
%INITIALIZE_SWING_EQUILIBRIUM Build a balanced initial swing-equation state.
%
% This helper is a simplified initialization routine for the RTS-79 swing
% prototype. It is not AGC, not OPF, and not a detailed transient-stability
% initialization. The goal is to remove artificial center-of-inertia power
% mismatch at the no-trip initial point and expose residual diagnostics.

if nargin < 5
    options = struct();
end

genBus = double(generators.bus_id);
delta0 = initialGeneratorAnglesInitLocal(branches, generators, loads, systemBaseMva);
omega0 = ones(height(generators), 1);
[Bbus0, ~] = buildBbusInitLocal(branches, strings(0, 1));
Bred0 = kronReduceToGeneratorsInitLocal(Bbus0, genBus);
couplingScale = fieldOrDefaultInitLocal(options, "coupling_scale", 2.0);
Bred0 = normalizeCouplingInitLocal(Bred0, couplingScale);
Pe0 = electricalPowerInitLocal(delta0, Bred0);

% Start from Pe0 and remove the COI active-power mismatch. This keeps the
% no-trip case near equilibrium instead of injecting artificial acceleration.
Pm0 = Pe0;
residual = Pm0 - Pe0;
residual = residual - mean(residual);
Pm0 = Pe0 + residual;

equilibrium = struct();
equilibrium.delta0 = delta0;
equilibrium.omega0 = omega0;
equilibrium.Pm0 = Pm0;
equilibrium.Pe0 = Pe0;
equilibrium.Bred0 = Bred0;
equilibrium.equilibriumResidual = Pm0 - Pe0;
equilibrium.residual_norm = norm(equilibrium.equilibriumResidual);
equilibrium.max_abs_residual = max(abs(equilibrium.equilibriumResidual));
equilibrium.mean_pm = mean(Pm0);
equilibrium.mean_pe = mean(Pe0);
equilibrium.total_load_mw = sum(double(loads.pd_mw));
equilibrium.total_generation_mw = sum(double(generators.pg_mw));
if equilibrium.max_abs_residual > fieldOrDefaultInitLocal(options, "equilibrium_residual_warning_threshold", 1e-4)
    warning("initialize_swing_equilibrium:LargeResidual", ...
        "Initial Pm/Pe residual max abs is %.6g pu.", equilibrium.max_abs_residual);
end
end

function value = fieldOrDefaultInitLocal(options, name, defaultValue)
if isstruct(options) && isfield(options, name)
    value = options.(name);
else
    value = defaultValue;
end
end

function [Bbus, activeBranches] = buildBbusInitLocal(branches, offlineLines)
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

function Bred = kronReduceToGeneratorsInitLocal(Bbus, genBus)
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

function Bscaled = normalizeCouplingInitLocal(Bred, couplingScale)
scale = max(abs(Bred), [], "all");
if scale < 1e-9
    Bscaled = Bred;
else
    Bscaled = couplingScale * Bred / scale;
end
end

function delta0 = initialGeneratorAnglesInitLocal(branches, generators, loads, systemBaseMva)
[Bbus, ~] = buildBbusInitLocal(branches, strings(0, 1));
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

function Pe = electricalPowerInitLocal(delta, Bred)
ng = numel(delta);
Pe = zeros(ng, 1);
for i = 1:ng
    for j = 1:ng
        Pe(i) = Pe(i) + Bred(i, j) * sin(delta(i) - delta(j));
    end
end
end
