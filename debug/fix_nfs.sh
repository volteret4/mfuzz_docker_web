#!/bin/bash

# Script para resolver problemas de permisos NFS en el contenedor Docker
# Este script debe ejecutarse en el HOST, no en el contenedor

echo "=== Solucionando problemas de permisos NFS para Docker ==="

# Configuración
NFS_MOUNT_POINT="/mnt/NFS/moode/moode"
USER_UID=1000
USER_GID=1000
USER_NAME="huan"

# Función para logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Verificar que el directorio NFS existe
if [ ! -d "$NFS_MOUNT_POINT" ]; then
    log "ERROR: El directorio NFS $NFS_MOUNT_POINT no existe"
    exit 1
fi

log "Directorio NFS encontrado: $NFS_MOUNT_POINT"

# Verificar el usuario y UID
CURRENT_UID=$(id -u $USER_NAME)
CURRENT_GID=$(id -g $USER_NAME)

log "Usuario actual: $USER_NAME (UID: $CURRENT_UID, GID: $CURRENT_GID)"

# SOLUCIÓN 1: Verificar opciones de montaje NFS
log "=== Verificando opciones de montaje NFS ==="
mount | grep $NFS_MOUNT_POINT

# SOLUCIÓN 2: Verificar permisos actuales
log "=== Verificando permisos del directorio NFS ==="
ls -la $NFS_MOUNT_POINT | head -10

# SOLUCIÓN 3: Configurar mapeo de usuarios en NFS (en el servidor NFS)
log "=== Configuración recomendada para el servidor NFS ==="
echo "En el servidor NFS, asegúrate de tener en /etc/exports:"
echo "$NFS_MOUNT_POINT *(ro,sync,no_subtree_check,all_squash,anonuid=$USER_UID,anongid=$USER_GID)"
echo ""
echo "O para acceso específico al cliente:"
echo "$NFS_MOUNT_POINT your_client_ip(ro,sync,no_subtree_check,no_root_squash)"

# SOLUCIÓN 4: Remontar NFS con opciones específicas
log "=== Comandos para remontar NFS con mejores opciones ==="
echo "sudo umount $NFS_MOUNT_POINT"
echo "sudo mount -t nfs -o ro,soft,intr,rsize=8192,wsize=8192,timeo=14 your_nfs_server:/path/to/music $NFS_MOUNT_POINT"

# SOLUCIÓN 5: Crear script de pre-start para Docker
PRESTART_SCRIPT="/home/$USER_NAME/contenedores/mfuzz/prestart.sh"
log "=== Creando script de pre-start: $PRESTART_SCRIPT ==="

mkdir -p "$(dirname $PRESTART_SCRIPT)"

cat > $PRESTART_SCRIPT << 'EOF'
#!/bin/bash
# Script de pre-start para el contenedor Music Web Explorer

echo "Verificando acceso a NFS..."

# Verificar que NFS está montado
if ! mountpoint -q /mnt/NFS/moode/moode; then
    echo "ERROR: NFS no está montado"
    exit 1
fi

# Verificar acceso de lectura
if [ ! -r /mnt/NFS/moode/moode ]; then
    echo "ERROR: No hay permisos de lectura en NFS"
    exit 1
fi

# Contar archivos musicales como test
MUSIC_FILES=$(find /mnt/NFS/moode/moode -name "*.mp3" -o -name "*.flac" -o -name "*.m4a" 2>/dev/null | wc -l)
echo "Archivos musicales encontrados: $MUSIC_FILES"

if [ $MUSIC_FILES -eq 0 ]; then
    echo "ADVERTENCIA: No se encontraron archivos musicales"
fi

echo "Verificación de NFS completada"
EOF

chmod +x $PRESTART_SCRIPT

# SOLUCIÓN 6: Actualizar docker-compose con mejores opciones
COMPOSE_FILE="/home/$USER_NAME/gits/pollo/mfuzz_docker_web/docker-compose.yml"
log "=== Recomendaciones para docker-compose.yml ==="
echo ""
echo "Añade estas opciones a tu servicio en docker-compose.yml:"
echo ""
echo "services:"
echo "  music-web-explorer:"
echo "    user: \"$USER_UID:$USER_GID\""
echo "    volumes:"
echo "      - $NFS_MOUNT_POINT:$NFS_MOUNT_POINT:ro"
echo "    environment:"
echo "      - PUID=$USER_UID"
echo "      - PGID=$USER_GID"
echo ""

# SOLUCIÓN 7: Test de acceso
log "=== Test de acceso a archivos musicales ==="
SAMPLE_FILES=$(find $NFS_MOUNT_POINT -name "*.mp3" -o -name "*.flac" -o -name "*.m4a" 2>/dev/null | head -5)

if [ -n "$SAMPLE_FILES" ]; then
    log "✓ Archivos musicales encontrados:"
    echo "$SAMPLE_FILES"
else
    log "⚠ No se encontraron archivos musicales en $NFS_MOUNT_POINT"
fi

# SOLUCIÓN 8: Configurar systemd para auto-montar NFS
log "=== Configuración automática de NFS con systemd ==="
FSTAB_ENTRY="your_nfs_server:/path/to/music $NFS_MOUNT_POINT nfs ro,soft,intr,rsize=8192,wsize=8192,timeo=14 0 0"
echo "Añade esta línea a /etc/fstab para montaje automático:"
echo "$FSTAB_ENTRY"

log "=== Script de solución de permisos NFS completado ==="
log "Ejecuta el script prestart.sh antes de iniciar el contenedor:"
log "$PRESTART_SCRIPT"