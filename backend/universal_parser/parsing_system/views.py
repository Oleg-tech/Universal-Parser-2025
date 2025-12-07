import json
import hashlib

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from .core.create_init_url_cache import save_for_backend
from .core.redis_connector import get_redis_client
from .parsing_subsystem.extract_initial_data import get_page_from_url

User = get_user_model()


def index(request):
    return HttpResponse("<h1>Welcome to My Homepage!</h1>")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@csrf_exempt
def scrape_website(request):
    print("1")
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            webresource_url = data.get("webresource_url")

            if not webresource_url:
                return JsonResponse(
                    data={"error": "Missing URL"},
                    status=400
                )

            webresource_url = webresource_url.strip()

            redis_client = get_redis_client()

            redis_key = hashlib.md5(webresource_url.encode('utf-8')).hexdigest()
            if not redis_client.exists(redis_key):
                redis_value = get_page_from_url(url=webresource_url)
                redis_client.set(redis_key, redis_value, ex=3600)

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
    return JsonResponse(
        data={"status": "error", "message": "Method Not Allowed"},
        status=405
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@csrf_exempt
def create_init_url_cache(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            webresource_url = data.get("webresource_url")

            if not webresource_url:
                return JsonResponse(
                    data={"error": "Missing URL"},
                    status=400
                )

            webresource_url = webresource_url.strip()

            redis_client = get_redis_client()

            salt = "kVMLLSAKMDKmlkdLASMOIWJ3489SAOIFJ3911"
            redis_key = hashlib.md5((salt + webresource_url).encode('utf-8')).hexdigest()
            if not redis_client.exists(redis_key):
                redis_value = save_for_backend(webresource_url, include_images=False)
                redis_client.set(redis_key, redis_value, ex=3600)
                return JsonResponse(
                    data={"data": redis_value},
                    status=200
                )
            else:
                return JsonResponse(
                    data={"data": redis_client.get(redis_key)},
                    status=200
                )
        except Exception as ex:
            return JsonResponse(
                data={
                    "status": "error",
                    "message": f"Error occurred: {ex}"
                },
                status=500
            )
    return JsonResponse(
        data={"status": "error", "message": "Method Not Allowed"},
        status=405
    )
