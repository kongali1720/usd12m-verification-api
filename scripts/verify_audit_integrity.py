import hashlib
import hmac
import json
import sys
from pathlib import Path

AUDIT_FILE = Path("data/audit.jsonl")


def verify_audit(path: Path) -> bool:
    if not path.is_file():
        print(f"FAIL: audit file not found: {path}")
        return False

    lines = path.read_text(encoding="utf-8").splitlines()

    if not lines:
        print("FAIL: audit file is empty")
        return False

    previous_hash = ""
    errors = []

    for line_number, line in enumerate(lines, start=1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"Line {line_number}: invalid JSON")
            continue

        if not isinstance(record, dict):
            errors.append(f"Line {line_number}: record is not an object")
            continue

        stored_hash = record.get("event_hash")
        linked_hash = record.get("previous_hash")

        if not isinstance(stored_hash, str) or not stored_hash:
            errors.append(f"Line {line_number}: missing event_hash")
            continue

        if linked_hash != previous_hash:
            errors.append(
                f"Line {line_number}: previous_hash does not match "
                "the preceding valid record"
            )

        unhashed_record = {
            key: value
            for key, value in record.items()
            if key != "event_hash"
        }

        canonical = json.dumps(
            unhashed_record,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        calculated_hash = hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()

        if not hmac.compare_digest(stored_hash, calculated_hash):
            errors.append(f"Line {line_number}: event_hash mismatch")

        previous_hash = stored_hash

    if errors:
        print("FAIL: audit integrity check detected problems")
        for error in errors:
            print(f"- {error}")
        return False

    print("PASS: all audit records parsed")
    print(f"PASS: {len(lines)} record(s) checked")
    print("PASS: event hashes and previous_hash links match")
    print("NOTE: this checks internal consistency, not authenticity")
    return True


if __name__ == "__main__":
    sys.exit(0 if verify_audit(AUDIT_FILE) else 1)
