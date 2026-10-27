from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DeviceJWK(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kty: Literal["EC"]
    crv: Literal["P-256"]
    x: str = Field(min_length=1)
    y: str = Field(min_length=1)
    use: Literal["sig", "enc"]
    keyFunction: Literal["AUTHENTICITY", "KEY_AGREEMENT"]


class VisaJWK(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kty: str = Field(min_length=1)
    keyFunction: Literal["AUTHENTICITY", "KEY_AGREEMENT"]
    kid: str | None = None


class DeviceEnrollmentDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deviceAlias: str = Field(min_length=1, max_length=50)
    deviceKeys: list[DeviceJWK] = Field(min_length=1, max_length=5)
    deviceSoftware: dict
    visaKeys: list[VisaJWK] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def validate_enrollment_rules(self):
        if not any(
            key.keyFunction == "AUTHENTICITY"
            for key in self.deviceKeys
        ):
            raise ValueError(
                "At least one device AUTHENTICITY key is required"
            )

        functions = {key.keyFunction for key in self.visaKeys}
        if functions != {"AUTHENTICITY", "KEY_AGREEMENT"}:
            raise ValueError(
                "visaKeys must contain AUTHENTICITY and KEY_AGREEMENT"
            )

        return self


def enrollment_status():
    return {
        "module": "visa-terminal-enrollment",
        "mode": "draft-only",
        "live_requests_enabled": False,
        "endpoint_configured": False,
        "visa_credentials_configured": False,
        "enrollment_submitted": False,
        "note": (
            "Draft validation only. No Visa request is sent. "
            "Use the exact endpoint, authentication instructions, "
            "and Visa-issued certificates from the authorized project."
        ),
    }
