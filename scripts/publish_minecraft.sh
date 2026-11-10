#!/usr/bin/env bash
# Publish the Minecraft server, on its own: build the world from web/public/data (and the plugin, if its sources
# changed), upload it with the server's files and settings, start the container. The server notices a new map within
# 30 s, gives online players a one-minute countdown, restarts and loads it (minecraft/server/start.sh).
#
#   bash scripts/publish_minecraft.sh                 build the world (~3 min) and upload everything
#   bash scripts/publish_minecraft.sh --no-build      upload the last build
#   bash scripts/publish_minecraft.sh --config-only   only the plugin's settings and messages (config.yml): they
#                                                     apply within 30 s, without a restart
#
# Settings: ~/.config/voxelpest/minecraft.env (from minecraft/minecraft.env.example). Needs uv, rsync and ssh;
# JDK 25 and Maven to rebuild the plugin.
set -euo pipefail
cd "$(dirname "$0")/.."

BUILD=1 CONFIG_ONLY=0
for a in "$@"; do
    case "$a" in
        --no-build) BUILD=0 ;;
        --config-only) BUILD=0 CONFIG_ONLY=1 ;;
        *) echo "unknown option $a"; exit 2 ;;
    esac
done

CONF=${VOXELPEST_MINECRAFT_ENV:-${XDG_CONFIG_HOME:-$HOME/.config}/voxelpest/minecraft.env}
[ -f "$CONF" ] || [ -n "${VOXELPEST_MINECRAFT_ENV:-}" ] || CONF=minecraft/minecraft.env   # or next to the example (not in git)
[ -f "$CONF" ] || { echo "No settings yet: copy minecraft/minecraft.env.example to ~/.config/voxelpest/minecraft.env (or minecraft/minecraft.env) and fill it in."; exit 1; }
set -a; . "$CONF"; set +a
: "${MC_HOST:?set MC_HOST in $CONF}"
DIR=${MC_DIR:-/srv/voxelpest-minecraft}
HOST=$MC_HOST
step() { printf '\n== %s\n' "$*"; }

if [ "$CONFIG_ONLY" = 1 ]; then
    rsync -a minecraft/plugin/src/main/resources/config.yml "$HOST:$DIR/map/plugins/config.yml"
    echo "config.yml uploaded: the server reloads it within 30 s"
    exit 0
fi

if [ "$BUILD" = 1 ]; then
    [ -f web/public/data/meta.json ] || { echo "no map data in web/public/data: ./bv unpack, or ./bv map"; exit 1; }
    step "Minecraft world"
    uv run python scripts/minecraft.py
    JAR=minecraft/voxelpest.jar
    if command -v mvn >/dev/null && [ -n "$(find minecraft/plugin/src minecraft/plugin/pom.xml -newer "$JAR" -type f 2>/dev/null | head -1)" ]; then
        step "plugin"
        (cd minecraft/plugin && mvn -q -B package) && cp minecraft/plugin/target/voxelpest.jar "$JAR"
    fi
fi
[ -f build/minecraft/map.yml ] || { echo "no build/minecraft yet: run without --no-build"; exit 1; }

step "uploading to $HOST:$DIR"
ssh "$HOST" "mkdir -p '$DIR/server' '$DIR/map/plugins' '$DIR/data'"
rsync -a minecraft/docker-compose.yml "$HOST:$DIR/"
rsync -a --delete minecraft/server/ "$HOST:$DIR/server/"
ENVF=$(mktemp)
trap 'rm -f "$ENVF"' EXIT
for k in EULA MC_VERSION MEMORY MAX_PLAYERS VIEW_DISTANCE SIMULATION_DISTANCE BEDROCK VIA MOTD ONLINE_MODE WHITELIST \
         MC_ADDRESS MAP_URL BAR_URL STATUS_PORT STATUS_BIND JAVA_OPTS; do
    if [ -n "${!k:-}" ]; then printf "%s='%s'\n" "$k" "${!k}" >> "$ENVF"; fi
done
rsync "$ENVF" "$HOST:$DIR/.env"
rsync -a --delete --delay-updates build/minecraft/world/ "$HOST:$DIR/map/world/"
rsync -a minecraft/voxelpest.jar "$HOST:$DIR/map/plugins/"
rsync -a minecraft/plugin/src/main/resources/config.yml "$HOST:$DIR/map/plugins/config.yml"  # read live
rsync -a build/minecraft/landmarks.yml "$HOST:$DIR/map/"
rsync -a build/minecraft/map.yml "$HOST:$DIR/map/"   # last: the server restarts when this one changes
echo "map: $(grep '^built' build/minecraft/map.yml)"

if [ "${RUN_COMPOSE:-true}" = true ]; then
    step "docker compose up"
    ssh "$HOST" "cd '$DIR' && docker compose pull --quiet && docker compose up -d"
fi
step "done: ${MC_ADDRESS:-$HOST} picks the new map up within a minute or two (docker logs -f voxelpest-minecraft)"
