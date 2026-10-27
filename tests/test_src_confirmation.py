"""Unit test untuk app/visa/src_confirmation.py.

Semua tes bersifat offline: tidak ada panggilan jaringan.
"""
import pytest
from pydantic import ValidationError

from app.visa.src_confirmation import (
    SrcTransactionCredentialsRequest,
    post_transaction_credentials,
    load_client_config_from_env,
)


def valid_payload(**overrides):
    """Payload minimal yang valid untuk skenario CARD_ON_FILE retail."""
    base = {
        "dpaData": {
            "dpaUri": "https://merchant.example/checkout",
            "dpaPresentationName": "Demo Shop",
        },
        "srcDpaId": "dpa-1",
        "serviceId": "CARD_ON_FILE",
        "srcClientId": "client-1",
        "assuranceData": {
            "eci": "05",
            "verificationData": [{
                "methodResults": {"threeDsData": {
                    "dsTransId": "ds-1", "acsTransId": "acs-1", "transStatus": "Y",
                }},
                "additionalData": "",
                "verificationType": "CARDHOLDER",
                "verificationEntity": "01",
                "verificationEvents": ["01"],
                "verificationMethod": "01",
                "verificationResults": "01",
                "verificationTimestamp": "2026-10-27T00:00:00Z",
            }],
        },
        "srcCorrelationId": "corr-1",
        "srcDigitalCardId": "card-1",
        "srciTransactionId": "tx-1",
        "dpaTransactionOptions": {
            "acquirerBin": "123456",
            "merchantName": "Demo Shop",
            "merchantCountryCode": "US",
            "merchantCategoryCode": "5999",
            "merchantOrderId": "order-1",
            "paymentOptions": [{"dynamicDataType": "CARD_APPLICATION_CRYPTOGRAM_SHORT_FORM"}],
            "transactionAmount": {
                "transactionAmount": "25.00",
                "transactionCurrencyCode": "USD",
            },
        },
    }
    base.update(overrides)
    return base


def test_valid_minimal_payload_passes():
    SrcTransactionCredentialsRequest.model_validate(valid_payload())


def test_missing_required_top_level_field_fails():
    p = valid_payload()
    del p["srcCorrelationId"]
    with pytest.raises(ValidationError) as exc:
        SrcTransactionCredentialsRequest.model_validate(p)
    assert any(e["loc"] == ("srcCorrelationId",) for e in exc.value.errors())


def test_service_id_must_be_card_on_file():
    p = valid_payload(serviceId="TOKEN_REQUEST")
    with pytest.raises(ValidationError):
        SrcTransactionCredentialsRequest.model_validate(p)


def test_dpa_uri_must_be_https_or_app():
    p = valid_payload()
    p["dpaData"]["dpaUri"] = "string"
    with pytest.raises(ValidationError) as exc:
        SrcTransactionCredentialsRequest.model_validate(p)
    assert any("https://" in e["msg"] for e in exc.value.errors())


def test_amount_must_be_positive():
    p = valid_payload()
    p["dpaTransactionOptions"]["transactionAmount"]["transactionAmount"] = 0
    with pytest.raises(ValidationError):
        SrcTransactionCredentialsRequest.model_validate(p)


def test_amount_12_million_is_rejected():
    """Nominal $12jt dari PDF harus ditolak, bahkan jika field lain valid."""
    p = valid_payload()
    p["dpaTransactionOptions"]["transactionAmount"]["transactionAmount"] = "12000000.11"
    with pytest.raises(ValidationError) as exc:
        SrcTransactionCredentialsRequest.model_validate(p)
    msgs = " ".join(e["msg"] for e in exc.value.errors())
    assert "exceeds sane e-commerce limit" in msgs or "outside SRC retail scope" in msgs


def test_currency_must_be_iso_4217():
    p = valid_payload()
    p["dpaTransactionOptions"]["transactionAmount"]["transactionCurrencyCode"] = "str"
    with pytest.raises(ValidationError):
        SrcTransactionCredentialsRequest.model_validate(p)


