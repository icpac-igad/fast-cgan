from argparse import ArgumentParser
from datetime import datetime
from typing import Literal

import requests
from bs4 import BeautifulSoup
from loguru import logger

from fastcgan.jobs.stubs import cgan_model_literal, open_ifs_literal
from fastcgan.jobs.utils import get_data_store_path


def deep_crawl_http_dataset_links(data_page: str, data_ext: str | None = "nc", links: set[str] | None = set()) -> list[str]:
    r = requests.get(data_page, allow_redirects=True)
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, features="html.parser")
        for a in soup.find_all("a"):
            href = f"{data_page}/{a['href']}"
            if href.endswith(data_ext):
                links.add(href)
            elif "../" not in href and href.endswith("/"):
                links = deep_crawl_http_dataset_links(data_page=href[:-1], links=links)
        logger.info(f"crawled a total of {len(links)} data files from {data_page}")
    else:
        logger.warning(f"failed to crawl links from {data_page} with status code {r.status_code} and response text {r.text}")
    return links


def download_open_ifs_ens_dataset(link: str):
    file_name = link.split("/")[-1]
    filename_parts = file_name.split("-")
    destination = get_data_store_path(source="open-ifs", mask_region=filename_parts[0].replace("_", "").title())
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
    jobs_dir = get_data_store_path(source="jobs")
    destination = jobs_dir / model_name
    if not destination.exists():
        destination.mkdir(parents=True, exist_ok=True)
    file_name = link.split("/")[-1]
    file_path = destination / file_name
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
