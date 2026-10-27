from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
import json
import hashlib
import uuid
import os
import secrets
import re

from fastapi import FastAPI, Header, HTTPException
from app.visa.enrollment import enrollment_status
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

CASE_FILE = DATA_DIR / "case.json"
AUDIT_FILE = DATA_DIR / "audit.jsonl"
LOCK = RLock()

API_KEY = os.environ.get("VERIFICATION_API_KEY")
if not API_KEY or len(API_KEY) < 32:
    raise RuntimeError(
        "Set VERIFICATION_API_KEY to a random secret of at least 32 characters"
    )

app = FastAPI(
    title="USD 12M Verification API",
    version="0.1.0",
    description=(
        "Local evidence tracking only. "
        "This API does not verify bank balances or initiate transfers."
    ),
    docs_url=None,
    redoc_url=None,
)

INITIAL_CASE = {
    "case_id": "ED-12M-001",
    "claimed_amount": "12000000.11",
    "currency": "USD",
    "claimed_source": "UNIDENTIFIED",
    "beneficiary_bank": "Bank Mandiri (claimed)",
    "verification_status": "UNVERIFIED",
    "bank_confirmed": False,
    "available_funds_confirmed": False,
    "evidence": {
        "originator_identity": False,
        "originating_institution": False,
        "official_payment_confirmation": False,
        "traceable_transaction_reference": False,
        "receiving_bank_confirmation": False,
        "available_balance_confirmation": False,
    },
}


def now():
    return datetime.now(timezone.utc).isoformat()


def audit(event, details=None, actor_id="system"):
    with LOCK:
        previous_hash = ""
        if AUDIT_FILE.exists():
            lines = AUDIT_FILE.read_text(encoding="utf-8").splitlines()
            if lines:
                try:
                    previous_hash = json.loads(lines[-1]).get("event_hash", "")
                except (json.JSONDecodeError, AttributeError):
                    previous_hash = "LEGACY_OR_INVALID"

        record = {
            "event_id": str(uuid.uuid4()),
            "timestamp": now(),
            "actor_id": actor_id,
            "event": event,
            "previous_hash": previous_hash,
            "details": details or {},
        }
        canonical = json.dumps(
            record, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        record["event_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        with AUDIT_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_case():
    if not CASE_FILE.exists():
        CASE_FILE.write_text(
            json.dumps(INITIAL_CASE, indent=2),
            encoding="utf-8",
        )
    return json.loads(CASE_FILE.read_text(encoding="utf-8"))


def save_case(case):
    with LOCK:
        CASE_FILE.write_text(
            json.dumps(case, indent=2),
            encoding="utf-8",
        )


def require_key(x_api_key):
    if not x_api_key or not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API key")


class EvidenceUpdate(BaseModel):
    evidence_type: str = Field(min_length=1, max_length=80)
    received: bool
    note: str = Field(default="", max_length=500)


ALLOWED_EVIDENCE = {
    "originator_identity",
    "originating_institution",
    "official_payment_confirmation",
    "traceable_transaction_reference",
    "receiving_bank_confirmation",
    "available_balance_confirmation",
}


@app.get("/health")
def health():
    return {
        "service": "usd12m-verification-api",
        "status": "running",
        "mode": "local-evidence-tracking",
        "bank_connection": False,
        "timestamp": now(),
    }


@app.get("/v1/case")
def get_case(x_api_key: str | None = Header(default=None)):
    require_key(x_api_key)
    return load_case()


@app.post("/v1/evidence")
def update_evidence(
    update: EvidenceUpdate,
    x_api_key: str | None = Header(default=None),
    x_actor_id: str | None = Header(default=None),
):
    require_key(x_api_key)

    if not x_actor_id or not re.fullmatch(r"[A-Za-z0-9_.@-]{3,100}", x_actor_id):
        raise HTTPException(
            status_code=400,
            detail="A valid X-Actor-ID header is required",
        )

    if update.evidence_type not in ALLOWED_EVIDENCE:
        raise HTTPException(
            status_code=400,
            detail="Unsupported evidence type",
        )

    # Keep free-text notes out of the audit log to reduce accidental
    # recording of personal, banking, or authentication information.
    with LOCK:
        case = load_case()
        case["evidence"][update.evidence_type] = update.received
        case["verification_status"] = "UNVERIFIED"
        case["bank_confirmed"] = False
        case["available_funds_confirmed"] = False
        save_case(case)

        audit(
            "evidence_recorded",
            {
                "evidence_type": update.evidence_type,
                "received": update.received,
                "note_recorded": bool(update.note.strip()),
                "bank_confirmed": False,
                "available_funds_confirmed": False,
            },
            actor_id=x_actor_id,
        )

    return {
        "recorded": True,
        "verification_status": "UNVERIFIED",
        "bank_confirmed": False,
        "available_funds_confirmed": False,
        "message": "Evidence recorded; authenticity and funds remain unverified.",
    }


@app.get("/v1/readiness")
def readiness(x_api_key: str | None = Header(default=None)):
    require_key(x_api_key)
    case = load_case()
    evidence = case["evidence"]

    missing = [
        item for item, received in evidence.items() if not received
    ]

    return {
        "case_id": case["case_id"],
        "evidence_items_received": len(evidence) - len(missing),
        "evidence_items_required": len(evidence),
        "missing_evidence": missing,
        "verification_status": "UNVERIFIED",
        "funds_available": False,
        "note": (
            "Completeness does not prove authenticity, payment, "
            "or availability of funds."
        ),
    }


@app.get("/v1/audit")
def get_audit(x_api_key: str | None = Header(default=None)):
    require_key(x_api_key)

    if not AUDIT_FILE.exists():
        return {"events": []}

    events = []
    for line in AUDIT_FILE.read_text(encoding="utf-8").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return {"events": events[-100:]}


load_case()


@app.get("/v1/visa/status")
def visa_status(x_api_key: str | None = Header(default=None)):
    require_key(x_api_key)
    return enrollment_status()
