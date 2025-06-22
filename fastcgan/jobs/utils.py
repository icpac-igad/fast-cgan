import json
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal

import pandas as pd
import xarray as xr
from loguru import logger
from show_forecasts.constants import COUNTRY_NAMES
from show_forecasts.data_utils import get_region_extent

from fastcgan.jobs.stubs import cgan_ifs_literal, cgan_model_literal, open_ifs_literal
from fastcgan.models.settings import GanOutputDate
from fastcgan.tools.config import settings


def get_possible_forecast_dates(data_date: str | None = None, dateback: int = 4) -> list[date]:
    if data_date is not None:
        return [datetime.strptime(data_date, "%Y-%m-%d").date()]
    now = datetime.now()
    dates = [now.date()]
    for i in range(1, dateback + 1):
        new_date = now - timedelta(days=i)
        dates.append(new_date.date())
    return dates


def get_relevant_forecast_steps(start: int = 30, final: int = 54, step: int = 3) -> list[int]:
    return list(range(start, final + 1, step))


def get_data_store_path(
    source: str,
    mask_region: str | None = None,
    ens_ifs_models: list[str] = ["cgan-ifs-6h-ens", "cgan-ifs-7d-ens"],
) -> Path:
    if source == "jobs":
        data_dir_path = Path(settings.ASSETS_DIR_MAP["jobs"])
    else:
        base_dir = Path(settings.ASSETS_DIR_MAP["forecasts"]) / source
        data_dir_path = base_dir if mask_region is None or source in ens_ifs_models else Path(f"{base_dir}/{mask_region}")

    # return None if directory doesn't exist
    if not data_dir_path.exists():
        data_dir_path.mkdir(parents=True, exist_ok=True)

    return data_dir_path


def get_dataset_file_path(
    source: str,
    data_date: datetime | date,
    file_name: str,
    mask_region: str | None = None,
) -> Path:
    store_path = get_data_store_path(source=source, mask_region=mask_region) / str(data_date.year) / f"{str(data_date.month).rjust(2, '0')}"

    # create directory tree
    if not store_path.exists():
        store_path.mkdir(parents=True, exist_ok=True)

    mask_code = "" if mask_region is None else mask_region.replace(" ", "_").lower()

    return store_path / f"{mask_code}-{source.replace('-','_')}-{file_name}"


# recursive function that calls itself until all directories in data_path are traversed
def get_directory_files(data_path: Path, files: set[Path] = set(), file_extension: str = "nc") -> set[Path]:
    for item in data_path.iterdir():
        if item.is_file() and item.name.endswith(file_extension):
            files.add(item)
        elif item.is_dir():
            files.update(get_directory_files(data_path=item, files=files))
    return files


def get_forecast_data_files(
    source: str,
    mask_region: str | None = None,
) -> list[str]:
    store_path = get_data_store_path(source=source, mask_region=mask_region)
    if store_path is not None:
        data_files = get_directory_files(data_path=store_path, files=set())
        return [dfile.name for dfile in data_files]
    return []


def get_ecmwf_files_for_date(data_date: datetime, mask_region: str = COUNTRY_NAMES[0]) -> list[str]:
    steps = get_relevant_forecast_steps()
    return [f"{mask_region.lower().replace(' ', '_')}-open_ifs-{data_date.strftime('%Y%m%d')}000000-{step}h-enfo-ef.nc" for step in steps]


def get_forecast_data_dates(
    source: open_ifs_literal | cgan_ifs_literal | cgan_model_literal,
    mask_region: str | None = None,
    strict: bool | None = True,
) -> list[str]:
    data_files = get_forecast_data_files(source=source, mask_region=mask_region)
    if "-count" in source:
        data_dates = sorted({dfile.replace(".nc", "").split("_")[1] for dfile in data_files})
        return list(reversed([datetime.strptime(data_date, "%Y%m%d").strftime("%b %d, %Y") for data_date in data_dates]))

    data_dates = sorted({dfile.replace(".nc", "").split("-")[2].split("_")[0] for dfile in data_files})
    if not strict or source != "open-ifs":
        return list(reversed([datetime.strptime(data_date.replace("000000", ""), "%Y%m%d").strftime("%b %d, %Y") for data_date in data_dates]))
    tmp_dates = []
    for date_str in data_dates:
        data_date = datetime.strptime(date_str.replace("000000", ""), "%Y%m%d")
        files_for_date = get_ecmwf_files_for_date(data_date)
        in_files = [True if dfile in data_files else False for dfile in files_for_date]
        if False not in in_files:
            tmp_dates.append(data_date)
    return [data_date.strftime("%b %d, %Y") for data_date in reversed(tmp_dates)]


