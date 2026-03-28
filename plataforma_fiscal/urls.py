from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),  # Ahora 'core' es accesible
    path('fiel/', include('fiel.urls')),
    path('cfdi/', include('cfdi.urls')),
    path('proveedores/', include('proveedores.urls')),

]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)