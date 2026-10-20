import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import handler  # noqa: E402


def event(body, method="POST"):
    if not isinstance(body, str):
        body = json.dumps(body)
    return {
        "body": body,
        "requestContext": {"http": {"method": method, "sourceIp": "127.0.0.1"}},
    }


class HandlerTests(unittest.TestCase):
    def setUp(self):
        handler.TABLE_NAME = ""
        handler._table = None

    def test_success_without_dynamodb(self):
        response = handler.lambda_handler(
            event(
                {
                    "name": "Grace Hopper",
                    "email": "grace@example.com",
                    "message": "Please send internship details for the cloud team.",
                }
            ),
            SimpleNamespace(aws_request_id="test-1"),
        )
        self.assertEqual(response["statusCode"], 200)
        payload = json.loads(response["body"])
        self.assertTrue(payload["ok"])
        self.assertIn("id", payload)
        self.assertEqual(response["headers"]["Access-Control-Allow-Origin"], "*")

    def test_validation_error_shape(self):
        response = handler.lambda_handler(event({"name": "", "email": "x", "message": ""}), None)
        self.assertEqual(response["statusCode"], 400)
        payload = json.loads(response["body"])
        self.assertFalse(payload["ok"])
        self.assertIn("name", payload["fields"])
        self.assertIn("email", payload["fields"])
        self.assertIn("message", payload["fields"])

    def test_invalid_json(self):
        response = handler.lambda_handler(event("{not json"), None)
        self.assertEqual(response["statusCode"], 400)

    def test_method_not_allowed(self):
        response = handler.lambda_handler(event({}, method="GET"), None)
        self.assertEqual(response["statusCode"], 405)

    def test_options_preflight(self):
        response = handler.lambda_handler(event("", method="OPTIONS"), None)
        self.assertEqual(response["statusCode"], 204)

    def test_payload_too_large(self):
        huge = {"name": "Ada Lovelace", "email": "ada@example.com", "message": "x" * 9000}
        response = handler.lambda_handler(event(huge), None)
        self.assertEqual(response["statusCode"], 413)

    def test_dynamodb_failure_returns_500(self):
        handler.TABLE_NAME = "contact-messages"
        mock_table = MagicMock()
        mock_table.put_item.side_effect = RuntimeError("throttled")
        with patch.object(handler, "_dynamodb_table", return_value=mock_table):
            response = handler.lambda_handler(
                event(
                    {
                        "name": "Alan Turing",
                        "email": "alan@example.com",
                        "message": "Interested in the cloud internship track.",
                    }
                ),
                SimpleNamespace(aws_request_id="test-db"),
            )
        self.assertEqual(response["statusCode"], 500)
        payload = json.loads(response["body"])
        self.assertFalse(payload["ok"])

    def test_dynamodb_put_item_called(self):
        handler.TABLE_NAME = "contact-messages"
        mock_table = MagicMock()
        with patch.object(handler, "_dynamodb_table", return_value=mock_table):
            response = handler.lambda_handler(
                event(
                    {
                        "name": "Alan Turing",
                        "email": "alan@example.com",
                        "message": "Interested in the cloud internship track.",
                    }
                ),
                None,
            )
        self.assertEqual(response["statusCode"], 200)
        mock_table.put_item.assert_called_once()
        item = mock_table.put_item.call_args.kwargs["Item"]
        self.assertEqual(item["email"], "alan@example.com")
        self.assertIn("ttl", item)

    def test_json_array_rejected(self):
        response = handler.lambda_handler(event("[1, 2, 3]"), None)
        self.assertEqual(response["statusCode"], 400)

    def test_base64_encoded_body(self):
        import base64

        payload = {
            "name": "Grace Hopper",
            "email": "grace@example.com",
            "message": "Please send internship details for the cloud team.",
        }
        encoded = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
        evt = event(encoded)
        evt["isBase64Encoded"] = True
        response = handler.lambda_handler(evt, None)
        self.assertEqual(response["statusCode"], 200)

    def test_sam_invalid_event_fixture(self):
        fixture = json.loads((ROOT / "tests" / "events" / "invalid.json").read_text(encoding="utf-8"))
        response = handler.lambda_handler(fixture, None)
        self.assertEqual(response["statusCode"], 400)


if __name__ == "__main__":
    unittest.main()

