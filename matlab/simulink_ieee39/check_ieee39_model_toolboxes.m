function summary = check_ieee39_model_toolboxes(outputPath)
%CHECK_IEEE39_MODEL_TOOLBOXES Check toolboxes needed by the IEEE39 model wrapper.

if nargin < 1 || isempty(outputPath)
    outputPath = "../../results/gcn_search/ieee39_graphical_dynamic_model/toolbox_check_summary.json";
end

required = ["Simulink", "Simscape", "Simscape Electrical"];
optional = ["Stateflow", "Simulink Control Design"];
installed = ver;
summary = struct();
summary.required = checkNames(required, installed);
summary.optional = checkNames(optional, installed);
summary.all_required_available = all([summary.required.installed]);
summary.note = "Stateflow is optional unless relay/protection logic is later implemented with charts.";

[folder, ~, ~] = fileparts(outputPath);
if ~exist(folder, "dir")
    mkdir(folder);
end
fid = fopen(outputPath, "w");
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, "%s", jsonencode(summary, PrettyPrint=true));
fprintf("Wrote IEEE39 toolbox check summary: %s\n", outputPath);
end

function rows = checkNames(names, installed)
rows = repmat(struct("name", "", "installed", false, "version", ""), 1, numel(names));
for idx = 1:numel(names)
    match = strcmp({installed.Name}, names(idx));
    rows(idx).name = char(names(idx));
    rows(idx).installed = any(match);
    if any(match)
        item = installed(find(match, 1));
        rows(idx).version = item.Version;
    end
end
end
