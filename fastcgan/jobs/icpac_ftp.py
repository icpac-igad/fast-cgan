from argparse import ArgumentParser  # noqa: I001
from datetime import datetime
from typing import Literal
from os import getenv
import requests
from bs4 import BeautifulSoup
from loguru import logger
from re import compile
from fastcgan.jobs.stubs import cgan_model_literal, open_ifs_literal
from fastcgan.jobs.utils import get_data_store_path


def deep_crawl_http_dataset_links(data_page: str, data_ext: str | None = "nc", links: set[str] | None = set()) -> list[str]:
    logger.debug(f"starting data links crawler task for {data_page}")
    r = requests.get(data_page, allow_redirects=True)
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, features="html.parser")
        today = datetime.now()
        env = getenv("ENVIRONMENT", "local")
        sync_months = getenv("SYNC_DATA_MONTHS", f"{str(today.month).rjust(2, '0')}")
        link_regx = data_page + r"/([a-zA-Z0-9%\s]{5,15})/"
        entry_ptn = compile(link_regx)
        for a in soup.find_all("a"):
            href = f"{data_page}/{a['href']}"
            if href.endswith(data_ext):
                links.add(href)
            if env in ["production", "staging"]:
                if "../" not in href and href.endswith("/"):
                    links = deep_crawl_http_dataset_links(data_page=href[:-1], links=links)
            else:
                if "open-ifs" in href and bool(entry_ptn.match(href)):
                    for month in sync_months.split(","):
                        links = deep_crawl_http_dataset_links(data_page=f"{href}{today.year}/{month}", links=links)
                elif "../" not in href and href.endswith("/") and str(today.year) in href:
                    for month in sync_months.split(","):
                        links = deep_crawl_http_dataset_links(data_page=f"{href}{month}", links=links)
        logger.info(f"crawled a total of {len(links)} data files from {data_page}")
    else:
        logger.warning(f"failed to crawl links from {data_page} with status code {r.status_code} due to {r.reason}")
    return links


def download_open_ifs_ens_dataset(link: str):
    file_name = link.split("/")[-1]
    filename_parts = file_name.split("-")
    destination = get_data_store_path(source="open-ifs", mask_region=filename_parts[0].replace("_", " ").title())
    data_date = datetime.strptime(filename_parts[2], "%Y%m%d000000")
    file_dir = destination / str(data_date.year) / f"{data_date.month:02d}"
    if not file_dir.exists():
        file_dir.mkdir(parents=True, exist_ok=True)
    file_path = file_dir / file_name
    if not file_path.exists():
        logger.debug(f"trying download of {link}")
        try:
            with requests.get(link, stream=True) as r:
                logger.debug(f"downloading {link} into {file_path}")

                if r.status_code == 200:
                    with file_path.open(mode="wb") as f:
                        f.write(r.content)
                    logger.info(f"Finished downloading {link}.\t" + f"Data stream was saved into {file_path.name}")
                else:
                    logger.error(f"failed to download dataset file {link} " + f"with http response {r.text}")

        except Exception as err:
            logger.error(f"failed to download {link} with error {err}")


def download_cgan_ifs_ens_dataset(model_name: Literal["cgan-ifs-6h-ens", "cgan-ifs-7d-ens"], link: str):
    link_parts = link.split("/")
    destination = get_data_store_path(source=model_name) / link_parts[-3] / link_parts[-2]
    if not destination.exists():
        destination.mkdir(parents=True, exist_ok=True)
    file_path = destination / link_parts[-1]
    if not file_path.exists():
        logger.debug(f"trying download of {link}")
        try:
            with requests.get(link, stream=True) as r:
                logger.debug(f"downloading {link} into {file_path}")

                if r.status_code == 200:
                    with file_path.open(mode="wb") as f:
                        f.write(r.content)
                    logger.info(f"Finished downloading {link}.\t" + f"Data stream was saved into {file_path.name}")
                else:
                    logger.error(f"failed to download dataset file {link} " + f"with http response {r.text}")

        except Exception as err:
            logger.error(f"failed to download {link} with error {err}")


def sync_icpac_ifs_data(
    model: cgan_model_literal | open_ifs_literal,
    provider_url: str | None = "https://cgan.icpac.net/ftp",
) -> None:
    if model == "open-ifs":
        links = deep_crawl_http_dataset_links(data_page=f"{provider_url}/open-ifs")
        logger.info(f"crawled a total of {len(links)} open-ifs data files from {provider_url}")
        for link in sorted(links, reverse=True):
            download_open_ifs_ens_dataset(link=link)
    else:
        source_model = "cgan-ifs-6h-ens" if "jurre-brishti" in model else "cgan-ifs-7d-ens"
        links = deep_crawl_http_dataset_links(data_page=f"{provider_url}/{source_model}")
        logger.info(f"crawled a total of {len(links)} data files from {provider_url}")
        for link in sorted(links, reverse=True):
            download_cgan_ifs_ens_dataset(model_name=source_model, link=link)


if __name__ == "__main__":
    parser = ArgumentParser(
        prog="data-download",
        description="a program for downloading data from ICPAC FTP server",
        usage="python icpac_ftp.py -m <model-name>",
    )
    parser.add_argument(
        "-m",
        "--model",
        dest="model",
        type=str,
        required=True,
        help="cGAN model name. Options are jurre-brishti, mvua-kubwa, open-ifs",
    )
    sync_icpac_ifs_data(**vars(parser.parse_args()))
