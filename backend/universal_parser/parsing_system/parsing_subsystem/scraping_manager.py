from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from datetime import datetime, timedelta, UTC

from .cache_manager import get_page_cache, make_page_cache


# Згенерувати посилання на всі сторінки
def generate_links(url_template: str, number_of_pages: int) -> list:
    list_of_links = []

    for page_idx in range(number_of_pages):
        list_of_links.append(
            url_template.replace("PAGE_NUMBER", str(page_idx + 1))
        )

    return list_of_links


def make_request(url: str, directory_name: str):
    try:
        start_time = (datetime.now(UTC) + timedelta(hours=3)).strftime("%Y%m%d_%H%M%S")
        options = Options()
        options.add_argument("--headless")
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        driver = webdriver.Chrome(options=options)
        driver.get(url)

        page_html = driver.page_source

        driver.quit()

        end_time = (datetime.now(UTC) + timedelta(hours=3)).strftime("%Y%m%d_%H%M%S")

        make_page_cache(page_html, url, directory_name, start_time, end_time)

        return page_html
    except Exception as ex:
        print(f"ERROR: Failed to open webpage: {ex}")


def requests_manager(list_of_urls: list, directory_name: str):
    for page_url_idx, page_url in enumerate(list_of_urls):
        print(f"{page_url_idx + 1}.\tProcessing url: {page_url}")

        cached_file = get_page_cache(
            page_url=page_url,
            directory_name=directory_name
        )

        if not cached_file:
            make_request(
                url=page_url,
                directory_name=directory_name
            )
        else:
            print(f"Already scraped")
