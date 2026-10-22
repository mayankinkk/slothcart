import base64
import json
import os
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request

DEFAULT_MODEL = os.environ.get("SOTHCART_MODEL", "gemma3:4b")
DEFAULT_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")

INVENTORY_PROMPT = """\
You are looking at a photo of the inside of a fridge, pantry, or kitchen shelf.

Scan slowly, shelf by shelf, including door compartments. List every distinct food,
drink, or ingredient item you can actually see. Be thorough but do not invent items.

Estimate quantities in human terms ("6", "half a loaf", "about 1 litre").
Assign each item exactly one category from this list (lowercase):
produce, dairy, meat & seafood, bakery, frozen, pantry, drinks, condiments, snacks, leftovers, other

Respond with ONLY a JSON object, no markdown fences, no prose:
{"items": [{"name": "item name", "quantity": "estimated amount", "category": "one of the categories above"}]}
"""


class OllamaError(RuntimeError):
    pass


def _sniff(head):
    if head.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None


def _convert_to_jpeg(path):
    sips = shutil.which("sips")
    if not sips:
        raise OllamaError(
            f"{path} is not a JPEG/PNG/GIF/WebP image and no converter is available. "
            "Convert it to JPEG first (Ollama only accepts those formats)."
        )
    fd, tmp = tempfile.mkstemp(suffix=".jpg")
    os.close(fd)
    try:
        proc = subprocess.run(
            [sips, "-s", "format", "jpeg", path, "--out", tmp],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0 or not os.path.getsize(tmp):
            detail = (proc.stderr or proc.stdout or "").strip()
            raise OllamaError(f"Could not convert {path} to JPEG: {detail}")
        with open(tmp, "rb") as f:
            return f.read()
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def encode_image(path):
    with open(path, "rb") as f:
        head = f.read(16)
        if _sniff(head):
            f.seek(0)
            data = f.read()
        else:
            data = _convert_to_jpeg(path)
    return base64.b64encode(data).decode("ascii")


def ask(model, prompt, image_b64, host=DEFAULT_HOST):
    payload = {
        "model": model,
        "stream": False,
        "options": {"temperature": 0.1},
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [image_b64],
            }
        ],
    }
    req = urllib.request.Request(
        f"{host}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise OllamaError(
            f"Cannot reach Ollama at {host} ({e}). Is it running? Try: ollama serve"
        ) from e
    if "error" in data:
        err = data["error"]
        if "not found" in err.lower():
            raise OllamaError(f"{err}. Try: ollama pull {model}")
        raise OllamaError(err)
    return data["message"]["content"]


def extract_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"No JSON object found in model response: {text[:200]!r}")
    return json.loads(text[start : end + 1])


def inventory(image_path, model=DEFAULT_MODEL, host=DEFAULT_HOST):
    raw = ask(model, INVENTORY_PROMPT, encode_image(image_path), host=host)
    data = extract_json(raw)
    items = data.get("items")
    if not isinstance(items, list):
        raise ValueError(f"Model returned unexpected JSON: {data!r}")
    cleaned = []
    for it in items:
        if not isinstance(it, dict):
            continue
        name = str(it.get("name", "")).strip()
        if not name:
            continue
        cleaned.append(
            {
                "name": name,
                "quantity": str(it.get("quantity", "")).strip(),
                "category": (str(it.get("category", "other")) or "other").strip().lower(),
            }
        )
    return cleaned
