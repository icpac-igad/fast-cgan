import concurrent
from argparse import ArgumentParser
from datetime import datetime
from multiprocessing import cpu_count
from os import getenv
from pathlib import Path
from time import sleep

import schedule
import xarray as xr
from loguru import logger
from show_forecasts.constants import COUNTRY_NAMES, DATA_PARAMS
from show_forecasts.data_utils import get_region_extent

from fastcgan.jobs.data_sync import run_ecmwf_ifs_sync
from fastcgan.jobs.icpac_ftp import sync_icpac_ifs_data
from fastcgan.jobs.stubs import open_ifs_literal
from fastcgan.jobs.utils import (
    get_data_store_path,
    get_data_sycn_status,
    get_dataset_file_path,
    get_forecast_data_dates,
    get_possible_forecast_dates,
    get_processing_task_status,
    migrate_files,
    set_data_sycn_status,
    slice_dataset_by_bbox,
    standardize_dataset,
)


def read_dataset(
    file_path: str | Path, mask_area: str | None = COUNTRY_NAMES[0]
) -> xr.Dataset:
    try:
        import cfgrib
    except Exception as err:
        logger.error(
            f"cgrib is not available for ECMWF data processing. attempt failed with error {err}"
        )
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
            data_params = [
                data_param for data_param in DATA_PARAMS.keys() if data_param != "wind"
            ]
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
    idx_files = [
        idxf for idxf in downloads_path.iterdir() if idxf.name.endswith(".idx")
    ]
    logger.info(
        f"cleaning up grib2 index files {' -> '.join([idxf.name for idxf in idx_files])}"
    )
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
    grib2_size = (
        0 if not grib2_file.exists() else grib2_file.stat().st_size / (1024 * 1024)
    )
    # remove grib2 file if its size is less than the required size
    if grib2_size < min_grib2_size:
        grib2_file.unlink(missing_ok=True)
    elif not nc_file.exists() or force_process:
        logger.info(
            f"post-processing ECMWF open IFS forecast data file {grib2_file_name}"
        )
        ds = None
        for _ in range(re_try_times):
            ds = read_dataset(grib2_file)
            if ds is not None:
                break
        if ds is None:
            logger.error(
                f"failed to read {grib2_file} after {re_try_times} unsuccessful trials"
            )
            grib2_file.unlink(missing_ok=True)
        else:
            try:
                ds.to_netcdf(nc_file, mode="w", format="NETCDF4", engine="netcdf4")
            except Exception as error:
                logger.error(
                    f"failed to save {source} open ifs dataset slice for {mask_region} with error {error}"
                )
            else:
                if save_for_countries:
                    for country_name in COUNTRY_NAMES[1:]:
                        logger.info(
                            f"processing {source} open ifs dataset slice for {country_name}"
                        )
                        sliced = slice_dataset_by_bbox(
                            ds, get_region_extent(country_name)
                        )
                        slice_file = get_dataset_file_path(
                            source=source,
                            mask_region=country_name,
                            data_date=data_date,
                            file_name=nc_file_name,
                        )
                        logger.debug(
                            f"saving {source} open ifs dataset slice for {country_name} into {slice_file}"
                        )
                        try:
                            sliced.to_netcdf(
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
                        archive_dir.mkdir(parents=True, exist_ok=True)

                    try:
                        grib2_file.replace(target=archive_dir / grib2_file_name)
                    except Exception as err:
                        logger.error(
                            f"failed to archive {grib2_file_name} to {archive_dir} with error {err}"
                        )

                # remove idx files from the disk
                idx_files = [
                    idxf
                    for idxf in downloads_path.iterdir()
                    if idxf.name.endswith(".idx")
                ]
                logger.info(
                    f"cleaning up grib2 index files {' -> '.join([idxf.name for idxf in idx_files])}"
                )
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
        logger.error(
            f"cgrib is not available for ECMWF data processing. attempt failed with error {err}"
        )
    else:
        # run infinite loop that is executed when there are no other active workers
        while True:
            if not get_processing_task_status():
                downloads_path = get_data_store_path(source="jobs") / source
                if downloads_path.exists():
                    grib2_files = [
                        dfile.name
                        for dfile in downloads_path.iterdir()
                        if dfile.name.endswith(".grib2")
                    ]
                    if not len(grib2_files):
                        logger.warning(
                            "no un-processed open-ifs datasets found. task skipped!"
                        )
                    else:
                        logger.info(
                            f"starting batch post-processing tasks for {'  <---->  '.join(grib2_files)}"
                        )
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
        sync_icpac_ifs = (
            True
            if getenv("USE_ICPAC_IFS", "false").lower()
            in ["yes", "y", "true", "t", "1"]
            else False
        )
        if not sync_icpac_ifs:
            try:
                import cfgrib  # noqa: F401
            except Exception as err:
                sync_icpac_ifs = True
                logger.error(
                    f"cgrib is not available for ECMWF data processing. attempt failed with error {err}"
                )
        if sync_icpac_ifs:
            sync_icpac_ifs_data(model="open-ifs")
        else:
            logger.info(
                f"starting open-ifs forecast data syncronization for {mask_region} at "
                + f"{datetime.now().strftime('%Y-%m-%d %H:%M')} {dt_fx} with time steps "
                + f"{start_step} to {final_step} and {dateback} days back"
            )
            # generate download parameters
            data_dates = get_possible_forecast_dates(
                data_date=date_str, dateback=dateback
            )
            ifs_dates = [
                datetime.strptime(value, "%b %d, %Y").date()
                for value in get_forecast_data_dates(
                    source="open-ifs", mask_region=mask_region
                )
            ]

            # set data syncronization status
            set_data_sycn_status(sync_type="download", source="open-ifs", status=True)
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=int(cpu_count() / 2)
            ) as executor:
                # TODO: use coiled to run parallel download jobs
                results = [
                    executor.submit(
                        run_ecmwf_ifs_sync,
                        data_date=data_date,
                        start_step=start_step,
                        final_step=final_step,
                    )
                    for data_date in [
                        value for value in data_dates if value not in ifs_dates
                    ]
                ]
                for future in concurrent.futures.as_completed(results):
                    if future.result() is not None:
                        grib2_files = future.result()
                        if grib2_files is not None:
                            # run infinite loop that is executed when there are no other active workers
                            while True:
                                # TODO: use coiled to perform parallel processing
                                if not get_processing_task_status():
                                    for grib2_file in grib2_files:
                                        post_process_ecmwf_grib2_dataset(
                                            grib2_file_name=grib2_file
                                        )
                                    # break the loop at the end of execution
                                    break
                                # sleep for 10 minutes
                                sleep(60 * 10)

        # set data syncronization status
        set_data_sycn_status(sync_type="download", source="open-ifs", status=False)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "-c",
        "--command",
        dest="command",
        type=str,
        help="command to be executed. either download or process",
        default=None,
    )
    parser.add_argument(
        "-d",
        "--date",
        dest="date_str",
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
    dict_args = {
        key: value
        for key, value in args.__dict__.items()
        if key != "command" and value is not None
    }
    data_model = "open-ifs"
    set_data_sycn_status(source=data_model, sync_type="download", status=False)
    set_data_sycn_status(source=data_model, sync_type="processing", status=False)
    if args.command == "download":
        syncronize_open_ifs_forecast_data(**dict_args)
    elif args.command == "migrate":
        migrate_files(data_model)
    elif args.command == "process":
        logger.info(
            f"received ecmwf forecast data download task with parameters {dict_args}"
        )
        post_process_downloaded_ecmwf_forecasts(data_model)
        syncronize_open_ifs_forecast_data(**dict_args)
    else:
        # drop to scheduler by defaukt
        schedule.every().hour.do(syncronize_open_ifs_forecast_data, **dict_args)
        schedule.every().hour.do(
            post_process_downloaded_ecmwf_forecasts, source=data_model
        )

        schedule.run_all(delay_seconds=10)

        while True:
            schedule.run_pending()
            sleep(10)
