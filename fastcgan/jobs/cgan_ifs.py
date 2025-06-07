import subprocess
from argparse import ArgumentParser
from datetime import datetime
from os import getenv
from time import sleep

import schedule
from loguru import logger
from show_forecasts.constants import COUNTRY_NAMES

from fastcgan.jobs.counts import make_cgan_forecast_counts
from fastcgan.jobs.icpac_ftp import sync_icpac_ifs_data
from fastcgan.jobs.sftp import sync_sftp_data_files
from fastcgan.jobs.stubs import cgan_model_literal
from fastcgan.jobs.utils import (
    get_data_store_path,
    get_data_sycn_status,
    get_dataset_file_path,
    get_gan_forecast_dates,
    get_processing_task_status,
    migrate_files,
    save_to_new_filesystem_structure,
    set_data_sycn_status,
)


def generate_cgan_forecasts(
    model: cgan_model_literal,
    mask_region: str | None = COUNTRY_NAMES[0],
    min_gbmc_size: int | None = 260,
):
    # start an infinite loop that will execute when other data-processing jobs are completed
    while True:
        if not get_processing_task_status():
            logger.debug(f"starting cGAN forecast generation for {model} model")
            set_data_sycn_status(source=model, sync_type="processing", status=True)
            gbmc_source = (
                "cgan-ifs-7d-ens" if "mvua-kubwa" in model else "cgan-ifs-6h-ens"
            )
            ifs_dates = sorted(
                get_gan_forecast_dates(mask_region=None, source=gbmc_source),
                reverse=True,
            )
            gan_dates = get_gan_forecast_dates(
                mask_region=None if "count" in model else mask_region, source=model
            )
            missing_dates = [
                data_date
                for data_date in ifs_dates
                if data_date not in gan_dates and int(data_date[:4]) > 2018
            ]
            logger.debug(
                f"launching forecast generation workers for data dates {' ==> '.join(missing_dates)}"
            )
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
                store_path = get_data_store_path(
                    source=gbmc_source, mask_region=mask_region
                )
                gan_ifs = str(gbmc_filename).replace(f"{store_path}/", "")
                logger.debug(
                    f"starting {model} forecast generation with IFS file {gan_ifs}"
                )
                py_script = (
                    "forecast_date.py" if "mvua-kubwa" in model else "test_forecast.py"
                )
                gan_status = subprocess.call(
                    shell=True,
                    cwd=f'{getenv("WORK_HOME","/opt/cgan")}/ensemble-cgan/dsrnngan',
                    args=f"python {py_script} -f {gan_ifs}",
                )
                cgan_file_path = (
                    get_data_store_path(source="jobs")
                    / model
                    / f"GAN_{date_str}_{init_time}Z.nc"
                )
                if gan_status:
                    logger.error(
                        f"failed to generate {model} cGAN forecast for {missing_date}. deleting intermediary forecast file {cgan_file_path}"
                    )
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
    # TODO: split tasks to coiled clusters
    while True:
        if not get_processing_task_status():
            source_model = (
                "cgan-ifs-6h-ens" if "jurre-brishti" in model else "cgan-ifs-7d-ens"
            )
            downloads_path = get_data_store_path(source="jobs") / source_model
            if downloads_path.exists():
                gbmc_files = [
                    file_path
                    for file_path in downloads_path.iterdir()
                    if file_path.name.endswith(".nc")
                ]
                if not len(gbmc_files):
                    logger.warning(
                        f"no un-processed {source_model} datasets found. task skipped!"
                    )
                else:
                    logger.info(
                        f"starting {source_model} forecasts batch post-processing task for "
                        + f"{'  <---->  '.join([gbmc_file.name for gbmc_file in gbmc_files])}"
                    )
                    for gbmc_file in gbmc_files:
                        save_to_new_filesystem_structure(
                            file_path=gbmc_file,
                            source=source_model,
                            part_to_replace=(
                                "IFS_"
                                if "IFS_" in gbmc_file.name
                                else f"east_africa-{source_model.replace('-','_')}-"
                            ),
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
    # syncronize on cGAN ens jobs ony!
    if (
        not get_data_sycn_status(source=model, sync_type="download")
        and "count" not in model
    ):
        # set data syncronization status
        set_data_sycn_status(source=model, sync_type="download", status=True)
        # sync from ICPAC if GBMC server credentials are not provided
        if (
            getenv("IFS_SERVER_HOST", "domain.example") == "domain.example"
            or getenv("IFS_SERVER_USER", "username") == "username"
            or getenv("IFS_PRIVATE_KEY", None) is None
        ):
            sync_icpac_ifs_data(model=model)
        else:
            sync_sftp_data_files(model="cgan-ifs-6h-ens" if "jurre-brishti" in model else "cgan-ifs-7d-ens")
        set_data_sycn_status(source=model, sync_type="download", status=False)
    post_process_downloaded_cgan_ifs(model=model)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "-m",
        "--model",
        dest="model",
        type=str,
        default="jurre-brishti-ens",
        help="forecast model or process to be executed. options are: jurre-brishti-ens,mvua-kubwa-ens,jurre-brishti-count,mvua-kubwa-count",
    )
    parser.add_argument(
        "-c",
        "--command",
        dest="command",
        type=str,
        help="command to be executed. either download or process",
        default="download",
    )
    args = parser.parse_args()
    dict_args = {key: value for key, value in args.__dict__.items() if key != "command"}
    set_data_sycn_status(source=args.model, sync_type="download", status=False)
    if args.command == "download":
        syncronize_post_processed_ifs_data(model=args.model)
    elif args.command == "migrate":
        for source in ["cgan-ifs", "cgan-forecast"]:
            migrate_files(source)
    elif args.command == "process":
        post_process_downloaded_cgan_ifs(
            model="cgan-ifs-7d-ens" if args.model == "mvua-kubwa" else "cgan-ifs-6h-ens"
        )
    else: # drop to scheduler by default
        # no need of executing sync task on count jobs
        if 'ens' in args.model:
            schedule.every().hour.do(syncronize_post_processed_ifs_data, model=args.model)
        schedule.every().hour.do(post_process_downloaded_cgan_ifs, model=args.model)
        schedule.every().hour.do(generate_cgan_forecasts, model=args.model)

        schedule.run_all(delay_seconds=10)

        while True:
            schedule.run_pending()
            sleep(10)
