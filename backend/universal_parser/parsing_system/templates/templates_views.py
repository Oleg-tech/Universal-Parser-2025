import os
import csv
import json
import logging

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework import generics, status, filters

from .templates_serializers import TemplateSerializer, TemplateCreateSerializer
from ..models import Template
from ..parsing_subsystem.extract_initial_data import make_extraction_request, parse_data_from_page
from ..parsing_subsystem.main_subsystem import analyser
from ..parsing_subsystem.utils import get_folders_list_from_archive, get_data_from_last_scrape

User = get_user_model()

logger = logging.getLogger(__name__)


class TemplatePagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 100


class TemplateListView(generics.ListCreateAPIView):
    serializer_class = TemplateSerializer
    pagination_class = TemplatePagination
    permission_classes = [IsAuthenticated]

    # Sorting
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    ordering_fields = ['name', 'number_of_scrapes', 'last_scrape']
    ordering = ['-last_scrape']  # default sorting

    # Search
    search_fields = ['name']

    def get_queryset(self):
        return Template.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        # print("Data = ", request.data)

        serializer = TemplateCreateSerializer(data=request.data)

        if not serializer.is_valid():
            print("Validation errors:", serializer.errors)  # Add this line
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)

        template = Template.objects.get(id=serializer.instance.id)
        response_serializer = TemplateSerializer(template)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def template_detail(request, pk):
    """
    Retrieve, update or delete a template instance.
    """
    template = get_object_or_404(Template, pk=pk, user=request.user)

    if request.method == 'GET':
        serializer = TemplateSerializer(template)
        return Response(serializer.data)

    elif request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        serializer = TemplateSerializer(template, data=request.data, partial=partial)
        if serializer.is_valid():
            # Update last_scrape if number_of_scrapes increased
            if 'number_of_scrapes' in serializer.validated_data:
                if serializer.validated_data['number_of_scrapes'] > template.number_of_scrapes:
                    serializer.save(last_scrape=timezone.now())
                else:
                    serializer.save()
            else:
                serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        template_name = template.hashed_name
        template.delete()
        return Response(
            {'message': f'Template "{template_name}" has been deleted successfully.'},
            status=status.HTTP_204_NO_CONTENT
        )


