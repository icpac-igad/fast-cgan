from __future__ import annotations

import os
import sys
import time
from argparse import ArgumentParser
from pathlib import Path

import schedule
from loguru import logger

from fastcgan.jobs.download import (
    generate_cgan_forecasts,
    post_process_downloaded_cgan_ifs,
    post_process_downloaded_ecmwf_forecasts,
    syncronize_open_ifs_forecast_data,
    syncronize_post_processed_ifs_data,
)
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
    logger.info(f"initializing {source} data sync and associated forecasts generation where necessary!")

    set_data_sycn_status(source=source, sync_type="download", status=False)
    set_data_sycn_status(source=source, sync_type="processing", status=False)

    # start data syncronization and forecasts generation jobs
    # follows the pattern; data sync -> post-processing -> forecast generation
    for hour in range(11, 24, 1):
        if source in [
            "mvua-kubwa-count",
            "jurre-brishti-count",
            "mvua-kubwa-ens",
            "jurre-brishti-ens",
        ]:
            schedule.every().day.at(f"{str(hour).rjust(2, '0')}:00", "Africa/Nairobi").do(
                syncronize_post_processed_ifs_data, model=source
            )
            schedule.every().day.at(f"{str(hour).rjust(2, '0')}:00", "Africa/Nairobi").do(
                post_process_downloaded_cgan_ifs, model=source
            )
            schedule.every().day.at(f"{str(hour).rjust(2, '0')}:00", "Africa/Nairobi").do(
                generate_cgan_forecasts, model=source
            )

        elif source == "open-ifs":
            # post_process_downloaded_ecmwf_forecasts(source="open-ifs")
            # syncronize_open_ifs_forecast_data()
            for hour in range(11, 24, 1):
                schedule.every().day.at(f"{str(hour).rjust(2, '0')}:00", "Africa/Nairobi").do(
                    syncronize_open_ifs_forecast_data, dateback=1
                )
                schedule.every().day.at(f"{str(hour).rjust(2, '0')}:00", "Africa/Nairobi").do(
                    post_process_downloaded_ecmwf_forecasts, source="open-ifs"
                )

    for job in schedule.get_jobs():
        logger.info(f"scheduled data syncronization and forecast generation task {job}")

    schedule.run_all(delay_seconds=10)

    while True:
        schedule.run_pending()
        time.sleep(30 * 60)
