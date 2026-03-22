from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),  # Ahora 'core' es accesible
    path('fiel/', include('fiel.urls')),

]
