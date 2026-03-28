from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.signing import loads
from django.apps import apps
import tempfile
import os
from datetime import date
from satcfdi.models import Signer
from satcfdi.pacs.sat import SAT, TipoDescargaMasivaTerceros, EstadoComprobante

from apps.core.decorators import cliente_required
from .models import PeticionSat
from .forms import PeticionSatForm

@cliente_required
def peticion_sat(request):
    # Obtener el modelo CargaFiel de la app 'fiel' sin importarlo directamente
    CargaFiel = apps.get_model('fiel', 'CargaFiel')

    empresa_db = request.session.get('empresa_db')
    rfc_cliente = request.session.get('user_rfc')
    if not empresa_db or not rfc_cliente:
        messages.error(request, 'No se pudo identificar al cliente.')
        return redirect('cliente_dashboard')

    # Obtener la FIEL del cliente desde la tabla fiel
    try:
        fiel = CargaFiel.objects.db_manager(empresa_db).get(rfc_cliente=rfc_cliente, estatus='validado')
    except CargaFiel.DoesNotExist:
        messages.error(request, 'No tienes una FIEL válida cargada. Cárgala y valídala primero en el módulo FIEL.')
        return redirect('fiel:carga_fiel')

    if request.method == 'POST':
        form = PeticionSatForm(request.POST)
        if form.is_valid():
            fechainicio = form.cleaned_data['fechainicio']
            fechafinal = form.cleaned_data['fechafinal']

            if fechafinal > date.today():
                messages.error(request, 'La fecha final no puede ser mayor a hoy.')
                return redirect('cfdi:peticion_sat')

            # Preparar archivos temporales con la FIEL almacenada
            try:
                with tempfile.NamedTemporaryFile(mode='wb', suffix='.cer', delete=False) as cer_temp:
                    cer_temp.write(fiel.archivo_cer.read())
                    cer_path = cer_temp.name

                with tempfile.NamedTemporaryFile(mode='wb', suffix='.key', delete=False) as key_temp:
                    key_temp.write(fiel.archivo_key.read())
                    key_path = key_temp.name

                password = loads(fiel.password)
                signer = Signer.load(
                    certificate=open(cer_path, 'rb').read(),
                    key=open(key_path, 'rb').read(),
                    password=password
                )

                sat = SAT(signer=signer)
                respuesta = sat.recover_comprobante_received_request(
                    fecha_inicial=fechainicio,
                    fecha_final=fechafinal,
                    rfc_receptor=signer.rfc,
                    tipo_solicitud=TipoDescargaMasivaTerceros.CFDI,
                    estado_comprobante=EstadoComprobante.VIGENTE
                )

                # Guardar la petición en la base de datos de la empresa
                PeticionSat.objects.db_manager(empresa_db).create(
                    idpeticion=respuesta['IdSolicitud'],
                    estatuspeticion=0,
                    fechainicio=fechainicio,
                    fechafinal=fechafinal,
                    rfc=rfc_cliente,
                    CodEstatus=respuesta.get('CodEstatus', ''),
                    Mensaje=respuesta.get('Mensaje', ''),
                    RfcSolicitante=respuesta.get('RfcSolicitante', ''),
                    tipo='R'
                )
                messages.success(request, f'Petición creada correctamente. ID: {respuesta["IdSolicitud"]}')
                return redirect('cfdi:peticion_sat')

            except Exception as e:
                messages.error(request, f'Error en la petición: {str(e)}')
            finally:
                # Eliminar archivos temporales
                if os.path.exists(cer_path):
                    os.unlink(cer_path)
                if os.path.exists(key_path):
                    os.unlink(key_path)
        else:
            messages.error(request, 'Corrige los errores del formulario.')
    else:
        form = PeticionSatForm(initial={'rfc': rfc_cliente})

    peticiones = PeticionSat.objects.db_manager(empresa_db).filter(rfc=rfc_cliente).order_by('-fechainicio')
    return render(request, 'cfdi/peticion_sat.html', {'form': form, 'peticiones': peticiones})


from datetime import date, datetime
import json
from django.http import JsonResponse
from django.db import connections
from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from django.contrib import messages
from apps.core.decorators import cliente_required
from .forms import FechaForm