def get_cgan_forecast_dates(
    source: cgan_model_literal,
    mask_region: str | None = None,
) -> list[GanOutputDate]:
    data_files = get_forecast_data_files(source=source, mask_region=mask_region)
    if "-count" in source:
        ptn = re.compile(r"^counts_([0-9]{8})_([0-9]{2})_([0-9]{1,3})h.nc$")
        fmeta = [ptn.split(dfile)[1:-1] for dfile in data_files]
        df = (
            pd.DataFrame(data=fmeta, columns=["init_date", "init_time", "valid_time"])
            .assign(
                valid_time=lambda x: x["valid_time"].apply(lambda value: int(value)),
                init_date=lambda x: x["init_date"].apply(lambda value: datetime.strptime(value, "%Y%m%d")),
            )
            .sort_values(by=["init_date", "valid_time"], ascending=False)
            .assign(init_date=lambda x: x["init_date"].apply(lambda value: value.strftime("%Y-%b-%d")))
        )
        return json.loads(df.to_json(orient="records"))
    elif "-ens" in source:
        mask_region = COUNTRY_NAMES[0] if mask_region is None else mask_region
        ptn = re.compile(f"^{mask_region.lower().replace(' ','_')}-{source.replace('-','_')}" + "-([0-9]{8})_([0-9]{2})Z.nc")
        fmeta = [ptn.split(dfile)[1:-1] for dfile in data_files]
        df = (
            pd.DataFrame(data=fmeta, columns=["init_date", "init_time"])
            .assign(
                init_time=lambda x: x["init_time"].apply(lambda value: int(value)),
                init_date=lambda x: x["init_date"].apply(lambda value: datetime.strptime(value, "%Y%m%d")),
            )
            .sort_values(by=["init_date", "init_time"], ascending=False)
            .assign(init_date=lambda x: x["init_date"].apply(lambda value: value.strftime("%Y-%b-%d")))
        )
        return json.loads(df.to_json(orient="records"))
    else:
        return []


def get_forecast_initialization_times(
    data_date: str | None = None,
    model: Literal["jurre-brishti-ens", "jurre-brishti-count"] = "jurre-brishti-ens",
) -> list[str]:
    if data_date is None:
        fcst_dates = get_forecast_data_dates(source=model)
        if not len(fcst_dates):
            return []
        data_date = fcst_dates[0]
    fcst_date = datetime.strptime(data_date, "%b %d, %Y").strftime("%Y%m%d")
    data_files = get_forecast_data_files(source=model)
    if "-count" in model:
        return list({data_file.split("_")[2] for data_file in data_files if fcst_date in data_file})
    return list({data_file.split("_")[-1].replace("Z.nc", "") for data_file in data_files if fcst_date in data_file})


def get_gan_forecast_dates(
    source: str,
    mask_region: str | None = None,
) -> list[str]:
    store_path = get_data_store_path(source=source, mask_region=mask_region)
    if store_path is None:
        return []
    data_files = get_directory_files(data_path=store_path, files=set())
    if "count" in source:
        data_dates = set()
        for data_file in data_files:
            file_parts = data_file.name.split("_")
            data_dates.add(f"{file_parts[1]}_{file_parts[2]}")
        return list(data_dates)
    return list({dfile.name.replace("Z.nc", "").split("-")[2] for dfile in data_files})


def get_gan_forecast_initializations(
    source: str,
    mask_region: str | None = COUNTRY_NAMES[0],
) -> dict[str, list[str]]:
    init_dates = {}
    for data_date in reversed(get_gan_forecast_dates(source=source, mask_region=mask_region)):
        date_str, init_time = data_date.split("_")
        if date_str in init_dates.keys():
            init_dates[date_str] = init_dates[date_str].append(init_time)
        else:
            init_dates[date_str] = [init_time]
    # output {YYYYMMMDD: [init_time]}
    return init_dates


def standardize_dataset(d: xr.DataArray | xr.Dataset):
    if "x" in d.dims and "y" in d.dims:
        d = d.rename({"x": "longitude", "y": "longitude"})
    if "lon" in d.dims and "lat" in d.dims:
        d = d.rename({"lon": "longitude", "lat": "latitude"})
    return d


def slice_dataset_by_bbox(ds: xr.Dataset, bbox: list[float]):
    try:
        ds = ds.sel(longitude=slice(bbox[0], bbox[1]))
    except Exception as err:
        logger.error(f"failed to slice dataset by bbox with error {err}. Dataset dims: {ds.dims}")
        return None
    else:
        if ds.latitude.values[0] < ds.latitude.values[-1]:
            ds = ds.sel(latitude=slice(bbox[2], bbox[3]))
        else:
            ds = ds.sel(latitude=slice(bbox[3], bbox[2]))
        return ds


