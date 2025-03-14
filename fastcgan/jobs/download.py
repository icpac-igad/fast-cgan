import concurrent
import subprocess
from argparse import ArgumentParser
from datetime import datetime
from multiprocessing import cpu_count
from os import getenv
from pathlib import Path
from time import sleep

import xarray as xr
from loguru import logger
from show_forecasts.constants import COUNTRY_NAMES, DATA_PARAMS
from show_forecasts.data_utils import get_region_extent

from fastcgan.jobs.counts import make_cgan_forecast_counts
from fastcgan.jobs.data_sync import run_ecmwf_ifs_sync
from fastcgan.jobs.icpac_ftp import sync_icpac_ifs_data
from fastcgan.jobs.sftp import sync_sftp_data_files
from fastcgan.jobs.stubs import cgan_model_literal, open_ifs_literal
from fastcgan.jobs.utils import (
    get_data_store_path,
    get_data_sycn_status,
    get_dataset_file_path,
    get_forecast_data_dates,
    get_gan_forecast_dates,
    get_possible_forecast_dates,
    get_processing_task_status,
    migrate_files,
    save_to_new_filesystem_structure,
    set_data_sycn_status,
    slice_dataset_by_bbox,
    standardize_dataset,
)


def read_dataset(file_path: str | Path, mask_area: str | None = COUNTRY_NAMES[0]) -> xr.Dataset:
    try:
        import cfgrib
    except Exception as err:
        logger.error(f"cgrib is not available for ECMWF data processing. attempt failed with error {err}")
    else:
        try:
            ds = cfgrib.open_datasets(str(file_path))
        except Exception as err:
            logger.error(f"failed to read {file_path} dataset file with error {err}")
            return None
        if isinstance(ds, list):
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


def clean_grib2_index_files(source: str | None = "open-ifs"):
    # remove idx files from the disk
    downloads_path = get_data_store_path(source="jobs") / source
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


def post_process_ecmwf_grib2_dataset(
    grib2_file_name: str,
    source: open_ifs_literal | None = "open-ifs",
    re_try_times: int | None = 5,
    force_process: bool | None = False,
    mask_region: str | None = COUNTRY_NAMES[0],
    save_for_countries: bool | None = True,
    archive_grib2: bool | None = False,
    min_grib2_size: float | None = 5.9 * 1024,
) -> None:
    logger.info(f"executing post-processing task for {grib2_file_name}")
    set_data_sycn_status(source=source, sync_type="processing", status=True)
    clean_grib2_index_files()
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
        grib2_file.unlink(missing_ok=True)
    elif not nc_file.exists() or force_process:
        logger.info(f"post-processing ECMWF open IFS forecast data file {grib2_file_name}")
        ds = None
        for _ in range(re_try_times):
            ds = read_dataset(grib2_file)
            if ds is not None:
                break
        if ds is None:
            logger.error(f"failed to read {grib2_file} after {re_try_times} unsuccessful trials")
            grib2_file.unlink(missing_ok=True)
        else:
            try:
                ds.to_netcdf(nc_file, mode="w", format="NETCDF4", engine="netcdf4")
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
                            sliced.to_netcdf(
                                path=slice_file,
                                mode="w",
                                format="NETCDF4",
                                engine="netcdf4",
                            )
                        except Exception as error:
                            logger.error(f"failed to save {source} open ifs dataset slice for {mask_region} with error {error}")
                # remove grib2 file from disk
                if not archive_grib2:
                    logger.info(f"removing {grib2_file_name} from disk. Pass archive_grib2=True" + "to archive the file on local storage disk.")
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
                        archive_dir.mkdir(parents=True, exist_ok=True)

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

    set_data_sycn_status(source=source, sync_type="processing", status=False)


