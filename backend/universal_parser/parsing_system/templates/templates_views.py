from datetime import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from ..models import Template
from .templates_serializers import TemplateSerializer, TemplateCreateSerializer


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
            # Return the created object with full serializer
            template = Template.objects.get(id=serializer.instance.id)
            response_serializer = TemplateSerializer(template)
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
