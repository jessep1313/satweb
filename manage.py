#!/usr/bin/env python
import os
import sys
from pathlib import Path

def main():
    # Agregar el directorio 'apps' al path de Python
    sys.path.insert(0, str(Path(__file__).parent / 'apps'))
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'plataforma_fiscal.settings.local')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()