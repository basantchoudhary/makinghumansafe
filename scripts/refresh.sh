#!/bin/zsh
# Refresh news feeds, alerts and incidents for every place, then rebuild the site. Run by launchd 4x a day
# (feeds only show their latest ~20 items, so history only builds up if we read them often).
# Install: sed "s|__REPO__|$PWD|g" scripts/in.dataagents.safety-intelligence.plist > ~/Library/LaunchAgents/in.dataagents.safety-intelligence.plist && launchctl load ~/Library/LaunchAgents/in.dataagents.safety-intelligence.plist
# Remove:  launchctl unload ~/Library/LaunchAgents/in.dataagents.safety-intelligence.plist && rm that file
cd "$(dirname "$0")/.." || exit 1
echo "=== $(date '+%F %T')"
for p in $(python3 -c "import tomllib;print(' '.join(tomllib.load(open('places.toml','rb'))))"); do
  python3 -m safety.fetch "$p" feeds alerts incois notices
  python3 -m safety.extract "$p" 30 | tail -1
  python3 -m safety.verify "$p"
done
python3 -m safety.site
# Publish: upload site/ to Cloudflare Pages (project makinghumansafe).
# Needs CLOUDFLARE_API_TOKEN (Pages: Edit) and CLOUDFLARE_ACCOUNT_ID in .env (never committed).
set -a; [ -f .env ] && . ./.env; set +a
if [ -n "$CLOUDFLARE_API_TOKEN" ]; then
  npx -y wrangler@3.114.0 pages deploy site --project-name makinghumansafe --branch main --commit-dirty=true 2>&1 | grep -E "Deployment complete|ERROR" | tail -1
else
  echo "skip publish: no CLOUDFLARE_API_TOKEN in .env"
fi
