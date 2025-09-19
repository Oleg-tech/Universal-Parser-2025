import json
import logging
import threading

import jwt
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import UntypedToken

from universal_parser import settings
from ..models import Template

from ..parsing_subsystem import main_subsystem, archive_data


User = get_user_model()

logger = logging.getLogger(__name__)


def get_user_from_token(request):
    """
    Видобуває користувача з Bearer токену
    """
    # Отримуємо токен з заголовка Authorization
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None

    # Витягуємо токен
    token = auth_header.split(' ')[1]

    try:
        # Перевіряємо токен через simplejwt
        UntypedToken(token)  # Це перевіряє валідність токену

        # Декодуємо токен для отримання payload
        decoded_token = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )

        # Отримуємо user_id з токену
        user_id = decoded_token.get('user_id')
        if not user_id:
            return None

        # Знаходимо користувача
        try:
            user = User.objects.get(id=user_id)
            return user
        except User.DoesNotExist:
            return None

    except (InvalidToken, TokenError, jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def run_scraping_task(template_id):
    """
    Функція для запуску скрейпінгу в окремому потоці
    """
    try:
        template = Template.objects.get(id=template_id)

        print(f"Base Hash = {template.base_hashed_name}")
        print(f"Hashed Name = {template.hashed_name}")

        if template.scraping_status == 'completed':
            archive_data.archive_template_data(
                base_hash=template.base_hashed_name,
                hashed_name=template.hashed_name
            )

        # Оновлюємо статус на "running"
        template.scraping_status = 'running'
        template.scraping_started_at = timezone.now()
        template.scraping_progress = 0
        template.scraping_message = 'Starting scraping process...'
        template.scraping_error = ''
        template.save()

        # Запускаємо основний процес
        main_subsystem.main(
            url=template.webresource_url,
            base_hash=template.base_hashed_name,
            user_url_hash=template.hashed_name
        )

        # Успішне завершення
        template.scraping_status = 'completed'
        template.scraping_progress = 100
        template.scraping_message = 'Scraping completed successfully'
        template.number_of_scrapes += 1
        template.last_scrape = timezone.now()
        template.save()

    except Exception as e:
        logger.error(f"Scraping failed for template {template_id}: {str(e)}")
        try:
            template.scraping_status = 'failed'
            template.scraping_error = str(e)
            template.scraping_message = 'Scraping failed'
            template.save()
        except:
            pass


@csrf_exempt
@require_http_methods(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def start_scraping(request, hashed_name):
    """
    API ендпоінт для запуску процесу скрейпінгу
    URL: /api/scrape/<str:hashed_name>/
    """
    try:
        with transaction.atomic():
            template = get_object_or_404(Template, hashed_name=hashed_name)

            current_user = get_user_from_token(request)
            print(f"Template: {template.user}")
            print(f"User: {current_user}")

            # Currently does not work
            # if template.user != current_user:
            #     return JsonResponse({
            #         'error': 'Permission denied. This template does not belong to you.'
            #     }, status=403)

            # Перевіряємо, чи не запущений вже процес скрейпінгу
            if template.scraping_status == 'running':
                return JsonResponse({
                    'error': 'Scraping is already in progress for this template',
                    'status': 'running',
                    'started_at': template.scraping_started_at.isoformat() if template.scraping_started_at else None,
                    'progress': template.scraping_progress,
                    'message': template.scraping_message
                }, status=409)  # Conflict

            # Запускаємо скрейпінг в окремому потоці
            thread = threading.Thread(
                target=run_scraping_task,
                args=(template.id,)
            )
            thread.daemon = True
            thread.start()

            return JsonResponse({
                'success': True,
                'message': f'Scraping started for template: {template.name}',
                'template_info': {
                    'name': template.name,
                    'hashed_name': template.hashed_name,
                    'status': 'running',
                    'started_at': timezone.now().isoformat()
                }
            }, status=202)  # Accepted

    except Template.DoesNotExist:
        return JsonResponse({
            'error': f'Template with hashed_name "{hashed_name}" not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Unexpected error in start_scraping: {str(e)}")
        return JsonResponse({
            'error': 'An unexpected error occurred'
        }, status=500)


@require_http_methods(["GET"])
@login_required
def get_scraping_status(request, hashed_name):
    """
    API ендпоінт для отримання статусу скрейпінгу
    URL: /api/scrape/<str:hashed_name>/status/
    """
    try:
        template = get_object_or_404(Template, hashed_name=hashed_name)

        # Перевіряємо доступ
        if template.user != request.user:
            return JsonResponse({
                'error': 'Permission denied. This template does not belong to you.'
            }, status=403)

        return JsonResponse({
            'template_info': {
                'name': template.name,
                'hashed_name': template.hashed_name,
                'status': template.scraping_status,
                'progress': template.scraping_progress,
                'message': template.scraping_message,
                'error': template.scraping_error,
                'started_at': template.scraping_started_at.isoformat() if template.scraping_started_at else None,
                'last_scrape': template.last_scrape.isoformat() if template.last_scrape else None,
                'total_scrapes': template.number_of_scrapes
            }
        }, status=200)

    except Template.DoesNotExist:
        return JsonResponse({
            'error': f'Template with hashed_name "{hashed_name}" not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Unexpected error in get_scraping_status: {str(e)}")
        return JsonResponse({
            'error': 'An unexpected error occurred'
        }, status=500)
