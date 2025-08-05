import json

from cache_manager import get_url_hash


configuration_template = {
    "base_url": "",
    "pagination": {},
    "elements_to_parse": []
}


def get_json_parameters(url: str):
    """
        Читання параметрів з JSON-файлу.
        Файл повинен бути створений на етапі аналізу перед першим скрейпом
    """
    url_hash = get_url_hash(url=url)
    filename = f"./data/{url_hash}/configuration.json"

    with open(filename, "r", encoding="utf-8") as file:
        try:
            data = json.load(file)
        except json.JSONDecodeError:
            data = {}

    return data


# Збереження результатів аналізу пагінації
def save_pagination_analysis_results(pagination_analysis_result: dict, filename: str):
    if not pagination_analysis_result:
        return

    with open(filename, "r", encoding="utf-8") as file:
        try:
            data = json.load(file)
        except json.JSONDecodeError:
            data = {}

    data["pagination"].update(pagination_analysis_result)

    pagination_type = pagination_analysis_result["type"]
    if pagination_type == "static":
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
    else:
        ...
