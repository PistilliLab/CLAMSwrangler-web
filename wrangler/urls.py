from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import (
    homepage_view, upload_csv_files, download_zip, check_zip_exists, download_config_template, clear_session,
)


urlpatterns = [
    path('', homepage_view, name='home'),
    path('upload-csv/', upload_csv_files, name='upload_csv_files'),
    path('download/<str:upload_id>/', download_zip, name='download_zip'),
    path('check-zip/<str:upload_id>/', check_zip_exists, name='check_zip_exists'),
    path('download-config/', download_config_template, name='download_config_template'),
    path('clear-session/', clear_session, name='clear_session'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
