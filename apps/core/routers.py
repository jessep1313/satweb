# apps/core/routers.py
import threading

_thread_locals = threading.local()

def get_current_db():
    return getattr(_thread_locals, 'db_alias', None)

def set_current_db(db_alias):
    _thread_locals.db_alias = db_alias

class TenantRouter:
    """
    Enruta las consultas del modelo Usuario a la base de datos
    especificada en el thread local (db_alias).
    """
    route_app_labels = {'usuarios_tenant'}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return get_current_db() or 'default'  # Si no hay, usar default (aunque no debería)
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return get_current_db() or 'default'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return None