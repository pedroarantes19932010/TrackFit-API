"""Bounded AI coding proposal. Requires OPENAI_API_KEY. No external packages."""
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MAX_RESPONSE_BYTES = 40000
MAX_FILE_CHARS = 12000
MAX_FILES = 2
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
ALLOWED_MODEL = re.fullmatch(r"[A-Za-z0-9._-]{1,80}", MODEL)
if not ALLOWED_MODEL:
    raise SystemExit("Invalid model name")

TASK = (
    "Improve tests for existing workout domain behavior, or implement a small, "
    "self-contained validation improvement in trackfit_api/workouts.py with matching tests. "
    "Do not add dependencies, APIs, credentials, persistence, external network calls, "
    "health prescriptions, or personal data. Prefer a meaningful small improvement."
)
paths = ["trackfit_api/workouts.py", "tests/test_workouts.py"]
context = "\n\n".join(f"FILE: {p}\n{(ROOT / p).read_text(encoding='utf-8')[:16000]}" for p in paths)
instruction = (
    "You are a careful Python developer. Return ONLY valid JSON with shape "
    '{"files":[{"path":"tests/test_workouts.py","content":"complete file contents"}]}. '
    "Allowed paths: trackfit_api/workouts.py, tests/test_workouts.py. "
    "Return 1 or 2 complete replacement files. Keep existing tests and behaviors. "
    "No shell, workflow, secrets, network, imports of subprocess/socket/requests/urllib, "
    "or dynamic execution. Never use markdown fences. Limit each file to 12000 chars. "
    "Task: " + TASK + "\n\nExisting source:\n" + context
)
payload = {
    "model": MODEL,
    "input": instruction,
    "max_output_tokens": 4500,
    "store": False,
}
request = urllib.request.Request(
    "https://api.openai.com/v1/responses",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
             "Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(request, timeout=90) as response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
except urllib.error.HTTPError as exc:
    raise SystemExit(f"OpenAI API returned HTTP {exc.code}") from None
if len(raw) > MAX_RESPONSE_BYTES:
    raise SystemExit("Response too large")
data = json.loads(raw)
if data.get("status") != "completed":
    raise SystemExit("AI response incomplete")
parts = []
for item in data.get("output", []):
    if item.get("type") == "message":
        for piece in item.get("content", []):
            if piece.get("type") == "output_text":
                parts.append(piece.get("text", ""))
result = json.loads("".join(parts))
changes = result.get("files")
if not isinstance(changes, list) or not 1 <= len(changes) <= MAX_FILES:
    raise SystemExit("Invalid number of files")
seen = set()
for change in changes:
    if not isinstance(change, dict) or set(change) != {"path", "content"}:
        raise SystemExit("Invalid file entry")
    path, content = change["path"], change["content"]
    if path not in paths or path in seen or not isinstance(content, str):
        raise SystemExit("Path not allowed")
    if not 0 < len(content) <= MAX_FILE_CHARS:
        raise SystemExit("File exceeds size limits")
    # This is a limited guard, not a sandbox or security proof.
    if re.search(r"\b(?:subprocess|socket|requests|urllib|eval|exec|compile|__import__)\b", content):
        raise SystemExit("Forbidden operation in generated source")
    compile(content, path, "exec")
    seen.add(path)
# Only write after validating the entire response.
for change in changes:
    (ROOT / change["path"]).write_text(change["content"], encoding="utf-8")
print("Generated bounded proposal; run tests before creating PR.")
