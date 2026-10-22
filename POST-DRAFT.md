---
title: "slothcart: a fridge photo → grocery list that never phones home"
published: false
description: "Hacktoberfest Week 3 — an offline, zero-dependency CLI that turns a photo of your fridge into a pantry-aware grocery list using a local open-weight vision model."
tags: hacktoberfest, ai, opensource, python
---

# slothcart: a fridge photo → grocery list that never phones home

*Challenge: Slow and Steady — build something with open-source AI that rewards laziness.*

## The sloth thesis

International Sloth Day (Oct 20) is a reminder that sloths don't hurry — and neither
should automation. The dread task I picked: **standing at the open fridge, door
ajar, trying to remember what we already have before writing down what we need.**

So I stopped standing there. One photo, taken once, and a local model does the
staring, remembering, and list-making.

**`slothcart`** is a CLI: point it at a photo of your fridge or pantry and it hands
back an aisle-grouped grocery list, minus anything your `pantry.txt` says you
already stock. It runs entirely on my M2 laptop with the network cable pulled.

## Demo

```console
$ slothcart examples/fridge.jpg --pantry examples/pantry.txt --save-list shop.md
Reading fridge.jpg with gemma3:4b (local, offline)...

GROCERY LIST
========================================

PRODUCE
-------
  [ ] grapes  (about 1/2 kg)
  [ ] green apples  (about 3)
  [ ] oranges  (about 6)
  [ ] lemon  (1)

DAIRY
-----
  [ ] milk cartons  (6)

PANTRY
------
  [ ] jar of pickles  (1)
  [ ] jar of olives  (1)

DRINKS
------
  [ ] green bottles  (3)

ALREADY AT HOME (skipped)
------------------------
  loaf of bread
  cheese
  tomatoes
  yogurt
```

The markdown version it saves is a ready-to-share checkbox list:

```markdown
## Produce

- [ ] grapes (about 1/2 kg)
- [ ] green apples (about 3)
- [ ] oranges (about 6)
```

It also does `--inventory-only` (just tell me what's in the photo),
`--json` (for piping into other lazy automations), `--save-inventory`
(detect once, reuse forever), and `--diet vegetarian|vegan`.

## How it works

```
fridge photo ──> gemma3:4b (Ollama, localhost) ──> strict JSON inventory
                                                     │
                                   pantry.txt ───────┤
                                   --diet filter ────┤
                                                     ▼
                                        aisle-grouped grocery list
```

1. **Vision inventory** — the photo is base64'd and POSTed to a local Ollama
   server. The open-weight `gemma3:4b` model (3.9B params, Q4 quantised) scans
   shelf by shelf and returns `{"items": [{name, quantity, category}]}` — one
   temperature-0.1 pass, JSON extracted and validated on my side.
2. **Pantry diff** — `pantry.txt` lists what we stock. Matching is deliberately
   boring: normalise, word-boundary match ("cheddar cheese" has "cheese",
   but "eggplant" does **not** have "egg"), skip the rest.
3. **Aisle grouping** — output ordered like a store walk: produce → dairy →
   meat → bakery → frozen → pantry → drinks → condiments → snacks → leftovers.

The whole thing is **Python stdlib only** — no `requests`, no `pillow`, no
lockfile. `pip install -e .` gives you a `slothcart` command; the model stays
in Ollama where it belongs.

### Checking its honesty

I test-drove it on a [CC BY-SA 4.0 Wikimedia featured photo](https://commons.wikimedia.org/wiki/File:Open_refrigerator_with_food_at_night.jpg)
whose exact contents are documented on the file page: eggs, bell pepper, grapefruit
soda, coconut milk, ham, butter, cheese, pickles, lemons, tomatoes, grapes, carrots,
onions, oranges. The model caught most of it (tomatoes, grapes, oranges, cheese,
pickles, carrots, lemons, bottled drinks...), merged a few into "green bottles" and
"cans", and missed some small door items. A 3.9B model is *roughly* right, not
kitchen-inventory perfect — and that's a fair trade for free, private, and offline.
Bigger local models (`--model llava`, whatever your RAM allows) improve recall
without changing a line of code. Slow and steady.

## Why open innovation matters for this

**1. It runs with no internet.** Ollama on `127.0.0.1:11434` is the only endpoint
in the codebase. Airplane mode, cabin weekend, flaky village Wi-Fi — same command,
same result. A closed vision API makes a grocery list impossible precisely when
you're most off-grid.

**2. My fridge stays my fridge.** A fridge photo is a surprisingly intimate
document: what you eat, what you buy, when you're home. With closed APIs, every
demo run means uploading that to a server I don't control, training-adjacent
terms I didn't read, and logs I can't delete. Here the photo path goes
`argv → base64 → localhost`. Nothing else. I can *read* the exact code path my
data travels.

**3. Set it up once, pay nothing again.** Zero API keys, zero per-photo cost,
zero rate limits. `ollama pull gemma3:4b` once (~3.4 GB) and the tool runs
forever. The per-run cost of automation should be zero, or people won't
automate the small stuff — which is exactly the stuff sloths avoid.

**4. Swap the brain, keep the tool.** `--model llava` today, `gemma3:12b` when
the laptop is plugged in, whatever vision model lands in Ollama next month.
Closed models make "upgrade" a pricing change; open weights make it a
one-word flag. I can also quantise differently, fine-tune on my own labelled
shelf photos, or set behaviour with a prompt I fully control.

**Where open beat closed for me, concretely:** privacy (home interior photos
never uploaded), cost (hundreds of local runs at $0 vs. per-image pricing),
and independence (the demo worked while my network didn't). The one place
closed wins is raw accuracy at the frontier — a giant hosted VLM sees more
small jars. For a checklist that costs nothing and never phones home, open
wins the product, not just the principles.

## Show your work

- Repo: `<REPO_URL>` — MIT
- Built with: `<DEVRAY_SESSION_LINK>` (agent session — full build process)
- Stack: Python 3.14 stdlib, Ollama, `gemma3:4b` (open weights), 25 unit tests
  (`python3 -m unittest discover -s tests`), Apple M2 / 16 GB

```bash
ollama pull gemma3:4b
pip install -e .
slothcart your-fridge.jpg --pantry pantry.txt --save-list shop.md
```

*Example photo: "Open refrigerator with food at night" by W.carter,
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) via Wikimedia Commons.*
