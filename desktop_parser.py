"""
desktop_parser.py - Utilidades para generar, leer y validar archivos .desktop
"""
import os
import subprocess
import configparser

STANDARD_CATEGORIES = [
    ("Development", "Desarrollo / Programación"),
    ("Utility", "Utilidad / Herramientas"),
    ("Game", "Juegos / Entretenimiento"),
    ("AudioVideo", "Sonido y Video / Multimedia"),
    ("Office", "Oficina / Documentos"),
    ("Network", "Internet / Redes"),
    ("Graphics", "Gráficos / Diseño"),
    ("System", "Sistema / Administración"),
    ("Settings", "Configuración y Ajustes"),
    ("Education", "Educación / Ciencia"),
]

def get_user_applications_dir():
    """Retorna el directorio predeterminado del usuario para accesos directos."""
    data_home = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    apps_dir = os.path.join(data_home, "applications")
    os.makedirs(apps_dir, exist_ok=True)
    return apps_dir

def build_desktop_content(data):
    """
    Genera el texto de un archivo .desktop a partir de un diccionario de datos.
    """
    lines = ["[Desktop Entry]"]
    lines.append("Type=Application")
    
    if data.get("name"):
        lines.append(f"Name={data['name'].strip()}")
    if data.get("generic_name"):
        lines.append(f"GenericName={data['generic_name'].strip()}")
    if data.get("comment"):
        lines.append(f"Comment={data['comment'].strip()}")
    if data.get("exec"):
        lines.append(f"Exec={data['exec'].strip()}")
    if data.get("icon"):
        lines.append(f"Icon={data['icon'].strip()}")
    if data.get("path"):
        lines.append(f"Path={data['path'].strip()}")
        
    categories = data.get("categories", [])
    if categories:
        cat_str = ";".join(categories) + ";"
        lines.append(f"Categories={cat_str}")
        
    keywords = data.get("keywords", [])
    if keywords:
        kw_str = ";".join(keywords) + ";"
        lines.append(f"Keywords={kw_str}")

    mime_types = data.get("mime_types", [])
    if mime_types:
        mime_str = ";".join(mime_types) + ";"
        lines.append(f"MimeType={mime_str}")

    lines.append(f"Terminal={'true' if data.get('terminal') else 'false'}")
    lines.append(f"StartupNotify={'true' if data.get('startup_notify', True) else 'false'}")
    
    if data.get("no_display"):
        lines.append("NoDisplay=true")

    return "\n".join(lines) + "\n"

def save_desktop_file(filepath, data):
    """Guarda los datos en una ruta de archivo .desktop con permisos de ejecución."""
    content = build_desktop_content(data)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    os.chmod(filepath, 0o755)

def parse_desktop_file(filepath):
    """Lee un archivo .desktop y retorna un diccionario con sus propiedades."""
    config = configparser.ConfigParser(interpolation=None)
    config.optionxform = str  # Preservar mayúsculas/minúsculas de claves
    config.read(filepath, encoding="utf-8")
    
    if "Desktop Entry" in config:
        section = config["Desktop Entry"]
    elif "[Desktop Entry]" in config:
        section = config["[Desktop Entry]"]
    else:
        raise ValueError("El archivo no contiene la sección [Desktop Entry]")
    
    categories = [c.strip() for c in section.get("Categories", "").split(";") if c.strip()]
    keywords = [k.strip() for k in section.get("Keywords", "").split(";") if k.strip()]
    mime_types = [m.strip() for m in section.get("MimeType", "").split(";") if m.strip()]

    def to_bool(val, default=False):
        if not val:
            return default
        return val.lower() in ("true", "1", "yes")

    return {
        "name": section.get("Name", ""),
        "generic_name": section.get("GenericName", ""),
        "comment": section.get("Comment", ""),
        "exec": section.get("Exec", ""),
        "icon": section.get("Icon", ""),
        "path": section.get("Path", ""),
        "terminal": to_bool(section.get("Terminal", ""), False),
        "startup_notify": to_bool(section.get("StartupNotify", ""), True),
        "no_display": to_bool(section.get("NoDisplay", ""), False),
        "categories": categories,
        "keywords": keywords,
        "mime_types": mime_types,
    }

def validate_desktop_file(filepath):
    """Verifica si desktop-file-validate reporta errores."""
    try:
        res = subprocess.run(
            ["desktop-file-validate", filepath],
            capture_output=True,
            text=True
        )
        return res.returncode == 0, res.stderr or res.stdout
    except FileNotFoundError:
        return True, "desktop-file-validate no está instalado."
