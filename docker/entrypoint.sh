#!/bin/bash
set -e

echo "=== Iniciando Music Web Explorer ==="

# Función para logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Crear directorios necesarios si no existen
log "Creando directorios necesarios..."
mkdir -p /app/logs /app/data /app/images /app/static/images /downloads

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
    log "Base de datos encontrada: /app/data/musica.sqlite"
    # Verificar permisos de lectura sin intentar cambiar ownership
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
    # Verificar acceso de lectura sin listar contenido
    if [ -r "/mnt/NFS/moode/moode" ]; then
        log "✓ Directorio NFS accesible para lectura"
        # Intentar contar archivos sin mostrar errores
        MUSIC_COUNT=$(find /mnt/NFS/moode/moode -maxdepth 1 -type f 2>/dev/null | wc -l)
        log "Archivos en directorio raíz NFS: $MUSIC_COUNT"
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

# Configurar permisos para nginx (solo directorios escribibles)
log "Configurando permisos para nginx..."
chown -R $USER:$USER /app/logs 2>/dev/null || true
chown -R $USER:$USER /app/images 2>/dev/null || true
chown -R $USER:$USER /downloads 2>/dev/null || true

# NO cambiar permisos de archivos read-only:
# - /app/data/musica.sqlite (montado :ro)
# - /app/config.yml (montado :ro)

# Configurar nginx solo si los directorios existen y son escribibles
[ -w /var/log/nginx ] && chown -R $USER:$USER /var/log/nginx 2>/dev/null || true
[ -w /var/lib/nginx ] && chown -R $USER:$USER /var/lib/nginx 2>/dev/null || true

# Inicializar configuración si no existe
if [ ! -f "/app/config.ini" ] && [ -f "/app/config.yml" ]; then
    log "Usando configuración por defecto"
fi

# Variables de entorno de Telegram
export TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN:-""}
export TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID:-""}
export TELEGRAM_ENABLED=${TELEGRAM_ENABLED:-"false"}

log "Configuración de Telegram:"
log "  Habilitado: $TELEGRAM_ENABLED"
log "  Bot Token: ${TELEGRAM_BOT_TOKEN:0:10}..." # Solo primeros 10 caracteres
log "  Chat ID: $TELEGRAM_CHAT_ID"

# Probar aplicación Flask
log "Verificando aplicación Flask..."
cd /app
python3 -c "import app; print('✓ Aplicación Flask cargada correctamente')" || {
    log "❌ Error cargando aplicación Flask"
    exit 1
}

log "=== Iniciando servicios ==="
log "  - Nginx: puerto 80"
log "  - Flask: puerto 5157"

# Ejecutar comando principal
exec "$@"