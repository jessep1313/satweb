from django.urls import path
from . import views

app_name = 'fiel'
urlpatterns = [
    path('', views.carga_fiel, name='carga_fiel'),
    path('eliminar/<int:carga_id>/', views.eliminar_carga, name='eliminar_carga'),
    path('descargar/<int:carga_id>/<str:tipo>/', views.descargar_archivo, name='descargar_archivo'),
    path('validar/<int:carga_id>/', views.validar_fiel, name='validar_fiel'),
    path('config-correos/', views.config_correos, name='config_correos'),
    path('config-correos/crear/', views.crear_config_correo, name='crear_config_correo'),
    path('config-correos/eliminar/<int:config_id>/', views.eliminar_config_correo, name='eliminar_config_correo'),
    path('config-correos/editar/<int:config_id>/', views.editar_config_correo, name='editar_config_correo'),
]