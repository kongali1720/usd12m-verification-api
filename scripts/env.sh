#!/usr/bin/env bash
# Load .env into current shell. Usage: source scripts/env.sh
set -a
. "$(dirname "${BASH_SOURCE[0]}")/../.env"
set +a
echo "loaded key (len=${#VERIFICATION_API_KEY}, prefix=${VERIFICATION_API_KEY:0:8})"
