import json
import sys
import unittest
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
from slothcart.ollama import extract_json


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
