FROM python:3.11-slim

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV USER=1000
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

# Crear usuario con UID específico y grupo music para evitar problemas de permisos NFS
RUN groupadd -g 1001 music 2>/dev/null || true && \
    groupadd -g ${USER_GID} ${USER} 2>/dev/null || true && \
    useradd -u ${USER_UID} -g ${USER_GID} -G music -m -s /bin/bash ${USER}

# Crear directorios necesarios
RUN mkdir -p /app /app/data /app/logs /app/static /app/templates /app/images \
    && chown -R ${USER}:${USER} /app

# Instalar dependencias de Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copiar archivos de la aplicación
COPY . /app/
WORKDIR /app

# Configurar Nginx
COPY docker/nginx.conf /etc/nginx/sites-available/default
RUN rm -f /etc/nginx/sites-enabled/default && \
    ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/

# Configurar Supervisor
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Crear archivo de salud para healthcheck
RUN echo '<html><body>OK</body></html>' > /app/static/health.html

# Configurar permisos (solo directorios que necesitan escritura)
RUN chown -R ${USER}:${USER} /app/logs /app/images
# NO chown de /app completo para evitar problemas con archivos read-only
RUN chown -R ${USER}:${USER} /var/log/nginx
RUN chown -R ${USER}:${USER} /var/lib/nginx

# Exponer puertos
EXPOSE 80 5157

# Script de entrada
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]