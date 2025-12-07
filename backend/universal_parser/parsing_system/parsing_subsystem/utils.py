import os
import csv
import json
from datetime import datetime

from bs4 import BeautifulSoup

base_path = "./parsing_system/parsing_subsystem/data"


def calculate_duration(start_time, end_time):
    fmt = "%Y-%m-%d %H:%M:%S"
    start_dt = datetime.strptime(start_time, fmt)
    end_dt = datetime.strptime(end_time, fmt)
    diff_seconds = int((end_dt - start_dt).total_seconds())
    return diff_seconds


def get_csv_rows_number(filepath):
    rows_number = 0

    if not os.path.exists(filepath):
        return rows_number

    with open(filepath, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        rows_number = sum(1 for row in reader)

    return rows_number


def get_size(path: str) -> int:
    """Повертає розмір папки у байтах (включаючи вкладені файли)."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.isfile(fp):
                total_size += os.path.getsize(fp)
    return total_size


def get_folders_list_from_archive(folder_path: str):
    """Виводить назви всіх папок у folder_path та їхній розмір."""
    files = []

    if os.path.exists(folder_path):
        for item in os.listdir(folder_path):
            full_path = os.path.join(folder_path, item)
            if os.path.isdir(full_path):
                configuration_file_path = f"{folder_path}/{item}/configuration.json"
                with open(configuration_file_path, "r") as f:
                    configuration_json = json.load(f)

                if configuration_json.get("is_deactivated") is True:
                    print(f"Already Deactivated: {item}")
                    continue

                size_bytes = get_size(full_path)
                size_mb = size_bytes / (1024 * 1024)
                print(f"{item}: {size_mb:.2f} MB")

                scrape_info_path = f"{folder_path}/{item}/cache/scrape_info.json"
                with open(scrape_info_path, "r") as f:
                    scrape_info = json.load(f)

                number_of_pages = 0
                list_of_pages = scrape_info.get("list_of_pages")
                if list_of_pages:
                    number_of_pages = len(list_of_pages.keys())

                start_time = scrape_info.get("start_time")
                end_time = scrape_info.get("end_time")

                duration = 0
                if start_time and end_time:
                    duration = calculate_duration(start_time, end_time)

                rows_number = get_csv_rows_number(f"{folder_path}/{item}/product_data.csv")

                item_data = {
                    "filename": item,
                    "file_size": size_mb,
                    "number_of_pages": number_of_pages,
                    "date": end_time,
                    "duration": duration,
                    "rows_number": rows_number
                }

                files.append(item_data)

    return files


def get_data_from_last_scrape(folder_path: str):
    item_data = {}

    if os.path.exists(folder_path):
        size_bytes = get_size(folder_path)
        size_mb = size_bytes / (1024 * 1024)

        scrape_info_path = f"{folder_path}/cache/scrape_info.json"
        if os.path.exists(scrape_info_path):
            with open(scrape_info_path, "r") as f:
                scrape_info = json.load(f)

            number_of_pages = 0
            list_of_pages = scrape_info.get("list_of_pages")
            if list_of_pages:
                number_of_pages = len(list_of_pages.keys())

            start_time = scrape_info.get("start_time")
            end_time = scrape_info.get("end_time")

            filename = ""
            if end_time:
                filename = end_time.replace(" ", "_").replace(":", "-")

            duration = 0
            if start_time and end_time:
                duration = calculate_duration(start_time, end_time)

            rows_number = get_csv_rows_number(f"{folder_path}/product_data.csv")

            item_data = {
                "filename": filename,
                "file_size": size_mb,
                "number_of_pages": number_of_pages,
                "date": end_time,
                "duration": duration,
                "rows_number": rows_number
            }

    # print("Last Scrape Data = ", item_data)

    return item_data


def find_parent_element(elements_to_parse: list, base_hash: str, hashed_name: str):
    init_page_path = f"{base_path}/{base_hash}/{hashed_name}/init_page.html"

    # print(init_page_path)
    with open(init_page_path, "r", encoding="utf-8") as file:
        init_soup = BeautifulSoup(file, "html.parser")

    elements_list = []
    for element in elements_to_parse:
        if element["source"] == "Product Page":
            continue

        element_tag = element.get("tag")
        element_attrs = element.get("attrs")

        elements_list.append(
            init_soup.find(element_tag, attrs=element_attrs)
        )

        # print(len(init_soup.find_all(element_tag, attrs=element_attrs)))

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

    # print("Parent_element = ", parent_element)

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
