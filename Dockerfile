FROM python:3.11-slim

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV USER=appuser
ENV USER_UID=1000
ENV USER_GID=1001

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    curl \
    sqlite3 \
    nginx \
    supervisor \
    rsync \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario y grupos
RUN groupadd -g 1001 music 2>/dev/null || true && \
    groupadd -g ${USER_GID} ${USER} 2>/dev/null || true && \
    useradd -u ${USER_UID} -g ${USER_GID} -G music -m -s /bin/bash ${USER}

# Crear directorios base
RUN mkdir -p /app /app/data /app/logs /app/static /app/templates /app/images \
    && chown -R ${USER_UID}:${USER_GID} /app

# Copiar y instalar requirements primero (para cache de Docker)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copiar archivos de configuración
COPY docker/entrypoint.sh /entrypoint.sh
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker/nginx.conf /etc/nginx/sites-available/default
COPY app.py db_manager.py download_manager.py apis_endpoints.py img_manager.py stats_manager.py telegram_notifier.py config.yml /app/
COPY templates/index.html templates/sistema.html /app/



# Configurar nginx
RUN rm -f /etc/nginx/sites-enabled/default && \
    ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/



# Crear archivos básicos si no existen
RUN echo '<html><body>OK</body></html>' > /app/static/health.html

# Crear stubs básicos si faltan archivos
RUN cd /app && \
    if [ ! -f "img_manager.py" ]; then \
        echo "import logging; logger = logging.getLogger(__name__); class ImageManager: pass" > img_manager.py; \
    fi && \
    if [ ! -f "telegram_notifier.py" ]; then \
        echo "import logging; logger = logging.getLogger(__name__); class TelegramNotifier: pass; def create_notifier(c): return TelegramNotifier()" > telegram_notifier.py; \
    fi

# Configurar permisos
RUN chmod +x /entrypoint.sh && \
    chown -R ${USER}:${USER} /app/logs /app/images /app/static /app/templates && \
    chown -R ${USER}:${USER} /var/log/nginx /var/lib/nginx 2>/dev/null || true

# Crear directorio de templates y copiar archivos HTML
RUN mkdir -p /app/templates && \
    if [ -f "/app/index.html" ]; then cp /app/index.html /app/templates/; fi && \
    if [ -f "/app/sistema.html" ]; then cp /app/sistema.html /app/templates/; fi

WORKDIR /app

# Exponer puertos
EXPOSE 80 5157

# Punto de entrada
ENTRYPOINT ["/entrypoint.sh"]
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]