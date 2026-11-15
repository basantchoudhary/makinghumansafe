"""Print a valid Cloudflare access token for publishing, renewing the wrangler login when it has expired.

Order: CLOUDFLARE_API_TOKEN in .env (a permanent API token) if set; otherwise the wrangler login saved on this
machine (from `npx wrangler login`), renewed with its refresh token through Cloudflare's OAuth endpoint, the same
way wrangler renews it. Prints nothing and exits 1 if no usable login exists.
"""
import datetime as dt, json, os, pathlib, re, sys, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLIENT_ID = "54d11594-84e4-41aa-b438-e81b8fa78ee7"  # wrangler's public OAuth client id
CONFIGS = [pathlib.Path.home() / ".wrangler/config/default.toml", pathlib.Path.home() / "Library/Preferences/.wrangler/config/default.toml"]


def from_env():
    p = ROOT / ".env"
    if p.exists():
        m = re.search(r"^CLOUDFLARE_API_TOKEN=(\S+)", p.read_text(), re.M)
        if m:
            return m.group(1)
    return None


def from_wrangler():
    cfgs = [c for c in CONFIGS if c.exists()]
    if not cfgs:
        return None
    cfg = max(cfgs, key=lambda c: c.stat().st_mtime)
    text = cfg.read_text()
    get = lambda k: (re.search(rf'^{k} = "([^"]*)"', text, re.M) or [None, None])[1]
    exp = get("expiration_time")
    if exp and dt.datetime.fromisoformat(exp.replace("Z", "+00:00")) > dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=5):
        return get("oauth_token")
    body = urllib.parse.urlencode({"grant_type": "refresh_token", "refresh_token": get("refresh_token"), "client_id": CLIENT_ID}).encode()
    r = json.load(urllib.request.urlopen(urllib.request.Request("https://dash.cloudflare.com/oauth2/token", data=body,
                                                                headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "wrangler/3.114.0"}), timeout=30))
    new_exp = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=r["expires_in"])).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    for k, v in (("oauth_token", r["access_token"]), ("refresh_token", r.get("refresh_token", get("refresh_token"))), ("expiration_time", new_exp)):
        text = re.sub(rf'^{k} = "[^"]*"', f'{k} = "{v}"', text, flags=re.M)
    cfg.write_text(text)
    return r["access_token"]


if __name__ == "__main__":
    tok = from_env() or from_wrangler()
    if not tok:
        sys.exit(1)
    print(tok)
