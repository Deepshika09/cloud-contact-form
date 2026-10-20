import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from validation import ValidationError, validate_contact_payload  # noqa: E402


class ValidationTests(unittest.TestCase):
    def test_valid_payload(self):
        result = validate_contact_payload(
            {
                "name": "  Ada  Lovelace ",
                "email": "Ada@Example.COM",
                "message": "I would like to intern on the cloud team.",
            }
        )
        self.assertEqual(result["name"], "Ada Lovelace")
        self.assertEqual(result["email"], "ada@example.com")

    def test_rejects_short_message(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_contact_payload(
                {"name": "Ada Lovelace", "email": "ada@example.com", "message": "Hi"}
            )
        self.assertIn("message", ctx.exception.fields)

    def test_rejects_bad_email(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_contact_payload(
                {
                    "name": "Ada Lovelace",
                    "email": "not-an-email",
                    "message": "This is a longer valid message.",
                }
            )
        self.assertIn("email", ctx.exception.fields)

    def test_rejects_numeric_name(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_contact_payload(
                {"name": "12345", "email": "ada@example.com", "message": "This is a longer valid message."}
            )
        self.assertIn("name", ctx.exception.fields)

    def test_rejects_non_object(self):
        with self.assertRaises(ValidationError):
            validate_contact_payload(["not", "an", "object"])  # type: ignore[arg-type]

    def test_rejects_missing_keys(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_contact_payload({})
        self.assertEqual(set(ctx.exception.fields), {"name", "email", "message"})

    def test_rejects_non_string_fields(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_contact_payload({"name": 1, "email": True, "message": ["x"]})
        self.assertIn("name", ctx.exception.fields)
        self.assertIn("email", ctx.exception.fields)
        self.assertIn("message", ctx.exception.fields)

    def test_allows_hyphen_and_apostrophe_in_name(self):
        result = validate_contact_payload(
            {
                "name": "Mary-Jane O'Neil",
                "email": "mj@example.com",
                "message": "This is a valid message for the form.",
            }
        )
        self.assertEqual(result["name"], "Mary-Jane O'Neil")


if __name__ == "__main__":
    unittest.main()

