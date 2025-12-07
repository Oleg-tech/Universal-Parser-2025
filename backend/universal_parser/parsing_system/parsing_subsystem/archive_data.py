import os
import json
import uuid
import shutil


current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_file))

base_path = "./parsing_system/parsing_subsystem/data"
archived_base_path = "C:\\Users\\olegu\\Desktop\\Universal Parser\\backend\\universal_parser\\archive"


def LIGHT_archive_template_data(base_hash, hashed_name):
    source_path = f"{base_path}/{base_hash}/{hashed_name}"
    configuration_file_path = f"{source_path}/configuration.json"

    end_date_file = f"{source_path}/cache/scrape_info.json"
    if os.path.exists(end_date_file):
        with open(end_date_file, "r", encoding="utf-8") as f:
            scrape_info_data = json.load(f)

        end_date_filename = scrape_info_data["start_time"].replace(" ", "_").replace(":", "-")
    else:
        end_date_filename = str(uuid.uuid4())

    archived_base_name = f"{archived_base_path}/{base_hash}"
    os.makedirs(archived_base_name, exist_ok=True)

    if os.path.exists(configuration_file_path):
        archived_destination = f"{archived_base_name}/{hashed_name}/{end_date_filename}"
        shutil.move(source_path, archived_destination)
        os.makedirs(source_path, exist_ok=True)

        cache_folder = f"{source_path}/cache"
        os.makedirs(cache_folder, exist_ok=True)

        files_to_keep = ["configuration.json", "init_page.html"]
        for file_name in files_to_keep:
            archived_file = f"{archived_destination}/{file_name}"
            if os.path.exists(archived_file):
                shutil.copy2(archived_file, f"{source_path}/{file_name}")

        print(f"INFO: ARCHIVED - Left cache folder and required files in original location")
    else:
        print(f"INFO: DATA NOT FOUND")


def FULL_archive_template_data(base_hash, hashed_name):
    source_path = f"{base_path}/{base_hash}/{hashed_name}"
    configuration_file_path = f"{base_path}/{base_hash}/{hashed_name}/configuration.json"

    end_date_file = f"{source_path}/cache/scrape_info.json"
    if os.path.exists(end_date_file):
        with open(end_date_file, "r", encoding="utf-8") as f:
            scrape_info_data = json.load(f)

        end_date_filename = scrape_info_data["start_time"].replace(" ", "_").replace(":", "-")
    else:
        end_date_filename = str(uuid.uuid4())

    archived_base_name = f"{archived_base_path}/{base_hash}"
    os.makedirs(archived_base_name, exist_ok=True)

    if os.path.exists(configuration_file_path):
        archived_destination = f"{archived_base_name}/{hashed_name}/{end_date_filename}"
        shutil.move(f"{base_path}/{base_hash}/{hashed_name}", archived_destination)
        print(f"INFO: ARCHIVED")
    else:
        print(f"INFO: DATA NOT FOUND")
