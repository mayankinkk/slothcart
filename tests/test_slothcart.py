import base64
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from slothcart.grocery import (
    build_list,
    group,
    is_banned,
    load_pantry,
    matches_pantry,
    normalize,
    render_markdown,
    render_text,
)
from slothcart.ollama import OllamaError, _sniff, encode_image, extract_json


def item(name, category="pantry", quantity="1"):
    return {"name": name, "quantity": quantity, "category": category}


class TestExtractJson(unittest.TestCase):
    def test_plain_object(self):
        self.assertEqual(extract_json('{"items": []}'), {"items": []})

    def test_fenced_object(self):
        text = '```json\n{"items": [{"name": "milk"}]}\n```'
        self.assertEqual(extract_json(text), {"items": [{"name": "milk"}]})

    def test_surrounded_by_prose(self):
        text = 'Here you go: {"items": []} hope that helps'
        self.assertEqual(extract_json(text), {"items": []})

    def test_no_json_raises(self):
        with self.assertRaises(ValueError):
            extract_json("sorry, I cannot see anything")


class TestNormalize(unittest.TestCase):
    def test_lowercases_and_drops_stopwords(self):
        self.assertEqual(normalize("Fresh Whole Milk"), "whole milk")

    def test_keeps_meaningful_words(self):
        self.assertEqual(normalize("Greek yoghurt"), "greek yoghurt")


class TestPantryMatching(unittest.TestCase):
    def test_exact(self):
        self.assertTrue(matches_pantry("milk", "milk"))

    def test_substring(self):
        self.assertTrue(matches_pantry("whole milk", "milk"))

    def test_shared_full_word(self):
        self.assertTrue(matches_pantry("cheddar cheese", "cheese"))

    def test_unrelated(self):
        self.assertFalse(matches_pantry("ketchup", "mustard"))

    def test_partial_word_does_not_match(self):
        self.assertFalse(matches_pantry("eggplant", "egg"))


class TestPantryFile(unittest.TestCase):
    def test_skips_comments_and_blanks(self):
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write("milk  # staple\n\nbread\n")
            path = f.name
        self.assertEqual(load_pantry(path), ["milk", "bread"])


class TestDietFilter(unittest.TestCase):
    def test_vegetarian_drops_meat(self):
        self.assertTrue(is_banned(item("chicken thighs", "meat & seafood"), "vegetarian"))

    def test_vegetarian_keeps_dairy(self):
        self.assertFalse(is_banned(item("cheddar", "dairy"), "vegetarian"))

    def test_vegan_keeps_plant_milk(self):
        self.assertFalse(is_banned(item("oat milk", "drinks"), "vegan"))

    def test_vegan_drops_dairy_category(self):
        self.assertTrue(is_banned(item("cow milk", "dairy"), "vegan"))

    def test_any_never_bans(self):
        self.assertFalse(is_banned(item("steak", "meat & seafood"), "any"))


class TestBuildList(unittest.TestCase):
    def test_splits_pantry_and_need(self):
        inv = [item("milk"), item("eggs"), item("spinach", "produce")]
        result = build_list(inv, pantry=["milk"])
        self.assertEqual([i["name"] for i in result["have"]], ["milk"])
        self.assertEqual([i["name"] for i in result["need"]], ["eggs", "spinach"])

    def test_diet_filter_removes_from_both(self):
        inv = [item("beef", "meat & seafood"), item("rice")]
        result = build_list(inv, pantry=[], diet="vegetarian")
        self.assertEqual([i["name"] for i in result["need"]], ["rice"])
        self.assertEqual(result["have"], [])


class TestRendering(unittest.TestCase):
    def setUp(self):
        self.result = build_list(
            [item("spinach", "produce", "1 bag"), item("milk", "dairy")],
            pantry=["milk"],
        )

    def test_text_shows_sections_and_have(self):
        text = render_text(self.result)
        self.assertIn("GROCERY LIST", text)
        self.assertIn("PRODUCE", text)
        self.assertIn("[ ] spinach  (1 bag)", text)
        self.assertIn("ALREADY AT HOME", text)
        self.assertIn("milk", text)

    def test_text_empty_list(self):
        text = render_text(build_list([item("milk")], pantry=["milk"]))
        self.assertIn("fully stocked", text)

    def test_markdown_checkbox(self):
        md = render_markdown(self.result)
        self.assertIn("## Produce", md)
        self.assertIn("- [ ] spinach (1 bag)", md)

    def test_group_order(self):
        items = [item("soda", "drinks"), item("apple", "produce"), item("x", "other")]
        cats = [c for c, _ in group(items)]
        self.assertEqual(cats, ["produce", "drinks", "other"])


def make_png():
    def chunk(tag, data):
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    idat = zlib.compress(b"\x00\x00\x00\x00\xff")
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


class TestImageFormats(unittest.TestCase):
    def test_sniff_supported_formats(self):
        self.assertEqual(_sniff(b"\xff\xd8\xff\xe0rest"), "jpeg")
        self.assertEqual(_sniff(b"\x89PNG\r\n\x1a\n"), "png")
        self.assertEqual(_sniff(b"GIF89a...."), "gif")
        self.assertEqual(_sniff(b"RIFF\x00\x00\x00\x00WEBP"), "webp")

    def test_sniff_heic_returns_none(self):
        heic = b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00"
        self.assertIsNone(_sniff(heic))

    def test_encode_png_untouched(self):
        png = make_png()
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(png)
            path = f.name
        try:
            self.assertEqual(base64.b64decode(encode_image(path)), png)
        finally:
            os.unlink(path)

    def test_garbage_file_raises_ollama_error(self):
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            f.write(b"definitely not an image")
            path = f.name
        try:
            with self.assertRaises(OllamaError):
                encode_image(path)
        finally:
            os.unlink(path)

    @unittest.skipUnless(shutil.which("sips"), "sips is macOS-only")
    def test_heic_converts_to_jpeg(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(make_png())
            png_path = f.name
        heic_path = png_path + ".heic"
        try:
            subprocess.run(
                ["sips", "-s", "format", "heic", png_path, "--out", heic_path],
                capture_output=True,
                check=True,
            )
            with open(heic_path, "rb") as f:
                self.assertIsNone(_sniff(f.read(16)))
            data = base64.b64decode(encode_image(heic_path))
            self.assertEqual(_sniff(data[:16]), "jpeg")
        finally:
            for p in (png_path, heic_path):
                if os.path.exists(p):
                    os.unlink(p)


class TestCliOffline(unittest.TestCase):
    def test_json_flag_parses(self):
        from slothcart.cli import parse_args

        args = parse_args(["shot.jpg", "--json", "--diet", "vegan"])
        self.assertTrue(args.json)
        self.assertEqual(args.diet, "vegan")

    def test_missing_image_fails_cleanly(self):
        from slothcart.cli import main

        self.assertEqual(main(["/no/such/image.jpg"]), 2)


if __name__ == "__main__":
    unittest.main()
