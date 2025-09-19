import os
import shutil


base_path = "./parsing_system/parsing_subsystem/data"


def archive_template_data(base_hash, hashed_name):
    configuration_file_path = f"{base_path}/{base_hash}/{hashed_name}/configuration.json"

    archived_base_path = f"C:\\Users\\Oleh\\Desktop\\diploma\\Universal-Parser-2025-development\\backend\\universal_parser\\data"
    archived_base_name = f"{archived_base_path}/{base_hash}"
    os.makedirs(archived_base_name, exist_ok=True)

    if os.path.exists(configuration_file_path):
        shutil.move(f"{base_path}/{base_hash}/{hashed_name}", archived_base_name)
        print(f"INFO: ARCHIVED")
    else:
        print(f"INFO: DATA NOT FOUND")
