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

if [[ $# -eq 0 ]]; then
    # Run all scripts in order
    run_python "shp_wrangling.py"
    run_python "generate_csv.py"
    run_python "aggregate_radiance.py"
    run_python "prepare_training_dataset.py"
else
    # Run only the specified Python script
    run_python "$@"
fi
