from argparse import ArgumentParser
from os import getenv
from pathlib import Path
from typing import Literal

import requests
from bs4 import BeautifulSoup
from loguru import logger


def crawl_http_dataset_links(data_page: str) -> list[str]:
    data_files = []
    logger.info(f"crawling dataset links from {data_page}")
    r = requests.get(data_page, allow_redirects=True)
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, features="html.parser")
        data_files.extend([f"{data_page}{a['href']}" for a in soup.find_all("a") if "../" not in a])
        logger.info(f"crawled a total of {len(data_files)} data files from {data_page}")
    else:
        logger.warning(
            f"failed to crawl links from {data_page} with status code {r.status_code} and response text {r.text}"
        )
    return data_files


def make_dataset_path(dataset_url: str, data_source: str, trim_part: str | None = "") -> None:
    dir_tree = "/".join(dataset_url.replace(trim_part, "").split("/"))
    forecasts_dir = getenv("FORECAST_DIR", "./data")
    data_dir = Path(f"{forecasts_dir}/{data_source}/{dir_tree.replace('%20', ' ') if dir_tree != '/' else ''}")
    if not data_dir.exists():
        data_dir.mkdir(parents=True)


def retrieve_cgan_data_links(
    start_month: int = 1,
    final_month: int = 12,
    year: int = 2024,
    provider_url: str = "https://cgan.icpac.net",
    data_path: Literal["cgan-forecast", "cgan-ifs", "open-ifs"] = "cgan-forecast",
) -> list[str]:
    data_page = f"{provider_url}/{data_path}/"
    ms_links = crawl_http_dataset_links(data_page)
    datasets_links = []
    for ms_link in ms_links:
        for month in range(start_month, final_month + 1):
            data_page_url = f"{ms_link}{year}/{str(month).rjust(2, '0')}/"
            make_dataset_path(
                dataset_url=data_page_url,
                trim_part=data_page,
                data_source=data_path,
            )
            datasets_links.extend(crawl_http_dataset_links(data_page_url))
    return datasets_links


def sync_data_source(
    sources: str,
    start_month: int = 1,
    final_month: int = 12,
    year: int = 2024,
    provider_url: str = "https://cgan.icpac.net",
) -> None:
    for source in sources.split(","):
        data_urls = retrieve_cgan_data_links(
            start_month=start_month,
            final_month=final_month,
            year=year,
            data_path=source,
            provider_url=provider_url,
        )
        for datafile_url in data_urls:
            logger.debug(f"trying download of {datafile_url}")
            try:
                forecasts_dir = getenv("FORECAST_DIR", "./data")
                relative_path = datafile_url.replace(provider_url, "").replace(f"/{source}", "")
                destination = Path(f"{forecasts_dir}/{source}/{relative_path}".replace("%20", " "))
                with requests.get(datafile_url, stream=True) as r:
                    logger.debug(f"downloading {datafile_url} into {destination}")

                    if r.status_code == 200:
                        with destination.open(mode="wb") as f:
                            f.write(r.content)
                    else:
                        logger.error(f"failed to download dataset file {datafile_url} with error {r.text}")
                        return None

                    logger.debug(f"Finished downloading {datafile_url}.\nData stream was saved in {f.name}")

            except Exception as e:
                logger.error(f"Error *{e}*")


if __name__ == "__main__":
    parser = ArgumentParser(
        prog="data-download",
        description="a program for downloading data from online cGAN sources",
        usage="python download.py -y <year> -sm <start-month> -fm <final-month>",
    )
    parser.add_argument("-y", "--year", dest="year", type=int, default=2024, help="data year")
    parser.add_argument(
        "-sm",
        "--start-month",
        dest="start_month",
        type=int,
        default=1,
        help="data start month for the year",
    )
    parser.add_argument(
        "-fm",
        "--final-month",
        dest="final_month",
        type=int,
        default=12,
        help="data final month for the year",
    )
    parser.add_argument(
        "-p",
        "--provider",
        dest="provider_url",
        type=str,
        default="https://cgan.icpac.net",
        help="data provider URL",
    )
    parser.add_argument(
        "-s",
        "--source",
        dest="sources",
        type=str,
        default="cgan-forecast,cgan-ifs,open-ifs",
        help="a list of data sources separated by comma: options are cgan-forecast,cgan-ifs,open-ifs",
    )
    sync_data_source(**vars(parser.parse_args()))
