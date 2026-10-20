"""AWS Lambda handler for POST /contact (API Gateway HTTP API payload v2.0)."""

from __future__ import annotations

import base64
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from validation import ValidationError, validate_contact_payload

logger = logging.getLogger()
logger.setLevel(logging.INFO)

MAX_BODY_BYTES = 8192
TABLE_NAME = os.environ.get("CONTACT_TABLE", "").strip()
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*").strip() or "*"
MESSAGE_TTL_DAYS = int(os.environ.get("MESSAGE_TTL_DAYS", "90"))

_table = None


def _dynamodb_table():
    """Lazy DynamoDB client so local tests do not require boto3 or AWS."""
    global _table
    if not TABLE_NAME:
        return None
    if _table is None:
        import boto3

        _table = boto3.resource("dynamodb").Table(TABLE_NAME)
    return _table


def _cors_headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
        "Access-Control-Allow-Headers": "content-type",
        "Access-Control-Allow-Methods": "POST,OPTIONS",
        "Access-Control-Max-Age": "600",
    }


def _response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": _cors_headers(),
        "body": json.dumps(body),
    }


def _http_method(event: dict[str, Any]) -> str:
    method = (
        event.get("requestContext", {}).get("http", {}).get("method")
        or event.get("httpMethod")
        or "POST"
    )
    return str(method).upper()


def _decode_body(event: dict[str, Any]) -> str:
    raw = event.get("body")
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8")
    return raw


def _source_ip(event: dict[str, Any]) -> str:
    return (
        event.get("requestContext", {}).get("http", {}).get("sourceIp")
        or event.get("requestContext", {}).get("identity", {}).get("sourceIp")
        or "unknown"
    )


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    request_id = getattr(context, "aws_request_id", None) or str(uuid.uuid4())
    method = _http_method(event)

    if method == "OPTIONS":
        return {"statusCode": 204, "headers": _cors_headers(), "body": ""}

    if method != "POST":
        return _response(
            405,
            {"ok": False, "error": "Method not allowed.", "requestId": request_id},
        )

    raw = _decode_body(event)
    if len(raw.encode("utf-8")) > MAX_BODY_BYTES:
        return _response(
            413,
            {"ok": False, "error": "Payload too large.", "requestId": request_id},
        )

    try:
        data = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return _response(
            400,
            {"ok": False, "error": "Request body must be valid JSON.", "requestId": request_id},
        )

    if not isinstance(data, dict):
        return _response(
            400,
            {"ok": False, "error": "Request body must be a JSON object.", "requestId": request_id},
        )

    try:
        payload = validate_contact_payload(data)
    except ValidationError as exc:
        return _response(
            400,
            {
                "ok": False,
                "error": "Please fix the highlighted fields.",
                "fields": exc.fields,
                "requestId": request_id,
            },
        )

    now = datetime.now(timezone.utc)
    item_id = str(uuid.uuid4())
    item = {
        "id": item_id,
        "name": payload["name"],
        "email": payload["email"],
        "message": payload["message"],
        "createdAt": now.isoformat(),
        "sourceIp": _source_ip(event),
        "ttl": int(now.timestamp()) + MESSAGE_TTL_DAYS * 24 * 3600,
    }

    table = _dynamodb_table()
    if table is not None:
        try:
            table.put_item(Item=item)
        except Exception:
            # Do not log the message body (PII). Request id is enough to correlate.
            logger.exception("Failed to persist contact message requestId=%s", request_id)
            return _response(
                500,
                {
                    "ok": False,
                    "error": "Unable to save your message. Please try again later.",
                    "requestId": request_id,
                },
            )
    else:
        logger.info("CONTACT_TABLE unset; skipping persistence requestId=%s", request_id)

    logger.info("Contact stored id=%s requestId=%s", item_id, request_id)
    return _response(
        200,
        {
            "ok": True,
            "message": "Thanks - your message was received.",
            "id": item_id,
            "requestId": request_id,
        },
    )
