#!/bin/bash
set -e

echo "=== Iniciando Music Web Explorer ==="

# Función para logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Crear directorios necesarios si no existen
log "Creando directorios necesarios..."
mkdir -p /app/logs /app/data /app/images /app/static/images /app/templates /downloads

# Crear templates si no existen
log "Verificando templates..."
if [ ! -d "/app/templates" ]; then
    mkdir -p /app/templates
fi

# Copiar index.html a templates si existe en /app/
if [ -f "/app/index.html" ] && [ ! -f "/app/templates/index.html" ]; then
    log "Copiando index.html a templates..."
    cp /app/index.html /app/templates/
fi

# Copiar sistema.html a templates si existe en /app/
if [ -f "/app/sistema.html" ] && [ ! -f "/app/templates/sistema.html" ]; then
    log "Copiando sistema.html a templates..."
    cp /app/sistema.html /app/templates/
fi

# Crear archivos mínimos necesarios si faltan
if [ ! -f "/app/templates/index.html" ]; then
    log "Creando index.html básico..."
    cat > /app/templates/index.html << 'EOF'
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Music Web Explorer</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; }
        h1 { color: #333; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎵 Music Web Explorer</h1>
        <p>Aplicación cargada con template básico.</p>
        <p><a href="/health">🔍 Estado del Sistema</a> | <a href="/debug">🛠️ Debug</a></p>
    </div>
</body>
</html>
EOF
fi

# Crear imagen por defecto si no existe
if [ ! -f "/app/static/images/default_album.jpg" ]; then
    log "Creando imagen por defecto..."
    python3 -c "
try:
    from PIL import Image, ImageDraw
    import os
    os.makedirs('/app/static/images', exist_ok=True)
    img = Image.new('RGB', (300, 300), color='#333333')
    d = ImageDraw.Draw(img)
    try:
        d.text((150, 150), 'No Cover', fill=(255,255,255), anchor='mm')
    except:
        d.text((120, 140), 'No Cover', fill=(255,255,255))
    img.save('/app/static/images/default_album.jpg')
    print('✓ Imagen por defecto creada')
except Exception as e:
    print(f'⚠ No se pudo crear imagen: {e}')
"
fi

# Configurar SSH si está disponible
if [ -d "/tmp/host_ssh" ]; then
    log "Configurando SSH..."
    mkdir -p /home/$USER/.ssh
    cp -r /tmp/host_ssh/* /home/$USER/.ssh/ 2>/dev/null || true
    chown -R $USER:$USER /home/$USER/.ssh
    chmod 700 /home/$USER/.ssh
    chmod 600 /home/$USER/.ssh/* 2>/dev/null || true
fi

# Verificar base de datos
if [ -f "/app/data/musica.sqlite" ]; then
    log "✓ Base de datos encontrada: /app/data/musica.sqlite"
    if [ -r "/app/data/musica.sqlite" ]; then
        log "✓ Base de datos accesible"
    else
        log "⚠ Advertencia: Base de datos no es legible"
    fi
else
    log "⚠ Advertencia: Base de datos no encontrada en /app/data/musica.sqlite"
fi

# Verificar directorio de música NFS
if [ -d "/mnt/NFS/moode/moode" ]; then
    log "✓ Directorio de música NFS encontrado"
    if [ -r "/mnt/NFS/moode/moode" ]; then
        log "✓ Directorio NFS accesible para lectura"
    else
        log "⚠ Advertencia: Directorio NFS no es legible"
    fi
else
    log "⚠ Advertencia: Directorio NFS no encontrado"
fi

# Verificar directorio de descargas
if [ -d "/downloads" ]; then
    log "✓ Directorio de descargas montado"
    chown $USER:$USER /downloads 2>/dev/null || true
else
    log "⚠ Advertencia: Directorio de descargas no encontrado"
fi

# Configurar permisos para directorios escribibles
log "Configurando permisos..."
chown -R $USER:$USER /app/logs 2>/dev/null || true
chown -R $USER:$USER /app/images 2>/dev/null || true
chown -R $USER:$USER /app/templates 2>/dev/null || true
chown -R $USER:$USER /app/static 2>/dev/null || true
chown -R $USER:$USER /downloads 2>/dev/null || true

# Configurar nginx
[ -w /var/log/nginx ] && chown -R $USER:$USER /var/log/nginx 2>/dev/null || true
[ -w /var/lib/nginx ] && chown -R $USER:$USER /var/lib/nginx 2>/dev/null || true

# Variables de entorno de Telegram
export TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN:-""}
export TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID:-""}
export TELEGRAM_ENABLED=${TELEGRAM_ENABLED:-"false"}

log "Configuración de Telegram:"
log "  Habilitado: $TELEGRAM_ENABLED"
log "  Bot Token: ${TELEGRAM_BOT_TOKEN:0:10}..." # Solo primeros 10 caracteres
log "  Chat ID: $TELEGRAM_CHAT_ID"


# Verificar que los archivos de Python básicos existen
log "Verificando archivos de aplicación..."

if [ ! -f "/app/app.py" ]; then
    log "❌ app.py no encontrado"
    exit 1
fi

if [ ! -f "/app/db_manager.py" ]; then
    log "❌ db_manager.py no encontrado"
    exit 1
fi

if [ ! -f "/app/img_manager.py" ]; then
    log "❌ img_manager.py no encontrado"
    exit 1
fi


# Verificar que los archivos de Telegram básicos existen
if [ ! -f "/app/telegram_notifier.py" ]; then
    log "Creando telegram_notifier.py básico..."
    cat > /app/telegram_notifier.py << 'EOF'
import logging

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self, enabled=False, bot_token=None, chat_id=None):
        self.enabled = enabled
        logger.info(f"TelegramNotifier {'habilitado' if enabled else 'deshabilitado'}")
    
    def notify_download_started(self, album_name, artist_name, user_ip, source):
        if self.enabled:
            logger.info(f"[TELEGRAM] Download started: {artist_name} - {album_name}")
    
    def notify_download_completed(self, album_name, artist_name, file_count, file_path, source):
        if self.enabled:
            logger.info(f"[TELEGRAM] Download completed: {artist_name} - {album_name}")
    
    def notify_download_error(self, album_name, artist_name, error_message):
        if self.enabled:
            logger.info(f"[TELEGRAM] Download error: {artist_name} - {album_name}")
    
    def notify_album_extracted(self, album_name, artist_name, extract_path, file_count):
        if self.enabled:
            logger.info(f"[TELEGRAM] Album extracted: {artist_name} - {album_name}")
    
    def notify_file_auto_deleted(self, album_name, artist_name, file_path):
        if self.enabled:
            logger.info(f"[TELEGRAM] File auto-deleted: {artist_name} - {album_name}")

def create_notifier(config):
    if not config:
        return TelegramNotifier(enabled=False)
    try:
        enabled = config.getboolean('telegram', 'enabled', fallback=False)
        return TelegramNotifier(enabled=enabled)
    except:
        return TelegramNotifier(enabled=False)
EOF
fi

# Verificar y crear stats_manager.py si no existe
if [ ! -f "/app/stats_manager.py" ]; then
    log "Creando stats_manager.py básico..."
    cat > /app/stats_manager.py << 'EOF'
import logging
import sqlite3
import os
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class StatsManager:
    def __init__(self, db_path: str, config: dict = None):
        self.db_path = db_path
        self.config = config or {}
        logger.info("StatsManager básico inicializado")
    
    def get_system_overview(self) -> Dict[str, Any]:
        return {
            'database': {'size_mb': 0, 'total_tables': 0, 'last_updated': '2024-01-01'},
            'content': {'total_artists': 0, 'total_albums': 0, 'total_songs': 0, 'total_duration_hours': 0},
            'completeness': 0
        }
    
    def get_database_info(self) -> Dict[str, Any]:
        return {
            'tables': {},
            'database_size': 0,
            'total_tables': 0,
            'last_updated': '2024-01-01'
        }
    
    def get_artists_stats(self) -> Dict[str, Any]:
        return {
            'total_artists': 0,
            'by_country': [],
            'top_artists': []
        }
    
    def get_albums_stats(self) -> Dict[str, Any]:
        return {
            'total_albums': 0,
            'by_decade': [],
            'by_genre': [],
            'by_label': []
        }
    
    def get_songs_stats(self) -> Dict[str, Any]:
        return {
            'total_songs': 0,
            'by_genre': [],
            'duration_stats': {},
            'lyrics_stats': {}
        }
    
    def get_missing_data_stats(self) -> Dict[str, Any]:
        return {}
    
    def get_chart_data_for_frontend(self, chart_type: str, category: str) -> Dict[str, Any]:
        return {
            'chart': '{"data": [], "layout": {"title": "No data available"}}',
            'data': []
        }
EOF
fi

# Verificar img_manager.py y recrearlo si tiene problemas
if [ -f "/app/img_manager.py" ]; then
    # Verificar si el archivo tiene sintaxis correcta
    python3 -c "
import ast
try:
    with open('/app/img_manager.py', 'r') as f:
        content = f.read()
    ast.parse(content)
    print('✓ img_manager.py syntax OK')
except SyntaxError as e:
    print(f'❌ img_manager.py syntax error: {e}')
    exit(1)
except Exception as e:
    print(f'❌ img_manager.py error: {e}')
    exit(1)
" || {
    log "Recreando img_manager.py con sintaxis correcta..."
    cat > /app/img_manager.py << 'EOF'
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

class ImageManager:
    def __init__(self, config):
        self.config = config
        self.images_dir = config.get('paths', {}).get('images', '/app/images')
        logger.info("ImageManager básico inicializado")
        
        # Crear directorios necesarios
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs('/app/static/images', exist_ok=True)
    
    def get_artist_image(self, artist_id: int) -> Optional[str]:
        return self.get_default_artist_image()
    
    def get_album_image(self, album_id: int) -> Optional[str]:
        return self.get_default_album_image()
    
    def get_default_artist_image(self) -> str:
        return "/app/static/images/default_album.jpg"
    
    def get_default_album_image(self) -> str:
        return "/app/static/images/default_album.jpg"
    
    def clear_cache(self, category: str = None) -> bool:
        return True
    
    def get_cache_stats(self) -> dict:
        return {'artists': 0, 'albums': 0, 'total_size_mb': 0}
EOF
}
else
    log "img_manager.py no encontrado, creando uno básico..."
    cat > /app/img_manager.py << 'EOF'
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

class ImageManager:
    def __init__(self, config):
        self.config = config
        self.images_dir = config.get('paths', {}).get('images', '/app/images')
        logger.info("ImageManager básico inicializado")
        
        # Crear directorios necesarios
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs('/app/static/images', exist_ok=True)
    
    def get_artist_image(self, artist_id: int) -> Optional[str]:
        return self.get_default_artist_image()
    
    def get_album_image(self, album_id: int) -> Optional[str]:
        return self.get_default_album_image()
    
    def get_default_artist_image(self) -> str:
        return "/app/static/images/default_album.jpg"
    
    def get_default_album_image(self) -> str:
        return "/app/static/images/default_album.jpg"
    
    def clear_cache(self, category: str = None) -> bool:
        return True
    
    def get_cache_stats(self) -> dict:
        return {'artists': 0, 'albums': 0, 'total_size_mb': 0}
EOF
fi


# Probar aplicación Flask
log "Verificando aplicación Flask..."
cd /app

# Test de importación básica
python3 -c "
import sys
import traceback
try:
    print('Testing basic imports...')
    import flask
    print('✓ Flask imported')
    import yaml  
    print('✓ PyYAML imported')
    import sqlite3
    print('✓ SQLite3 imported')
    import os
    print('✓ OS imported')
    
    print('Testing app import...')
    from app import create_app
    print('✓ App module imported')
    
    app = create_app()
    print('✓ Flask app created successfully')
    
except Exception as e:
    print(f'❌ Error: {e}')
    traceback.print_exc()
    sys.exit(1)
" || {
    log "❌ Error cargando aplicación Flask"
    exit 1
}

log "✓ Aplicación Flask verificada correctamente"

log "=== Iniciando servicios ==="
log "  - Nginx: puerto 80"
log "  - Flask: puerto 5157"

# Ejecutar comando principal
exec "$@"