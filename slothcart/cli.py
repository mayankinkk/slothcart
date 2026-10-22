import argparse
import json
import os
import sys

from . import __version__
from .grocery import build_list, load_pantry, render_markdown, render_text
from .ollama import DEFAULT_HOST, DEFAULT_MODEL, OllamaError, inventory

def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="slothcart",
        description="Point it at a fridge photo. Get a grocery list. Never stand at an open fridge again.",
    )
    p.add_argument("image", help="path to a photo of your fridge/pantry")
    p.add_argument("--pantry", metavar="FILE", help="file listing what you already have (one item per line)")
    p.add_argument("--diet", choices=["any", "vegetarian", "vegan"], default="any")
    p.add_argument("--model", default=DEFAULT_MODEL, help=f"ollama model (default: {DEFAULT_MODEL})")
    p.add_argument("--host", default=DEFAULT_HOST, help=f"ollama host (default: {DEFAULT_HOST})")
    p.add_argument("--json", action="store_true", help="print machine-readable JSON")
    p.add_argument("--save-list", metavar="FILE", help="write the grocery list as markdown")
    p.add_argument("--save-inventory", metavar="FILE", help="write the raw inventory as JSON")
    p.add_argument("--inventory-only", action="store_true", help="stop after detecting items (no grocery list)")
    p.add_argument("--version", action="version", version=f"slothcart {__version__}")
    return p.parse_args(argv)


def render_inventory_table(items):
    lines = ["SEEN IN PHOTO", "=" * 40]
    width = max((len(it["name"]) for it in items), default=4) + 2
    for it in items:
        qty = it["quantity"] or "-"
        lines.append(f"  {it['name']:<{width}} {qty:<14} {it['category']}")
    if not items:
        lines.append("  (nothing recognised)")
    return "\n".join(lines)


def main(argv=None):
    args = parse_args(argv)

    if not os.path.exists(args.image):
        print(f"slothcart: image not found: {args.image}", file=sys.stderr)
        return 2

    if args.pantry and not os.path.exists(args.pantry):
        print(f"slothcart: pantry file not found: {args.pantry}", file=sys.stderr)
        return 2

    print(f"Reading {os.path.basename(args.image)} with {args.model} (local, offline)...", file=sys.stderr)
    try:
        items = inventory(args.image, model=args.model, host=args.host)
    except OllamaError as e:
        print(f"slothcart: {e}", file=sys.stderr)
        return 1
    except (ValueError, OSError) as e:
        print(f"slothcart: {e}", file=sys.stderr)
        return 1

    if args.save_inventory:
        with open(args.save_inventory, "w", encoding="utf-8") as f:
            json.dump({"items": items}, f, indent=2)
            f.write("\n")
        print(f"Inventory saved to {args.save_inventory}", file=sys.stderr)

    if args.inventory_only:
        if args.json:
            print(json.dumps({"items": items}, indent=2))
        else:
            print(render_inventory_table(items))
        return 0

    pantry = load_pantry(args.pantry) if args.pantry else []
    result = build_list(items, pantry=pantry, diet=args.diet)

    if args.save_list:
        with open(args.save_list, "w", encoding="utf-8") as f:
            f.write(render_markdown(result) + "\n")
        print(f"Grocery list saved to {args.save_list}", file=sys.stderr)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(render_text(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
