import os
import json
import time
from datetime import datetime, timedelta, UTC

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from .cache_manager import get_url_hash
from .calculate_time_estimation import get_main_page_parsing_time_estimation, get_product_page_parsing_time_estimation, \
    make_time_estimation, get_number_of_products_per_page
from .configuration_manager import save_pagination_analysis_results, configuration_template, get_json_parameters
from .request import make_request
from .pagination import find_pagination
from .scraping_manager import generate_links, requests_manager_sync
from .parsing_manager import parsing_main
from .extract_product_page_urls import product_page_urls_extraction


# https://epicentrk.ua/
# https://allo.ua/  #   https://allo.ua/ua/jelektrovelosipedy/  #   https://allo.ua/ua/graficheskie-planshety/
# https://anitube.in.ua/anime/
# https://tsn.ua/politika


base_path = "./parsing_system/parsing_subsystem/data"


def get_page_html(url: str):
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--headless')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(options=options)
    driver.get(url)

    page_html = driver.page_source

    driver.quit()

    return page_html


def analyser(url: str, base_hash: str, hashed_name: str):
    """
        - Проведення аналізу перед скрейпом сайту, пошук пагінації (або скрол до низу)
        - Збір посилань на всі сторінки / з'ясування кількості сторінок
        - Можливо, перевірка чи однакові дані відображаються для користувачів з різних країн
    """
    start_time = time.time()
    initial_page = make_request(url=url, base_hash=base_hash, hashed_name=hashed_name)
    end_time = time.time()

    # Average time to scrape one page (T_avg)
    scraping_time_per_page = end_time - start_time
    print(f"scraping_time_per_page = {scraping_time_per_page}")

    # url_hash = get_url_hash(url=url)
    info_filename = f"{base_path}/{base_hash}/{hashed_name}/configuration.json"
    if not os.path.exists(info_filename):
        with open(info_filename, 'w', encoding='utf-8') as f:
            configuration_template_tmp = configuration_template
            configuration_template_tmp["base_url"] = url    # Can be a problem
            configuration_template_tmp["time_per_page"] = scraping_time_per_page

            # print(configuration_template_tmp)

            json.dump(configuration_template_tmp, f, ensure_ascii=False, indent=4)
    else:
        with open(info_filename, 'r', encoding='utf-8') as f:
            configuration_data = json.load(f)

        configuration_data["scraping_time_per_page"] = scraping_time_per_page

        with open(info_filename, 'w', encoding='utf-8') as f:
            json.dump(configuration_data, f, ensure_ascii=False, indent=4)

    # Пошук пагінації
    pagination_analysis_result = find_pagination(initial_page, url)
    # print(f"Pagination Analysis Result = {pagination_analysis_result}")
    save_pagination_analysis_results(pagination_analysis_result, info_filename)

    with open(info_filename, 'r', encoding='utf-8') as f:
        configuration_data = json.load(f)

    if not configuration_data.get("run_estimation_time"):
        main_page_soup = BeautifulSoup(get_page_html(configuration_data["base_url"]), 'html.parser')

        main_page_parsing_time = get_main_page_parsing_time_estimation(
            main_page_soup=main_page_soup,
            elements_to_parse=configuration_data["elements_to_parse"]
        )

        product_page_parsing_time = 0
        if configuration_data.get("product_page_url"):
            product_page_parsing_time = get_product_page_parsing_time_estimation(
                product_page_soup=BeautifulSoup(get_page_html(configuration_data["product_page_url"]), 'html.parser'),
                elements_to_parse=configuration_data["elements_to_parse"]
            )

        run_estimation_time = make_time_estimation(
            main_pages_number=configuration_data["pagination"]["number_of_pages"],
            product_per_page_number=get_number_of_products_per_page(page_soup=main_page_soup, elements_to_parse=configuration_data["elements_to_parse"]),
            main_page_parsing_time=main_page_parsing_time,
            product_page_parsing_time=product_page_parsing_time,
            threads_number=15,
            average_time_per_page=configuration_data["scraping_time_per_page"],
            sigma=0.2,
            network_latency=0.02
        )

        configuration_data["run_estimation_time"] = run_estimation_time

        with open(info_filename, 'w', encoding='utf-8') as file:
            json.dump(configuration_data, file, ensure_ascii=False, indent=4)

    # number_of_pages = pagination_analysis_result.get('number_of_pages')    # Кількість сторінок
    # print(f"Number of pages = {number_of_pages}")
    # link_to_page_attribute = pagination_analysis_result                    # Вигляд посилання на сторінку (посилання пагінації)


