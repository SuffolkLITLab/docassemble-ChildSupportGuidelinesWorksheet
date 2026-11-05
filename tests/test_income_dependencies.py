"""Verify edit/recalculation behavior using docassemble's interview engine."""
import unittest
import yaml
from docassemble.base import parse
from docassemble.base.plugin_manager import pm
from docassemble.base.thread_context import empty_globals, global_context
import pluggy
from test_income_adjustment import BLOCKS, calculation

hookimpl = pluggy.HookimplMarker("docassemble")


class TestConfiguration:
    """Supply server configuration while running the engine without a web server."""

    @hookimpl
    def get_configuration(self):
        return {}

    @hookimpl
    def get_main_page_parts(self):
        return {}

    @hookimpl
    def get_default_language(self):
        return "en"

    @hookimpl
    def get_default_timezone(self):
        return "UTC"



class IncomeDependencyTests(unittest.TestCase):
    def setUp(self):
        self.configuration = TestConfiguration()
        pm.register(self.configuration)
        self.addCleanup(pm.unregister, self.configuration)
        self.enterContext(global_context(empty_globals()))

    def test_edits_invalidate_and_recalculate_for_both_parents(self):
        for parent in ("parents1", "parents2"):
            with self.subTest(parent=parent):
                # Include the real input question so the engine registers edits.
                question = next(b for b in BLOCKS if any(
                    parent + "_gross_amount" in field.values()
                    for field in b.get("fields", []) if isinstance(field, dict)))
                blocks = [question,
                          calculation(f"adjust_{parent}_gross_amount = True"),
                          calculation(f"calculate_{parent}_available_income_amount = True"),
                          {"mandatory": True, "question": f"Result ${{ {parent}_available_income_amount }}"}]
                source = parse.InterviewSourceString(content=yaml.safe_dump_all(blocks))
                source.package = "docassemble.base"
                interview = parse.Interview(source=source)
                values = parse.get_initial_dict()
                values.update({f"{parent}_{k}": v for k, v in {
                    "gross_amount": 1000, "gross_include_public_assistance": True,
                    "ssi_amount": 100, "food_stamps_amount": 50, "tafdc_amount": 25,
                    "SS_dependency_amount": 20, "other_obligations_amount": 100,
                    "health_care_amount": 30, "dental_vision_amount": 20,
                }.items()})

                def assemble():
                    interview.assemble(values, parse.InterviewStatus(current_info={
                        "user": {"session_uid": "regression", "device_id": "test", "the_user_id": "test"}}))

                assemble()
                assemble()
                self.assertEqual(values[f"{parent}_adjusted_gross_amount"], 825)
                self.assertEqual(values[f"{parent}_available_income_amount"], 695)
                self.assertEqual(values[f"{parent}_gross_amount"], 1000)
                for field, value, expected in [
                    ("ssi_amount", 120, 805), ("food_stamps_amount", 75, 780),
                    ("tafdc_amount", 30, 775), ("gross_amount", 1200, 975),
                    ("gross_include_public_assistance", False, 1200),
                    ("gross_include_public_assistance", True, 975),
                ]:
                    name = f"{parent}_{field}"
                    old = {name: values[name]}
                    values[name] = value
                    interview.invalidate_dependencies(name, values, old)
                    self.assertNotIn(f"{parent}_adjusted_gross_amount", values)
                    self.assertNotIn(f"{parent}_available_income_amount", values)
                    assemble()
                    self.assertEqual(values[f"{parent}_adjusted_gross_amount"], expected)
                    self.assertEqual(values[f"{parent}_available_income_amount"], expected - 130)


if __name__ == "__main__":
    unittest.main()
