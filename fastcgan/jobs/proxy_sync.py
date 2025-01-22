from argparse import ArgumentParser
from pathlib import Path
from typing import Any, Literal

import requests
from bs4 import BeautifulSoup
from loguru import logger

from fastcgan.jobs.utils import get_data_store_path, get_directory_files


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
    forecasts_dir = get_data_store_path(source=data_source)
    data_dir = forecasts_dir / f"{dir_tree.replace('%20', ' ') if dir_tree != '/' else ''}"
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


def download_ens_dataset(source: str, year: str, month: str, day: str, start_time: str, valid_time: str):
    data_dir = get_data_store_path(source=f"{source}-count")
    model_path = "Jurre_brishti_counts" if source == "jurre-brishti" else "Mvua_kubwa_counts"
    dwnld_link = (
        f"http://megacorr.dynu.net/ICPAC/cGAN_examplePlots/data/{model_path}/{year}"
        + f"/counts_{year}{month}{day}_{start_time}_{valid_time}h.nc"
    )
    destination = data_dir / year / month
    if not destination.exists():
        destination.mkdir(parents=True)
    logger.debug(f"trying download of {dwnld_link}")
    try:
        file_path = destination / f"counts_{year}{month}{day}_{start_time}_{valid_time}h.nc"
        with requests.get(dwnld_link, stream=True) as r:
            logger.debug(f"downloading {dwnld_link} into {destination}")

            if r.status_code == 200:
                with file_path.open(mode="wb") as f:
                    f.write(r.content)
                logger.info(f"Finished downloading {dwnld_link}.\t" + f"Data stream was saved in {file_path.name}")
            else:
                logger.error(f"failed to download dataset file {dwnld_link} " + f"with http response {r.text}")

    except Exception as err:
        logger.error(f"failed to download {dwnld_link} with error {err}")


def retrieve_ens_counts_datasets_for_date(
    source: Literal["jurre-brishti", "mvua-kubwa"], data_date: str, forecast_dates: list[dict[str, Any]] | None = None
):
    logger.debug(f"received cgan ensemble counts retrieval task for {source} model {data_date}")
    year, month, day = (str(int(value)) for value in data_date.split("-"))
    if forecast_dates is None:
        model_path = "Jurre_brishti_counts" if source == "jurre-brishti" else "Mvua_kubwa_counts"
        dates_json = f"http://megacorr.dynu.net/ICPAC/cGAN_examplePlots/data/{model_path}/available_dates.json"
        r = requests.get(dates_json)
        if r.status_code == 200:
            forecast_dates = r.json()
    if forecast_dates is not None:
        for start_time in reversed(forecast_dates[year][month][day].keys()):
            for valid_time in reversed(forecast_dates[year][month][day][start_time]):
                download_ens_dataset(
                    source=source,
                    year=year,
                    month=month.rjust(2, "0"),
                    day=day.rjust(2, "0"),
                    start_time=str(start_time).rjust(2, "0"),
                    valid_time=valid_time,
                )


def retrieve_ens_counts_datasets(source: Literal["jurre-brishti", "mvua-kubwa"]):
    model_path = "Jurre_brishti_counts" if source == "jurre-brishti" else "Mvua_kubwa_counts"
    dates_json = f"http://megacorr.dynu.net/ICPAC/cGAN_examplePlots/data/{model_path}/available_dates.json"
    r = requests.get(dates_json)
    if r.status_code == 200:
        forecast_dates = r.json()
        for year in reversed(forecast_dates.keys()):
            for month in reversed(forecast_dates[year].keys()):
                for day in reversed(forecast_dates[year][month].keys()):
                    retrieve_ens_counts_datasets_for_date(
                        source=source,
                        forecast_dates=forecast_dates,
                        data_date=f"{year}-{str(month).rjust(2, '0')}-{str(day).rjust(2, '0')}",
                    )


def sync_data_source(
    sources: str,
    data_date: str | None = None,
    start_month: int | None = 1,
    final_month: int | None = 12,
    year: int | None = 2024,
    provider_url: str | None = "https://cgan.icpac.net",
) -> None:
    for source in sources.split(","):
        if source == "mvua-kubwa" or source == "jurre-brishti":
            if data_date is not None:
                retrieve_ens_counts_datasets_for_date(data_date=data_date, source=source)
            else:
                retrieve_ens_counts_datasets(source)
        else:
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
                    relative_path = datafile_url.replace(provider_url, "").replace(f"/{source}", "")
                    destination = get_data_store_path(source=source) / f"{relative_path}".replace("%20", " ")
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


def rename_gbmc_files():
    data_dir = get_data_store_path(source="cgan-ifs-6h-ens")
    for data_file in get_directory_files(data_path=data_dir, files=set()):
        new_path = Path(str(data_file).replace("cgan_ifs", "cgan_ifs_6h_ens").replace("gbmc_ifs", "cgan_ifs_6h_ens"))
        data_file.rename(new_path)


data_source_options = "cgan-forecast,mvua-kubwa,jurre-brishti,cgan-ifs,open-ifs"
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
        default=data_source_options,
        help=f"a list of data sources separated by comma: options are {data_source_options}",
    )
    parser.add_argument(
        "-dt",
        "--date",
        dest="data_date",
        type=str,
        default=None,
        help="data date in the format YYYY-MM-DD",
    )
    sync_data_source(**vars(parser.parse_args()))
