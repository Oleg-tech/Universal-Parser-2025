import math
import re
import time

from bs4 import BeautifulSoup

from parsing_system.parsing_subsystem.extract_initial_data import find_parent_element


def get_number_of_products_per_page(page_soup: BeautifulSoup, elements_to_parse: list):
    parent_element = find_parent_element(page_soup=page_soup, elements_to_parse=elements_to_parse)
    # print(f"PARENT ELEMENT = {parent_element}")
    parent_list_objects = page_soup.find_all(parent_element["tag"], attrs=parent_element["attrs"])

    return len(parent_list_objects)


def parse_main_page_data(page_soup: BeautifulSoup, elements_to_parse: list):
    list_of_elements = elements_to_parse

    if not list_of_elements:
        return

    parsed_data = []

    parent_element = find_parent_element(page_soup=page_soup, elements_to_parse=elements_to_parse)
    parent_list_objects = page_soup.find_all(parent_element["tag"], attrs=parent_element["attrs"])

    for product_obj in parent_list_objects:
        product_data = {}

        for element in list_of_elements:
            obj_data = product_obj.find(element["tag"], attrs=element["attrs"])

            try:
                product_data[element["field_name"]] = re.sub(r'\s*\n\s*', ' ', obj_data.text).strip()
            except Exception as ex:
                print(f"ERROR: {ex}")
                product_data[element["field_name"]] = ""

        parsed_data.append(product_data)


def parse_product_page_data(page_soup: BeautifulSoup, elements_to_parse: list):
    list_of_elements = elements_to_parse

    if not list_of_elements:
        return

    product_data = {}
    parsed_data = []

    for element in list_of_elements:
        obj_data = page_soup.find(element["tag"], attrs=element["attrs"])

        try:
            product_data[element["field_name"]] = re.sub(r'\s*\n\s*', ' ', obj_data.text).strip()
        except Exception as ex:
            print(f"ERROR: {ex}")
            product_data[element["field_name"]] = ""

        parsed_data.append(product_data)


def get_main_page_parsing_time_estimation(main_page_soup: BeautifulSoup, elements_to_parse: list):
    start_time = time.time()
    parse_main_page_data(
        page_soup=main_page_soup,
        elements_to_parse=elements_to_parse
    )
    end_time = time.time()

    return end_time - start_time


def get_product_page_parsing_time_estimation(product_page_soup: BeautifulSoup, elements_to_parse: list):
    start_time = time.time()
    parse_product_page_data(
        page_soup=product_page_soup,
        elements_to_parse=elements_to_parse
    )
    end_time = time.time()

    return end_time - start_time


# def calculate_adaptive_overhead(total_pages: int) -> float:
#     """
#     Розраховує адаптивний коефіцієнт затримок на основі кількості сторінок.
#
#     Використовує кусково-лінійну інтерполяцію, калібровану на реальних даних:
#     - 3 сторінки: 0.6x (малий overhead)
#     - 44 сторінки: 1.35x
#     - 67 сторінок: 1.76x
#
#     Args:
#         total_pages: Загальна кількість сторінок для скрейпінгу
#
#     Returns:
#         Коефіцієнт затримок (overhead multiplier)
#     """
#     if total_pages <= 5:
#         # Для дуже малої кількості сторінок - мінімальний overhead
#         return 0.6
#     elif total_pages <= 30:
#         # Лінійна інтерполяція між 5 і 30 сторінками
#         return 0.6 + (1.1 - 0.6) * ((total_pages - 5) / (30 - 5))
#     elif total_pages <= 50:
#         # Лінійна інтерполяція між 30 і 50
#         return 1.1 + (1.4 - 1.1) * ((total_pages - 30) / (50 - 30))
#     elif total_pages <= 100:
#         # Лінійна інтерполяція між 50 і 100
#         return 1.4 + (1.8 - 1.4) * ((total_pages - 50) / (100 - 50))
#     else:
#         # Для великої кількості сторінок - повільне зростання
#         return min(1.8 + 0.005 * (total_pages - 100), 2.5)


