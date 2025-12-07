import os
import json
from rest_framework import serializers
from django.contrib.auth import get_user_model
from ..models import Template
from ..parsing_subsystem.utils import get_folders_list_from_archive, get_data_from_last_scrape, get_csv_rows_number


User = get_user_model()

base_path = "./parsing_system/parsing_subsystem/data"

configuration_template = {
    "base_url": "",
    "pagination": {},
}


class TemplateSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    attributes_list = serializers.SerializerMethodField()
    total_memory_used = serializers.SerializerMethodField()
    total_number_of_products = serializers.SerializerMethodField()
    scraping_frequency = serializers.SerializerMethodField()

    class Meta:
        model = Template
        fields = [
            'id',
            'name',
            'hashed_name',
            'base_hashed_name',
            'webresource_url',
            'number_of_scrapes',
            'is_automated',
            'last_scrape',
            'delay_between_scrapes',
            'user',
            'attributes_list',
            'total_memory_used',
            'total_number_of_products',
            'scraping_frequency'
        ]
        read_only_fields = ['id', 'user']

    def get_attributes_list(self, obj):
        filepath = f"{base_path}/{obj.base_hashed_name}/{obj.hashed_name}/configuration.json"

        if not os.path.isfile(filepath):
            return []

        with open(filepath, "r", encoding="utf-8") as f:    # for configuration .json
            data = json.load(f)

        return data.get("elements_to_parse") or []

    def get_total_memory_used(self, obj):
        total_size = 0

        script_dir = os.path.dirname(os.path.abspath(__file__))

        parent_dir = os.path.dirname(script_dir)
        root_dir = os.path.dirname(os.path.dirname(script_dir))
        archive_data_dir = os.path.join(root_dir, "archive")

        base_hashed_name = obj.base_hashed_name
        hashed_name = obj.hashed_name

        number_of_scrapes = obj.number_of_scrapes

        if number_of_scrapes > 1:
            archive_folder_path = f"{archive_data_dir}/{base_hashed_name}/{hashed_name}"
            archive_data = get_folders_list_from_archive(archive_folder_path)

            for element in archive_data:
                element_memory_size = element.get("file_size")
                total_size += element_memory_size

            last_scrape_path = f"{parent_dir}/parsing_subsystem/data/{base_hashed_name}/{hashed_name}"
            last_scrape_data = get_data_from_last_scrape(last_scrape_path)

            if last_scrape_data:
                total_size += last_scrape_data.get("file_size")
        elif number_of_scrapes == 1:
            last_scrape_path = f"{parent_dir}/parsing_subsystem/data/{base_hashed_name}/{hashed_name}"
            last_scrape_data = get_data_from_last_scrape(last_scrape_path)

            if last_scrape_data:
                total_size = last_scrape_data.get("file_size")

        return total_size

    def get_total_number_of_products(self, obj):
        total_number_of_rows = 0

        script_dir = os.path.dirname(os.path.abspath(__file__))

        parent_dir = os.path.dirname(script_dir)
        root_dir = os.path.dirname(os.path.dirname(script_dir))
        data_dir = os.path.join(root_dir, "archive")

        base_hashed_name = obj.base_hashed_name
        hashed_name = obj.hashed_name

        number_of_scrapes = obj.number_of_scrapes

        if number_of_scrapes > 1:
            archive_folder_path = f"{data_dir}/{base_hashed_name}/{hashed_name}"
            archive_data = get_folders_list_from_archive(archive_folder_path)

            for element in archive_data:
                total_number_of_rows += element.get("rows_number")

            last_scrape_products_path = f"{parent_dir}/parsing_subsystem/data/{base_hashed_name}/{hashed_name}/product_data.csv"
            last_scrape_rows_number = get_csv_rows_number(last_scrape_products_path)
            total_number_of_rows += last_scrape_rows_number
        elif number_of_scrapes == 1:
            last_scrape_products_path = f"{parent_dir}/parsing_subsystem/data/{base_hashed_name}/{hashed_name}/product_data.csv"
            last_scrape_rows_number = get_csv_rows_number(last_scrape_products_path)
            total_number_of_rows = last_scrape_rows_number

        return total_number_of_rows

    def validate_webresource_url(self, value):
        """
        Validate that the URL is properly formatted
        """
        if not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("URL must start with http:// or https://")
        return value

    def validate_delay_between_scrapes(self, value):
        """
        Ensure delay is not negative
        """
        if value < 0:
            raise serializers.ValidationError("Delay between scrapes cannot be negative")
        return value

    def get_scraping_frequency(self, obj):
        script_dir = os.path.dirname(os.path.abspath(__file__))

        parent_dir = os.path.dirname(script_dir)

        base_hashed_name = obj.base_hashed_name
        hashed_name = obj.hashed_name

        last_scrape_path = f"{parent_dir}/parsing_subsystem/data/{base_hashed_name}/{hashed_name}"
        with open(f"{last_scrape_path}/configuration.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        frequency = data.get("scraping_frequency")
        if not frequency:
            frequency = 0

        return frequency


class TemplateCreateSerializer(serializers.ModelSerializer):
    """
    Separate serializer for creation to handle different validation if needed
    """
    name = serializers.CharField(max_length=150, write_only=True)
    webresource_url = serializers.URLField()
    hashed_name = serializers.CharField(read_only=True)
    base_hashed_name = serializers.CharField(read_only=True)
    elements_to_parse = serializers.JSONField(write_only=True, required=False)
    scraping_frequency = serializers.IntegerField(write_only=True, required=False)
    product_page_url = serializers.URLField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Template
        fields = [
            'name',
            'hashed_name',
            'base_hashed_name',
            'webresource_url',
            'is_automated',
            'delay_between_scrapes',
            'elements_to_parse',
            'scraping_frequency',
            'product_page_url'
        ]

    def create(self, validated_data):
        import hashlib
        import uuid
        from django.utils import timezone

        # Extract the name field
        web_resource_url = validated_data.pop('webresource_url')

        # print("URL: ", web_resource_url)

        # Create base hash from name
        base_hash = hashlib.md5(web_resource_url.encode('utf-8')).hexdigest()

        # Create unique hashed_name by adding timestamp and UUID
        timestamp = str(int(timezone.now().timestamp()))
        unique_suffix = str(uuid.uuid4())[:8]
        unique_string = f"{web_resource_url}_{timestamp}_{unique_suffix}"
        hashed_name = hashlib.sha256(unique_string.encode('utf-8')).hexdigest()[:30]

        # Ensure uniqueness (in case of collision)
        counter = 1
        original_hashed_name = hashed_name
        while Template.objects.filter(hashed_name=hashed_name).exists():
            hashed_name = f"{original_hashed_name}_{counter}"
            counter += 1

        # Set the hashed values
        validated_data['hashed_name'] = hashed_name
        validated_data['base_hashed_name'] = base_hash
        validated_data['webresource_url'] = web_resource_url

        elements_to_parse = validated_data.pop("elements_to_parse", [])
        # print(f"Elements To Parse: {elements_to_parse}")

        is_automated = validated_data.pop("is_automated", False)
        scraping_frequency = validated_data.pop("scraping_frequency", 0)

        # print(f"Is Automated: {is_automated}")
        # print(f"Scraping Frequency: {scraping_frequency}")

        if validated_data.get("product_page_url") and validated_data.get("product_page_url") != "":
            product_page_url = validated_data.pop("product_page_url", None)
        else:
            product_page_url = None

        # print(f"Product Page URL: {product_page_url}")

        config_dir = os.path.join(base_path, base_hash, hashed_name)
        os.makedirs(config_dir, exist_ok=True)

        config_path = os.path.join(config_dir, "configuration.json")
        configuration_template["elements_to_parse"] = elements_to_parse
        configuration_template["base_url"] = web_resource_url
        configuration_template["hashed_name"] = hashed_name
        configuration_template["is_automated"] = is_automated
        if is_automated is True:
            configuration_template["scraping_frequency"] = scraping_frequency

        if product_page_url:
            configuration_template["product_page_url"] = product_page_url

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(
                configuration_template,
                f,
                ensure_ascii=False,
                indent=4
            )

        return super().create(validated_data)
