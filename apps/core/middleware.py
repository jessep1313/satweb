# apps/core/middleware.py
from .routers import set_current_db

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Si el usuario está autenticado y es de tipo tenant (admin/cliente),
        # obtenemos el db_alias de la sesión y lo establecemos en el thread local.
        if request.user.is_authenticated and hasattr(request.user, 'use_tipo'):
            db_alias = request.session.get('db_alias')
            if db_alias:
                set_current_db(db_alias)
        response = self.get_response(request)
        # Limpiar después de la respuesta
        set_current_db(None)
        return response