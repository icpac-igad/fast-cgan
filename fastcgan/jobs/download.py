import concurrent
import subprocess
from argparse import ArgumentParser
from datetime import datetime, timedelta
from multiprocessing import cpu_count
from os import getenv
from pathlib import Path
from time import sleep

import cfgrib
import xarray as xr
from loguru import logger
from show_forecasts.constants import COUNTRY_NAMES, DATA_PARAMS
from show_forecasts.data_utils import get_region_extent

from fastcgan.jobs.data_sync import run_ecmwf_ifs_sync, run_sftp_rsync
from fastcgan.jobs.stubs import cgan_ifs_literal, cgan_model_literal, open_ifs_literal
from fastcgan.jobs.utils import (
    data_sync_jobs_status,
    get_data_store_path,
    get_data_sycn_status,
    get_dataset_file_path,
    get_forecast_data_dates,
    get_possible_forecast_dates,
    migrate_files,
    save_to_new_filesystem_structure,
    set_data_sycn_status,
    slice_dataset_by_bbox,
    standardize_dataset,
)


def read_dataset(file_path: str | Path, mask_area: str | None = COUNTRY_NAMES[0]) -> xr.Dataset:
    try:
        ds = cfgrib.open_datasets(str(file_path))
    except Exception as err:
        logger.error(f"failed to read {file_path} dataset file with error {err}")
        return None
    if type(ds) is list:
        arrays = []
        for i in range(len(ds)):
            if "number" in ds[i].dims:
                arrays.append(standardize_dataset(ds[i]))
        try:
            ds = xr.merge(arrays, compat="override")
        except Exception as err:
            logger.error(f"failed to read dataset {file_path} with error {err}")
    try:
        data_params = [data_param for data_param in DATA_PARAMS.keys() if data_param != "wind"]
        data_params.extend(["u10", "v10"])
        return slice_dataset_by_bbox(
            standardize_dataset(ds[data_params]),
            get_region_extent(shape_name=mask_area),
        )
    except Exception as err:
        logger.error(f"processing for {file_path} failed with error {err}")
        return None


