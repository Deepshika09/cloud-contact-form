"""Shared contact-form validation used by Lambda (and mirrored in the frontend)."""

from __future__ import annotations

import re
from typing import Any

NAME_MIN, NAME_MAX = 2, 80
MESSAGE_MIN, MESSAGE_MAX = 10, 2000
EMAIL_MAX = 254

# Letters, spaces, hyphen, apostrophe; must start with a letter.
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z '\-]*$")
# Practical email check (not a full RFC parser). Backend is the source of truth.
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,24}$")

ALLOWED_FIELDS = frozenset({"name", "email", "message"})


class ValidationError(Exception):
    def __init__(self, fields: dict[str, str]) -> None:
        self.fields = fields
        super().__init__("Validation failed")


def _as_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    return value


def validate_contact_payload(data: dict[str, Any]) -> dict[str, str]:
    """Return a sanitized payload or raise ValidationError with field messages."""
    if not isinstance(data, dict):
        raise ValidationError({"_form": "Request body must be a JSON object."})

    fields: dict[str, str] = {}

    raw_name = _as_string(data.get("name"))
    raw_email = _as_string(data.get("email"))
    raw_message = _as_string(data.get("message"))

    if raw_name is None:
        fields["name"] = "Name is required."
        name = ""
    else:
        name = " ".join(raw_name.strip().split())
        if not name:
            fields["name"] = "Name is required."
        elif len(name) < NAME_MIN or len(name) > NAME_MAX:
            fields["name"] = f"Name must be between {NAME_MIN} and {NAME_MAX} characters."
        elif not NAME_RE.fullmatch(name):
            fields["name"] = "Use letters, spaces, hyphens, or apostrophes only."

    if raw_email is None:
        fields["email"] = "Email is required."
        email = ""
    else:
        email = raw_email.strip().lower()
        if not email:
            fields["email"] = "Email is required."
        elif len(email) > EMAIL_MAX:
            fields["email"] = "Email is too long."
        elif not EMAIL_RE.fullmatch(email):
            fields["email"] = "Enter a valid email address."

    if raw_message is None:
        fields["message"] = "Message is required."
        message = ""
    else:
        message = raw_message.strip()
        if not message:
            fields["message"] = "Message is required."
        elif len(message) < MESSAGE_MIN or len(message) > MESSAGE_MAX:
            fields["message"] = (
                f"Message must be between {MESSAGE_MIN} and {MESSAGE_MAX} characters."
            )

    if fields:
        raise ValidationError(fields)

    return {"name": name, "email": email, "message": message}
