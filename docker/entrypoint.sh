#!/bin/bash
set -e

echo "🎵 Iniciando Music Web Explorer..."

# Leer configuración del config.ini
CONFIG_FILE="/app/config.ini"
if [ -f "$CONFIG_FILE" ]; then
    # Leer usuario del contenedor desde config.ini
    CONTAINER_USER=$(python3 -c "
import configparser
c = configparser.ConfigParser()
c.read('$CONFIG_FILE')
try:
    print(c.get('container', 'user', fallback='appuser'))
except:
    print('appuser')
" 2>/dev/null || echo "appuser")
    
    # Leer UID/GID del contenedor desde config.ini
    CONTAINER_UID=$(python3 -c "
import configparser
c = configparser.ConfigParser()
c.read('$CONFIG_FILE')
try:
    print(c.get('container', 'uid', fallback='1000'))
except:
    print('1000')
" 2>/dev/null || echo "1000")
    
    CONTAINER_GID=$(python3 -c "
import configparser
c = configparser.ConfigParser()
c.read('$CONFIG_FILE')
try:
    print(c.get('container', 'gid', fallback='1000'))
except:
    print('1000')
" 2>/dev/null || echo "1000")
    
    # Leer configuración SSH desde config.ini
    SSH_USER=$(python3 -c "
import configparser
c = configparser.ConfigParser()
c.read('$CONFIG_FILE')
try:
    print(c.get('download', 'ssh_user', fallback='pepe'))
except:
    print('pepe')
" 2>/dev/null || echo "pepe")
    
    SSH_HOST=$(python3 -c "
import configparser
c = configparser.ConfigParser()
c.read('$CONFIG_FILE')
try:
    print(c.get('download', 'ssh_host', fallback='pepecono'))
except:
    print('pepecono')
" 2>/dev/null || echo "pepecono")
    
    SSH_KEY_PATH=$(python3 -c "
import configparser
c = configparser.ConfigParser()
c.read('$CONFIG_FILE')
try:
    print(c.get('download', 'ssh_key_path', fallback=''))
except:
    print('')
" 2>/dev/null || echo "")
    
    echo "📋 Configuración leída del config.ini:"
    echo "   👤 Usuario contenedor: $CONTAINER_USER (UID:$CONTAINER_UID GID:$CONTAINER_GID)"
    echo "   🔗 SSH destino: $SSH_USER@$SSH_HOST"
    echo "   🔑 Clave SSH desde config: $SSH_KEY_PATH"
else
    echo "⚠️  config.ini no encontrado, usando valores por defecto"
    CONTAINER_USER="appuser"
    CONTAINER_UID="1000"
    CONTAINER_GID="1000"
    SSH_USER="pepe"
    SSH_HOST="pepecono"
    SSH_KEY_PATH=""
fi

# Crear directorios necesarios
mkdir -p /app/data /app/music /downloads /app/logs /app/static

# Manejar creación de usuario de forma más robusta
echo "➕ Configurando usuario de ejecución..."

# Verificar si ya existe un usuario con ese UID
EXISTING_USER=$(getent passwd "$CONTAINER_UID" | cut -d: -f1 || echo "")

if [ -n "$EXISTING_USER" ]; then
    echo "👤 Usuario existente con UID $CONTAINER_UID: $EXISTING_USER"
    if [ "$EXISTING_USER" != "$CONTAINER_USER" ]; then
        echo "🔄 Usando usuario existente: $EXISTING_USER"
        CONTAINER_USER="$EXISTING_USER"
    fi
else
    # Crear grupo si no existe
    if ! getent group "$CONTAINER_GID" >/dev/null 2>&1; then
        groupadd -g "$CONTAINER_GID" "$CONTAINER_USER" || echo "⚠️  No se pudo crear grupo"
    fi
    
    # Crear usuario si no existe
    if ! id "$CONTAINER_USER" >/dev/null 2>&1; then
        useradd -u "$CONTAINER_UID" -g "$CONTAINER_GID" -m -s /bin/bash "$CONTAINER_USER" || {
            echo "⚠️  No se pudo crear usuario $CONTAINER_USER, usando root"
            CONTAINER_USER="root"
        }
    fi
fi

echo "✅ Usuario de ejecución final: $CONTAINER_USER"

# Configurar permisos
echo "📁 Configurando permisos..."

# Solo cambiar permisos en directorios de escritura
if [ -w "/downloads" ]; then
    chown -R "$CONTAINER_USER":"$CONTAINER_USER" /downloads 2>/dev/null || echo "⚠️  No se pudieron cambiar permisos de /downloads"
fi

if [ -w "/app/logs" ]; then
    chown -R "$CONTAINER_USER":"$CONTAINER_USER" /app/logs 2>/dev/null || echo "⚠️  No se pudieron cambiar permisos de /app/logs"
fi

if [ -w "/app/static" ]; then
    chown -R www-data:www-data /app/static 2>/dev/null || echo "⚠️  No se pudieron cambiar permisos de /app/static"
fi

# Verificar base de datos (pero NO cambiar permisos - es solo lectura)
if [ -f "/app/data/musica.sqlite" ]; then
    echo "✅ Base de datos encontrada en /app/data/musica.sqlite"
    if [ -r "/app/data/musica.sqlite" ]; then
        echo "✅ Base de datos es legible"
    else
        echo "❌ Base de datos no es legible"
    fi
else
    echo "⚠️  Base de datos no encontrada en /app/data/musica.sqlite"
    echo "   Asegúrate de montar el volumen con la base de datos"
fi

# Configurar SSH si es necesario
if [ -n "$SSH_KEY_PATH" ] && [ -f "/tmp/host_ssh/$(basename "$SSH_KEY_PATH")" ]; then
    echo "🔍 Configurando SSH para usuario $CONTAINER_USER..."
    
    USER_HOME=$(getent passwd "$CONTAINER_USER" | cut -d: -f6)
    if [ -z "$USER_HOME" ]; then
        USER_HOME="/home/$CONTAINER_USER"
    fi
    
    mkdir -p "$USER_HOME/.ssh"
    
    # Copiar clave SSH
    SSH_KEY_NAME=$(basename "$SSH_KEY_PATH")
    echo "📋 Copiando clave SSH: /tmp/host_ssh/$SSH_KEY_NAME → $USER_HOME/.ssh/$SSH_KEY_NAME"
    cp "/tmp/host_ssh/$SSH_KEY_NAME" "$USER_HOME/.ssh/$SSH_KEY_NAME"
    chmod 600 "$USER_HOME/.ssh/$SSH_KEY_NAME"
    
    # Copiar config SSH si existe
    if [ -f "/tmp/host_ssh/config" ]; then
        echo "📋 Copiando config SSH: /tmp/host_ssh/config → $USER_HOME/.ssh/config"
        cp "/tmp/host_ssh/config" "$USER_HOME/.ssh/config"
        chmod 600 "$USER_HOME/.ssh/config"
    fi
    
    # Configurar permisos
    chown -R "$CONTAINER_USER":"$CONTAINER_USER" "$USER_HOME/.ssh" 2>/dev/null || true
    chmod 700 "$USER_HOME/.ssh"
    
    echo "✅ Clave SSH configurada: $USER_HOME/.ssh/$SSH_KEY_NAME"
    
    # Verificar conectividad SSH
    echo "🔍 Verificando conectividad SSH a $SSH_HOST..."
    if su - "$CONTAINER_USER" -c "ssh -i '$USER_HOME/.ssh/$SSH_KEY_NAME' -o ConnectTimeout=5 -o StrictHostKeyChecking=no $SSH_USER@$SSH_HOST 'echo OK'" 2>/dev/null; then
        echo "✅ Conectividad SSH verificada"
    else
        echo "⚠️  No se puede conectar SSH a $SSH_HOST"
        echo "   Verifica la clave SSH y la conectividad de red"
    fi
else
    echo "⚠️  No se encontró configuración SSH válida"
    echo "   Las descargas SSH no funcionarán"
fi

# Crear página de health check
cat > /app/static/health.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Music Explorer - Health Check</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial; text-align: center; margin: 40px; }
        .status { padding: 20px; margin: 20px; border-radius: 10px; }
        .ok { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <h1>🎵 Music Web Explorer</h1>
    <h2>Container Health Check</h2>
    <div class="status ok">✅ Contenedor funcionando</div>
    <p><a href="/">Ir a la aplicación</a></p>
    <div style="margin-top: 20px; font-size: 12px; color: #666;">
        Timestamp: $(date)
    </div>
</body>
</html>
EOF

echo "✅ Configuración inicial completada"
echo "🌐 Acceso web: http://localhost:8447"
echo "🔌 API directa: http://localhost:5157"
echo "📁 Directorio de descargas: /downloads"
echo "👤 Usuario de ejecución: $CONTAINER_USER (UID:$CONTAINER_UID)"
echo "🔗 SSH configurado para: $SSH_USER@$SSH_HOST"

# Actualizar configuración de supervisor dinámicamente
if [ -f "/etc/supervisor/conf.d/supervisord.conf" ]; then
    echo "🔧 Actualizando configuración de supervisor..."
    
    # Crear nueva configuración de supervisor con el usuario correcto
    cat > /etc/supervisor/conf.d/supervisord.conf << EOF
[supervisord]
nodaemon=true
user=root
logfile=/app/logs/supervisord.log
childlogdir=/app/logs/

[program:flask_app]
command=python3 /app/app.py
directory=/app
user=$CONTAINER_USER
autostart=true
autorestart=true
stdout_logfile=/app/logs/flask_app.log
stderr_logfile=/app/logs/flask_app_error.log
environment=PYTHONUNBUFFERED=1,USER="$CONTAINER_USER",CONTAINER_UID="$CONTAINER_UID",HOME="/home/$CONTAINER_USER"

[program:nginx]
command=/usr/sbin/nginx -g "daemon off;"
user=root
autostart=true
autorestart=true
stdout_logfile=/app/logs/nginx.log
stderr_logfile=/app/logs/nginx_error.log
EOF

    echo "🚀 Iniciando servicios con supervisor..."
    exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
else
    echo "⚠️  Supervisor no encontrado, iniciando Flask directamente..."
    echo "👤 Cambiando a usuario: $CONTAINER_USER"
    cd /app
    
    # Cambiar al usuario correcto y ejecutar Flask
    if [ "$CONTAINER_USER" = "root" ]; then
        export USER="root"
        export CONTAINER_UID="$CONTAINER_UID"
        export HOME="/root"
        exec python3 app.py
    else
        export USER="$CONTAINER_USER"
        export CONTAINER_UID="$CONTAINER_UID"
        export HOME="/home/$CONTAINER_USER"
        exec su - "$CONTAINER_USER" -c "cd /app && USER='$CONTAINER_USER' CONTAINER_UID='$CONTAINER_UID' HOME='/home/$CONTAINER_USER' python3 app.py"
    fi
fi