@cliente_required
def recibidas(request):
    empresa_db = request.session.get('empresa_db')
    rfc_cliente = request.session.get('user_rfc')
    if not empresa_db or not rfc_cliente:
        messages.error(request, 'No se pudo identificar al cliente.')
        return redirect('cliente_dashboard')

    tabla = f"cfdi_{rfc_cliente}"

    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    # Si es una petición AJAX, devolvemos JSON con los datos
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        where_clause = ""
        params = []
        if fecha_inicio:
            where_clause += " AND fecha_comprobante >= %s"
            params.append(fecha_inicio)
        if fecha_fin:
            where_clause += " AND fecha_comprobante <= %s"
            params.append(fecha_fin)

        with connections[empresa_db].cursor() as cursor:
            # Datos de la tabla
            cursor.execute(f"""
                SELECT 
                    uudi, fecha_comprobante, rfc_emisor, rfc_receptor, total, 
                    moneda, forma_pago, metodo_pago, fecha_timbrado, saldo_pendiente
                FROM {tabla}
                WHERE 1=1 {where_clause}
                ORDER BY fecha_comprobante DESC
            """, params)
            cfdis = cursor.fetchall()

            # Resumen
            cursor.execute(f"""
                SELECT COUNT(*) as total, SUM(CAST(total AS DECIMAL(18,2))) as suma_total
                FROM {tabla}
                WHERE 1=1 {where_clause}
            """, params)
            resumen = cursor.fetchone()
            total_registros = resumen[0] or 0
            suma_total = float(resumen[1] or 0)

            # Datos para gráficos (por mes)
            cursor.execute(f"""
                SELECT 
                    CONCAT(YEAR(fecha_comprobante), '-', LPAD(MONTH(fecha_comprobante), 2, '0')) as mes,
                    COUNT(*) as cantidad,
                    SUM(CAST(total AS DECIMAL(18,2))) as monto
                FROM {tabla}
                WHERE fecha_comprobante IS NOT NULL {where_clause}
                GROUP BY YEAR(fecha_comprobante), MONTH(fecha_comprobante)
                ORDER BY mes
            """, params)
            datos_meses = cursor.fetchall()

        meses = [row[0] for row in datos_meses]
        cantidades = [row[1] for row in datos_meses]
        montos = [float(row[2]) for row in datos_meses]

        # Formatear datos para DataTables
        data = []
        for row in cfdis:
            # Procesar fecha_comprobante
            fecha_comp = row[1]
            if fecha_comp:
                if isinstance(fecha_comp, str):
                    try:
                        fecha_comp = datetime.strptime(fecha_comp, '%Y-%m-%d').date()
                    except:
                        pass
                fecha_comp_str = fecha_comp.strftime('%d/%m/%Y') if hasattr(fecha_comp, 'strftime') else str(fecha_comp)
            else:
                fecha_comp_str = ''

            # Procesar fecha_timbrado
            fecha_timb = row[8]
            if fecha_timb:
                if isinstance(fecha_timb, str):
                    try:
                        fecha_timb = datetime.strptime(fecha_timb, '%Y-%m-%d %H:%M:%S')
                    except:
                        try:
                            fecha_timb = datetime.strptime(fecha_timb, '%Y-%m-%d')
                        except:
                            pass
                fecha_timb_str = fecha_timb.strftime('%d/%m/%Y %H:%M') if hasattr(fecha_timb, 'strftime') else str(fecha_timb)
            else:
                fecha_timb_str = ''

            data.append([
                row[0],
                fecha_comp_str,
                row[2],
                row[3],
                f"{float(row[4]):.2f}",
                row[5],
                row[6],
                row[7],
                fecha_timb_str,
                f"{float(row[9]):.2f}"
            ])

        return JsonResponse({
            'data': data,
            'total': total_registros,
            'suma_total': suma_total,
            'meses': meses,
            'cantidades': cantidades,
            'montos': montos,
        })

    # Si no es AJAX, mostrar plantilla con el formulario vacío
    form = FechaForm(initial={'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin} if fecha_inicio else None)
    return render(request, 'cfdi/recibidas.html', {'form': form})