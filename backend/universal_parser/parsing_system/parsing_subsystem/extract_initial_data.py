import redis
import requests
import hashlib
from contextlib import closing
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)


def make_extraction_request(url: str):
    key_hashed_name = hashlib.md5(url.encode('utf-8')).hexdigest()

    cached_html = redis_client.get(key_hashed_name)
    if cached_html:
        return cached_html
    else:
        page_html = get_page_from_url(
            url=url
        )

        redis_client.setex(key_hashed_name, 3600, page_html)

        return page_html


def get_page_from_url(url: str):
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        with closing(webdriver.Chrome(options=options)) as driver:
            driver.get(url)
            page_html = driver.page_source

        return page_html
    except Exception as ex:
        print(f"ERROR: Failed to open webpage: {ex}")


def parse_data_from_page(page_html: str, elements_to_parse: list):
    page_soup = BeautifulSoup(page_html, 'html.parser')

    parent_element = find_parent_element(
        page_soup=page_soup,
        elements_to_parse=elements_to_parse
    )

    parent_list_objects = page_soup.find_all(parent_element["tag"], attrs=parent_element["attrs"])
    # print(f"parent_list_objects = {len(parent_list_objects)}")

    parsed_data = []
    for product_obj in parent_list_objects:
        product_data = {}

        for element in elements_to_parse:
            if element.get("source") == "Product Page":
                continue

            obj_data = product_obj.find(element["tag"], attrs=element["attrs"])

            # print("element = ", element["field_name"])
            # print(f"obj_data = {obj_data}")

            try:
                product_data[element["field_name"]] = obj_data.text
            except Exception as ex:
                print(f"ERROR: {ex}")
                product_data[element["field_name"]] = ""

        parsed_data.append(product_data)

    # print(f"parsed_data = {parsed_data}")

    return parsed_data


def find_parent_element(page_soup: BeautifulSoup, elements_to_parse: list):
    print("PARENT ELEMENT CALLED")
    elements_list = []
    for element in elements_to_parse:
        if element.get("source") == "Product Page":
            continue

        element_tag = element.get("tag")
        element_attrs = element.get("attrs")

        elements_list.append(
            page_soup.find(element_tag, attrs=element_attrs)
        )

    parent_lists = [list(el.parents) for el in elements_list]
    parent_lists = [list(reversed(lst)) for lst in parent_lists]

    parent_element = None
    for parents in zip(*parent_lists):
        if all(p == parents[0] for p in parents):
            parent_element = parents[0]
        else:
            break

    parent_info = {
        "tag": parent_element.name,
        "attrs": parent_element.attrs
    }

    return parent_info
