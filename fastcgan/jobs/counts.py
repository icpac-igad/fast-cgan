# Script to compute the histogram data from 1000 member ensembles

import sys
from pathlib import Path
from typing import Literal

import netCDF4 as nc
import numpy as np
from loguru import logger

from fastcgan.jobs.utils import get_data_store_path


def make_cgan_forecast_counts(
    date_str: str,
    hour_str: str,
    model_name: Literal["jurre-brishti", "mvua-kubwa"],
):
    year = int(date_str[0:4])
    month = int(date_str[4:6])
    day = int(date_str[6:8])
    hour = int(hour_str)

    # Where the forecasts are downloaded to
    data_dir = get_data_store_path(source="jobs")
    # Where the counts are saved to
    output_dir = get_data_store_path(source=f"{model_name}-count")
    # input forecast file name
    in_file_name = f"{data_dir}/{model_name}-ens/GAN_{year}{month:02d}{day:02d}_{hour:02d}Z.nc"
    logger.debug(f"reading {model} forecast file {in_file_name}")
    # model incremetor time in hours
    multiplier = 6 if model_name == "jurre-brishti" else 24
    time_steps = 30 if model_name == "jurre-brishti" else 6

    # Open a NetCDF file for reading
    nc_file = nc.Dataset(in_file_name, "r")
    latitude = np.array(nc_file["latitude"][:])
    longitude = np.array(nc_file["longitude"][:])
    time = np.array(nc_file["time"][:])
    valid_time = np.array(nc_file["fcst_valid_time"][:])[0]
    precip = np.array(nc_file["precipitation"][:])
    nc_file.close()

    num_ensemble_members = precip.shape[1]
    # Define the bins we will use on an approximate log scale (mm/h)
    bin_spec_1h = np.array(
        [
            0,
            0.04,
            0.1,
            0.25,
            0.4,
            0.6,
            0.8,
            1,
            1.25,
            1.5,
            1.8,
            2.2,
            2.6,
            3,
            3.5,
            4,
            4.7,
            5.4,
            6.1,
            7,
            8,
            9.1,
            10.3,
            11.7,
            13.25,
            15,
            1000,
        ]
    )
    # Compute the counts at each valuid time, latitude and longitude
    logger.debug("computing the counts at each valuid time, latitude and longitude")
    counts = np.zeros(
        (len(valid_time), len(latitude), len(longitude), len(bin_spec_1h) - 1),
        dtype=int,
    )
    for valid_time_num in range(len(valid_time)):
        for j in range(len(latitude)):
            for i in range(len(longitude)):
                counts[valid_time_num, j, i, :], _ = np.histogram(precip[0, :, valid_time_num, j, i], bin_spec_1h)

    # Save each valid time in a different file
    logger.debug("saving each valid time in a different file")
    for valid_time_num in range(len(valid_time)):
        # counts in bin zero are not stored.
        pref_outdir = f"{output_dir}/{year}/{month:02d}"
        fcst_valid_time = valid_time_num * multiplier + time_steps
        file_name = f"{pref_outdir}/counts_{year}{month:02d}{day:02d}_{hour:02d}_{fcst_valid_time}h.nc"

        # Create a new NetCDF file
        logger.info(f"creating new NetCDF file {file_name} for {model_name}:{valid_time_num}")
        rootgrp = nc.Dataset(file_name, "w", format="NETCDF4")

        # Describe where this data comes from
        rootgrp.description = f"{model_name.title()} cGAN forecast histogram counts"

        # Create dimensions
        rootgrp.createDimension("longitude", len(longitude))
        rootgrp.createDimension("latitude", len(latitude))
        rootgrp.createDimension("time", 1)
        rootgrp.createDimension("valid_time", 1)
        rootgrp.createDimension("bins", len(bin_spec_1h) - 2)
        logger.info(f"processing {rootgrp.description}")
        # Create the longitude variable
        longitude_data = rootgrp.createVariable("longitude", "f4", ("longitude"), zlib=False)
        longitude_data.units = "degrees_east"
        longitude_data[:] = longitude  # Write the longitude data

        # Create the latitude variable
        latitude_data = rootgrp.createVariable("latitude", "f4", ("latitude"), zlib=False)
        latitude_data.units = "degrees_north"
        latitude_data[:] = latitude  # Write the latitude data

        # Create the time variable
        time_data = rootgrp.createVariable("time", "f4", ("time"), zlib=False)
        time_data.units = "hours since 1900-01-01 00:00:00.0"
        time_data.description = "Time corresponding to forecast model start"
        time_data[:] = time  # Write the forecast model start time

        # Create the valid_time variable
        valid_time_data = rootgrp.createVariable("valid_time", "f4", ("valid_time"), zlib=False)
        valid_time_data.units = "hours since 1900-01-01 00:00:00.0"
        valid_time_data.description = "Time corresponding to forecast prediction"
        valid_time_data[:] = valid_time[valid_time_num]  # Write the forecast model valid times

        # Bin specification. First bin is zero, final bin is infinity.
        bins_data = rootgrp.createVariable("bins", "f4", ("bins"), zlib=False)
        bins_data.units = "mm/h"
        bins_data.description = "Histogram bin edges"
        bins_data[:] = bin_spec_1h[1:-1]  # Write histogram bin specification

        # Create the counts variable
        counts_data = rootgrp.createVariable("counts", "i2", ("bins", "latitude", "longitude"), zlib=True, complevel=9)
        counts_data.description = "Histogram bin counts"
        counts_data.num_members = num_ensemble_members
        # Compression is better if we move the axis order
        logger.info("compressing and re-arranging axis orger")
        counts_data[:] = np.moveaxis(counts, [0, 1, 2, 3], [0, 2, 3, 1])[valid_time_num, 1:, :, :]

        # Close the netCDF file
        rootgrp.close()
        input_path = Path(in_file_name)
        logger.debug(f"removing input forecast file {input_path}")
        input_path.unlink(missing_ok=True)


if __name__ == "__main__":
    # Get the date from the command line argument
    date_str = sys.argv[1]
    hour_str = sys.argv[2]
    model = sys.argv[3]

    make_cgan_forecast_counts(date_str=date_str, hour_str=hour_str, model_name=model)
