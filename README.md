# Code for the master thesis "The potential role of high temperature aquifer thermal energy storage in the Dutch energy"

This repository is a fork of [PyPSA-Eur](https://github.com/PyPSA/pypsa-eur), extended to integrate high-temperature aquifer thermal energy storage (HT-ATES) in the Netherlands. This repository contains the code and report accompanying the master thesis "The potential role of high temperature aquifer thermal energy storage in the Dutch energy".

## What's modified

Compared to the original PyPSA-Eur repository (updated last on 28 May 2025), this version includes:

- **New data**:
  -  `data/TNO-HT-ATES/` with HT-ATES data on the potential locations and energy production in the Netherlands.
  -  `data/dh_areas.gpkg`, which is also included in the newer PyPSA-Eur v2025.07.0
  -  `data/custom_powerplants.csv`, to account for a bug that mislabeled the nuclear power plant in Borssele as a coal power plant.
  -  `resources/costs_2030.csv` with HT-ATES technology and cost data.
- **Custom config file**: `config_HT-ATES.yaml` that is used to model different scenarios with and without HT-ATES.
- **New script**: `scripts/determine_ht_ates_availability.py` where the potential energy production of HT-ATES is calculated for each cluster.
- **Modified scripts and rules**:
  - `scripts/prepare_sector_network.py` to add HT-ATES components.
  - `scripts/solve_network.py` to add HT-ATES to the energy-to-power ratio constraint.
  - `scripts/build_geothermal_heat_potential.py` to account for a bug in the script.
  - `rules/build_sector.smk` to ensure `determine_ht_ates_availability.py` is run and to adapt the input for `scripts/prepare_sector_network.py`.
- **Notebooks** in the `Notebooks/` folder for analysis and visualisation.

## Purpose

These changes are part of a research project that invsetigates how HT-ATES can contribute to the Dutch energy system.

## How to use

You can follow the standard PyPSA-Eur instructions with the following differences:
- Use the `config_HT-ATES.yaml` to create scenarios with HT-ATES by running
```sh
 snakemake all --configfile config_HT-ATES.yaml -j 10
```
- A custom costs_2030.csv file is used, therefore retrieve_cost_data is turned to false in the configuration. Using the overwrite function in the configuration does not work, so the CSV file is altered by hand when changes are made to HT-ATES technology or cost data.
- See the Notebooks for the analysis.
