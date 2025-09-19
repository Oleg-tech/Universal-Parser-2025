import os
import json
from datetime import datetime, timedelta, UTC

from .cache_manager import get_url_hash
from .configuration_manager import save_pagination_analysis_results, configuration_template, get_json_parameters
from .request import make_request
from .pagination import find_pagination
from .scraping_manager import generate_links, requests_manager
from .parsing_manager import parsing_main


# https://epicentrk.ua/
# https://allo.ua/  #   https://allo.ua/ua/jelektrovelosipedy/  #   https://allo.ua/ua/graficheskie-planshety/
# https://anitube.in.ua/anime/
# https://tsn.ua/politika


base_path = "./parsing_system/parsing_subsystem/data"


def analyser(url: str, base_hash: str, hashed_name: str):
    """
        - Проведення аналізу перед скрейпом сайту, пошук пагінації (або скрол до низу)
        - Збір посилань на всі сторінки / з'ясування кількості сторінок
        - Можливо, перевірка чи однакові дані відображаються для користувачів з різних країн
    """
    initial_page = make_request(url=url, base_hash=base_hash, hashed_name=hashed_name)

    # url_hash = get_url_hash(url=url)
    info_filename = f"{base_path}/{base_hash}/{hashed_name}/configuration.json"
    if not os.path.exists(info_filename):
        with open(info_filename, 'w', encoding='utf-8') as f:
            configuration_template_tmp = configuration_template
            configuration_template_tmp["base_url"] = url
            json.dump(configuration_template_tmp, f, ensure_ascii=False, indent=4)

    # Пошук пагінації
    pagination_analysis_result = find_pagination(initial_page, url)
    save_pagination_analysis_results(pagination_analysis_result, info_filename)

    # number_of_pages = pagination_analysis_result.get('number_of_pages')    # Кількість сторінок
    # print(f"Number of pages = {number_of_pages}")
    # link_to_page_attribute = pagination_analysis_result                    # Вигляд посилання на сторінку (посилання пагінації)


def scraper(url: str, base_hash: str, hashed_name: str):
    start_scrape_time = None
    analyser_data = get_json_parameters(url=url, base_hash=base_hash, hashed_name=hashed_name)

    # url_hash = get_url_hash(url=url)
    directory_name = f"{base_path}/{base_hash}/{hashed_name}/cache"
    os.makedirs(directory_name, exist_ok=True)

    if not os.listdir(directory_name):
        configuration_filename = f"{directory_name}/scrape_info.json"
        start_scrape_time = (datetime.now(UTC) + timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')

        with open(configuration_filename, 'w', encoding='utf-8') as file:
            json.dump({"start_time": start_scrape_time, "list_of_pages": {}}, file, ensure_ascii=False, indent=4)

    url_template = analyser_data["pagination"]["pagination_link_template"]
    number_of_pages = analyser_data["pagination"]["number_of_pages"]

    list_of_links = generate_links(url_template, number_of_pages)

    # Отримуємо HTML сторінок за списком посилань
    requests_manager(list_of_links, directory_name)

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
