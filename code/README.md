# Code Folder

Python scripts are in `Python/`; the R project is in `R/`.

## Quick Python command

From the repository root, run a Python script without changing directories:

```bash
./run-python.sh extract_viirs_pixels.py
```

Pass script arguments after the filename as usual:

```bash
./run-python.sh plot_viirs_pixels.py --help
```

## VIIRS Workflow

1. Download the VNL `.tif` files from EOG and place them in `data/`.

2. From the repository root, generate a Vietnam-wide pixel-radiance CSV for
   every `.tif` in `data/viirs_raw`:

   ```bash
   ./run-python.sh generate_csv.py
   ```

   The files are named `vnm_<year>_pixel_radiance.csv` and saved under
   `data/viirs_pixel_radiance/`. The generator uses the formatted national
   boundary at `data/shp_boundaries/level0/vnm_level0.shp` and calls
   `extract_viirs_pixels.py` to extract each raster.

   The same command also generates one CSV per province from the
   formatted boundaries in `data/shp_boundaries/level1/vnm_level1.shp`, saved under
   `data/viirs_pixel_radiance_province/<year>/`, named
   `<province>_viirs_<year>_pixel_radiance.csv`.

3. Generate national and provincial maps with:

   ```bash
   python code/Python/plot_viirs_pixels.py
   ```

   Figures are saved under `figures/`. Use `--raster`, `--csv`, or the output
   options to select different input and output files.

4. Aggregate pixel radiance by province:

   ```bash
   python code/Python/aggregate_radiance.py
   ```

   The script assigns pixel centers to the provincial polygons in
   `data/vnm_admin_boundaries.shp/vnm_admin1.shp` and writes each polygon's
   mean radiance and assigned pixel count to
   `data/viiirs_average_radiance/vietnam_2025_mean_radiance_by_province.csv`.
   It matches the boundary file's `adm1_name` values to `Provincies` in
   `data/vnm_population.csv`, so the output's `province` column uses the
   population CSV's names. Use `--population` to select a different labels file.
