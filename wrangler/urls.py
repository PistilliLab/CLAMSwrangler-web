from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from .views import (
    homepage_view, upload_csv_files, download_zip_file, check_zip_exists, download_config_template, clear_session,
    task_status, processing_view, download_view, process_view, privacy_policy_view
)

urlpatterns = [
    path('', homepage_view, name='home'),
    path('process/', process_view, name='process'),
    path('upload/', upload_csv_files, name='upload_csv_files'),
    path('download/<str:upload_id>/', download_view, name='download'),
    path('download-file/<str:upload_id>/', download_zip_file, name='download_zip_file'),
    path('check-zip/<str:upload_id>/', check_zip_exists, name='check_zip_exists'),
    path('download-config/', download_config_template, name='download_config_template'),
    path('clear-session/', clear_session, name='clear_session'),
    path('task-status/<str:task_id>/', task_status, name='task_status'),
    path('processing/<str:task_id>/', processing_view, name='processing'),
    path('privacy-policy', privacy_policy_view, name='privacy_policy'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
