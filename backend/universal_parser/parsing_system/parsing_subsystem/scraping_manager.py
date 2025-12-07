import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from datetime import datetime, timedelta, UTC
from concurrent.futures import ThreadPoolExecutor
from functools import partial

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
    """Синхронна функція для запиту (викликається в окремому потоці)"""
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
        return None


async def process_url(
        page_url_idx: int, page_url: str, directory_name: str, executor: ThreadPoolExecutor, semaphore: asyncio.Semaphore
):
    """Асинхронна обробка одного URL"""
    async with semaphore:  # Обмежуємо кількість одночасних запитів
        print(f"{page_url_idx + 1}.\tProcessing url: {page_url}")

        # Перевіряємо кеш (синхронно, але швидко)
        loop = asyncio.get_event_loop()
        cached_file = await loop.run_in_executor(
            executor,
            partial(get_page_cache, page_url=page_url, directory_name=directory_name)
        )

        if not cached_file:
            # Виконуємо запит в окремому потоці
            await loop.run_in_executor(
                executor,
                partial(make_request, url=page_url, directory_name=directory_name)
            )
        else:
            print(f"Already scraped")


async def requests_manager(list_of_urls: list, directory_name: str, max_concurrent: int = 10):
    """Асинхронний менеджер запитів з обмеженням потоків"""
    # Семафор для обмеження одночасних операцій
    semaphore = asyncio.Semaphore(max_concurrent)
    results = []

    # ThreadPoolExecutor для запуску Selenium (він не async)
    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        # Створюємо задачі для всіх URL
        tasks = [
            process_url(idx, url, directory_name, executor, semaphore)
            for idx, url in enumerate(list_of_urls)
        ]

        # Виконуємо всі задачі одночасно (з обмеженням semaphore)
        results = await asyncio.gather(*tasks)

    print(f"Results: {results}")


# Для виклику з синхронного коду:
def requests_manager_sync(list_of_urls: list, directory_name: str, max_concurrent: int = 15):
    """Синхронна обгортка для асинхронного менеджера"""
    results = asyncio.run(requests_manager(list_of_urls, directory_name, max_concurrent))
    print(f"Results: {results}")
