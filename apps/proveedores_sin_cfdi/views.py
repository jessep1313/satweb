import csv
import io
import json
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connections
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import PermissionDenied

from apps.core.decorators import cliente_required

@cliente_required
def lista(request):
    """Página principal del módulo."""
    return render(request, 'proveedores_sin_cfdi/lista.html')

@cliente_required
def data(request):
    """Devuelve JSON con los proveedores del cliente actual."""
    empresa_db = request.session.get('empresa_db')
    rfc_cliente = request.session.get('user_rfc')
    if not empresa_db or not rfc_cliente:
        return JsonResponse({'error': 'No se pudo identificar al cliente'}, status=400)

    with connections[empresa_db].cursor() as cursor:
        cursor.execute("""
            SELECT id, NombreComercial, RazonSocial, RFC,
                   Correo, Correo2, Correo3, tipoProveedor,
                   codigoPostal, calle, noInt, noExt, colonia, estado, municipio, ciudad, telefono
            FROM proveedores_sin_cfdi
            WHERE rfc_identy = %s
            ORDER BY id
        """, [rfc_cliente])
        rows = cursor.fetchall()

    data = []
    for row in rows:
        data.append({
            'id': row[0],
            'NombreComercial': row[1] or '',
            'RazonSocial': row[2] or '',
            'RFC': row[3] or '',
            'Correo': row[4] or '',
            'Correo2': row[5] or '',
            'Correo3': row[6] or '',
            'tipoProveedor': row[7] or '',
            'codigoPostal': row[8] or '',
            'calle': row[9] or '',
            'noInt': row[10] or '',
            'noExt': row[11] or '',
            'colonia': row[12] or '',
            'estado': row[13] or '',
            'municipio': row[14] or '',
            'ciudad': row[15] or '',
            'telefono': row[16] or '',
        })
    return JsonResponse(data, safe=False)

@cliente_required
@csrf_exempt
def actualizar(request):
    """Actualiza un proveedor (solo campos editables) para el cliente actual."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body)
        proveedor_id = data.get('id')
        if not proveedor_id:
            return JsonResponse({'error': 'ID de proveedor no proporcionado'}, status=400)

        empresa_db = request.session.get('empresa_db')
        rfc_cliente = request.session.get('user_rfc')
        if not empresa_db or not rfc_cliente:
            return JsonResponse({'error': 'No se pudo identificar al cliente'}, status=400)

        # Verificar que el proveedor pertenezca al cliente
        with connections[empresa_db].cursor() as cursor:
            cursor.execute("SELECT id FROM proveedores_sin_cfdi WHERE id = %s AND rfc_identy = %s", [proveedor_id, rfc_cliente])
            if not cursor.fetchone():
                return JsonResponse({'error': 'Proveedor no encontrado o no pertenece a este cliente'}, status=404)

        campos_editables = [
            'Correo', 'Correo2', 'Correo3', 'tipoProveedor',
            'codigoPostal', 'calle', 'noInt', 'noExt', 'colonia',
            'estado', 'municipio', 'ciudad', 'telefono'
        ]
        set_clause = []
        valores = []
        for campo in campos_editables:
            if campo in data:
                set_clause.append(f"{campo} = %s")
                valores.append(data[campo])
        if not set_clause:
            return JsonResponse({'error': 'No se proporcionaron campos para actualizar'}, status=400)

        sql = f"UPDATE proveedores_sin_cfdi SET {', '.join(set_clause)} WHERE id = %s AND rfc_identy = %s"
        valores.append(proveedor_id)
        valores.append(rfc_cliente)

        with connections[empresa_db].cursor() as cursor:
            cursor.execute(sql, valores)

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@cliente_required
def exportar(request):
    """Exporta los proveedores del cliente actual a CSV."""
    empresa_db = request.session.get('empresa_db')
    rfc_cliente = request.session.get('user_rfc')
    if not empresa_db or not rfc_cliente:
        messages.error(request, 'No se pudo identificar al cliente.')
        return redirect('cliente_dashboard')

    with connections[empresa_db].cursor() as cursor:
        cursor.execute("""
            SELECT id, NombreComercial, RazonSocial, RFC,
                   Correo, Correo2, Correo3, tipoProveedor,
                   codigoPostal, calle, noInt, noExt, colonia, estado, municipio, ciudad, telefono
            FROM proveedores_sin_cfdi
            WHERE rfc_identy = %s
            ORDER BY id
        """, [rfc_cliente])
        rows = cursor.fetchall()

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="proveedores_sin_cfdi_{rfc_cliente}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'NombreComercial', 'RazonSocial', 'RFC',
        'Correo', 'Correo2', 'Correo3', 'tipoProveedor',
        'codigoPostal', 'calle', 'noInt', 'noExt', 'colonia', 'estado', 'municipio', 'ciudad', 'telefono'
    ])
    for row in rows:
        writer.writerow(row)

    return response

@cliente_required
@csrf_exempt
def importar(request):
    """Importa un archivo CSV y actualiza los proveedores del cliente actual."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No se envió ningún archivo'}, status=400)

    archivo = request.FILES['file']
    if not archivo.name.endswith('.csv'):
        return JsonResponse({'error': 'Solo se aceptan archivos CSV'}, status=400)

    empresa_db = request.session.get('empresa_db')
    rfc_cliente = request.session.get('user_rfc')
    if not empresa_db or not rfc_cliente:
        return JsonResponse({'error': 'No se pudo identificar al cliente'}, status=400)

    campos_editables = [
        'Correo', 'Correo2', 'Correo3', 'tipoProveedor',
        'codigoPostal', 'calle', 'noInt', 'noExt', 'colonia',
        'estado', 'municipio', 'ciudad', 'telefono'
    ]

    try:
        decoded_file = archivo.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded_file))
        expected_headers = ['ID'] + campos_editables
        if not all(h in reader.fieldnames for h in expected_headers):
            return JsonResponse({'error': 'El archivo no tiene las columnas requeridas (ID, Correo, Correo2, ...)'}, status=400)

        updates = []
        for row in reader:
            proveedor_id = row.get('ID')
            if not proveedor_id or not proveedor_id.isdigit():
                continue
            # Verificar que el proveedor pertenezca al cliente
            with connections[empresa_db].cursor() as cursor:
                cursor.execute("SELECT id FROM proveedores_sin_cfdi WHERE id = %s AND rfc_identy = %s", [proveedor_id, rfc_cliente])
                if not cursor.fetchone():
                    continue  # Saltar filas que no pertenecen al cliente
            set_clause = []
            valores = []
            for campo in campos_editables:
                if campo in row:
                    set_clause.append(f"{campo} = %s")
                    valores.append(row[campo])
            if set_clause:
                updates.append((set_clause, valores, proveedor_id))

        with connections[empresa_db].cursor() as cursor:
            for set_clause, valores, proveedor_id in updates:
                sql = f"UPDATE proveedores_sin_cfdi SET {', '.join(set_clause)} WHERE id = %s AND rfc_identy = %s"
                valores.append(proveedor_id)
                valores.append(rfc_cliente)
                cursor.execute(sql, valores)

        return JsonResponse({'success': True, 'updated': len(updates)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)