def save_to_new_filesystem_structure(
    file_path: Path,
    source: cgan_model_literal | cgan_ifs_literal,
    mask_region: str | None = COUNTRY_NAMES[0],
    min_gbmc_size: int = 42 * 1024,
    part_to_replace: str | None = None,
    ens_ifs_models: list[str] = ["cgan-ifs-6h-ens", "cgan-ifs-7d-ens"],
) -> None:
    logger.debug(f"received filesystem migration task for - {source} - {file_path}")
    if source in ens_ifs_models and file_path.stat().st_size / 1024 < float(min_gbmc_size):
        logger.debug(f"{file_path.name} migration task skipped due to invalid size of {file_path.stat().st_size / 1024}Kb")
        file_path.unlink()
    else:
        logger.debug(f"processing {file_path.name} migration into revised filesystem structure")
        set_data_sycn_status(source=source, sync_type="processing", status=True)
        try:
            ds = standardize_dataset(xr.open_dataset(file_path, decode_times=False))
        except Exception as err:
            logger.error(f"failed to read {source} data file {file_path} with error {err}")
            file_path.unlink(missing_ok=True)
        else:
            fname = file_path.name if part_to_replace is None else file_path.name.replace(part_to_replace, "")
            data_date = datetime.strptime(fname.replace("Z.nc", ""), "%Y%m%d_%H")
            target_file = get_dataset_file_path(
                source=source,
                data_date=data_date,
                file_name=fname,
                mask_region=mask_region,
            )
            logger.debug(f"migrating dataset file {file_path} to {target_file}")
            errors = []
            try:
                ds.to_netcdf(target_file, mode="w", format="NETCDF4")
            except Exception as error:
                errors.append(f"failed to save {target_file} with error {error}")
            else:
                logger.debug(f"succeefully saved dataset file {file_path} to {target_file}")
                if source not in ens_ifs_models:  # split cGAN forecasts by country
                    for country_name in COUNTRY_NAMES[1:]:
                        # create country slices
                        sliced = slice_dataset_by_bbox(
                            ds=ds,
                            bbox=get_region_extent(shape_name=country_name),  # type: ignore
                        )
                        if sliced is None:
                            errors.append(f"error slicing {file_path.name} for bbox {country_name}")
                        else:
                            slice_target = get_dataset_file_path(
                                source=source,
                                data_date=data_date,
                                file_name=fname,
                                mask_region=country_name,
                            )
                            logger.debug(f"migrating dataset slice for {country_name} to {slice_target}")
                            try:
                                sliced.to_netcdf(slice_target, mode="w", format="NETCDF4")
                            except Exception as error:
                                errors.append(f"failed to save {slice_target} with error {error}")
                            else:
                                logger.debug(f"succeefully migrated dataset slice for {country_name}")
            if not len(errors):
                logger.debug(f"removing forecast file {file_path.name} after a successful migration")
                file_path.unlink(missing_ok=True)
        set_data_sycn_status(source=source, sync_type="processing", status=False)


# migrate dataset files from initial filesystem structure to revised.
def migrate_files(source: cgan_model_literal | cgan_ifs_literal):
    store = Path(os.getenv("DATA_STORE_DIR", str(Path("./store")))).absolute()
    data_dir = None
    part_to_replace = ""
    match source:
        case "cgan-ifs":
            data_dir = store / "IFS"
            part_to_replace = "IFS_"
        case "cgan-forecast":
            data_dir = store / "GAN_forecasts"
            part_to_replace = "GAN_"
        case "open-ifs":
            data_dir = store / "interim" / "EA" / "open-ifs" / "enfo"
            part_to_replace = ""
    if data_dir is not None:
        data_files = [fpath for fpath in data_dir.iterdir() if fpath.name.endswith(".nc")]
        logger.info(f"processing file-structure migration for {len(data_files)} {source} data files")
        # copy data_files to new files path
        for dfile in data_files:
            save_to_new_filesystem_structure(file_path=dfile, source=source, part_to_replace=part_to_replace)


def set_data_sycn_status(
    sync_type: Literal["download", "processing"],
    source: cgan_model_literal | cgan_ifs_literal | open_ifs_literal,
    status: bool | None = True,
):
    status_file = Path(os.getenv("LOGS_DIR", "./")) / "data-sync-tasks-status.json"
    if not status_file.exists():
        with open(status_file, "w") as sf:
            sf.write(json.dumps({sync_type: {source: status}}))
    else:
        try:
            with open(status_file) as sf:
                data = json.loads(sf.read())
        except Exception as err:
            logger.warning(f"failed to read contents of tasks status log file with error {err}")
            logger.debug(f"recreating tasks status log file {status_file}")
            with open(status_file, "w") as sf:
                sf.write(json.dumps({sync_type: {source: status}}))
        else:
            if sync_type not in data.keys():
                data.update({sync_type: {source: status}})
            else:
                data[sync_type][source] = status
            with open(status_file, "w") as sf:
                sf.write(json.dumps(data))


def get_data_sycn_status(
    sync_type: Literal["download", "processing"],
    source: cgan_model_literal | cgan_ifs_literal | open_ifs_literal,
) -> bool:
    status_file = Path(os.getenv("LOGS_DIR", "./")) / "data-sync-tasks-status.json"

    if not status_file.exists():
        return False

    # check if there is an active data syncronization job
    with open(status_file) as sf:
        data = json.loads(sf.read())
        if source in data[sync_type].keys():
            return data[sync_type][source]
        return False


def get_processing_task_status(sync_type: str | None = "processing") -> bool:
    status_file = Path(os.getenv("LOGS_DIR", "./")) / "data-sync-tasks-status.json"
    if not status_file.exists():
        return False

    with open(status_file) as sf:
        data = json.loads(sf.read())
        if sync_type not in data.keys():
            return False
        return not all(value is False for value in data[sync_type].values())
