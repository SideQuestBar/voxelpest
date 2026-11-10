#!/usr/bin/env bash
# Publish the web viewer to Cloudflare Pages: build web/dist from web/public/data and deploy it with wrangler. Pages
# stores files by their hash, so only what changed is uploaded, and the new deployment goes live as a whole.
#
#   bash scripts/publish_web.sh             build and deploy
#   bash scripts/publish_web.sh --no-build  deploy the last build
#
# Settings: ~/.config/voxelpest/web.env (from web/deploy/web.env.example). Needs Bun and Node (bunx fetches
# wrangler). The first run logs in to Cloudflare in the browser and creates the Pages project.
set -euo pipefail
cd "$(dirname "$0")/.."

BUILD=1
for a in "$@"; do
    case "$a" in
        --no-build) BUILD=0 ;;
        *) echo "unknown option $a"; exit 2 ;;
    esac
done

CONF=${VOXELPEST_WEB_ENV:-${XDG_CONFIG_HOME:-$HOME/.config}/voxelpest/web.env}
[ -f "$CONF" ] || [ -n "${VOXELPEST_WEB_ENV:-}" ] || CONF=web/deploy/web.env   # or next to the example (not in git)
[ -f "$CONF" ] || { echo "No settings yet: copy web/deploy/web.env.example to ~/.config/voxelpest/web.env (or web/deploy/web.env) and fill it in."; exit 1; }
set -a; . "$CONF"; set +a
PROJECT=${CF_PROJECT:-voxelpest}
BRANCH=${CF_BRANCH:-main}
step() { printf '\n== %s\n' "$*"; }
wrangler() { bunx "wrangler@${WRANGLER_VERSION:-4}" "$@"; }

[ -f web/public/data/meta.json ] || { echo "no map data in web/public/data: ./bv unpack, or ./bv map"; exit 1; }
if [ "$BUILD" = 1 ]; then
    step "web viewer (Minecraft card: ${MINECRAFT:-false})"
    (cd web && bun install --frozen-lockfile --silent \
        && VITE_MINECRAFT="${MINECRAFT:-false}" VITE_MC_ADDRESS="${MC_ADDRESS:-}" VITE_MC_STATUS="${MC_STATUS_URL:-}" \
           VITE_BAR_URL="${BAR_URL:-}" VITE_UMAMI_URL="${UMAMI_URL:-}" VITE_UMAMI_ID="${UMAMI_ID:-}" bun run build)
fi
[ -f web/dist/index.html ] || { echo "no web/dist yet: run without --no-build"; exit 1; }

# the shipped map parts are for git, not the site (vite.config.js leaves them out; a build from before that didn't)
rm -f web/dist/voxelpest-data.tar.gz*
# Pages' limits: 20 000 files per deployment, 25 MiB per file
FILES=$(find web/dist -type f | wc -l)
[ "$FILES" -le 20000 ] || { echo "web/dist has $FILES files: Cloudflare Pages takes at most 20 000"; exit 1; }
BIG=$(find web/dist -type f -size +26214400c)
[ -z "$BIG" ] || { printf 'over Cloudflare Pages'"'"' 25 MiB per file:\n%s\n' "$BIG"; exit 1; }

if [ -z "${CLOUDFLARE_API_TOKEN:-}" ] && ! wrangler whoami --json >/dev/null 2>&1; then
    step "Cloudflare login"
    wrangler login
fi

# Create the project as a Pages project first: a deploy to a missing project would ask (or go to Workers instead).
step "Cloudflare Pages project $PROJECT"
PROJECTS=$(wrangler pages project list --json)
if grep -Fq "\"$PROJECT\"" <<<"$PROJECTS"; then
    echo "exists"
else
    wrangler pages project create "$PROJECT" --production-branch "$BRANCH"
fi

step "deploying web/dist ($FILES files) to $PROJECT, branch $BRANCH"
wrangler pages deploy web/dist --project-name "$PROJECT" --branch "$BRANCH" --commit-dirty=true
step "done: https://$PROJECT.pages.dev"

# WEB_DOMAIN only names the domain: it serves the site once it is attached to the project in the dashboard. Until
# then a DNS record of its own answers there (an older page from the cache, then 404s for its scripts).
if [ -n "${WEB_DOMAIN:-}" ]; then
    DOMAINS=$(node -e 'const p = JSON.parse(require("fs").readFileSync(0, "utf8")).find(p => p["Project Name"] === process.argv[1]);
                      console.log(p ? p["Project Domains"] : "")' "$PROJECT" <<<"$PROJECTS")
    if grep -Fqx "$WEB_DOMAIN" <<<"${DOMAINS//, /$'\n'}"; then
        echo "  and https://$WEB_DOMAIN"
    else
        printf '  %s is not attached to the Pages project %s yet, so it does not show this site. In the dashboard:\n' "$WEB_DOMAIN" "$PROJECT"
        printf '  Workers & Pages > %s > Custom domains > Set up a custom domain > %s. Delete any DNS record of\n' "$PROJECT" "$WEB_DOMAIN"
        printf '  its own first (Pages makes the CNAME), then purge it from the cache (Caching > Configuration > Custom Purge).\n'
    fi
fi