def scraper(url: str, base_hash: str, hashed_name: str):
    start_scrape_time = None
    analyser_data = get_json_parameters(url=url, base_hash=base_hash, hashed_name=hashed_name)

    # url_hash = get_url_hash(url=url)
    directory_name = f"{base_path}/{base_hash}/{hashed_name}/cache"
    os.makedirs(directory_name, exist_ok=True)

    # print("1")
    if not os.listdir(directory_name):
        configuration_filename = f"{directory_name}/scrape_info.json"
        start_scrape_time = (datetime.now(UTC) + timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')

        with open(configuration_filename, 'w', encoding='utf-8') as file:
            json.dump({"start_time": start_scrape_time, "list_of_pages": {}, "list_of_products": {}}, file, ensure_ascii=False, indent=4)

    print("2")
    url_template = analyser_data["pagination"]["pagination_link_template"]
    number_of_pages = analyser_data["pagination"]["number_of_pages"]

    list_of_main_links = generate_links(url_template, number_of_pages)

    print("3")
    # Отримуємо HTML сторінок за списком посилань
    # requests_manager(list_of_main_links, directory_name)
    requests_manager_sync(list_of_main_links, directory_name, max_concurrent=10)

    # region Collect Product Page URLS
    has_product_page_attributes = False
    elements_to_parse = analyser_data.get("elements_to_parse")
    # print("Elements to Parse: ", elements_to_parse)
    for element in elements_to_parse:
        # print(f"Element: {element}")
        if element["source"] == "Product Page":
            has_product_page_attributes = True
            break

    # print(f"has_product_page_attributes = {has_product_page_attributes}")
    if has_product_page_attributes:
        # print("Here1")
        list_of_product_page_links = product_page_urls_extraction(
            configuration_path=f"{base_path}/{base_hash}/{hashed_name}/configuration.json",
            scrape_info_directory_path=f"{base_path}/{base_hash}/{hashed_name}",
            analyser_data=analyser_data
        )
        # for link_idx, link in enumerate(list_of_product_page_links):
        #     print(f"Link {link_idx}: {link}")

        # print("List of Product Page Links: ", list_of_product_page_links)

        requests_manager_sync(list_of_product_page_links, directory_name, max_concurrent=10)

    # endregion

    if start_scrape_time:
        configuration_filename = f"{directory_name}/scrape_info.json"
        with open(configuration_filename, 'r', encoding='utf-8') as file:
            data = json.load(file)

        data['end_time'] = (datetime.now(UTC) + timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')

        with open(configuration_filename, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)


def parser(base_hash: str, hashed_name: str):
    parsing_main(base_hash=base_hash, hashed_name=hashed_name)


def main(url, base_hash, user_url_hash):
    # Провести початковий аналіз сторінки
    # print(f"Analysis")
    # analyser(url=url, base_hash=base_hash, hashed_name=user_url_hash)

    # Зробити потрібні запити
    print(f"\nScraping")
    scraper(url=url, base_hash=base_hash, hashed_name=user_url_hash)

    # Витягти потрібні дані
    print(f"\nParsing")
    parser(base_hash=base_hash, hashed_name=user_url_hash)

    return "CSV created successfully"


# if __name__ == '__main__':
#     main(
#         url="https://anitube.in.ua/anime/"
#     )
