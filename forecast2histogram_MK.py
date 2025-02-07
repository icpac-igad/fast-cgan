# Script to compute the histogram data from 1000 member ensembles

import sys

import netCDF4 as nc
import numpy as np

# Where the forecasts are downloaded to
data_dir = "/home/jason/.docker-data/cGAN/mvua-kubwa/forecasts"

# Where the counts are saved to
output_dir = "/home/jason/.docker-data/cGAN/mvua-kubwa/counts"

# Get the date from the command line argument
time_str = sys.argv[1]
year = int(time_str[0:4])
month = int(time_str[4:6])
day = int(time_str[6:8])

# # Choose the date
# forecast_init_date = datetime(year=2024, month=5, day=21)
# # Pick today instead:
# #forecast_init_date = datetime.now()
# year = forecast_init_date.year
# month = forecast_init_date.month
# day = forecast_init_date.day

file_name = f"{data_dir}/GAN_{year}{month:02d}{day:02d}_00Z.nc"

# Open a NetCDF file for reading
nc_file = nc.Dataset(file_name, "r")
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
counts = np.zeros((len(valid_time), len(latitude), len(longitude), len(bin_spec_1h) - 1), dtype=int)
for valid_time_num in range(len(valid_time)):
    for j in range(len(latitude)):
        for i in range(len(longitude)):
            counts[valid_time_num, j, i, :], _ = np.histogram(precip[0, :, valid_time_num, j, i], bin_spec_1h)

# Save each valid time in a different file
for valid_time_num in range(len(valid_time)):
    # counts in bin zero are not stored.
    file_name = f"{output_dir}/counts_{year}{month:02d}{day:02d}_00_{valid_time_num*24+6}h.nc"

    # Create a new NetCDF file
    rootgrp = nc.Dataset(file_name, "w", format="NETCDF4")

    # Describe where this data comes from
    rootgrp.description = "cGAN forecast histogram counts"

    # Create dimensions
    longitude_dim = rootgrp.createDimension("longitude", len(longitude))
    latitude_dim = rootgrp.createDimension("latitude", len(latitude))
    time_dim = rootgrp.createDimension("time", 1)
    valid_time_dim = rootgrp.createDimension("valid_time", 1)
    bins_dim = rootgrp.createDimension("bins", len(bin_spec_1h) - 2)

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
    counts_data[:] = np.moveaxis(counts, [0, 1, 2, 3], [0, 2, 3, 1])[valid_time_num, 1:, :, :]

    # Close the netCDF file
    rootgrp.close()
