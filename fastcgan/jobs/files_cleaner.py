from datetime import datetime
from os import getenv
from pathlib import Path
from time import sleep

import schedule
from loguru import logger

from fastcgan.jobs.utils import get_directory_files


def delete_old_files() -> None:
    max_age = getenv("MAX_FILE_AGE_DAYS", None)
    try:
        max_age = int(max_age)
    except Exception as err:
        logger.error(f"failed to convert max file age to integer with error {err}")
    else:
        files_dir = getenv("FORECASTS_DATA_DIR", None)
        files = get_directory_files(data_path=Path(files_dir), files=set())
        for file in files:
            file_age = (datetime.now() - datetime.fromtimestamp(file.stat().st_atime)).days
            if file_age > max_age:
                logger.info(f"deleting data file {file} with an age of {file_age} days")
                file.unlink(missing_ok=True)
            # delete empty directories
            parent = file.parent
            for _ in file.parts[:-1]:
                if parent.is_dir() and not len(list(parent.iterdir())):
                    logger.info(f"deleting empty directory {parent}")
                    parent.rmdir()
                else:
                    break
                parent = parent.parent


if __name__ == "__main__":
    files_dir = getenv("FORECASTS_DATA_DIR", None)
    if files_dir is None:
        logger.error(
            "FORECASTS_DATA_DIR environment variable is undefined. Old data cleaner jobs stopped!"
        )
        exit(1)
    max_age = getenv("MAX_FILE_AGE_DAYS", None)
    if max_age is None:
        logger.error(
            "MAX_FILE_AGE_DAYS environment variable is undefined. Old data cleaner jobs stopped!"
        )
        exit(1)
    logger.debug(
        f"starting old data files cleaner scheduled jobs for data directory {files_dir} "
        + f"with files older than {max_age} deleted together with empty directories"
    )
    schedule.every().day.at("00:00").do(delete_old_files)
    schedule.run_all(delay_seconds=10)
    while True:
        schedule.run_pending()
        sleep(30)
