"""Small JSON client for an open-weight model on Groq (free tier). The model only proposes; callers verify."""
import json, os, pathlib, re, time, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = os.environ.get("SAFETY_MODEL", "qwen/qwen3.8-27b")


def _key():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))
    return os.environ.get("GROQ_API_KEY")


def json_call(prompt, model=MODEL, temperature=0):
    """Return the JSON object the model replies with ({} on failure)."""
    key = _key()
    if not key:
        return {}
    body = json.dumps({"model": model, "temperature": temperature, "response_format": {"type": "json_object"},
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    for attempt in range(5):
        req = urllib.request.Request(URL, data=body, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                                                              "User-Agent": "making-human-safe/0.1"})
        try:
            reply = json.loads(urllib.request.urlopen(req, timeout=120).read())["choices"][0]["message"]["content"]
            reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.S)
            m = re.search(r"\{.*\}", reply, flags=re.S)
            return json.loads(m.group(0)) if m else {}
        except urllib.error.HTTPError as ex:
            if ex.code in (429, 500, 502, 503):
                time.sleep(15 * (attempt + 1))
                continue
            raise
        except (json.JSONDecodeError, KeyError):
            return {}
    return {}
