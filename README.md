# slothcart

**Point it at a fridge photo. Get a grocery list. Never stand at an open fridge again.**

`slothcart` is a fully local CLI that turns a photo of your fridge, pantry, or kitchen
shelf into an aisle-grouped grocery list — while staying "Slow and Steady" about it:
you take one lazy photo, it does the rest. All inference runs on your own machine via
[Ollama](https://ollama.com) and an open-weight vision model. No internet, no API keys,
no data leaving your kitchen.

![slothcart demo](https://raw.githubusercontent.com/mayankinkk/slothcart/main/docs/demo.gif)

```
$ slothcart examples/fridge.jpg --pantry examples/pantry.txt --save-list list.md
Reading fridge.jpg with gemma3:4b (local, offline)...

GROCERY LIST
========================================

PRODUCE
-------
  [ ] grapes  (about 1/2 kg)
  [ ] green apples  (about 3)
  [ ] oranges  (about 6)

DAIRY
-----
  [ ] milk cartons  (6)

...
ALREADY AT HOME (skipped)
------------------------
  loaf of bread
  cheese
  tomatoes
  yogurt
```

## Why a sloth built this

Standing in front of an open fridge, door ajar, trying to remember what you already
have before you forget what you actually need — that's the dread task this kills.
One photo. The model does the staring, remembering, and list-making. You get the list.

## How it works

```
fridge photo ──> gemma3:4b (Ollama, local) ──> JSON inventory
                                                  │
                            pantry file ──────────┤
                            diet filter ──────────┤
                                                  ▼
                                    aisle-grouped grocery list
                                    (text / markdown / JSON)
```

1. **Vision inventory** — the photo goes to `gemma3:4b` (open-weight, 3.9B, Q4) through
   Ollama's local API. The model scans shelf by shelf and returns strict JSON:
   item, estimated quantity, category.
2. **Pantry diff** — everything you already have (one item per line in a `pantry.txt`,
   comments with `#` allowed) is matched with word-boundary logic and skipped.
3. **Diet filter** — optional `--vegetarian` / `--vegan` filtering by category + keyword.
4. **Aisle grouping** — output is ordered the way a store is: produce, dairy, meat,
   bakery, frozen, pantry, drinks, condiments, snacks, leftovers.

## Install

Requirements:

- Python 3.10+ (stdlib only — zero dependencies)
- [Ollama](https://ollama.com) running locally, with a vision model:
  ```
  ollama pull gemma3:4b
  ```

Then:

```
git clone https://github.com/mayankinkk/slothcart.git slothcart
cd slothcart
pip install -e .
```

Or skip installing and run `python3 -m slothcart ...` directly.

## Usage

```
slothcart FRIDGE_PHOTO [options]

  --pantry FILE          file of items you already have (one per line)
  --diet {any,vegetarian,vegan}
  --model MODEL          ollama model (default: gemma3:4b)
  --inventory-only       just list what's in the photo, no shopping list
  --save-inventory FILE  dump the raw inventory as JSON
  --save-list FILE       write the grocery list as markdown
  --json                 machine-readable output
  --host URL             ollama host (default: http://127.0.0.1:11434)
```

Examples:

```bash
# one-shot: photo -> grocery list
slothcart fridge.jpg

# subtract what you already have
slothcart fridge.jpg --pantry pantry.txt

# save a markdown checklist for the household
slothcart fridge.jpg --pantry pantry.txt --save-list shop.md

# pipeline mode: detect once, reuse the inventory
slothcart fridge.jpg --save-inventory inv.json --inventory-only
```

## Offline by design

- Talks only to `http://127.0.0.1:11434` — pull the ethernet cable and it still works.
- Your fridge photos never leave your machine (you can see exactly where they go: `slothcart/ollama.py`).
- No API keys, no per-call cost, no rate limits. Install once, run forever.
- Swap the model with `--model` whenever you want — bigger at home, smaller on a laptop.

## Why open innovation matters here

A grocery-list tool knows intimate things: what you eat, when you're home, whether
you drink. Closed vision APIs mean uploading your open fridge to a stranger's server,
paying per photo, and being stuck with their model, their rate limits, and their
outage days. Running an open-weight model on my own machine flips every one of those:
privacy by default, free per run, and the freedom to swap `gemma3:4b` for whatever
runs best on my hardware. Full write-up in [POST-DRAFT.md](POST-DRAFT.md).

## Tests

```bash
python3 -m unittest discover -s tests
```

25 tests covering JSON extraction, pantry matching (incl. "eggplant" vs "egg"),
diet filters, grouping order, rendering, and CLI error paths.

## Credits

- Example photo: [Open refrigerator with food at night](https://commons.wikimedia.org/wiki/File:Open_refrigerator_with_food_at_night.jpg)
  by W.carter, licensed [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)
  (Wikimedia Commons) — chosen because its contents are documented, so accuracy can be checked.
- Inference: [Ollama](https://ollama.com) + `gemma3:4b` (open weights, Gemma Terms of Use).

## License

MIT — see [LICENSE](LICENSE).
