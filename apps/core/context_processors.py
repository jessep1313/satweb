def user_type(request):
    """Agrega el tipo de usuario al contexto de las plantillas"""
    return {
        'user_type': request.session.get('user_type', None)
    }