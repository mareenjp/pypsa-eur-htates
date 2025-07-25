"""
The script performs a land eligibility analysis of what share of land is
available for developing the HT-ATES at each cutout grid cell.
The script uses the data provided by TNO.

Inputs
------
- ``data/TNO-HT-ATES/HT-ATES-potential/-Total_Formation_ms.shp``: HT-ATES potential in Maassluis Formation
- ``data/TNO-HT-ATES/HT-ATES-potential/-Total_Formation_oo.shp``: HT-ATES potential in Oosterhout Formation
- ``data/TNO-HT-ATES/HT-ATES_msz2/msz2__energy_out_P50_basecase_80-45-40.asc``: Energy produced by HT-ATES in Maaslsuis z2 Formation
- ``data/TNO-HT-ATES/HT-ATES_msz3/msz3__energy_out_P50_basecase_80-45-40.asc``: Energy produced by HT-ATES in Maaslsuis z3 Formation
- ``data/TNO-HT-ATES/HT-ATES_msz4/msz4__energy_out_P50_basecase_80-45-40.asc``: Energy produced by HT-ATES in Maaslsuis z4 Formation
- ``data/TNO-HT-ATES/HT-ATES_ooz2/ooz2__energy_out_P50_basecase_80-45-40.asc``: Energy produced by HT-ATES in Oosterhout Formation
- ``data/dh_areas.gpkg``: Shapes of district heating areas
- ``resources/regions_onshore_base_s_{clusters}.geojson``: confer :ref:`busregions`
- ``"cutouts/" + params["renewable"][{technology}]['cutout']``: :ref:`cutout`
- ``networks/_base_s_{clusters}.nc``: :ref:`base`

Relevant Settings
-----------------
.. code:: yaml
    sector:
        district_heating:
            dh_area_buffer

Outputs
-------
- ``resources/htates_potentials_base_s_{clusters}_{planning_horizons}.csv`` : HT-ATES potentials per region in MWh

Source
----------
- TNO – GDN, ThermoGIS Nieuwe Ontwikkelingen HTO v2.4, https://www.thermogis.nl/hoge-temperatuur-opslag-hto, TNO - Geological Survey of the Netherlands (Ed.), CC-BY 4.0 licensed; obtained via personal communication on 27-05-2025, 2025.
"""

import geopandas as gpd
import numpy as np
import xarray as xr
import time
import logging
import rasterio
from rasterio.mask import mask
import pandas as pd
from shapely.ops import unary_union

from _helpers import configure_logging, set_scenario_config

logger = logging.getLogger(__name__)

def check_dh_areas_coverage(dh_areas: gpd.GeoDataFrame, countries: list) -> None:
    """
    Check if district heating areas exist for all specified countries.

    Issues a warning if any country in the countries list doesn't have
    corresponding district heating areas in the provided GeoDataFrame.

    Parameters
    ----------
    dh_areas : geopandas.GeoDataFrame
        GeoDataFrame containing district heating areas
    countries : list
        List of country codes to check for coverage

    Returns
    -------
    None
        Function only logs warnings for missing countries

    Raises
    ------
    ValueError
        If countries list is empty or None, or if district heating areas dataframe is empty
    KeyError
        If the 'country' column is missing from the district heating areas dataframe
    """

    if countries is None or len(countries) == 0:
        raise ValueError("Countries list is empty or None.")
    if dh_areas.empty:
        raise ValueError("District heating areas dataframe is empty.")
    if "country" in dh_areas.columns:
        dh_countries = set(dh_areas["country"].unique())
    else:
        raise KeyError("Cannot find 'country' column in district heating areas dataframe.")
    
    missing_countries = set(countries) - dh_countries
    if missing_countries:
        print(f" No district heating areas found for the following countries: {', '.join(missing_countries)}")
    else:
        print("District heating areas available for all requested countries")

def calculate_total_avg_mwh_per_m2(HTATES_potential: dict[str, gpd.GeoDataFrame], aquifer_energy: dict[str, list[str]]):
    """
    Calculate the MWh potential per square meter for HT-ATES systems. Also returns the HT-ATES suitable areas based on used formations.
    
    Parameters
    ----------
    HTATES_potential : dict[str, gpd.GeoDataFrame]
        Suitable HT-ATES areas for each separate formation
    aquifer_energy : dict[str, list[str]]
        Energy produced with HT-ATES for each layer in each formation in GJ

    Returns
    -------
    float
        The HT-ATES energy storage potential in MWh per square meter
    GeoDataFrame
        The HT-ATES suitable area based on formations used in this calculation
    """
    
    all_max_energy_layers = []
    all_geoms = []

    for key in HTATES_potential:
        potential = HTATES_potential[key] # suitable HT-ATES areas
        energy = aquifer_energy[key] # energy produced in GJ
        if potential.empty:
            continue

        geoms = potential.geometry.values
        all_geoms.extend(geoms)

        for raster_path in energy:
            with rasterio.open(raster_path) as src:
                out_image, _ = mask(src, geoms, crop=False, nodata=np.nan) # with geoms include only suitable HT-ATES areas
                data = out_image[0]
                data = np.where(np.isnan(data), 0, data)
                all_max_energy_layers.append(data) # store energy data of each aquifer layer

    if not all_max_energy_layers:
        return 0.0

    # Take the maximum energy value for each grid cell across all aquifer layers
    max_energy = np.max(np.stack(all_max_energy_layers), axis=0)
    total_energy = max_energy.sum()  # GJ

    # Find the total area of aquifers that produce energy
    # Merge the geometries of all potential maps, dissolving overlapping shapes into one to avoid counting the same area multiple times
    union_geom = unary_union(all_geoms)
    area_gdf = gpd.GeoDataFrame(geometry=[union_geom], crs=HTATES_potential[list(HTATES_potential.keys())[0]].crs)
    total_area = area_gdf.geometry.area.sum()  # m²

    total_mwh_per_m2 = (total_energy * (1000/3600)) / total_area if total_area > 0 else 0.0
    return total_mwh_per_m2, area_gdf

