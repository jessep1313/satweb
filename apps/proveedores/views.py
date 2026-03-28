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
def proveedores_lista(request):
    """Página principal del módulo proveedores (carga la plantilla)."""
    return render(request, 'proveedores/lista.html')

@cliente_required
def proveedores_data(request):
    """Devuelve JSON con todos los proveedores del cliente (para DataTable)."""
    empresa_db = request.session.get('empresa_db')
    rfc_cliente = request.session.get('user_rfc')
    if not empresa_db or not rfc_cliente:
        return JsonResponse({'error': 'No se pudo identificar al cliente'}, status=400)

    tabla = f"proveedores_{rfc_cliente}"
    with connections[empresa_db].cursor() as cursor:
        cursor.execute(f"""
            SELECT id, NombreComercial, RazonSocial, RFC,
                   Correo, Correo2, Correo3, tipoProveedor,
                   codigoPostal, calle, noInt, noExt, colonia, estado, municipio, ciudad, telefono
            FROM {tabla}
            ORDER BY id
        """)
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
def proveedores_actualizar(request):
    """Actualiza un proveedor (solo campos editables). Recibe JSON con id y campos."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body)
        proveedor_id = data.get('id')
        if not proveedor_id:
            return JsonResponse({'error': 'ID de proveedor no proporcionado'}, status=400)

        # Campos editables
        campos_editables = [
            'Correo', 'Correo2', 'Correo3', 'tipoProveedor',
            'codigoPostal', 'calle', 'noInt', 'noExt', 'colonia',
            'estado', 'municipio', 'ciudad', 'telefono'
        ]
        # Construir SET dinámico
        set_clause = []
        valores = []
        for campo in campos_editables:
            if campo in data:
                set_clause.append(f"{campo} = %s")
                valores.append(data[campo])
        if not set_clause:
            return JsonResponse({'error': 'No se proporcionaron campos para actualizar'}, status=400)

        empresa_db = request.session.get('empresa_db')
        rfc_cliente = request.session.get('user_rfc')
        if not empresa_db or not rfc_cliente:
            return JsonResponse({'error': 'No se pudo identificar al cliente'}, status=400)

        tabla = f"proveedores_{rfc_cliente}"
        sql = f"UPDATE {tabla} SET {', '.join(set_clause)} WHERE id = %s"
        valores.append(proveedor_id)

        with connections[empresa_db].cursor() as cursor:
            cursor.execute(sql, valores)

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@cliente_required
def proveedores_exportar(request):
    """Exporta todos los proveedores a CSV."""
    empresa_db = request.session.get('empresa_db')
    rfc_cliente = request.session.get('user_rfc')
    if not empresa_db or not rfc_cliente:
        messages.error(request, 'No se pudo identificar al cliente.')
        return redirect('cliente_dashboard')

    tabla = f"proveedores_{rfc_cliente}"
    with connections[empresa_db].cursor() as cursor:
        cursor.execute(f"""
            SELECT id, NombreComercial, RazonSocial, RFC,
                   Correo, Correo2, Correo3, tipoProveedor,
                   codigoPostal, calle, noInt, noExt, colonia, estado, municipio, ciudad, telefono
            FROM {tabla}
            ORDER BY id
        """)
        rows = cursor.fetchall()

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="proveedores_{rfc_cliente}.csv"'

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
def proveedores_importar(request):
    """Importa un archivo CSV y actualiza los proveedores (actualiza campos editables)."""
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

    tabla = f"proveedores_{rfc_cliente}"
    campos_editables = [
        'Correo', 'Correo2', 'Correo3', 'tipoProveedor',
        'codigoPostal', 'calle', 'noInt', 'noExt', 'colonia',
        'estado', 'municipio', 'ciudad', 'telefono'
    ]

    # Leer CSV
    try:
        decoded_file = archivo.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded_file))
        # Validar que las columnas esperadas existan (ID al menos)
        expected_headers = ['ID'] + campos_editables
        if not all(h in reader.fieldnames for h in expected_headers):
            return JsonResponse({'error': 'El archivo no tiene las columnas requeridas (ID, Correo, Correo2, ...)'}, status=400)

        updates = []
        for row in reader:
            proveedor_id = row.get('ID')
            if not proveedor_id or not proveedor_id.isdigit():
                continue  # ignorar filas sin ID válido
            # Construir SET dinámico
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
                sql = f"UPDATE {tabla} SET {', '.join(set_clause)} WHERE id = %s"
                valores.append(proveedor_id)
                cursor.execute(sql, valores)

        return JsonResponse({'success': True, 'updated': len(updates)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
# Create your views here.
