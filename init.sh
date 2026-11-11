
#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python_dir="${repo_root}/code/Python"

run_python() {
    python "${python_dir}/$1" "${@:2}"
}

if [[ $# -eq 0 ]]; then
    run_python "shp_wrangling.py"
    run_python "generate_csv.py"
    run_python "aggregate_radiance.py"
    run_python "generate_centroid.py"
    run_python "prepare_training_dataset.py"
else
    run_python "$@"
fi
