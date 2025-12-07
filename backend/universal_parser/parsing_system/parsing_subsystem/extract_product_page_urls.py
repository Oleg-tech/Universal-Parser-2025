import hashlib
import re
import json
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from parsing_system.parsing_subsystem.utils import get_parent_element


def find_needed_url(obj_soup, example_url):
    parsed_example = urlparse(example_url)
    example_path = parsed_example.path

    # Визначаємо паттерн URL (чи має розширення, чи закінчується слешем)
    has_extension = '.' in example_path.split('/')[-1]
    ends_with_slash = example_path.endswith('/')

    # Рахуємо кількість сегментів в шляху
    example_segments = len([s for s in example_path.split('/') if s])

    all_links = obj_soup.find_all('a', href=True)

    for link in all_links:
        href = link['href']

        if not href:
            continue

        parsed_href = urlparse(href)
        href_path = parsed_href.path

        # Пропускаємо зовнішні домени якщо є
        if parsed_href.netloc and parsed_href.netloc != parsed_example.netloc:
            continue

        href_has_extension = '.' in href_path.split('/')[-1]
        href_ends_with_slash = href_path.endswith('/')
        href_segments = len([s for s in href_path.split('/') if s])

        # Збіг паттерну: те саме закінчення і схожа структура
        if (has_extension == href_has_extension and
                ends_with_slash == href_ends_with_slash and
                abs(href_segments - example_segments) <= 1):  # дозволяємо різницю в 1 сегмент
            return href

    return None


def get_product_url_object_data(obj_soup, example_url):
    """
    Знаходить HTML-елемент (тег), який містить посилання на product page
    з використанням тієї ж логіки що й find_needed_url
    """
    parsed_example = urlparse(example_url)
    example_path = parsed_example.path

    # Визначаємо паттерн URL
    has_extension = '.' in example_path.split('/')[-1]
    ends_with_slash = example_path.endswith('/')
    example_segments = len([s for s in example_path.split('/') if s])

    all_links = obj_soup.find_all('a', href=True)

    for link in all_links:
        href = link['href']

        if not href:
            continue

        parsed_href = urlparse(href)
        href_path = parsed_href.path

        # Пропускаємо зовнішні домени
        if parsed_href.netloc and parsed_href.netloc != parsed_example.netloc:
            continue

        href_has_extension = '.' in href_path.split('/')[-1]
        href_ends_with_slash = href_path.endswith('/')
        href_segments = len([s for s in href_path.split('/') if s])

        # Збіг паттерну (та ж логіка що й у find_needed_url)
        if (has_extension == href_has_extension and
                ends_with_slash == href_ends_with_slash and
                abs(href_segments - example_segments) <= 1):
            return {
                'tag': link.name,
                'attrs': dict(link.attrs)
            }

    print("PRODUCT URL OBJECT IS MISSING")
    return None


def product_page_urls_extraction(
        configuration_path: str,
        scrape_info_directory_path: str,
        analyser_data: dict
):
    list_of_product_urls = []

    scrape_info_path = f"{scrape_info_directory_path}/cache/scrape_info.json"

    configuration_info = ""
    with open(configuration_path, "r") as f:
        configuration_info = json.load(f)

    parent_object = configuration_info.get("parent_element")
    if not parent_object:
        parent_object = get_parent_element(
            elements_to_parse=configuration_info["elements_to_parse"],
            base_hash=hashlib.md5(configuration_info["base_url"].encode('utf-8')).hexdigest(),
            hashed_name=configuration_info["hashed_name"]
        )

    scrape_info_data = ""
    with open(scrape_info_path, "r") as f:
        scrape_info_data = json.load(f)

    product_page_url = analyser_data.get("product_page_url")

    product_page_data_is_saved = False
    pages_filenames = scrape_info_data.get("list_of_pages")
    for page_filename in pages_filenames:
        with open(f"{scrape_info_directory_path}/cache/{page_filename}.html", "r", encoding="utf-8") as f:
            page_html = f.read()

        print(f"{page_filename}.html")
        print("Type = ", type(page_html))

        # print(page_html)

        page_soup = BeautifulSoup(page_html, "html.parser")

        # print("Page soup = ", page_soup)
        print(f"parent_object = {parent_object}")

        page_parent_objects = page_soup.find_all(parent_object["tag"], attrs=parent_object["attrs"])

        # print(f"Parent object = {page_parent_objects}")

        # Extract product_page_url object data
        if not product_page_data_is_saved:
            print("test here")
            product_url_obj = get_product_url_object_data(
                obj_soup=page_parent_objects[0],
                example_url=product_page_url
            )

            print(f"product_url_obj = {product_url_obj}")

            if product_url_obj and "class" not in product_url_obj["attrs"].keys():
                product_url_obj["attrs"] = {}
            else:
                product_url_obj["attrs"] = {"class": product_url_obj["attrs"]["class"]}

            print("Object = ", product_url_obj)

            with open(configuration_path, "r") as f:
                configuration_info = json.load(f)

            configuration_info["product_page_url_object"] = product_url_obj

            with open(configuration_path, "w") as f:
                json.dump(configuration_info, f, indent=4, ensure_ascii=False)

            product_page_data_is_saved = True
        #

        for page_parent_object in page_parent_objects:
            product_url = find_needed_url(
                obj_soup=page_parent_object,
                example_url=product_page_url
            )
            list_of_product_urls.append(product_url)
            print("PRODUCT URL = ", product_url)

    return list_of_product_urls
