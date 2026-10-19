#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

run_python() {
    local script_path="${repo_root}/code/Python/$1"
    shift

    if [[ ! -f "$script_path" ]]; then
        echo "Python script not found: ${script_path}" >&2
        exit 1
    fi

    python "$script_path" "$@"
}

run_python "shp_wrangling.py"
run_python "generate_csv.py"
run_python "aggregate_radiance.py"