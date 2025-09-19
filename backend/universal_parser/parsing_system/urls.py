from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import index, parse_website
from .users import users_views
from .templates import templates_views, scraping_process_views


urlpatterns = [
    path("home/", index, name="homepage"),
    path("analyse/", parse_website, name="make_analysis"),

    # Auth
    path('api/auth/register/', users_views.RegisterView.as_view(), name='register'),
    path('api/auth/login/', users_views.CustomTokenObtainPairView.as_view(), name='login'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/logout/', users_views.logout_view, name='logout'),
    path('api/auth/profile/', users_views.get_user_profile, name='user_profile'),
    path('api/auth/profile/update/', users_views.update_user_profile, name='update_profile'),

    # Templates
    path('api/templates/', templates_views.template_list_create, name='template-list'),
    path('api/templates/<int:pk>/', templates_views.template_detail, name='template-detail'),

    path('api/scrape/<str:hashed_name>/', scraping_process_views.start_scraping, name='start_scraping'),
    path('api/scrape/<str:hashed_name>/status/', scraping_process_views.get_scraping_status, name='scraping_status'),
    # path('api/scrape/<str:hashed_name>/stop/', templates_views.stop_scraping, name='stop_scraping'),

    path('api/initial_analysis/', templates_views.make_initial_analysis, name='initial_analysis'),

]