def test_acquirer_bin_must_be_6_to_11_digits():
    p = valid_payload()
    p["dpaTransactionOptions"]["acquirerBin"] = "string"
    with pytest.raises(ValidationError) as exc:
        SrcTransactionCredentialsRequest.model_validate(p)
    assert any("6-11 digits" in e["msg"] for e in exc.value.errors())


def test_merchant_country_iso_3166():
    p = valid_payload()
    p["dpaTransactionOptions"]["merchantCountryCode"] = "st"
    with pytest.raises(ValidationError):
        SrcTransactionCredentialsRequest.model_validate(p)


def test_extra_fields_are_forbidden():
    p = valid_payload()
    p["dpaTransactionOptions"]["consumerNameRequested"] = True
    with pytest.raises(ValidationError) as exc:
        SrcTransactionCredentialsRequest.model_validate(p)
    assert any("Extra inputs are not permitted" in e["msg"] for e in exc.value.errors())


def test_eci_must_be_two_digits():
    p = valid_payload()
    p["assuranceData"]["eci"] = "5"
    with pytest.raises(ValidationError):
        SrcTransactionCredentialsRequest.model_validate(p)


def test_three_ds_status_must_be_known_value():
    p = valid_payload()
    p["assuranceData"]["verificationData"][0]["methodResults"]["threeDsData"]["transStatus"] = "Z"
    with pytest.raises(ValidationError):
        SrcTransactionCredentialsRequest.model_validate(p)


def test_post_without_config_raises():
    """Klien sandbox harus menolak jika belum dikonfigurasi."""
    with pytest.raises(RuntimeError, match="not configured"):
        post_transaction_credentials(valid_payload(), cfg=None)


def test_load_config_returns_none_when_env_missing(monkeypatch):
    for k in ("VISA_SRC_API_KEY", "VISA_SRC_SHARED_SECRET",
              "VISA_SRC_CERT_PATH", "VISA_SRC_KEY_PATH"):
        monkeypatch.delenv(k, raising=False)
    assert load_client_config_from_env() is None


def test_swagger_placeholder_payload_is_rejected():
    """Payload persis dari Swagger harus ditolak dengan banyak error."""
    bad = {
      "dpaData": {"dpaUri": "string", "dpaPresentationName": "string"},
      "srcDpaId": "string", "serviceId": "CARD_ON_FILE", "srcClientId": "string",
      "assuranceData": {"eci": "05", "verificationData": [{
        "methodResults": {"threeDsData": {"dsTransId":"string","acsTransId":"string","transStatus":"Y"}},
        "additionalData":"string","verificationType":"CARDHOLDER","verificationEntity":"01",
        "verificationEvents":["01"],"verificationMethod":"01",
        "verificationResults":"01","verificationTimestamp":"string"}]},
      "srcCorrelationId":"string","srcDigitalCardId":"string","srciTransactionId":"string",
      "dpaTransactionOptions":{
        "dpaLocale":"strin","acquirerBin":"string","merchantName":"string",
        "paymentOptions":[{"dynamicDataType":"CARD_APPLICATION_CRYPTOGRAM_SHORT_FORM"}],
        "merchantOrderId":"string",
        "transactionAmount":{"transactionAmount":0,"transactionCurrencyCode":"str"},
        "acquirerMerchantId":"string","merchantCountryCode":"st","merchantCategoryCode":"stri",
        "consumerNameRequested":True,"consumerPhoneNumberRequested":True,
        "consumerEmailAddressRequested":True,"consumerNationalIdentifierRequested":True,
        "dpaAcceptedBillingCountries":["st"],
        "authenticationPreferences":{"payloadRequested":"AUTHENTICATED","authenticationMethods":[]},
      },
      "encryptedBillingAddress":"string","initializationSessionId":"string",
      "payloadTypeIndicatorPayload":"FULL","payloadTypeIndicatorCheckout":"FULL",
    }
    with pytest.raises(ValidationError) as exc:
        SrcTransactionCredentialsRequest.model_validate(bad)
    assert len(exc.value.errors()) >= 6