def post_process_ecmwf_grib2_dataset(
    grib2_file_name: str,
    source: open_ifs_literal | None = "open-ifs",
    re_try_times: int | None = 5,
    force_process: bool | None = False,
    mask_region: str | None = COUNTRY_NAMES[0],
    save_for_countries: bool | None = True,
    archive_grib2: bool | None = False,
    min_grib2_size: float | None = 4.5 * 1024,
) -> None:
    logger.info(f"executing post-processing task for {grib2_file_name}")
    data_date = datetime.strptime(grib2_file_name.split("-")[0], "%Y%m%d%H%M%S")
    downloads_path = get_data_store_path(source="jobs") / source
    grib2_file = downloads_path / grib2_file_name
    nc_file_name = grib2_file_name.replace("grib2", "nc")
    nc_file = get_dataset_file_path(
        source=source,
        mask_region=mask_region,
        file_name=nc_file_name,
        data_date=data_date,
    )
    grib2_size = 0 if not grib2_file.exists() else grib2_file.stat().st_size / (1024 * 1024)
    # remove grib2 file if its size is less than the required size
    if grib2_size < min_grib2_size:
        grib2_file.unlink()
    elif not nc_file.exists() or force_process:
        logger.info(f"post-processing ECMWF open IFS forecast data file {grib2_file_name}")
        ds = None
        for _ in range(re_try_times):
            ds = read_dataset(str(grib2_file))
            if ds is not None:
                break
        if ds is None:
            logger.error(f"failed to read {grib2_file} after {re_try_times} unsuccessful trials")
        else:
            try:
                ds.chunk().to_netcdf(nc_file, mode="w", format="NETCDF4", engine="netcdf4")
            except Exception as error:
                logger.error(f"failed to save {source} open ifs dataset slice for {mask_region} with error {error}")
            else:
                if save_for_countries:
                    for country_name in COUNTRY_NAMES[1:]:
                        logger.info(f"processing {source} open ifs dataset slice for {country_name}")
                        sliced = slice_dataset_by_bbox(ds, get_region_extent(country_name))
                        slice_file = get_dataset_file_path(
                            source=source,
                            mask_region=country_name,
                            data_date=data_date,
                            file_name=nc_file_name,
                        )
                        logger.debug(f"saving {source} open ifs dataset slice for {country_name} into {slice_file}")
                        try:
                            sliced.chunk().to_netcdf(
                                path=slice_file,
                                mode="w",
                                format="NETCDF4",
                                engine="netcdf4",
                            )
                        except Exception as error:
                            logger.error(
                                f"failed to save {source} open ifs dataset slice for {mask_region} with error {error}"
                            )
                # remove grib2 file from disk
                if not archive_grib2:
                    logger.info(
                        f"removing {grib2_file_name} from disk. Pass archive_grib2=True"
                        + "to archive the file on local storage disk."
                    )
                    for _ in range(10):
                        try:
                            grib2_file.unlink()
                        except Exception:
                            sleep(5)
                            pass
                        else:
                            break
                    if grib2_file.exists():
                        logger.error(f"failed to delete grib2 file {grib2_file}")

                else:
                    archive_dir = get_data_store_path(source="jobs") / "grib2"
                    logger.info(f"archiving {grib2_file_name} into {archive_dir}")

                    if not archive_dir.exists():
                        archive_dir.mkdir(parents=True)

                    try:
                        grib2_file.replace(target=archive_dir / grib2_file_name)
                    except Exception as err:
                        logger.error(f"failed to archive {grib2_file_name} to {archive_dir} with error {err}")

                # remove idx files from the disk
                idx_files = [idxf for idxf in downloads_path.iterdir() if idxf.name.endswith(".idx")]
                logger.info(f"cleaning up grib2 index files {' -> '.join([idxf.name for idxf in idx_files])}")
                for idx_file in idx_files:
                    for _ in range(10):
                        try:
                            idx_file.unlink()
                        except Exception:
                            sleep(5)
                            pass
                        else:
                            break
                    if idx_file.exists():
                        logger.error(f"failed to delete grib2 index file {idx_file}")


def post_process_downloaded_ecmwf_forecasts(source: open_ifs_literal | None = "open-ifs") -> None:
    # run infinite loop that is executed when there are no other active workers
    while True:
        if not data_sync_jobs_status():
            downloads_path = get_data_store_path(source="jobs") / source
            if downloads_path.exists():
                grib2_files = [dfile.name for dfile in downloads_path.iterdir() if dfile.name.endswith(".grib2")]
                if not len(grib2_files):
                    logger.warning("no un-processed open-ifs datasets found. task skipped!")
                else:
                    logger.info(f"starting batch post-processing tasks for {'  <---->  '.join(grib2_files)}")
                    for grib2_file in grib2_files:
                        post_process_ecmwf_grib2_dataset(source=source, grib2_file_name=grib2_file, force_process=True)
            # break the loop
            break
        # sleep for 10 minutes
        sleep(60 * 10)


