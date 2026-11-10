#!/bin/sh
# The Minecraft server's entrypoint, in the itzg/minecraft-server image (docker-compose.yml). The image downloads Paper
# and the plugins, writes server.properties from the environment and runs the server. This script prepares what is
# particular to this map, as root, then hands over to the image's /start:
#   1. when the uploaded map (/map/map.yml) differs from the one the server last ran, the overworld is replaced by it
#   2. the voxelpest plugin and its files, Geyser's first settings (Floodgate login), no End
#   3. the plugin list for the image: Geyser (Modrinth) and Floodgate (GeyserMC) for Bedrock, ViaVersion and
#      ViaBackwards (Modrinth) for other Java versions; the image fetches newer builds at every start
# The voxelpest plugin watches /map/map.yml and stops the server when a new map arrives (Docker restarts it), and
# reloads its settings when /map/plugins/config.yml changes.
set -eu

OW=world/dimensions/minecraft/overworld
FLOODGATE=https://download.geysermc.org/v2/projects/floodgate/versions/latest/builds/latest/downloads/spigot

if [ "${EULA:-false}" != "true" ]; then
    echo "start: set EULA=true in .env (minecraft.env) to agree to the Minecraft EULA, https://aka.ms/MinecraftEULA"
    sleep 30
    exit 1
fi

cd /data
mkdir -p plugins/voxelpest "$OW"

# The server's first setup fetched its own jars under fixed names (paper.jar, ViaVersion.jar, ...). Next to the
# image's versioned downloads they would load twice.
if [ -f paper.jar ]; then
    echo "start: removing the jars of the earlier setup"
    rm -f paper.jar plugins/Geyser-Spigot.jar plugins/floodgate-spigot.jar plugins/ViaVersion.jar plugins/ViaBackwards.jar
fi
# The plugin was called BudapestVoxel before: its jar would load next to voxelpest.jar, with the same commands.
rm -rf plugins/BudapestVoxel plugins/BudapestVoxel.jar

# 1. the map ---------------------------------------------------------------------------------------------------------
if [ -f /map/map.yml ] && [ -d "/map/$OW/region" ]; then
    if [ ! -d "$OW/region" ] || ! cmp -s /map/map.yml plugins/voxelpest/map.yml; then
        echo "start: new map ($(grep '^built' /map/map.yml)), replacing the overworld"
        rm -rf "$OW/region.new"
        cp -r "/map/$OW/region" "$OW/region.new"
        rm -rf "$OW/region" "$OW/entities" "$OW/poi"
        mv "$OW/region.new" "$OW/region"
        cp /map/map.yml plugins/voxelpest/map.yml
    fi
    cp /map/landmarks.yml plugins/voxelpest/landmarks.yml
else
    echo "start: no map in /map yet (scripts/publish_minecraft.sh uploads it)"
fi
[ -f /map/plugins/voxelpest.jar ] && cp /map/plugins/voxelpest.jar plugins/voxelpest.jar
export VOXELPEST_MAP_SOURCE=/map/map.yml VOXELPEST_CONFIG=/map/plugins/config.yml
export VOXELPEST_MAP_URL="${MAP_URL:-}" VOXELPEST_BAR_URL="${BAR_URL:-}" VOXELPEST_ADDRESS="${MC_ADDRESS:-}"

# 2. settings the image doesn't cover --------------------------------------------------------------------------------
if [ -f bukkit.yml ]; then
    sed -i 's/^\(\s*allow-end:\).*/\1 false/' bukkit.yml
else
    printf 'settings:\n  allow-end: false\n' > bukkit.yml
fi
if [ "${BEDROCK:-true}" = "true" ]; then
    mkdir -p plugins/Geyser-Spigot
    [ -f plugins/Geyser-Spigot/config.yml ] || cp /server/geyser-config.yml plugins/Geyser-Spigot/config.yml
    sed -i 's/^\(\s*auth-type:\).*/\1 floodgate/' plugins/Geyser-Spigot/config.yml
fi
# what was written here as root goes to the server's user (the image changes owners only when /data itself isn't its)
[ "$(id -u)" = 0 ] && chown -R "${UID:-1000}:${GID:-1000}" plugins "$OW" bukkit.yml

# 3. the plugins the image fetches -----------------------------------------------------------------------------------
# geyser: its newest build (Modrinth only has betas); via*: the newest release for this Minecraft version, else a beta
MODRINTH_PROJECTS=""
[ "${BEDROCK:-true}" = "true" ] && MODRINTH_PROJECTS="geyser:beta"
[ "${VIA:-true}" = "true" ] && MODRINTH_PROJECTS="${MODRINTH_PROJECTS:+$MODRINTH_PROJECTS,}viaversion:beta+,viabackwards:beta+"
export MODRINTH_PROJECTS   # a project dropped from the list is removed by the image
if [ "${BEDROCK:-true}" = "true" ]; then
    export PLUGINS="$FLOODGATE"   # Floodgate's Paper build isn't on Modrinth
else
    rm -f plugins/floodgate-spigot.jar
fi

export MOTD="${MOTD:-§6§lBudapest§r §7in blocks, 1 block = 1 m — by §fSideQuest Bar§r\n§7Fly the city · /lm for landmarks · Java & Bedrock}"
exec /start "$@"
