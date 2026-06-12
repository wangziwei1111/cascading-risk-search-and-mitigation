function paths = configure_ieee39_short_filegen_paths(baseDir)
%CONFIGURE_IEEE39_SHORT_FILEGEN_PATHS Use short Simulink generated-code paths.
%
% IEEE39 wrapper model names are long, and Windows builds can fail when
% slprj/code-generation artifacts are written below the repository results
% tree. This helper keeps generated files outside the repo in a short path.

if nargin < 1 || isempty(baseDir)
    systemDrive = string(getenv("SystemDrive"));
    if strlength(systemDrive) == 0
        systemDrive = "C:";
    end
    baseDir = fullfile(char(systemDrive), "ieee39_codegen");
end
if strlength(string(baseDir)) == 0 || strcmp(string(baseDir), filesep)
    baseDir = fullfile(tempdir, "ieee39_codegen");
end

cacheFolder = fullfile(baseDir, "cache");
codeGenFolder = fullfile(baseDir, "codegen");
ensureDir(cacheFolder);
ensureDir(codeGenFolder);

try
    Simulink.fileGenControl( ...
        "set", ...
        "CacheFolder", cacheFolder, ...
        "CodeGenFolder", codeGenFolder, ...
        "createDir", true);
catch ME
    warning("IEEE39:FileGenPath", ...
        "Could not set short Simulink file-generation folders: %s", ME.message);
end

paths = struct();
paths.base_dir = char(baseDir);
paths.cache_folder = char(cacheFolder);
paths.codegen_folder = char(codeGenFolder);
fprintf("IEEE39 Simulink file-generation folders:\n  cache: %s\n  codegen: %s\n", cacheFolder, codeGenFolder);
end

function ensureDir(pathValue)
if ~exist(pathValue, "dir")
    mkdir(pathValue);
end
end
