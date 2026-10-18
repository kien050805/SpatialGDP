#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: ./run-python.sh <script.py> [arguments ...]" >&2
    exit 2
fi

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
script_path="${repo_root}/code/Python/$1"
shift

if [[ ! -f "$script_path" ]]; then
    echo "Python script not found: ${script_path}" >&2
    exit 1
fi

exec python "$script_path" "$@"