def post_process_downloaded_ecmwf_forecasts(
    source: open_ifs_literal | None = "open-ifs",
) -> None:
    try:
        import cfgrib  # noqa: F401
    except Exception as err:
        logger.error(f"cgrib is not available for ECMWF data processing. attempt failed with error {err}")
    else:
        # run infinite loop that is executed when there are no other active workers
        while True:
            if not get_processing_task_status():
                downloads_path = get_data_store_path(source="jobs") / source
                if downloads_path.exists():
                    grib2_files = [dfile.name for dfile in downloads_path.iterdir() if dfile.name.endswith(".grib2")]
                    if not len(grib2_files):
                        logger.warning("no un-processed open-ifs datasets found. task skipped!")
                    else:
                        logger.info(f"starting batch post-processing tasks for {'  <---->  '.join(grib2_files)}")
                        for grib2_file in grib2_files:
                            post_process_ecmwf_grib2_dataset(
                                source=source,
                                grib2_file_name=grib2_file,
                                force_process=True,
                            )
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

    if not get_data_sycn_status(source="open-ifs", sync_type="download"):
        mask_region = getenv("DEFAULT_MASK", COUNTRY_NAMES[0])
        sync_icpac_ifs = True if getenv("USE_ICPAC_IFS", "false").lower() in ["yes", "y", "true", "t", "1"] else False
        if not sync_icpac_ifs:
            try:
                import cfgrib  # noqa: F401
            except Exception as err:
                sync_icpac_ifs = True
                logger.error(f"cgrib is not available for ECMWF data processing. attempt failed with error {err}")
        if sync_icpac_ifs:
            sync_icpac_ifs_data(model="open-ifs")
        else:
            logger.info(
                f"starting open-ifs forecast data syncronization for {mask_region} at "
                + f"{datetime.now().strftime('%Y-%m-%d %H:%M')} {dt_fx} with time steps "
                + f"{start_step} to {final_step} and {dateback} days back"
            )
            # generate download parameters
            data_dates = get_possible_forecast_dates(data_date=date_str, dateback=dateback)
            ifs_dates = [
                datetime.strptime(value, "%b %d, %Y").date() for value in get_forecast_data_dates(source="open-ifs", mask_region=mask_region)
            ]

            # set data syncronization status
            set_data_sycn_status(sync_type="download", source="open-ifs", status=True)
            with concurrent.futures.ThreadPoolExecutor(max_workers=int(cpu_count() / 2)) as executor:
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
                                if not get_processing_task_status():
                                    for grib2_file in grib2_files:
                                        post_process_ecmwf_grib2_dataset(grib2_file_name=grib2_file)
                                    # break the loop at the end of execution
                                    break
                                # sleep for 10 minutes
                                sleep(60 * 10)

        # set data syncronization status
        set_data_sycn_status(sync_type="download", source="open-ifs", status=False)


def generate_cgan_forecasts(model: cgan_model_literal, mask_region: str | None = COUNTRY_NAMES[0], min_gbmc_size: int | None = 260):
    # start an infinite loop that will execute when other data-processing jobs are completed
    while True:
        if not get_processing_task_status():
            logger.debug(f"starting cGAN forecast generation for {model} model")
            set_data_sycn_status(source=model, sync_type="processing", status=True)
            gbmc_source = "cgan-ifs-7d-ens" if "mvua-kubwa" in model else "cgan-ifs-6h-ens"
            ifs_dates = sorted(
                get_gan_forecast_dates(mask_region=None, source=gbmc_source),
                reverse=True,
            )
            gan_dates = get_gan_forecast_dates(mask_region=None if "count" in model else mask_region, source=model)
            missing_dates = [data_date for data_date in ifs_dates if data_date not in gan_dates and int(data_date[:4]) > 2018]
            logger.debug(f"launching forecast generation workers for data dates {' ==> '.join(missing_dates)}")
            for missing_date in missing_dates:
                logger.info(f"generating {model} cGAN forecast for {missing_date}")
                date_str, init_time = missing_date.split("_")
                # generate forecast for date
                data_date = datetime.strptime(date_str, "%Y%m%d")
                gbmc_filename = get_dataset_file_path(
                    source=gbmc_source,
                    data_date=data_date,
                    file_name=f"{data_date.strftime('%Y%m%d')}_{init_time}Z.nc",
                    mask_region=mask_region,
                )
                store_path = get_data_store_path(source=gbmc_source, mask_region=mask_region)
                gan_ifs = str(gbmc_filename).replace(f"{store_path}/", "")
                logger.debug(f"starting {model} forecast generation with IFS file {gan_ifs}")
                py_script = "forecast_date.py" if "mvua-kubwa" in model else "test_forecast.py"
                gan_status = subprocess.call(
                    shell=True,
                    cwd=f'{getenv("WORK_HOME","/opt/cgan")}/ensemble-cgan/dsrnngan',
                    args=f"python {py_script} -f {gan_ifs}",
                )
                cgan_file_path = get_data_store_path(source="jobs") / model / f"GAN_{date_str}_{init_time}Z.nc"
                if gan_status:
                    logger.error(f"failed to generate {model} cGAN forecast for {missing_date}. deleting intermediary forecast file {cgan_file_path}")
                    cgan_file_path.unlink(missing_ok=True)
                    if gbmc_filename.stat().st_size / (1024 * 1024) < min_gbmc_size:
                        logger.error(
                            f"deleting intermediarty IFS file {gbmc_filename} due "
                            + f"to invalid size of {round(gbmc_filename.stat().st_size / (1024 * 1024), 2)} Mib"
                        )
                        gbmc_filename.unlink(missing_ok=True)
                else:
                    if "count" in model:
                        make_cgan_forecast_counts(
                            date_str=date_str,
                            hour_str=init_time,
                            model_name=model,
                        )
                    else:
                        save_to_new_filesystem_structure(
                            file_path=cgan_file_path,
                            source=model,
                            part_to_replace="GAN_",
                        )
            set_data_sycn_status(source=model, sync_type="processing", status=False)
            # break the infinite loop
            break
        # sleep for 10 minutes
        sleep(10 * 60)


