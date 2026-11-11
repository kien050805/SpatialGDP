#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$repo_root"

model="${1:-}"

case "$model" in
    linear_model)
        csv="data/predicted_data/linear_model/linear_model_level2_predictions.csv"
        output_dir="figures/linear_model"
        ;;

    ridge_model)
        csv="data/predicted_data/ridge_model/ridge_model_level2_predictions.csv"
        output_dir="figures/ridge_model"
        ;;

    *)
        echo "Usage: ./plot.sh {linear_model|ridge_model}" >&2
        exit 1
        ;;
esac

# Create the output directory if it does not exist.
mkdir -p "$output_dir"

# Plot nationwide level-2 predictions.
python code/Python/plot_regions.py \
    --csv "$csv" \
    --metric additive_predictions \
    --level 2 \
    --year 2025 \
    --output "$output_dir/level2_${model}_additive_predictions_grdp_per_capita.png"

python code/Python/plot_regions.py \
    --csv "$csv" \
    --metric scaled_predictions \
    --level 2 \
    --year 2025 \
    --output "$output_dir/level2_${model}_scaled_predictions_grdp_per_capita.png"

# Plot Ha Noi.
python code/Python/plot_regions.py \
    --csv "$csv" \
    --metric additive_predictions \
    --level 2 \
    --province "Ha Noi" \
    --year 2025 \
    --output "$output_dir/ha_noi_level2_${model}_additive_predictions_grdp_per_capita.png"

# Plot Lam Dong.
python code/Python/plot_regions.py \
    --csv "$csv" \
    --metric scaled_predictions \
    --level 2 \
    --province "Lam Dong" \
    --year 2025 \
    --output "$output_dir/lam_dong_level2_${model}_scaled_predictions_grdp_per_capita.png"

# Plot Ho Chi Minh City.
python code/Python/plot_regions.py \
    --csv "$csv" \
    --metric scaled_predictions \
    --level 2 \
    --province "Ho Chi Minh city" \
    --year 2025 \
    --output "$output_dir/ho_chi_minh_city_level2_${model}_scaled_predictions_grdp_per_capita.png"