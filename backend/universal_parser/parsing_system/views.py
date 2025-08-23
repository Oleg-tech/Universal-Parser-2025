import json

from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, generics
# from .serializers import RegisterSerializer
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
# from .serializers import EmailTokenObtainPairSerializer


User = get_user_model()


def index(request):
    return HttpResponse("<h1>Welcome to My Homepage!</h1>")


# class RegisterView(generics.CreateAPIView):
#     permission_classes = (permissions.AllowAny,)
#     serializer_class = RegisterSerializer
#     queryset = User.objects.all()
#
#
# class EmailTokenObtainPairView(TokenObtainPairView):
#     serializer_class = EmailTokenObtainPairSerializer


def initial_analysis(request):
    ...


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@csrf_exempt
def parse_website(request):
    """
    request data example:
    {
        "url": "url_to_parse",
        "list_of_elements": [
            {
                "name": "custom name created by user",
                "tag": "tag name",
                "attributes": []
            }
        ]
    }
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            print(data)
            return JsonResponse(
                data={
                    "status": "success"
                },
                status=200
            )
        except Exception as ex:
            return JsonResponse(
                data={
                    "status": "error",
                    "message": f"Invalid JSON: {ex}"
                },
                status=400
            )
    else:
        return JsonResponse(
            data={
                "status": "error",
                "message": "Method Not Allowed"
            },
            status=405
        )
