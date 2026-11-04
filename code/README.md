# Code Folder

Python scripts are in `Python/`; the R project is in `R/`.

## Quick Python command

To initialize the repo, start with: 

```bash
./init.sh
```

This will take about 15-20 minues on OSC.

From the repository root, run a Python script without changing directories:

```bash
./init.sh plot_regions.py
```

Pass script arguments after the filename as usual:

```bash
./init.sh plot_pixels.py --help
```

## Workflow

1. Download the VNL `.tif` files from EOG and place them in `data/_viirs_raw`. Other `_vnm` data have been prepared. 

2. After initialization, the following directories are generated:

- `shp_boundaries`: Processed administrative boundary shapefiles organized into four levels (Level 0 to Level 3).

- `viirs_pixel_radiance`: VIIRS nighttime-light radiance pixels extracted for each administrative level.

- `average_radiance`: Average radiance values calculated for each administrative unit at each level.

- `training_data`: Prepared datasets containing the features used for model training and prediction.

3. Models and predictions are implemented in R and documented in `.Rmd` files stored in `R/`. Corresponding `.html` files provide explanations and code implementations. Running these R Markdown files generates outputs saved in their respective locations under `data/predicted_data/` and `figures/`.

4. Generate map with:

   ```bash
   ./init.sh plot_pixels.py --level<level> --province"<name>" --year<year>
   ```
The latest available year is used by default. Use `--level 0`, `--level 1`, or `--level 2` to choose national, provincial, or level-2 boundaries. Levels 0 and 1 use the national level-0 pixel CSV; level 2 uses the level-1 province pixel CSVs (or one province with `--province "<name>"`). This keeps the plotted pixels aligned with the boundary scope without reusing pixels clipped to each level-2 outline. `--year` selects a different year and `--output` overrides the generated figure path. Pixels are read from `data/viirs_pixel_radiance/` and boundaries from `data/shp_boundaries/`.

   ```bash
   ./init.sh plot_regions.py --csv <csv_path> --metric <metric> --level <level> --province "<name>" --year <year>
   ```
The input CSV must contain the administrative unit names and the numeric indicator or prediction to visualize. Use `--csv` to specify the input file, `--metric` to select the column to plot, and `--level 1` or `--level 2` to choose provincial or commune boundaries. For level 2, optionally use `--province "<name>"` to plot a single province. Use `--year` to filter by year and `--output` to specify the output figure path. The generated map is saved in `figures/` by default.