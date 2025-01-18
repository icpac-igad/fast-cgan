import os
import sys
import time
from pathlib import Path

import schedule
from loguru import logger

from fastcgan.jobs.download import (
    post_process_downloaded_cgan_ifs,
    post_process_downloaded_ecmwf_forecasts,
    syncronize_open_ifs_forecast_data,
    syncronize_post_processed_ifs_data,
)
from fastcgan.jobs.utils import set_data_sycn_status

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
            "sink": Path(os.getenv("LOGS_DIR", "./")) / "cgan-jobs.log",
            "serialize": True,
            **logger_opts,
        },
    ],
    "extra": {"app": "cgan-jobs"},
}
logger.configure(**config)

logger.info("executing jobs warm-up tasks on scripts initialization!")
post_process_downloaded_cgan_ifs()
post_process_downloaded_ecmwf_forecasts()
set_data_sycn_status(source="cgan-forecast", status=0)
set_data_sycn_status(source="open-ifs", status=0)
syncronize_post_processed_ifs_data()
syncronize_open_ifs_forecast_data(dateback=1)

for hour in range(11, 24, 1):
    schedule.every().day.at(f"{str(hour).rjust(2, '0')}:00", "Africa/Nairobi").do(syncronize_post_processed_ifs_data)
    schedule.every().day.at(f"{str(hour).rjust(2, '0')}:00", "Africa/Nairobi").do(
        syncronize_open_ifs_forecast_data, dateback=1
    )


for job in schedule.get_jobs():
    logger.info(f"scheduled forecasts data download task {job}")

while True:
    all_jobs = schedule.get_jobs()
    schedule.run_pending()
    time.sleep(30 * 60)
