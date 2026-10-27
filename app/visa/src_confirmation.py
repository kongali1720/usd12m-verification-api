"""Visa SRC transaction-credentials payload validator + sandbox client.

PENTING:
- Endpoint POST /src/v1/transaction-credentials MEMBUAT kredensial pembayaran
  (menagih kartu), BUKAN memverifikasi dana.
- Modul ini default-nya hanya memvalidasi payload secara lokal.
- Klien sandbox hanya aktif jika env VISA_SRC_* lengkap.
- Jangan pernah kirim data kartu asli atau dari dokumen tak terverifikasi.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

log = logging.getLogger(__name__)

# Batas wajar untuk transaksi e-commerce. SRC untuk retail, bukan transfer besar.
MAX_REASONABLE_AMOUNT = Decimal("1000000")


class DpaData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dpaUri: str = Field(min_length=1)
    dpaPresentationName: str = Field(min_length=1)

    @field_validator("dpaUri")
    @classmethod
    def _uri_scheme(cls, v: str) -> str:
        if not v.startswith(("https://", "app://")):
            raise ValueError("dpaUri must start with https:// or app://")
        return v


class ThreeDsData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dsTransId: str = Field(min_length=1)
    acsTransId: str = Field(min_length=1)
    transStatus: Literal["Y", "A", "N", "U", "C", "R"]


class MethodResults(BaseModel):
    model_config = ConfigDict(extra="forbid")
    threeDsData: ThreeDsData


class VerificationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    methodResults: MethodResults
    additionalData: str = Field(default="", max_length=512)
    verificationType: str = Field(min_length=1, max_length=40)
    verificationEntity: str = Field(min_length=1, max_length=40)
    verificationEvents: list[str] = Field(default_factory=list)
    verificationMethod: str = Field(min_length=1, max_length=40)
    verificationResults: str = Field(min_length=1, max_length=40)
    verificationTimestamp: str = Field(min_length=1, max_length=40)


class AssuranceData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    eci: str
    verificationData: list[VerificationItem] = Field(min_length=1, max_length=5)

    @field_validator("eci")
    @classmethod
    def _eci(cls, v: str) -> str:
        if not re.fullmatch(r"\d{2}", v):
            raise ValueError("eci must be a 2-digit string, e.g. '05'")
        return v


class PaymentOption(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dynamicDataType: str = Field(min_length=1, max_length=80)


class TransactionAmount(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transactionAmount: Decimal
    transactionCurrencyCode: str

    @field_validator("transactionAmount")
    @classmethod
    def _amount_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("transactionAmount must be > 0")
        if v > MAX_REASONABLE_AMOUNT:
            raise ValueError(
                f"transactionAmount {v} exceeds sane e-commerce limit "
                f"({MAX_REASONABLE_AMOUNT}); SRC is for retail payments"
            )
        return v

    @field_validator("transactionCurrencyCode")
    @classmethod
    def _iso4217(cls, v: str) -> str:
        if not re.fullmatch(r"[A-Z]{3}", v or ""):
            raise ValueError("transactionCurrencyCode must be ISO 4217 (3 uppercase letters)")
        return v


class DpaTransactionOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    acquirerBin: str
    merchantName: str = Field(min_length=1, max_length=120)
    merchantCountryCode: str
    merchantCategoryCode: str = Field(default="5999", min_length=4, max_length=4)
    merchantOrderId: str = Field(default="", max_length=120)
    paymentOptions: list[PaymentOption] = Field(default_factory=list)
    transactionAmount: TransactionAmount
    dpaLocale: str | None = None
    acquirerMerchantId: str | None = None

    @field_validator("acquirerBin")
    @classmethod
    def _acquirer_bin(cls, v: str) -> str:
        if not re.fullmatch(r"\d{6,11}", v or ""):
            raise ValueError("acquirerBin must be 6-11 digits")
        return v

    @field_validator("merchantCountryCode")
    @classmethod
    def _cc(cls, v: str) -> str:
        if not re.fullmatch(r"[A-Z]{2}", v or ""):
            raise ValueError("merchantCountryCode must be ISO 3166 alpha-2")
        return v


class SrcTransactionCredentialsRequest(BaseModel):
    """Model Pydantic untuk payload POST /src/v1/transaction-credentials.

    Hanya berisi field yang relevan untuk skenario CARD_ON_FILE.
    Field 'string'/'strin'/'st' dari contoh Swagger akan ditolak karena
    melanggar min_length atau validasi pola.
    """
    model_config = ConfigDict(extra="forbid")

    dpaData: DpaData
    srcDpaId: str = Field(min_length=1)
    serviceId: Literal["CARD_ON_FILE"]
    srcClientId: str = Field(min_length=1)
    assuranceData: AssuranceData
    srcCorrelationId: str = Field(min_length=1)
    srcDigitalCardId: str = Field(min_length=1)
    srciTransactionId: str = Field(min_length=1)
    dpaTransactionOptions: DpaTransactionOptions

    # Field opsional (tidak wajib di skenario CARD_ON_FILE minimal)
    encryptedBillingAddress: str | None = None
    initializationSessionId: str | None = None
    payloadTypeIndicatorPayload: Literal["FULL", "PARTIAL"] | None = None
    payloadTypeIndicatorCheckout: Literal["FULL", "PARTIAL"] | None = None

    @model_validator(mode="after")
    def _reject_multi_million(self):
        amt = self.dpaTransactionOptions.transactionAmount.transactionAmount
        if amt >= Decimal("1000000"):
            raise ValueError(
                "amounts >= 1,000,000 are outside SRC retail scope; "
                "SRC does not transfer or verify funds"
            )
        return self


# ---------------------------------------------------------------------------
# Sandbox client (aktif hanya jika env VISA_SRC_* lengkap)
# ---------------------------------------------------------------------------

SANDBOX_HOST = "sandbox.api.visa.com"
SRC_PATH = "/src/v1/transaction-credentials"


@dataclass
class SrcClientConfig:
    api_key: str
    shared_secret: str
    cert_path: str
    key_path: str
    base_url: str = f"https://{SANDBOX_HOST}"


def load_client_config_from_env() -> SrcClientConfig | None:
    api_key = os.environ.get("VISA_SRC_API_KEY")
    shared = os.environ.get("VISA_SRC_SHARED_SECRET")
    cert = os.environ.get("VISA_SRC_CERT_PATH")
    key = os.environ.get("VISA_SRC_KEY_PATH")
    base = os.environ.get("VISA_SRC_BASE_URL", f"https://{SANDBOX_HOST}")
    if not all([api_key, shared, cert, key]):
        log.warning(
            "Visa SRC sandbox client disabled: set VISA_SRC_API_KEY, "
            "VISA_SRC_SHARED_SECRET, VISA_SRC_CERT_PATH, VISA_SRC_KEY_PATH"
        )
        return None
    return SrcClientConfig(api_key=api_key, shared_secret=shared,
                           cert_path=cert, key_path=key, base_url=base)


def post_transaction_credentials(payload: dict, cfg: SrcClientConfig | None = None,
                                 timeout: float = 15.0) -> dict:
    """Kirim ke SRC sandbox. Validasi dulu via Pydantic. Butuh env VISA_SRC_*."""
    if cfg is None:
        raise RuntimeError("Visa SRC client not configured (env VISA_SRC_*).")
    SrcTransactionCredentialsRequest.model_validate(payload)  # raise on invalid

    import json
    import requests
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-api-key": cfg.api_key,
        # TODO: x-pay-token wajib untuk sandbox Visa. Lihat dokumentasi proyek.
    }
    resp = requests.post(
        cfg.base_url + SRC_PATH,
        headers=headers,
        data=json.dumps(payload),
        cert=(cfg.cert_path, cfg.key_path),
        timeout=timeout,
    )
    if resp.status_code >= 400:
        log.error("SRC sandbox error %s: %s", resp.status_code, resp.text[:500])
    resp.raise_for_status()
    return resp.json()
