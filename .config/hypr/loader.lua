local configHome = os.getenv("XDG_CONFIG_HOME")
if not configHome or configHome == "" then
    configHome = os.getenv("HOME") .. "/.config"
end

local function loadConfig(path)
    local file = io.open(path, "r")
    if not file then return false end
    file:close()
    dofile(path)
    return true
end

if loadConfig(configHome .. "/hypr/repo.lua") then return end

local dataDirs = os.getenv("XDG_DATA_DIRS")
if not dataDirs or dataDirs == "" then dataDirs = "/usr/local/share:/usr/share" end
for directory in dataDirs:gmatch("[^:]+") do
    if loadConfig(directory .. "/hypr/hyprland.lua") then return end
end

hl.monitor({ output = "", mode = "preferred", position = "auto", scale = "auto" })
hl.bind("SUPER + return", hl.dsp.exec_cmd("kitty"))
hl.bind("SUPER + Q", hl.dsp.window.close())
hl.bind("SUPER + R", hl.dsp.exec_cmd("hyprlauncher"))
hl.bind("SUPER + SHIFT + CTRL + M", hl.dsp.exit())
