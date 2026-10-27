import pytest

from app.visa.confirmation_validator import (
    PayloadValidationError,
    validate_confirmation,
)


@pytest.fixture
def valid_payload():
    return {
        "srcCorrelationId": "LOCAL-TEST-001",
        "confirmationData2": {
            "checkoutEventType": "01",
            "confirmationStatus": "02",
            "confirmationTimestamp": "1793066400",
            "confirmationReason": "Synthetic failure test",
            "transactionAmount": {
                "transactionAmount": 1.00,
                "transactionCurrencyCode": "USD",
            },
        },
    }


def test_valid_payload_is_local_only(valid_payload):
    result = validate_confirmation(valid_payload)

    assert result["valid"] is True
    assert result["validation_type"] == "LOCAL_ONLY"
    assert result["network_request_made"] is False
    assert result["bank_confirmed"] is False
    assert result["available_funds_confirmed"] is False
    assert result["case_status"] == "UNVERIFIED"


def test_invalid_event_type_is_rejected(valid_payload):
    valid_payload["confirmationData2"]["checkoutEventType"] = "99"

    with pytest.raises(PayloadValidationError):
        validate_confirmation(valid_payload)


def test_invalid_timestamp_is_rejected(valid_payload):
    valid_payload["confirmationData2"]["confirmationTimestamp"] = "invalid"

    with pytest.raises(PayloadValidationError):
        validate_confirmation(valid_payload)


def test_successful_authorization_requires_auth_code(valid_payload):
    data = valid_payload["confirmationData2"]
    data["confirmationStatus"] = "01"

    with pytest.raises(PayloadValidationError):
        validate_confirmation(valid_payload)
