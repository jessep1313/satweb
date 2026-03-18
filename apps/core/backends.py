# apps/core/backends.py
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from usuarios_tenant.models import Usuario

class TenantAuthBackend(BaseBackend):
    """
    Backend de autenticación para usuarios de empresas (Admin/Cliente).
    Requiere que en el request se pase el parámetro 'empresa' con el alias de la DB.
    """
    def authenticate(self, request, username=None, password=None, empresa=None):
        if not empresa:
            return None  # No es para este backend
        try:
            user = Usuario.objects.using(empresa).get(use_login=username)
            if user.check_password(password):
                # Guardamos la base de datos en el usuario para usarla después
                user._state.db = empresa
                return user
        except Usuario.DoesNotExist:
            return None
        return None

    def get_user(self, user_id):
        """
        Este método es llamado por Django para recuperar el usuario desde la sesión.
        Necesitamos saber a qué base de datos pertenece. Lo resolveremos guardando
        el alias en la sesión y luego usando ese alias aquí.
        """
        # No podemos obtener la sesión aquí directamente, pero podemos hacer que
        # el middleware o la vista guarden el alias en algún lugar accesible.
        # Una alternativa es usar un modelo proxy o un cache.
        # Sin embargo, dado que usaremos este backend solo para usuarios tenant,
        # y en la sesión guardaremos el user_id y el db_alias, podemos intentar
        # recuperar el db_alias de la sesión a través de un thread local.
        # Pero para simplificar, haremos que en el login guardemos en la sesión
        # el user_id y el db_alias, y en las vistas usaremos un mixin que
        # establezca la base de datos para las consultas.
        # Para get_user, podemos implementar una búsqueda en todas las bases,
        # pero es ineficiente. Mejor guardar el db_alias en la sesión y luego
        # en el middleware restaurar la conexión. Otra opción es no usar get_user
        # y en su lugar usar el sistema de sesiones de Django para almacenar
        # el usuario completo serializado, pero no es recomendable.
        #
        # La solución más común en multi-tenant con Django es usar un middleware
        # que, basado en la sesión, establece la conexión a la base de datos
        # para el modelo tenant, y luego el backend puede usar esa conexión.
        # Implementaremos un middleware que ponga en un thread local la DB activa.
        #
        # Por ahora, y para avanzar, haremos que este backend no implemente get_user,
        # y en su lugar, después del login, guardaremos en la sesión el user_id y el db_alias.
        # Luego, en un middleware personalizado, para cada request estableceremos
        # la base de datos por defecto para el modelo Usuario (usando using()).
        # Pero get_user se llama automáticamente por Django en cada request para
        # obtener el usuario desde la sesión. Si no implementamos get_user, fallará.
        #
        # Entonces, necesitamos un get_user que funcione. Podemos almacenar en la sesión
        # el db_alias, y get_user puede leerlo de la sesión si tenemos acceso a ella.
        # Django no pasa la sesión a get_user, pero podemos acceder a través del request
        # si usamos un thread local o un middleware que guarde el request actual.
        # Usaremos 'threading.local' para almacenar el request actual y así get_user
        # pueda obtener la sesión.
        #
        # Implementaremos un middleware que guarde el request en un thread local.
        # Luego en get_user, accedemos a ese request para obtener la sesión y el db_alias.
        #
        # Veamos:
        import threading
        _thread_locals = threading.local()

        def get_current_request():
            return getattr(_thread_locals, 'request', None)

        class RequestMiddleware:
            def __init__(self, get_response):
                self.get_response = get_response

            def __call__(self, request):
                _thread_locals.request = request
                response = self.get_response(request)
                return response

        # Luego en get_user:
        def get_user(self, user_id):
            request = get_current_request()
            if not request:
                return None
            db_alias = request.session.get('db_alias')
            if not db_alias:
                return None
            try:
                user = Usuario.objects.using(db_alias).get(pk=user_id)
                user._state.db = db_alias
                return user
            except Usuario.DoesNotExist:
                return None