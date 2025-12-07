import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup


pagination_possible_classnames = [
    "paginat",  # "pagination",   # "paginatorNavigate"
    "navigation",
]


def find_elements_with_any_class(soup, class_substrings):
    results = []
    for element in soup.find_all(class_=True):
        element_classes = element.get('class', [])
        for cls in element_classes:
            for substring in class_substrings:
                if substring in cls:
                    results.append(element)
                    break
            else:
                continue
            break
    return results


def create_pagination_template(initial_url, current_url):
    print(f"Initial URL = ", initial_url)
    print(f"Current URL = ", current_url)

    if not re.search(r'\d+', initial_url):
        return re.sub(r'\d+', 'PAGE_NUMBER', current_url, count=1)

    initial_numbers = set(re.findall(r'\d+', initial_url))

    def replace_new_number(match):
        num = match.group(0)
        if num not in initial_numbers:
            return 'PAGE_NUMBER'
        return num

    return re.sub(r'\d+', replace_new_number, current_url, count=1)


def add_base_domain_from_initial_url(initial_url, current_url):
    full_url = urljoin(initial_url, current_url)
    return full_url


def analyze_pagination(possible_pagination_soup, base_url):
    page_numbers = []
    pagination_link_template = ""

    # Перевірка посилань пагінації
    page_links = possible_pagination_soup.find_all('a', href=True)
    possible_page_links = {}
    for link in page_links:
        href = link.get('href')

        # зробити універсальним в майбутньому
        match = re.search(r'\b\d+\b', href)

        if match:
            if not possible_page_links.get(href.strip()):
                possible_page_links[href.strip()] = match.group(0)
                page_numbers.append(int(match.group(0)))
        else:
            # Перевірка тексту тегу "a"
            text = link.get_text().strip()
            if text.isdigit():
                page_numbers.append(int(text))

    # print("Page Numbers = ", page_numbers)

    try:
        page_numbers.remove(1)
    except:
        print("1 is missing in pagination")

    is_increasing = all(page_numbers[i] < page_numbers[i + 1] for i in range(len(page_numbers) - 1))

    if not is_increasing:
        print(f"WARNING: Послідовність сторінок не є зростаючою: {page_numbers}")
        return

    if possible_page_links:
        first_possible_link = list(possible_page_links.keys())[0]
        print(f"First Possible Link 1 = {first_possible_link}")

        first_possible_link = add_base_domain_from_initial_url(
            initial_url=base_url,
            current_url=first_possible_link
        )
        print(f"First Possible Link 2 = {first_possible_link}")

        pagination_link_template = create_pagination_template(
            initial_url=base_url,
            current_url=first_possible_link
        )

    pagination_search_result = {
        "type": "static",
        "number_of_pages": max(page_numbers),
        "pagination_link_template": pagination_link_template,
        "url_specification": "endpoint"
    }

    return pagination_search_result


def find_pagination(page_html, base_url):
    pagination_analysis_result = None
    page_soup = BeautifulSoup(page_html, 'html.parser')

    elements = find_elements_with_any_class(page_soup, pagination_possible_classnames)
    for el in elements:
        # print(f"Element = {el}")
        pagination_analysis_result = analyze_pagination(el, base_url)
        # print(f"Pagination Analysis Result = {pagination_analysis_result}")

        if pagination_analysis_result:
            break

    return pagination_analysis_result