def syncronize_open_ifs_forecast_data(
    date_str: str | None = None,
    dateback: int | None = 4,
    start_step: int | None = 30,
    final_step: int | None = 54,
) -> None:
    dt_fx = "" if date_str is None else f"for {date_str}"
    logger.info(
        f"recived IFS open forecast data syncronization job at {datetime.now().strftime('%Y-%m-%d %H:%M')} "
        + f"{dt_fx} with time steps {start_step} to {final_step} and {dateback} days back"
    )

    if not data_sync_jobs_status():
        mask_region = getenv("DEFAULT_MASK", COUNTRY_NAMES[0])
        logger.info(
            f"starting open-ifs forecast data syncronization for {mask_region} at "
            + f"{datetime.now().strftime('%Y-%m-%d %H:%M')} {dt_fx} with time steps "
            + f"{start_step} to {final_step} and {dateback} days back"
        )
        # generate download parameters
        data_dates = get_possible_forecast_dates(data_date=date_str, dateback=dateback)
        ifs_dates = [
            datetime.strptime(value, "%b %d, %Y").date()
            for value in get_forecast_data_dates(source="open-ifs", mask_region=mask_region)
        ]

        # set data syncronization status
        set_data_sycn_status(source="open-ifs", status=1)
        with concurrent.futures.ThreadPoolExecutor(max_workers=cpu_count() * 4) as executor:
            results = [
                executor.submit(
                    run_ecmwf_ifs_sync,
                    data_date=data_date,
                    start_step=start_step,
                    final_step=final_step,
                )
                for data_date in [value for value in data_dates if value not in ifs_dates]
            ]
            for future in concurrent.futures.as_completed(results):
                if future.result() is not None:
                    grib2_files = future.result()
                    if grib2_files is not None:
                        # run infinite loop that is executed when there are no other active workers
                        while True:
                            if not data_sync_jobs_status():
                                for grib2_file in grib2_files:
                                    post_process_ecmwf_grib2_dataset(grib2_file_name=grib2_file)
                                # break the loop at the end of execution
                                break
                            # sleep for 10 minutes
                            sleep(60 * 10)

        # set data syncronization status
        set_data_sycn_status(source="open-ifs", status=0)


def generate_cgan_forecasts(model: cgan_model_literal, mask_region: str | None = COUNTRY_NAMES[0]):
    set_data_sycn_status(source=model, status=1)
    ifs_dates = get_forecast_data_dates(mask_region=mask_region, source=model)
    gan_dates = get_forecast_data_dates(mask_region=mask_region, source=model)
    for ifs_date in ifs_dates:
        if ifs_date not in gan_dates:
            logger.info(f"generating {model} cGAN forecast for {ifs_date}")
            # generate forecast for date
            data_date = datetime.strptime(ifs_date, "%b %d, %Y")
            gbmc_source = "cgan-ifs-7d-ens" if model == "mvua-kubwa" else "cgan-ifs-6h-ens"
            gbmc_filename = get_dataset_file_path(
                source=gbmc_source,
                data_date=data_date,
                file_name=f"{data_date.strftime('%Y%m%d')}_00Z.nc",
                mask_region=mask_region,
            )
            store_path = get_data_store_path(source=gbmc_source, mask_region=mask_region)
            try:
                subprocess.call(
                    shell=True,
                    cwd=f'{getenv("WORK_HOME","/opt/cgan")}/ensemble-cgan/dsrnngan',
                    args=f"python test_forecast.py -f {str(gbmc_filename).replace(f'{store_path}/', '')}",
                )
            except Exception as error:
                logger.error(f"failed to generate cGAN forecast for {ifs_date} with error {error}")
            else:
                cgan_file_path = get_data_store_path(source="jobs") / model / f"GAN_{data_date.strftime('%Y%m%d')}.nc"
                save_to_new_filesystem_structure(file_path=cgan_file_path, source=model, part_to_replace="GAN_")
    set_data_sycn_status(source=model, status=0)


def post_process_downloaded_cgan_ifs(model: cgan_ifs_literal):
    # start an infinite loop that is executed when there are no other jobs running
    while True:
        if not data_sync_jobs_status():
            downloads_path = get_data_store_path(source="jobs") / model
            if downloads_path.exists():
                gbmc_files = [file_path for file_path in downloads_path.iterdir() if file_path.name.endswith(".nc")]
                if not len(gbmc_files):
                    logger.warning("no un-processed cgan-ifs datasets found. task skipped!")
                else:
                    logger.info(
                        "starting batch post-processing task for "
                        + f"{'  <---->  '.join([gbmc_file.name for gbmc_file in gbmc_files])}"
                    )
                    for gbmc_file in gbmc_files:
                        save_to_new_filesystem_structure(file_path=gbmc_file, source=model, part_to_replace="IFS_")
                    generate_cgan_forecasts(source=model)
                # purge invalid files
                for file_path in downloads_path.iterdir():
                    file_path.unlink()
            # break the loop
            break
        # sleep for 10 minutes
        sleep(60 * 10)


