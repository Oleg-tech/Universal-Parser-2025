from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from cache_manager import get_init_page_cache, make_init_page_cache


def make_request(url: str):
    cached_file = get_init_page_cache(url=url)

    if cached_file:
        return cached_file
    else:
        try:
            options = Options()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')

            driver = webdriver.Chrome(options=options)
            driver.get(url)

            page_html = driver.page_source

            driver.quit()

            make_init_page_cache(page_html, url)

            return page_html
        except Exception as ex:
            print(f"ERROR: Failed to open webpage: {ex}")


# def make_analyser_request(url: str):
#     cached_file = get_cached_file(url=url)
#
#     if cached_file:
#         return cached_file
#     else:
#         try:
#             options = Options()
#             options.add_argument('--no-sandbox')
#             options.add_argument('--disable-dev-shm-usage')
#
#             driver = webdriver.Chrome(options=options)
#             driver.get(url)
#
#             page_html = driver.page_source
#
#             driver.quit()
#
#             make_init_page_cache(page_html, url)
#
#             return page_html
#         except Exception as ex:
#             print(f"ERROR: Failed to open webpage: {ex}")
