from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import (
    homepage_view, upload_csv_files
)


urlpatterns = [
    path('', homepage_view, name='home'),
    path('upload-csv/', upload_csv_files, name='upload_csv_files'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
