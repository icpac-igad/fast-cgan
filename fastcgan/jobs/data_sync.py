from datetime import date
from pathlib import Path

from ecmwf.opendata import Client
from ecmwf.opendata.client import Result
from loguru import logger
from show_forecasts.constants import COUNTRY_NAMES

from fastcgan.jobs.utils import (
    get_data_store_path,
    get_dataset_file_path,
    get_relevant_forecast_steps,
)


def try_data_download(
    client: Client,
    request: dict[str, str],
    target_file: str,
    model: str | None = "ifs",
) -> Result | None:
    try:
        result = client.download(
            request=request,
            target=target_file,
        )
    except Exception as err:
        logger.error(f"failed to download {model} forecast data for {request['date']} with error {err}")
        Path(target_file).unlink(missing_ok=True)
        return None
    else:
        logger.info(f"downloaded {result.urls[0]} successfully")
        return result


def run_ecmwf_ifs_sync(
    data_date: date,
    source: str | None = "open-ifs",
    model: str | None = "ifs",
    resolution: str | None = "0p25",
    stream: str | None = "enfo",
    start_step: int | None = 30,
    final_step: int | None = 54,
    default_mask: str | None = COUNTRY_NAMES[0],
    re_try_times: int | None = 10,
    force_download: bool | None = False,
    min_grib2_size: float | None = 4.1 * 1024,
    min_nc_size: float | None = 360,
):
    # create data download client
    client = Client(source="ecmwf", model=model, resol=resolution)
    # get latest available forecast date
    latest_fdate = client.latest()
    # construct data store path
    downloads_path = get_data_store_path(source="jobs") / source
    # create data directory if it doesn't exist
    if not downloads_path.exists():
        downloads_path.mkdir(parents=True, exist_ok=True)
    steps = get_relevant_forecast_steps(start=start_step, final=final_step)

    if latest_fdate.date() >= data_date:
        requests = [
            {
                "date": data_date,
                "step": step,
                "stream": stream,
            }
            for step in steps
        ]
        grib2_files = []
        for request in requests:
            file_name = f"{request['date'].strftime('%Y%m%d')}000000-{request['step']}h-{stream}-ef.grib2"
            mask_file = get_dataset_file_path(
                source="open-ifs",
                mask_region=default_mask,
                data_date=data_date,
                file_name=file_name.replace(".grib2", ".nc"),
            )
            target_file = downloads_path / file_name
            target_size = 0 if not target_file.exists() else target_file.stat().st_size / (1024 * 1024)
            mask_size = 0 if not mask_file.exists() else mask_file.stat().st_size / (1024 * 1024)
            if (
                not (target_file.exists() or mask_file.exists())
                or not (target_size >= min_grib2_size or mask_size >= min_nc_size)
                or force_download
            ):
                get_url = client._get_urls(request=request, target=str(target_file), use_index=False)
                logger.info(f"trying {model} data download with payload {request} on URL {get_url.urls[0]}")
                for _ in range(re_try_times):
                    result = try_data_download(
                        client=client,
                        request=request,
                        target_file=str(target_file),
                        model=model,
                    )
                    if result is not None:
                        logger.info(
                            f"dataset for {model} forecast, {request['step']}h step, {result.datetime} "
                            + "successfully downloaded"
                        )
                        break
            else:
                logger.warning(
                    f"data download job for {request['step']}h {data_date} not executed because the file exist. "
                    + "Pass force_download=True to re-download the files"
                )
            # be sure grib2 file exists before adding to post-processing queue
            if target_file.exists():
                grib2_files.append(file_name)
        return grib2_files
    else:
        logger.warning(f"IFS forecast data for {data_date} is not available. Please try again later!")
        return None
