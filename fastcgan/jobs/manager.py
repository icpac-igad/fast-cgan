from __future__ import annotations

import os
import sys
import time
from argparse import ArgumentParser
from pathlib import Path

import schedule
from loguru import logger

from fastcgan.jobs.download import (
    post_process_downloaded_cgan_ifs,
    post_process_downloaded_ecmwf_forecasts,
    syncronize_open_ifs_forecast_data,
    syncronize_post_processed_ifs_data,
)
from fastcgan.jobs.proxy_sync import sync_data_source
from fastcgan.jobs.stubs import cgan_ifs_literal, open_ifs_literal
from fastcgan.jobs.utils import set_data_sycn_status


def initialize_logger(source: cgan_ifs_literal | open_ifs_literal):
    logger_opts = {
        "enqueue": True,
        "backtrace": True,
        "diagnose": True,
        "format": "{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    }

    config = {
        "handlers": [
            {"sink": sys.stdout, "colorize": True, **logger_opts},
            {
                "sink": Path(os.getenv("LOGS_DIR", "./")) / f"{source}-jobs.log",
                "serialize": True,
                **logger_opts,
            },
        ],
        "extra": {"app": "cgan-jobs"},
    }
    logger.configure(**config)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "-s",
        "--source",
        dest="source",
        type=str,
        default="jurre-brishti",
        help="data-source to be downloaded. For each source, associated forecasts are generated where necessary",
    )
    source = parser.parse_args().source
    initialize_logger(source)
    logger.info(
        f"initializing {source} data sync and associated forecasts generation where necessary!"
    )

    set_data_sycn_status(source=source, status=0)

    if source == "mvua-kubwa":
        sync_data_source(sources=source)
        set_data_sycn_status(source="cgan-ifs-7d-ens", status=0)
        post_process_downloaded_cgan_ifs(model="cgan-ifs-7d-ens")
        syncronize_post_processed_ifs_data(model="cgan-ifs-7d-ens")
        for hour in range(11, 24, 1):
            schedule.every().day.at(
                f"{str(hour).rjust(2, '0')}:00", "Africa/Nairobi"
            ).do(syncronize_post_processed_ifs_data, model="cgan-ifs-7d-ens")
        for hour in range(11, 24, 1):
            schedule.every().day.at(
                f"{str(hour).rjust(2, '0')}:00", "Africa/Nairobi"
            ).do(sync_data_source, sources=source)

    elif source == "jurre-brishti":
        sync_data_source(sources=source)
        set_data_sycn_status(source="cgan-ifs-6h-ens", status=0)
        post_process_downloaded_cgan_ifs(model="cgan-ifs-6h-ens")
        syncronize_post_processed_ifs_data(model="cgan-ifs-6h-ens")
        for hour in range(11, 24, 1):
            schedule.every().day.at(
                f"{str(hour).rjust(2, '0')}:00", "Africa/Nairobi"
            ).do(syncronize_post_processed_ifs_data, model="cgan-ifs-6h-ens")
        for hour in range(11, 24, 1):
            schedule.every().day.at(
                f"{str(hour).rjust(2, '0')}:00", "Africa/Nairobi"
            ).do(sync_data_source, sources=source)

    elif source == "open-ifs":
        post_process_downloaded_ecmwf_forecasts(source="open-ifs")
        syncronize_open_ifs_forecast_data()
        for hour in range(11, 24, 1):
            schedule.every().day.at(
                f"{str(hour).rjust(2, '0')}:00", "Africa/Nairobi"
            ).do(syncronize_open_ifs_forecast_data, dateback=1)

    for job in schedule.get_jobs():
        logger.info(f"scheduled data syncronization and forecast generation task {job}")

    while True:
        all_jobs = schedule.get_jobs()
        schedule.run_pending()
        time.sleep(30 * 60)
