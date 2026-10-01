# Code Folder

Python scripts are in `Python/`; the R project is in `R/`.

## VIIRS Workflow

1. Download the VNL `.tif` files from EOG and place them in `data/`.

2. From the repository root, extract radiance with:

   ```bash
   python code/Python/extract_viirs_pixels.py
   ```

   The default output is saved under `data/viirs_pixel_radiance/`.

3. Generate national and provincial maps with:

   ```bash
   python code/Python/plot_viirs_pixels.py
   ```

   Figures are saved under `figures/`. Use `--raster`, `--csv`, or the output
   options to select different input and output files.

