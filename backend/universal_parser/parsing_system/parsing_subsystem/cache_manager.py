import os
import json
import hashlib


base_path = "./parsing_system/parsing_subsystem/data"


def get_url_hash(url: str):
    return hashlib.md5(url.encode('utf-8')).hexdigest()


def get_init_page_directory_hash(base_hash: str, hashed_name: str):
    # url_hash = get_url_hash(url=url)
    os.makedirs(f"{base_path}/{base_hash}", exist_ok=True)
    os.makedirs(f"{base_path}/{base_hash}/{hashed_name}", exist_ok=True)

    return f"{base_path}/{base_hash}/{hashed_name}"


def get_init_page_filename_hash(base_hash: str, hashed_name: str):
    print("5")
    return f"{get_init_page_directory_hash(base_hash=base_hash, hashed_name=hashed_name)}/init_page.html"


def get_init_page_cache(base_hash: str, hashed_name: str):
    print("3")
    page_filename = get_init_page_filename_hash(base_hash=base_hash, hashed_name=hashed_name)
    # print(f'filename = {page_filename}')

    if os.path.isfile(page_filename):
        with open(page_filename, 'r', encoding='utf-8') as file:
            page_html = file.read()

        return page_html

    return ""


# Створення кешу для початкової сторінки
def make_init_page_cache(page_html, url, base_hash, hashed_name):
    page_directory_hash = get_init_page_directory_hash(base_hash=base_hash, hashed_name=hashed_name)
    page_filename = f"{page_directory_hash}/init_page.html"

    with open(page_filename, "w", encoding="utf-8") as file:
        file.write(page_html)

    print(f"Filename 'init_page.html' was successfully created.")


def get_page_filename_hash(url: str, directory_name: str):
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()

    for filename in os.listdir(directory_name):
        if filename.startswith(url_hash):
            return f"{directory_name}/{filename}"

    return ""


def get_page_cache(page_url: str, directory_name: str):
    page_filename = get_page_filename_hash(
        url=page_url,
        directory_name=directory_name
    )
    # print(f'filename = {page_filename}')

    return os.path.isfile(page_filename)


# Створення кешу для сторінки пагінації
def make_page_cache(page_html, url, directory_name, start_time, end_time):
    url_hash = get_url_hash(url=url)

    # page_filename = f"{directory_name}/{url_hash}_{timestamp}.html"
    page_filename = f"{directory_name}/{url_hash}.html"

    with open(page_filename, "w", encoding="utf-8") as file:
        file.write(page_html)

    with open(f"{directory_name}/scrape_info.json", "r", encoding="utf-8") as file:
        scrape_info_data = json.load(file)

    scrape_info_data["list_of_pages"][url_hash] = {
        "start_time": start_time,
        "end_time": end_time
    }

    with open(f"{directory_name}/scrape_info.json", "w", encoding="utf-8") as file:
        file.write(json.dumps(scrape_info_data, indent=4))

    print(f"Filename '{url_hash}.html' was successfully created.")


# Повертає список всіх імен файлів з кешу для цього сайту
def get_filenames_list(base_hash: str, hashed_name: str):
    filename_path = f"{base_path}/{base_hash}/{hashed_name}/cache/scrape_info.json"

    with open(filename_path, "r") as file:
        config_data = json.load(file)

    list_of_pages = config_data.get("list_of_pages")

    return list_of_pages


def get_elements_to_parse(base_hash: str, hashed_name: str):
    filename_path = f"{base_path}/{base_hash}/{hashed_name}/configuration.json"

    with open(filename_path, "r") as file:
        config_data = json.load(file)

    elements_to_parse = config_data.get("elements_to_parse")

    return elements_to_parse
