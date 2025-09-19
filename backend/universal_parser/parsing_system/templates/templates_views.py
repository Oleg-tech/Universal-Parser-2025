import json
import logging
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from ..models import Template
from .templates_serializers import TemplateSerializer, TemplateCreateSerializer

from ..parsing_subsystem.main_subsystem import analyser

User = get_user_model()

logger = logging.getLogger(__name__)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def template_list_create(request):
    """
    List all templates for the authenticated user, or create a new template.
    """
    if request.method == 'GET': # Get all templates
        templates = Template.objects.filter(user=request.user)
        serializer = TemplateSerializer(templates, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':  # Create template
        serializer = TemplateCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            template = Template.objects.get(id=serializer.instance.id)
            response_serializer = TemplateSerializer(template)

            # Parse Data
            # webresource_url = response_serializer.data['webresource_url']
            # user_hashed_url = response_serializer.data['hashed_name']
            # base_hashed_url = response_serializer.data['base_hashed_name']
            #
            # main_subsystem.main(
            #     url=webresource_url,
            #     base_hash=base_hashed_url,
            #     user_url_hash=user_hashed_url
            # )
            #

            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
@require_http_methods(["POST"])
@login_required
def make_initial_analysis(request):
    if request.method == 'POST':
        serializer = TemplateCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            template = Template.objects.get(id=serializer.instance.id)
            template_serializer = TemplateSerializer(template)

            analyser(
                url=request.data["url"],
                base_hash=template_serializer.data["base_hash"],
                hashed_name=template_serializer.data["hashed_name"]
            )

            with open("configuration.json", "r", encoding="utf-8") as f:
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
    return Response(data={"ERROR": "400 Bad Request"}, status=status.HTTP_400_BAD_REQUEST)


# Скрейпить дані з початкової сторінки та повертає результат та повертає результат у вигляді JSON-у
def extract_initial_data(request):
    if request.method == 'POST':
        serializer = TemplateCreateSerializer(data=request.data)
