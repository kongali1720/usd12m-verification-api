"""Local-only validator for Visa SRC confirmation payloads.

This module performs no network requests.
It does not verify bank settlement, account balances, or fund availability.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any


CHECKOUT_EVENT_TYPES = {
    "00", "01", "02", "03", "04",
    "05", "06", "07", "08",
}

CONFIRMATION_STATUSES = {"01", "02", "03", "04"}
MAX_TRANSACTION_AMOUNT = Decimal("1000000")


class PayloadValidationError(ValueError):
    """Raised when a confirmation payload fails local validation."""


def validate_confirmation(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a confirmation payload without making network requests."""

    if not isinstance(payload, dict):
        raise PayloadValidationError("Payload must be a JSON object.")

    data = payload.get("confirmationData2")
    if not isinstance(data, dict):
        raise PayloadValidationError(
            "confirmationData2 must be a JSON object."
        )

    event_type = data.get("checkoutEventType")
    if event_type not in CHECKOUT_EVENT_TYPES:
        raise PayloadValidationError(
            "checkoutEventType is not supported by this local validator."
        )

    status = data.get("confirmationStatus")
    if status not in CONFIRMATION_STATUSES:
        raise PayloadValidationError(
            "confirmationStatus must be 01, 02, 03, or 04."
        )

    timestamp = data.get("confirmationTimestamp")
    if not isinstance(timestamp, str) or not re.fullmatch(
        r"[0-9]{10}", timestamp
    ):
        raise PayloadValidationError(
            "confirmationTimestamp must be a 10-digit Unix timestamp."
        )

    if int(timestamp) <= 0:
        raise PayloadValidationError(
            "confirmationTimestamp must be positive."
        )

    correlation_id = payload.get("srcCorrelationId")
    if correlation_id is not None:
        if not isinstance(correlation_id, str) or not (
            1 <= len(correlation_id) <= 100
        ):
            raise PayloadValidationError(
                "srcCorrelationId must be a non-empty string of at most 100 characters."
            )

    amount_data = data.get("transactionAmount")
    if amount_data is not None:
        if not isinstance(amount_data, dict):
            raise PayloadValidationError(
                "transactionAmount must be a JSON object."
            )

        raw_amount = amount_data.get("transactionAmount")
        currency = amount_data.get("transactionCurrencyCode")

        if isinstance(raw_amount, bool) or raw_amount is None:
            raise PayloadValidationError(
                "transactionAmount must be a positive number."
            )

        try:
            amount = Decimal(str(raw_amount))
        except (InvalidOperation, ValueError) as exc:
            raise PayloadValidationError(
                "transactionAmount is invalid."
            ) from exc

        if (
            not amount.is_finite()
            or amount <= 0
            or amount >= MAX_TRANSACTION_AMOUNT
        ):
            raise PayloadValidationError(
                "transactionAmount is outside the local retail-test limit."
            )

        if not isinstance(currency, str) or not re.fullmatch(
            r"[A-Z]{3}", currency
        ):
            raise PayloadValidationError(
                "transactionCurrencyCode must contain three uppercase letters."
            )

    if event_type == "01" and status == "01":
        authorization_code = data.get("networkAuthorizationCode")
        if not isinstance(authorization_code, str) or not authorization_code.strip():
            raise PayloadValidationError(
                "Successful Authorize confirmation requires networkAuthorizationCode."
            )

    return {
        "valid": True,
        "validation_type": "LOCAL_ONLY",
        "network_request_made": False,
        "bank_confirmed": False,
        "available_funds_confirmed": False,
        "case_status": "UNVERIFIED",
    }
