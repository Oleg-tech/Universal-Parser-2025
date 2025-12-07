import os
import re
import csv
import json
from bs4 import BeautifulSoup

from .cache_manager import get_filenames_list, get_elements_to_parse, get_product_url, get_product_page_url_obj, \
    get_url_hash
from .extract_product_page_urls import find_needed_url
from .utils import get_parent_element


base_path = "./parsing_system/parsing_subsystem/data"


def parsing_main(base_hash: str, hashed_name: str):
    print("PARSING 1")
    list_of_pages = get_filenames_list(base_hash=base_hash, hashed_name=hashed_name)
    list_of_elements = get_elements_to_parse(base_hash=base_hash, hashed_name=hashed_name)

    if not list_of_elements:
        return

    # temporary solution
    list_of_main_elements = []
    list_of_product_page_elements = []
    for element in list_of_elements:
        if element["source"] != "Product Page":
            list_of_main_elements.append(element)
        else:
            list_of_product_page_elements.append(element)
    # list_of_elements = list_of_main_elements
    #

    parent_element = get_parent_element(
        elements_to_parse=list_of_main_elements,
        base_hash=base_hash,
        hashed_name=hashed_name
    )
    csv_column_names = [name["field_name"] for name in list_of_elements]

    # print(f"csv_column_names = {csv_column_names}")

    parsed_data = []
    for page_hash_name in list_of_pages:
        # print(f"page_hash_name = {page_hash_name}")

        page_soup = None
        with open(f"{base_path}/{base_hash}/{hashed_name}/cache/{page_hash_name}.html", "r", encoding="utf-8") as file:
            page_soup = BeautifulSoup(file, "html.parser")

        parent_list_objects = page_soup.find_all(parent_element["tag"], attrs=parent_element["attrs"])

        # print(f"parent_list_objects = {len(parent_list_objects)}")

        for product_obj in parent_list_objects:
            product_data = {}

            for element in list_of_elements:
                if element["source"] == "Main Page":
                    obj_data = product_obj.find(element["tag"], attrs=element["attrs"])
                else:
                    product_page_url_attrs = get_product_page_url_obj(base_hash=base_hash, hashed_name=hashed_name)

                    if product_page_url_attrs:
                        product_url = product_obj.find(product_page_url_attrs["tag"], attrs=product_page_url_attrs["attrs"])["href"]
                    else:
                        product_url = find_needed_url(
                            obj_soup=product_obj,
                            example_url=get_product_url(base_hash=base_hash, hashed_name=hashed_name)
                        )

                    product_url_hash = get_url_hash(url=product_url)

                    product_url_cache_path = f"{base_path}/{base_hash}/{hashed_name}/cache/{product_url_hash}.html"

                    if not os.path.isfile(product_url_cache_path):
                        obj_data = ""
                    else:
                        with open(product_url_cache_path, "r", encoding="utf-8") as file:
                            product_html = file.read()

                        product_url_soup = BeautifulSoup(product_html, "html.parser")

                        obj_data = product_url_soup.find(element["tag"], attrs=element["attrs"])

                # print("element = ", element["field_name"])
                # print(f"obj_data = {obj_data}")

                try:
                    product_data[element["field_name"]] = re.sub(r'\s*\n\s*', ' ', obj_data.text).strip()
                except Exception as ex:
                    print(f"ERROR: {ex}")
                    product_data[element["field_name"]] = ""

            parsed_data.append(product_data)

    with open(f"{base_path}/{base_hash}/{hashed_name}/product_data.csv", "w", newline="",  encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=csv_column_names)
        writer.writeheader()
        writer.writerows(parsed_data)

    print("PARSING 2")
