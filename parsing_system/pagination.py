import re
from bs4 import BeautifulSoup


pagination_possible_classnames = [
    "pagination",
    "navigation"
]


def find_elements_with_any_class(soup, classes):
    results = []
    for element in soup.find_all(class_=True):
        element_classes = element.get('class', [])
        if any(cls in element_classes for cls in classes):
            results.append(element)
    return results


def analyze_pagination(possible_pagination_soup, base_url):
    page_numbers = []
    pagination_link_template = ""

    # Перевірка посилань пагінації
    page_links = possible_pagination_soup.find_all('a', href=True)
    possible_page_links = {}
    for link in page_links:
        href = link.get('href')

        # зробити універсальним в майбутньому
        # match = re.search(r'/page/(\d+)/', href)
        match = re.search(r'\b\d+\b', href)
        # is_pagination_link = bool(re.search(r'\d', href))

        if base_url not in href:
            href = f"{base_url}/{href}"
        #

        if match:
            if not possible_page_links.get(href.strip()):
                possible_page_links[href.strip()] = match.group(0)
                page_numbers.append(int(match.group(0)))
        else:
            # Перевірка тексту тегу "a"
            text = link.get_text().strip()
            if text.isdigit():
                page_numbers.append(int(text))

    is_increasing = all(page_numbers[i] < page_numbers[i + 1] for i in range(len(page_numbers) - 1))

    if not is_increasing:
        print(f"WARNING: Послідовність сторінок не є зростаючою: {page_numbers}")
        return

    if possible_page_links:
        pagination_link_template = re.sub(r"\d+", "PAGE_NUMBER", next(iter(possible_page_links.keys())))
        # pagination_link_template = next(iter(possible_page_links.values())).group(0)

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
        pagination_analysis_result = analyze_pagination(el, base_url)

        if pagination_analysis_result:
            break

    return pagination_analysis_result
