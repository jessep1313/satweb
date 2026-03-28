from django.urls import path
from . import views

app_name = 'proveedores_sin_cfdi'

urlpatterns = [
    path('', views.lista, name='lista'),
    path('data/', views.data, name='data'),
    path('actualizar/', views.actualizar, name='actualizar'),
    path('exportar/', views.exportar, name='exportar'),
    path('importar/', views.importar, name='importar'),
]