def calculate_adaptive_overhead(total_pages: int) -> float:
    if total_pages <= 5:
        return 1.0
    elif total_pages <= 30:
        return 1.0 + (3.5 - 1.0) * ((total_pages - 5) / (30 - 5))
    elif total_pages <= 100:
        return 1.0 + (0.8 - 1.0) * ((total_pages - 30) / (100 - 30))
    else:
        return min(1.09 + 0.00015 * (total_pages - 100), 1.2)


def make_time_estimation(
    main_pages_number: int,
    product_per_page_number: int,
    main_page_parsing_time: float,
    product_page_parsing_time: float,
    threads_number: int,
    average_time_per_page: float,
    sigma: float,
    network_latency: float,
    use_adaptive_overhead: bool = True
):
    if product_page_parsing_time != 0:
        product_pages_number = main_pages_number * product_per_page_number
    else:
        product_pages_number = 0

    total_pages = main_pages_number + product_pages_number

    # Розрахунок коефіцієнта затримок
    if use_adaptive_overhead:
        overhead = 1 + calculate_adaptive_overhead(total_pages)
    else:
        overhead = 1.0

    # Кількість батчів
    main_batches = math.ceil(main_pages_number / threads_number)
    products_butches = math.ceil(product_pages_number / threads_number)
    batches = main_batches + products_butches

    # Scraping час
    time_per_page = average_time_per_page

    print(f"batches = {batches}")
    print(f"time_per_page = {time_per_page}")
    print(f"overhead = {overhead}")

    total_scraping_time = batches * time_per_page * overhead
    print(f"Total scraping time: {total_scraping_time}")

    # Parsing час
    total_parsing_time = (main_pages_number * main_page_parsing_time) + (product_pages_number * product_page_parsing_time)
    print(f"Total parsing time: {total_parsing_time}")

    run_estimation_time = total_scraping_time + total_parsing_time

    print(f"run_estimation_time = {run_estimation_time}")

    return run_estimation_time


# def make_time_estimation(
#     main_pages_number: int,
#     product_per_page_number: int,
#     main_page_parsing_time: float,
#     product_page_parsing_time: float,
#     threads_number: int,
#     average_time_per_page: float,
#     sigma: float,
#     network_latency: float
# ):
#     if product_page_parsing_time != 0:
#         product_pages_number = (main_pages_number * product_per_page_number)
#     else:
#         product_pages_number = 0
#
#     total_pages = main_pages_number + product_pages_number
#
#     main_batches = math.ceil(main_pages_number / threads_number)
#     products_butches = math.ceil(product_pages_number / threads_number)
#     batches = main_batches + products_butches
#
#     print(f"batches = {batches}")
#     print(f"average_time_per_page = {average_time_per_page}")
#
#     total_scraping_time = batches * average_time_per_page
#     print(f"Total scraping time: {total_scraping_time}")
#     total_parsing_time = (main_pages_number * main_page_parsing_time) + (product_pages_number * product_page_parsing_time)
#     print(f"Total parsing time: {total_parsing_time}")
#
#     run_estimation_time = total_scraping_time + total_parsing_time
#
#     return run_estimation_time


# def make_time_estimation(
#     main_pages_number: int,
#     product_per_page_number: int,
#     main_page_parsing_time: float,
#     product_page_parsing_time: float,
#     threads_number: int,
#     average_time_per_page: float,
#     sigma: float,
#     network_latency: float
# ):
#     if product_page_parsing_time != 0:
#         product_pages_number = (main_pages_number * product_per_page_number)
#     else:
#         product_pages_number = 0
#
#     total_links_number = main_pages_number + product_pages_number
#
#     if total_links_number < threads_number:
#         total_links_number = threads_number
#
#     total_scraping_time = (total_links_number / threads_number) * (average_time_per_page * (1 + sigma + network_latency))
#     total_parsing_time = (main_pages_number * main_page_parsing_time) + (product_pages_number * product_page_parsing_time)
#
#     run_estimation_time = total_scraping_time + total_parsing_time
#
#     return run_estimation_time
