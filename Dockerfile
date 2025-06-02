# Music Web Explorer - Dockerfile simplificado sin nginx
FROM python:3.11-slim

# Instalar dependencias del sistema mínimas
RUN apt-get update && apt-get install -y \
    sqlite3 \
    rsync \
    openssh-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear directorios de la aplicación
RUN mkdir -p /app/data /app/music /downloads /app/logs /app/static /app/templates /app/images

# Directorio de trabajo
WORKDIR /app

# Copiar requirements y instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar Pillow para procesamiento de imágenes
RUN pip install --no-cache-dir Pillow

# Copiar archivos de la aplicación
COPY app.py music_manager.py config.ini ./
COPY telegram_notifier.py /app/
COPY templates/ ./templates/

# IMPORTANTE: Copiar imágenes pre-procesadas al contenedor
# Este directorio debe existir antes del build (creado por extract_images.py)
COPY container_images/ /app/images/

# Verificar que las imágenes se copiaron correctamente
RUN echo "📊 Verificando imágenes copiadas..." && \
    if [ -d "/app/images" ]; then \
        IMAGE_COUNT=$(find /app/images -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" \) | wc -l); \
        echo "✅ Imágenes encontradas: $IMAGE_COUNT archivos"; \
        if [ -f "/app/images/master_index.json" ]; then \
            echo "✅ Índice maestro disponible"; \
            # Mostrar estadísticas del índice
            python3 -c "
import json
with open('/app/images/master_index.json', 'r') as f:
    data = json.load(f)
    artists = len(data.get('artists', {}))
    albums = len(data.get('albums', {}))
    print(f'📊 Índice: {artists} artistas, {albums} álbumes')
" || echo "⚠️  Error leyendo índice"; \
        else \
            echo "❌ Índice maestro no encontrado"; \
            echo "   Ejecuta 'extract_images.py' antes de construir"; \
            exit 1; \
        fi; \
    else \
        echo "❌ Directorio de imágenes no encontrado"; \
        echo "   Ejecuta 'extract_images.py' antes de construir"; \
        exit 1; \
    fi

# Configurar permisos - CORREGIDO para www-data
RUN chown -R www-data:www-data /app/images && \
    chmod -R 755 /app/images && \
    chmod -R 755 /app && \
    chmod +x /app/app.py

# También asegurar que el usuario de la aplicación puede leer las imágenes
RUN ls -la /app/images/ && \
    ls -la /app/images/artists/ | head -5 && \
    ls -la /app/images/albums/ | head -5
    
# Copiar solo el entrypoint (sin nginx/supervisor)
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Exponer solo el puerto de Flask
EXPOSE 8447

# Volúmenes para datos persistentes (SIN imágenes, ya están copiadas)
VOLUME ["/app/data", "/downloads", "/app/logs"]

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8447/api/stats || exit 1

# Entrypoint
ENTRYPOINT ["/entrypoint.sh"]