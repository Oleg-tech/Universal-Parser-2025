import csv
import json
from bs4 import BeautifulSoup

from .cache_manager import get_filenames_list, get_elements_to_parse


base_path = "./parsing_system/parsing_subsystem/data"


def find_parent_element(elements_to_parse: list, base_hash: str, hashed_name: str):
    init_page_path = f"{base_path}/{base_hash}/{hashed_name}/init_page.html"

    print(init_page_path)
    with open(init_page_path, "r", encoding="utf-8") as file:
        init_soup = BeautifulSoup(file, "html.parser")

    elements_list = []
    for element in elements_to_parse:
        element_tag = element.get("tag")
        element_attrs = element.get("attrs")

        elements_list.append(
            init_soup.find(element_tag, attrs=element_attrs)
        )

        print(len(init_soup.find_all(element_tag, attrs=element_attrs)))

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


def get_parent_element(elements_to_parse: list, base_hash: str, hashed_name: str):
    filename_path = f"{base_path}/{base_hash}/{hashed_name}/configuration.json"

    with open(filename_path, "r") as file:
        config_data = json.load(file)

    parent_element = config_data.get("parent_element")

    if parent_element:
        return parent_element

    parent_element = find_parent_element(
        elements_to_parse=elements_to_parse,
        base_hash=base_hash,
        hashed_name=hashed_name
    )

    config_data["parent_element"] = parent_element

    with open(filename_path, "w") as file:
        json.dump(config_data, file, ensure_ascii=False, indent=4)

    return parent_element


def parsing_main(base_hash: str, hashed_name: str):
    list_of_pages = get_filenames_list(base_hash=base_hash, hashed_name=hashed_name)
    list_of_elements = get_elements_to_parse(base_hash=base_hash, hashed_name=hashed_name)

    if not list_of_elements:
        return

    parent_element = get_parent_element(
        elements_to_parse=list_of_elements,
        base_hash=base_hash,
        hashed_name=hashed_name
    )
    csv_column_names = [name["field_name"] for name in list_of_elements]

    print(f"csv_column_names = {csv_column_names}")

    parsed_data = []
    for page_hash_name in list_of_pages:
        print(f"page_hash_name = {page_hash_name}")

        page_soup = None
        with open(f"{base_path}/{base_hash}/{hashed_name}/cache/{page_hash_name}.html", "r", encoding="utf-8") as file:
            page_soup = BeautifulSoup(file, "html.parser")

        parent_list_objects = page_soup.find_all(parent_element["tag"], attrs=parent_element["attrs"])

        print(f"parent_list_objects = {len(parent_list_objects)}")

        for product_obj in parent_list_objects:
            product_data = {}

            for element in list_of_elements:
                obj_data = product_obj.find(element["tag"], attrs=element["attrs"])

                print("element = ", element["field_name"])
                print(f"obj_data = {obj_data}")

                try:
                    product_data[element["field_name"]] = obj_data.text
                except Exception as ex:
                    print(f"ERROR: {ex}")
                    product_data[element["field_name"]] = ""

            parsed_data.append(product_data)

    with open(f"{base_path}/{base_hash}/{hashed_name}/product_data.csv", "w", newline="",  encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=csv_column_names)
        writer.writeheader()
        writer.writerows(parsed_data)