def syncronize_post_processed_ifs_data(model: cgan_ifs_literal, mask_region: str | None = COUNTRY_NAMES[0]):
    logger.debug(f"received cGAN data syncronization for {model} - {mask_region}")
    if not get_data_sycn_status(source=model):
        # set data syncronization status
        set_data_sycn_status(source=model, status=1)
        gan_dates = get_forecast_data_dates(mask_region=mask_region, source=model)
        gan_dates = [getenv("GAN_SYNC_START_DATE", "Jan 01, 2024")] if not len(gan_dates) else gan_dates
        final_data_date = datetime.strptime(gan_dates[0].lower(), "%b %d, %Y")
        delta = datetime.now() - final_data_date
        logger.debug(
            f"syncronizing {model} cGAN data for the period {final_data_date.date()} to {datetime.now().date()}"
        )

        ifs_host = getenv("IFS_SERVER_HOST", "domain.example")
        ifs_user = getenv("IFS_SERVER_USER", "username")
        src_ssh = f"{ifs_user}@{ifs_host}"
        assert src_ssh != "username@domain.example", "you must specify IFS data source server address"
        src_dir = getenv("IFS_DIR", f"/data/{'Operational' if model == 'cgan-ifs-6h-ens' else 'Operational_7d'}")
        dest_dir = get_data_store_path(source="jobs") / model

        if not dest_dir.exists():
            dest_dir.mkdir(parents=True)
        data_dates = [(final_data_date + timedelta(days=i)).strftime("%Y%m%d") for i in range(delta.days + 1)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=cpu_count() * 4) as executor:
            results = [
                executor.submit(
                    run_sftp_rsync,
                    data_date=data_date,
                    source_ssh=src_ssh,
                    source_dir=src_dir,
                    dest_dir=str(dest_dir),
                )
                for data_date in data_dates
            ]

            for future in concurrent.futures.as_completed(results):
                if future.result() is not None:
                    gbmc_file = future.result()
                    if gbmc_file is not None:
                        save_to_new_filesystem_structure(
                            file_path=dest_dir / gbmc_file, source=model, part_to_replace="IFS_"
                        )

        while True:
            if not data_sync_jobs_status():
                generate_cgan_forecasts(
                    model="jurre-brishti" if model == "cgan-ifs-6h-ens" else "mvua-kubwa", mask_region=mask_region
                )
                # set data syncronization status
                set_data_sycn_status(source=model, status=0)
                # break the loop
                break
            # sleep for 10 minutes
            sleep(60 * 10)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "-m",
        "--model",
        dest="model",
        type=str,
        default="open-ifs",
        help="forecast model or process to be executed. options are: open-ifs,jurre-brishti,mvua-kubwa",
    )
    parser.add_argument(
        "-d",
        "--date",
        dest="data_date",
        type=str,
        default=None,
        help="syncronize forecasts data for the given date",
    )
    parser.add_argument(
        "-p",
        "--period",
        dest="dateback",
        type=int,
        default=4,
        help="generate forecasts for the number of days give counted backwards since data-date",
    )
    parser.add_argument(
        "-s",
        "--start",
        dest="start_step",
        type=int,
        default=30,
        help="Forecast data start time step",
    )
    parser.add_argument(
        "-f",
        "--final",
        dest="final_step",
        type=int,
        default=54,
        help="Forecast data final time step",
    )
    args = parser.parse_args()
    dict_args = {key: value for key, value in args.__dict__.items() if key != "command"}
    if args.model == "open-ifs":
        logger.info(f"received ecmwf forecast data download task with parameters {dict_args}")
        post_process_downloaded_ecmwf_forecasts(args.model)
        syncronize_open_ifs_forecast_data(**dict_args)
    elif args.model == "jurre-brishti" or args.model == "mvua-kubwa":
        post_process_downloaded_cgan_ifs(model="cgan-ifs-7d-ens" if args.model == "mvua-kubwa" else "cgan-ifs-6h-ens")
        syncronize_post_processed_ifs_data(model=args.model)
    elif args.model == "migrate":
        for source in ["open-ifs", "cgan-ifs", "cgan-forecast"]:
            migrate_files(source)
