import concurrent
from argparse import ArgumentParser
from multiprocessing import cpu_count
from os import getenv

from loguru import logger
from paramiko import AutoAddPolicy, SFTPClient
from paramiko.client import SSHClient

from fastcgan.jobs.stubs import cgan_ifs_literal
from fastcgan.jobs.utils import get_data_store_path, get_gan_forecast_dates


def get_sftp_session(
    host: str | None = None,
    user: str | None = None,
    port: int | None = 22,
    key_file: str | None = None,
    allow_agent: bool | None = False,
    look_for_keys: bool | None = False,
    max_retry: int | None = 50,
) -> SFTPClient | str:
    client = SSHClient()
    client.set_missing_host_key_policy(AutoAddPolicy())
    retry_count, trial_error = (0, None)

    hostname = host if host is not None else getenv("IFS_SERVER_HOST", "domain.example")
    username = user if user is not None else getenv("IFS_SERVER_USER", "username")
    private_key = key_file if key_file is not None else getenv("IFS_PRIVATE_KEY", "/srv/ssl/private.key")
    assert f"{username}@{hostname}" != "username@domain.example", "you must specify IFS data source server address"
    while retry_count != max_retry:
        try:
            client.connect(
                hostname=hostname,
                port=port,
                username=username,
                key_filename=private_key,
                allow_agent=allow_agent,
                look_for_keys=look_for_keys,
            )
            return client.open_sftp()
        except Exception as err:
            trial_error = err
            retry_count += 1
    return trial_error


def fetch_remote_file(
    remote_path: str,
    local_path: str,
    host: str | None = None,
    user: str | None = None,
    key_file: str | None = None,
) -> str | None:
    file_name = remote_path.split("/")[-1]
    logger.debug(f"received sftp data download for {file_name}")
    sftp = get_sftp_session(host=host, user=user, key_file=key_file)
    if isinstance(sftp, str):
        logger.error(f"failed to open sftp transfer tunnel with error {sftp}")
        return None
    logger.debug(f"successfully opened sftp transfer tunnel for {file_name}")
    try:
        logger.debug(f"fetching data contents for {remote_path} and saving into {local_path}")
        # stream data and save on disk for ingestion
        sftp.get(remotepath=remote_path, localpath=local_path)
    except Exception as err:
        logger.error(f"failed to fetch sftp file from path {remote_path} with error {err}")
        return None
    return file_name


def sync_sftp_data_files(
    model: cgan_ifs_literal,
    host: str | None = None,
    user: str | None = None,
    key_file: str | None = None,
):
    logger.debug(f"received sftp data syncronization request for {model}")
    # open sftp connection session
    sftp = get_sftp_session(host=host, user=user, key_file=key_file)
    if isinstance(sftp, str):
        logger.error(f"failed to open sftp transfer tunnel with error {sftp}")
        return None
    src_dir = getenv(
        "IFS_DATA_DIR",
        f"/data/{'Operational' if model == 'cgan-ifs-6h-ens' else 'Operational_7d'}",
    )
    dest_dir = get_data_store_path(source="jobs") / model
    # list files in the target remote directory
    remote_files = sftp.listdir(path=src_dir)
    # compare with local filesystem to determine files to be synced
    data_dates = [remote_file.replace("IFS_", "").replace("Z.nc", "") for remote_file in remote_files]
    ifs_dates = get_gan_forecast_dates(source=model)
    to_sync = [f"IFS_{data_date}Z.nc" for data_date in data_dates if data_date not in ifs_dates]
    logger.debug(f"processing sftp data synscronization for {len(to_sync)} {model} source files")
    synced_files = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=cpu_count() * 4) as executor:
        results = [
            executor.submit(
                fetch_remote_file,
                remote_path=f"{src_dir}/{ifs_file}",
                local_path=f"{dest_dir}/{ifs_file}",
            )
            for ifs_file in to_sync
        ]
        for future in concurrent.futures.as_completed(results):
            if future.result() is not None:
                gbmc_file = future.result()
                if gbmc_file is not None:
                    synced_files.append(gbmc_file)


if __name__ == "__main__":
    parser = ArgumentParser(
        prog="sftp-data-sync",
        description="a program for syncronizing sftp data",
        usage="python sftp.py -m <model>",
    )
    parser.add_argument(
        "-m",
        "--model",
        dest="model",
        type=str,
        default="cgan-ifs-6h-ens",
        help="IFS forecast model name",
    )
    args = parser.parse_args()
    sync_sftp_data_files(args.model)
