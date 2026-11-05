"""Exercise the calculation code from the interview, not a duplicate formula."""
from pathlib import Path
import unittest
import yaml

INTERVIEW = Path(__file__).resolve().parents[1] / "docassemble/ChildSupportGuidelinesWorksheet/data/questions/child_support_guidelines_worksheet.yml"
BLOCKS = [b for b in yaml.safe_load_all(INTERVIEW.read_text()) if b]


def calculation(marker):
    return next(block for block in BLOCKS if marker in block.get("code", ""))


class IncomeAdjustmentTests(unittest.TestCase):
    def test_repeated_calculation_and_edits(self):
        for parent in ("parents1", "parents2"):
            with self.subTest(parent=parent):
                block = calculation(f"adjust_{parent}_gross_amount = True")
                values = {f"{parent}_{key}": value for key, value in {
                    "gross_amount": 1000, "gross_include_public_assistance": True,
                    "ssi_amount": 100, "food_stamps_amount": 50, "tafdc_amount": 25,
                }.items()}
                original = values.copy()
                for _ in range(3):
                    exec(block["code"], values)
                    self.assertEqual(values[f"{parent}_adjusted_gross_amount"], 825)
                    for key, value in original.items():
                        self.assertEqual(values[key], value)
                for field, value, expected in [
                    ("gross_amount", 1200, 1025),
                    ("ssi_amount", 120, 1005),
                    ("food_stamps_amount", 75, 980),
                    ("tafdc_amount", 30, 975),
                    ("gross_include_public_assistance", False, 1200),
                    ("gross_include_public_assistance", True, 975),
                ]:
                    name = f"{parent}_{field}"
                    self.assertIn(name, block["depends on"])
                    values[name] = value
                    exec(block["code"], values)
                    self.assertEqual(values[f"{parent}_adjusted_gross_amount"], expected)
                    self.assertEqual(values[f"{parent}_gross_amount"], 1200)

    def test_no_assistance_does_not_require_hidden_fields(self):
        for parent in ("parents1", "parents2"):
            values = {f"{parent}_gross_amount": 1000,
                      f"{parent}_gross_include_public_assistance": False}
            exec(calculation(f"adjust_{parent}_gross_amount = True")["code"], values)
            self.assertEqual(values[f"{parent}_adjusted_gross_amount"], 1000)

    def test_available_income_uses_adjusted_income(self):
        for parent in ("parents1", "parents2"):
            block = calculation(f"calculate_{parent}_available_income_amount = True")
            self.assertIn(f"{parent}_adjusted_gross_amount", block["depends on"])
            for gross, expected in [(825, 695), (0, 0), (-25, 0)]:
                values = {f"{parent}_{key}": value for key, value in {
                    "gross_amount": 1000, "adjusted_gross_amount": gross,
                    "SS_dependency_amount": 20, "other_obligations_amount": 100,
                    "health_care_amount": 30, "dental_vision_amount": 20,
                }.items()}
                exec(block["code"], values)
                self.assertEqual(values[f"{parent}_available_income_amount"], expected)

    def test_pdf_uses_adjusted_income(self):
        fields = next(a["fields"] for b in BLOCKS for a in b.get("attachments", [])
                      if "fields" in a)
        for parent in ("parents1", "parents2"):
            expression = next(f[f"{parent}_gross_amount"] for f in fields if f"{parent}_gross_amount" in f)
            self.assertEqual(expression, f"${{ currency({parent}_adjusted_gross_amount) }}")


if __name__ == "__main__":
    unittest.main()
