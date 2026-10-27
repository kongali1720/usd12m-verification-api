 <p align="center">
  <img src="https://github.com/kongali1720/KongWallet-Payment-Gateway-API/blob/main/kop_surat.jpg" width="100%" alt="Kongali Project Letterhead">
</p>

<h1 align="center">USD 12M Verification API</h1>

<p align="center">
  <strong>Local Evidence Tracking • Audit Integrity • Verification Readiness</strong>
</p>

<p align="center">
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  </a>
  <a href="https://fastapi.tiangolo.com/">
    <img src="https://img.shields.io/badge/FastAPI-API-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  </a>
  <a href="https://pytest.org/">
    <img src="https://img.shields.io/badge/Tests-19%20Passed-success?style=for-the-badge&logo=pytest&logoColor=white" alt="Tests">
  </a>
  <img src="https://img.shields.io/badge/Mode-Local%20Evidence%20Tracking-blue?style=for-the-badge" alt="Local evidence tracking">
  <img src="https://img.shields.io/badge/Bank%20Connection-Not%20Configured-lightgrey?style=for-the-badge" alt="Bank connection not configured">
  <img src="https://img.shields.io/badge/Verification-UNVERIFIED-orange?style=for-the-badge" alt="Verification unverified">
</p>

<p align="center">
  <a href="#overview">Overview</a> •
  <a href="#features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#api-endpoints">API Endpoints</a> •
  <a href="#testing">Testing</a> •
  <a href="#security">Security</a>
</p>

---

## Overview

**USD 12M Verification API** is a Python-based FastAPI application designed to track verification evidence, maintain an audit trail, and report evidence completeness for a financial verification case.

The application provides a local framework for organizing evidence related to an asserted USD-denominated transaction.

It does **not** independently establish the authenticity of submitted documents, confirm bank balances, initiate payments, or prove that funds have been received.

### Current operating mode

| Component | Status |
|---|---|
| FastAPI application | Operational locally |
| API-key authentication | Implemented |
| Evidence tracking | Implemented |
| SHA-256 audit hash chain | Implemented |
| Local confirmation payload validation | Implemented |
| Audit integrity checker | Implemented |
| Official bank API connection | Not configured |
| Live Visa requests | Disabled |
| Funds availability | Unverified |

> **Important:** A successful API response, complete evidence checklist, valid hash chain, payment-card confirmation, or successful test does not establish that a bank transfer has settled or that funds are available.

## Features

- **Evidence tracking:** Record whether required evidence items have been received.
- **Verification readiness:** Identify missing evidence without treating completeness as proof of authenticity.
- **API-key authentication:** Protect verification and audit endpoints.
- **Audit trail:** Record event timestamps, actor identifiers, event details, and SHA-256 event hashes.
- **Hash-chain consistency checking:** Inspect stored event hashes and their `previous_hash` links.
- **Local confirmation validation:** Validate supported Visa SRC-style confirmation payload fields without making network requests.
- **Regression tests:** Test local validation behavior and related safeguards.
- **Privacy-conscious audit details:** Free-text evidence notes are not copied into audit event details.

## Architecture

```text
Client / Operator
       |
       v
FastAPI Application
       |
       +---- API Key Authentication
       |
       +---- Case Management
       |        |
       |        +---- data/case.json
       |
       +---- Evidence Tracking
       |
       +---- Audit Logging
       |        |
       |        +---- data/audit.jsonl
       |
       +---- Local Confirmation Validator
       |
       +---- Readiness and Visa Status
```

The application currently operates in local evidence-tracking mode. External banking and Visa integrations require separate, authorized configuration and verification.

## API Endpoints

All endpoints except `/health` require a valid `x-api-key` header.

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Check application health |
| `GET` | `/v1/case` | Retrieve the current case and evidence flags |
| `POST` | `/v1/evidence` | Record an evidence item |
| `GET` | `/v1/readiness` | Inspect evidence completeness and verification status |
| `GET` | `/v1/audit` | Retrieve audit events |
| `GET` | `/v1/visa/status` | Inspect Visa module configuration status |

Interactive API documentation is available at `/docs` while the local server is running.

### Health check

```bash
curl -sS http://127.0.0.1:8000/health
```

The health endpoint reports the service status and operating mode. It is not a bank connectivity test.

### Retrieve readiness

```bash
curl -sS \
  -H "x-api-key: YOUR_LOCAL_API_KEY" \
  http://127.0.0.1:8000/v1/readiness
```

Use the actual locally configured key. Never commit API keys or place real credentials in documentation.

The readiness response identifies missing evidence and maintains the distinction between evidence completeness and verified funds availability.

### Record evidence

The evidence endpoint accepts an evidence type, a Boolean `received` flag, and an optional note.

```bash
curl -X POST \
  http://127.0.0.1:8000/v1/evidence \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_LOCAL_API_KEY" \
  -H "x-actor-id: local-operator" \
  -d '{
    "evidence_type": "originating_institution",
    "received": false,
    "note": "Awaiting independently verifiable documentation"
  }'
```

This is an example of a local evidence-tracking operation. It does not submit information to a bank or validate a document's authenticity.

Only mark evidence as received when the corresponding material has actually been obtained. A received flag alone is not proof that the material is genuine.

## Installation

### Requirements

- Python 3.10 or later
- `pip`
- Git
- WSL 2 with Ubuntu or another compatible Linux environment

### 1. Clone the repository