def post_process_downloaded_cgan_ifs(model: cgan_model_literal):
    # start an infinite loop that is executed when there are no other jobs running
    while True:
        if not get_processing_task_status():
            source_model = "cgan-ifs-6h-ens" if "jurre-brishti" in model else "cgan-ifs-7d-ens"
            downloads_path = get_data_store_path(source="jobs") / source_model
            if downloads_path.exists():
                gbmc_files = [file_path for file_path in downloads_path.iterdir() if file_path.name.endswith(".nc")]
                if not len(gbmc_files):
                    logger.warning(f"no un-processed {source_model} datasets found. task skipped!")
                else:
                    logger.info(
                        f"starting {source_model} forecasts batch post-processing task for "
                        + f"{'  <---->  '.join([gbmc_file.name for gbmc_file in gbmc_files])}"
                    )
                    for gbmc_file in gbmc_files:
                        save_to_new_filesystem_structure(
                            file_path=gbmc_file,
                            source=source_model,
                            part_to_replace="IFS_" if "IFS_" in gbmc_file.name else f"east_africa-{source_model.replace('-','_')}-",
                        )
                # purge invalid files
                for file_path in downloads_path.iterdir():
                    file_path.unlink(missing_ok=True)
            # break the loop
            break
        # sleep for 10 minutes
        sleep(60 * 10)


def syncronize_post_processed_ifs_data(model: cgan_model_literal):
    logger.debug(f"received cGAN data syncronization for {model}")
    if not get_data_sycn_status(source=model, sync_type="download") and "count" not in model:
        # set data syncronization status
        set_data_sycn_status(source=model, sync_type="download", status=True)
        # sync from ICPAC if GBMC server credentials are not provided
        if getenv("IFS_SERVER_HOST", "domain.example") == "domain.example" or getenv("IFS_SERVER_USER", "username") == "username":
            sync_icpac_ifs_data(model=model)
        else:
            sync_sftp_data_files(model=("cgan-ifs-6h-ens" if "jurre-brishti" in model else "cgan-ifs-7d-ens"))
        set_data_sycn_status(source=model, sync_type="download", status=False)
    post_process_downloaded_cgan_ifs(model=model)


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
        "-c",
        "--command",
        dest="command",
        type=str,
        help="command to be executed. either download or process",
        default="download",
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
    if args.command == "sync":
        if args.model == "open-ifs":
            syncronize_open_ifs_forecast_data(**{key: value for key, value in dict_args.items() if key != "model"})
        elif args.model == "jurre-brishti" or args.model == "mvua-kubwa":
            syncronize_post_processed_ifs_data(model=args.model)
    else:
        if args.model == "open-ifs":
            logger.info(f"received ecmwf forecast data download task with parameters {dict_args}")
            post_process_downloaded_ecmwf_forecasts(args.model)
            syncronize_open_ifs_forecast_data(**dict_args)
        elif args.model == "jurre-brishti" or args.model == "mvua-kubwa":
            post_process_downloaded_cgan_ifs(model=("cgan-ifs-7d-ens" if args.model == "mvua-kubwa" else "cgan-ifs-6h-ens"))
            syncronize_post_processed_ifs_data(model=args.model)
        elif args.model == "migrate":
            for source in ["open-ifs", "cgan-ifs", "cgan-forecast"]:
                migrate_files(source)