# Створити початкові папки та об'єкт шаблона в БД
class MakeInitialAnalysisView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TemplateCreateSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(user=request.user)
            template = Template.objects.get(id=serializer.instance.id)
            template_serializer = TemplateSerializer(template)

            analyser(
                url=template_serializer.data["webresource_url"],
                base_hash=template_serializer.data["base_hashed_name"],
                hashed_name=template_serializer.data["hashed_name"]
            )

            base_path = "./parsing_system/parsing_subsystem/data"
            configuration_file_path = f"{base_path}/{template_serializer.data["base_hashed_name"]}/{template_serializer.data["hashed_name"]}/configuration.json"

            with open(
                file=configuration_file_path,
                mode="r",
                encoding="utf-8"
            ) as f:
                config_data = json.load(f)

            pagination_is_found = False
            if "pagination" in config_data:
                pagination_is_found = True

            return Response(
                data={
                    "pagination_is_found": pagination_is_found,
                    "template_data": template_serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Скрейпить дані з початкової сторінки та повертає результату вигляді JSON-у
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def extract_initial_data(request):
    if request.method == 'POST':
        request_body = json.loads(request.body)

        print("TESTTEST")
        if not request_body.get("webresource_url") or not request_body.get("elements_to_parse"):
            return Response(
                data={
                    "message": "Wrong body"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        webresource_url = request_body["webresource_url"]
        elements_to_parse = request_body["elements_to_parse"]

        page_html = make_extraction_request(
            url=webresource_url
        )

        result_data = parse_data_from_page(
            page_html=page_html,
            elements_to_parse=elements_to_parse
        )

        return Response(
            data={
                "message": "Success",
                "data": result_data
            },
            status=status.HTTP_200_OK
        )

    return Response(
        data={
            "message": "Wrong body"
        },
        status=status.HTTP_400_BAD_REQUEST
    )


@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_cache(request, template_id):
    if request.method == 'GET':
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        root_dir = os.path.dirname(os.path.dirname(script_dir))
        archive_data_dir = os.path.join(root_dir, "archive")

        template = get_object_or_404(Template, id=template_id)
        if template.number_of_scrapes == 0:
            return Response(
                data={
                    "message": "Success",
                    "data": []
                },
                status=status.HTTP_200_OK
            )

        base_hashed_name = template.base_hashed_name
        hashed_name = template.hashed_name

        all_data = []

        # archive_folder_path = f"C:/Users/olegu/Desktop/Universal Parser/backend/universal_parser/archive/{base_hashed_name}/{hashed_name}"
        archive_folder_path = f"{archive_data_dir}/{base_hashed_name}/{hashed_name}"
        archive_data = get_folders_list_from_archive(archive_folder_path)
        if archive_data:
            all_data.extend(archive_data)

        # print("All data 1 = ", all_data)

        last_scrape_folder_path = f"{parent_dir}/parsing_subsystem/data/{base_hashed_name}/{hashed_name}"
        # print("Last scrape_folder path = ", last_scrape_folder_path)
        last_scrape_data = get_data_from_last_scrape(last_scrape_folder_path)
        if last_scrape_data:
            all_data.append(last_scrape_data)

        # print("All data 2 = ", all_data)

        return Response(
            data={
                "message": "Success",
                "data": all_data
            },
            status=status.HTTP_200_OK
        )
    return Response(
        data={
            "message": "Error"
        },
        status=status.HTTP_400_BAD_REQUEST
    )


archive_path = "C:\\Users\\olegu\\Desktop\\Universal Parser\\backend\\universal_parser\\archive"


@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated])
def process_archive(request, template_id, date):
    print("HERE")
    if request.method == 'GET':
        try:
            template = Template.objects.get(id=template_id)

            if not template:
                return Response(
                    data={'Error': 'Template does not exist'},
                    status=404
                )

            base_hash = template.base_hashed_name
            hashed_name = template.hashed_name

            script_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(script_dir)
            last_scrape_dir = f"{parent_dir}/parsing_subsystem/data/{base_hash}/{hashed_name}"
            last_scrape_info = f"{last_scrape_dir}/cache/scrape_info.json"

            if os.path.isfile(last_scrape_info):
                with open(last_scrape_info) as file:
                    scrape_info = json.load(file)

                scrape_info_last_scrape_date = scrape_info["end_time"]
                formatted_scrape_info_date = scrape_info_last_scrape_date.replace(" ", "_").replace(":", "-")

                # print("Date = ", date)
                # print("Formatted_scrape_info_date", formatted_scrape_info_date)

                if date == formatted_scrape_info_date:
                    rows = []

                    if os.path.exists(f"{last_scrape_dir}/product_data.csv") and os.path.isfile(f"{last_scrape_dir}/product_data.csv"):
                        with open(f"{last_scrape_dir}/product_data.csv", mode="r", encoding="utf-8") as csvfile:
                            reader = csv.DictReader(csvfile)  # reads header -> dict rows
                            for row in reader:
                                rows.append(row)

                    return Response(
                        data={"data": rows},
                        status=200
                    )

            url_path = f"{archive_path}/{base_hash}/{hashed_name}"
            archive_final_path = f"{archive_path}/{base_hash}/{hashed_name}/{date}"

            if not os.path.isdir(archive_final_path):
                return Response(
                    data={'Error': 'File not found'},
                    status=404
                )

            if not os.path.isfile(f"{archive_final_path}/product_data.csv"):
                return Response(
                    data={'Error': 'File not found'},
                    status=404
                )

            rows = []
            with open(f"{archive_final_path}/product_data.csv", mode="r", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)  # reads header -> dict rows
                for row in reader:
                    rows.append(row)

            return Response(
                data={"data": rows},
                status=200
            )

        except Exception as e:
            return Response({'Error': str(e)}, status=500)
    elif request.method == 'DELETE':
        try:
            template = Template.objects.get(id=template_id)

            if not template:
                return Response(
                    data={'Error': 'Template does not exist'},
                    status=404
                )

            base_hash = template.base_hashed_name
            hashed_name = template.hashed_name

            configuration_file_path = f"{archive_path}/{base_hash}/{hashed_name}/{date}/configuration.json"

            if not os.path.exists(configuration_file_path):
                return Response(
                    data={'Error': 'File not found'},
                    status=404
                )

            with open(configuration_file_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            if data.get("is_deactivated") and data.get("is_deactivated") is True:
                return Response(
                    data={'Error': 'File already deleted'},
                    status=404
                )

            data["is_deactivated"] = True

            with open(configuration_file_path, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4, ensure_ascii=False)

            template.number_of_scrapes -= 1
            template.save()

            return Response(
                data={"status": "success"},
                status=200
            )

        except Exception as e:
            return Response({'Error': str(e)}, status=500)
    return Response({"Error": "Bad Request"}, status=400)