```bash
git clone https://github.com/kongali1720/usd12m-verification-api.git
cd usd12m-verification-api
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
```

### 3. Install dependencies

If the repository contains `requirements.txt`:

```bash
python -m pip install -r requirements.txt
```

If it does not, install the dependencies specified by the project before starting the application. Do not assume that a fresh clone contains an already-configured environment.

### 4. Configure the API key

Create a local `.env` file using the configuration expected by the application.

Generate a random secret locally:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Add the generated value to `.env`:

```dotenv
VERIFICATION_API_KEY=REPLACE_WITH_YOUR_GENERATED_SECRET
```

Do not use the example placeholder as a real secret. Keep `.env` out of Git and never share the key in chat, screenshots, logs, or public documentation.

For a shell-based setup, load the environment before starting the application:

```bash
set -a
source .env
set +a
```

### 5. Start the application

```bash
python -m uvicorn app.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --log-level info
```

The application should be available at:

- Health: `http://127.0.0.1:8000/health`
- API documentation: `http://127.0.0.1:8000/docs`

Binding to `127.0.0.1` keeps the development server on the local machine. Do not expose this development configuration publicly without an appropriate deployment and security review.

## Testing

Run the test suite from the repository root:

```bash
python -m pytest -q
```

Run the local confirmation validator tests separately:

```bash
python -m pytest -q tests/test_confirmation_validator.py
```

The audit integrity checker can be executed with:

```bash
python scripts/verify_audit_integrity.py
```

A successful audit check means that the inspected records' hashes and chain links are internally consistent with the file being checked.

It does not prove who created the records, whether the underlying documents are authentic, or whether the audit file was never replaced or altered as a whole.

The current development checkpoint passed 19 automated tests. The badge above is a static project-status badge and does not represent a continuously running CI workflow.

## Audit Integrity

Audit events include:

- Event identifier
- Timestamp
- Actor identifier
- Event type
- Previous event hash
- Event details
- SHA-256 event hash

The audit verifier recalculates hashes and checks links between records.

For stronger production-grade audit guarantees, consider append-only external storage, restricted filesystem permissions, signed audit checkpoints, trusted timestamps, backups, and independent audit-log monitoring.

## Visa Confirmation Validation

The local confirmation validator checks supported fields in a confirmation payload and rejects invalid input according to its implemented rules.

Its current behavior is local-only:

- No Visa network request is made.
- No bank request is made.
- No payment is initiated.
- No funds availability is confirmed.
- The case remains unverified.

The Visa module currently reports draft-only operation, with live requests disabled and official endpoint and credentials not configured.

Any future integration must use official project documentation, authorized credentials, the correct environment, and the authentication method specified by the provider.

## Security

This project handles financial-verification metadata and should be treated accordingly.

- Never commit `.env`, private keys, API tokens, certificates, or banking credentials.
- Keep the repository private when it contains internal operational details or sensitive case metadata.
- Do not place account numbers, identity documents, or personal banking information in free-text notes.
- Use synthetic data for development and automated tests.
- Restrict access to case files and audit logs.
- Review authentication, authorization, rate limiting, logging, backup, and deployment configuration before production use.
- Verify financial claims through independently obtained official bank evidence and established bank channels.

### Scope limitations

This application is not a bank, payment processor, Visa authorization service, SWIFT gateway, or settlement system.

It does not independently verify:

- The existence or ownership of a bank account
- The authenticity of payment confirmations
- A SWIFT transfer or settlement
- A receiving bank's ledger balance
- Funds availability or withdrawal capability

A claimed amount recorded in the case must not be represented as received or available solely because the API accepts the record.

## Project Structure

```text
usd12m-verification-api/
├── app/
│   ├── main.py
│   └── visa/
│       ├── src_confirmation.py
│       └── confirmation_validator.py
├── scripts/
│   └── verify_audit_integrity.py
├── tests/
│   └── test_confirmation_validator.py
├── data/
│   ├── case.json
│   └── audit.jsonl
├── .env
└── README.md
```

The exact files present may vary by branch and local configuration. Keep `.env` and sensitive runtime data out of version control. Use the repository's `.gitignore` to exclude local secrets and data files.

## Roadmap

- [x] Local evidence tracking
- [x] API-key authentication
- [x] SHA-256 audit event hashing
- [x] Local confirmation payload validator
- [x] Audit integrity checker
- [x] Regression tests for local validation
- [ ] Continuous integration workflow
- [ ] Additional audit tampering tests
- [ ] Deployment security review
- [ ] Authorized provider integration, subject to official documentation and approval

## Contributing

Contributions should preserve the distinction between recorded evidence, verified evidence, bank confirmation, and funds availability.

Before submitting changes:

```bash
python -m pytest -q
python scripts/verify_audit_integrity.py
git diff --check
```

Do not include secrets, personal banking records, or unredacted financial documents in pull requests or test fixtures.

## License

No license has been specified for this repository yet. Unless a license is added, do not assume that the project is available for unrestricted reuse or redistribution.

---

## ☕ Support the Project

If this project has helped your research, learning, or security operations, consider supporting its continued development.

<div align="center">

<a href="https://www.paypal.com/paypalme/bungtempong99">
  <img src="https://img.shields.io/badge/☕-Support_Development-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=000000" alt="Support Development">
</a>

</div>

---

<p align="center">
  <sub>Built for transparent evidence tracking, local verification workflows, and responsible financial-system development.</sub>
</p>
