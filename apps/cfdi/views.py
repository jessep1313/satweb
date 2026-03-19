from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.core.decorators import cliente_required
from .models import CfdiRecibido

@cliente_required
def recibidas(request):
    empresa_db = request.session.get('empresa_db')
    rfc_cliente = request.session.get('user_rfc')  # Asumiendo que guardamos el RFC en sesión (lo haremos)
    cfdis = CfdiRecibido.objects.db_manager(empresa_db).filter(rfc_receptor=rfc_cliente).order_by('-fecha_emision')
    return render(request, 'cfdi/recibidas.html', {'cfdis': cfdis})