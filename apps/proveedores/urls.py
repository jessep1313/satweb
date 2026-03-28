from django.urls import path
from . import views

app_name = 'proveedores'

urlpatterns = [
    path('', views.proveedores_lista, name='lista'),
    path('data/', views.proveedores_data, name='data'),
    path('actualizar/', views.proveedores_actualizar, name='actualizar'),
    path('exportar/', views.proveedores_exportar, name='exportar'),
    path('importar/', views.proveedores_importar, name='importar'),
]