def calculate_htates_potential_per_cluster(
    regions_onshore: gpd.GeoDataFrame,
    dh_areas: gpd.GeoDataFrame,
    suitable_aquifers: gpd.GeoDataFrame,
    dh_area_buffer: float,
    mwh_per_m2: float,
) -> gpd.GeoDataFrame:
    """
    Calculate the HT-ATES potential for each onshore region.

    This function overlays suitable aquifers with onshore regions and district heating areas
    to calculate the potential HT-ATES capacity for each region.

    Parameters
    ----------
    regions_onshore : geopandas.GeoDataFrame
        GeoDataFrame containing the shapes of onshore regions
    dh_areas : geopandas.GeoDataFrame
        GeoDataFrame containing the shapes of district heating areas
    suitable_aquifers : geopandas.GeoDataFrame
        GeoDataFrame containing filtered suitable aquifers
    dh_area_buffer : float
        Buffer distance in meters to apply around district heating areas
    mwh_per_m2 : float
        HT-ATES potential in MWh per square meter

    Returns
    -------
    geopandas.GeoDataFrame
        GeoDataFrame with onshore regions and their HT-ATES potential in MWh

    Raises
    ------
    KeyError
        If required column 'name' is not found in regions_onshore dataframe
    Exception
        If calculation process fails
    """
    if suitable_aquifers.empty or regions_onshore.empty or dh_areas.empty:
            logger.warning("One or more input GeoDataFrames are empty")

    ret_val = regions_onshore.copy()
    if "name" not in ret_val.columns:
        raise KeyError("Column 'name' not found in regions.")
    
    ret_val.index = ret_val["name"]
    ret_val.drop(columns=["name"], inplace=True)

    # Filter aquifers to only those in regions
    suitable_in_regions = gpd.overlay(suitable_aquifers, regions_onshore, how="intersection")

    # Buffer district heating areas
    dh_areas_buffered = dh_areas.copy()
    dh_areas_buffered["geometry"] = dh_areas_buffered.geometry.buffer(dh_area_buffer)

    try:
        aquifers_in_dh_areas = (
            gpd.overlay(dh_areas_buffered, suitable_in_regions, how="intersection")
            .groupby("name")["geometry"]
            .apply(lambda x: x.area.sum())
        )

        missing_regions = set(ret_val.index) - set(aquifers_in_dh_areas.index)
        if missing_regions:
            print(f" {len(missing_regions)} regions have no ATES potential")

        ret_val["htates_potential"] = 0.0
        ret_val.loc[aquifers_in_dh_areas.index, "htates_potential"] = aquifers_in_dh_areas * mwh_per_m2

    except Exception as e:
        print(f" Error during overlay: {e}")
        ret_val["htates_potential"] = 0.0

    return ret_val.reset_index()


if __name__ == "__main__":
    if "snakemake" not in globals():
        from _helpers import mock_snakemake
        snakemake = mock_snakemake("determine_ht_ates_availability", clusters="6", planning_horizons=2030)

    configure_logging(snakemake)
    set_scenario_config(snakemake)

    # Get onshore regions
    regions = gpd.read_file(snakemake.input.regions)
    assert not regions.empty, f"{snakemake.input.regions} is empty"
    regions = regions.to_crs(epsg=3035)

    countries: list = snakemake.params.countries

    # Get DH areas
    dh_areas = gpd.read_file(snakemake.input.dh_areas).to_crs(regions.crs)

    # Get HT-ATES potential regions
    potentials = {
        "ms": gpd.read_file(snakemake.input.htates_ms_potential),
        "oo": gpd.read_file(snakemake.input.htates_oo_potential),
    }
    
    # Filter for favourable HT-ATES areas
    # Favourable: DN = 3000
    # Possible barriers: DN = 2000
    # One or more barriers: DN = 1000
    for key in potentials:
        potentials[key] = potentials[key][potentials[key]["DN"] == 3000]
        #potentials[key] = potentials[key][potentials[key]["DN"].isin([3000, 2000])]

    # Get HT-ATES energy production
    energy_maps = {
        "ms": [snakemake.input.energy_out_msz2,
               snakemake.input.energy_out_msz3,
               snakemake.input.energy_out_msz4],
        "oo": [snakemake.input.energy_out_ooz2],
    }

    # Check district heating areas coverage
    logger.info("Checking district heating areas coverage")
    check_dh_areas_coverage(
        dh_areas=dh_areas,
        countries=countries,
    )

    # Calculate HT-ATES potential in MWh
    logger.info("Calculating HT-ATES potential in MWh per region")
    mwh_per_m2, suitable_aquifers = calculate_total_avg_mwh_per_m2(potentials, energy_maps)

    suitable_aquifers = suitable_aquifers.set_crs(epsg=28992).to_crs(regions.crs)
    
    htates_potentials = calculate_htates_potential_per_cluster(
    regions_onshore=regions,
    dh_areas=dh_areas,
    suitable_aquifers=suitable_aquifers,
    dh_area_buffer=snakemake.params.dh_area_buffer,
    mwh_per_m2=mwh_per_m2,
    )


    logger.info(f"Writing results to {snakemake.output.htates_potentials}")
    htates_potentials.to_csv(snakemake.output.htates_potentials, index_label="name")
