#!/bin/bash
# Script para corregir redirecciones HTTPS en el contenedor

echo "🔧 Corrigiendo redirecciones HTTPS forzadas..."

# 1. Verificar y corregir nginx
echo "📝 Verificando configuración de nginx..."
NGINX_CONF="/etc/nginx/sites-available/default"

if [ -f "$NGINX_CONF" ]; then
    echo "🔍 Buscando redirecciones HTTPS en nginx..."
    
    # Buscar redirecciones problemáticas
    if grep -q "return.*https" "$NGINX_CONF"; then
        echo "⚠️ Encontradas redirecciones HTTPS en nginx"
        grep -n "return.*https" "$NGINX_CONF"
        
        # Hacer backup
        cp "$NGINX_CONF" "$NGINX_CONF.backup.$(date +%s)"
        
        # Comentar redirecciones HTTPS
        sed -i 's/return.*https/#&/' "$NGINX_CONF"
        echo "✅ Redirecciones HTTPS comentadas"
    fi
    
    # Verificar que no haya configuración SSL forzada
    if grep -q "ssl.*on" "$NGINX_CONF"; then
        echo "⚠️ SSL forzado encontrado en nginx"
        sed -i 's/ssl.*on/#&/' "$NGINX_CONF"
        echo "✅ SSL forzado deshabilitado"
    fi
fi

# 2. Verificar configuración de Flask
echo "🐍 Verificando configuración de Flask..."
FLASK_APP="/app/app.py"

if [ -f "$FLASK_APP" ]; then
    # Verificar que no esté corriendo con SSL
    if grep -q "ssl_context" "$FLASK_APP"; then
        echo "⚠️ SSL context encontrado en Flask"
        sed -i 's/ssl_context=/#ssl_context=/' "$FLASK_APP"
        echo "✅ SSL context deshabilitado en Flask"
    fi
    
    # Verificar puerto correcto
    if grep -q "port=5157" "$FLASK_APP"; then
        echo "✅ Puerto Flask correcto (5157)"
    else
        echo "⚠️ Puerto Flask incorrecto"
    fi
fi

# 3. Verificar headers de seguridad
echo "🔒 Verificando headers de seguridad..."

# Verificar que no haya HSTS permanente
if grep -rq "max-age=[1-9]" /etc/nginx/ 2>/dev/null; then
    echo "⚠️ HSTS con max-age > 0 encontrado"
    # Corregir HSTS
    find /etc/nginx/ -type f -name "*.conf" -exec sed -i 's/max-age=[0-9]*/max-age=0/g' {} \;
    echo "✅ HSTS corregido a max-age=0"
fi

# 4. Reiniciar servicios si es necesario
echo "🔄 Verificando si necesita reiniciar servicios..."

# Verificar si nginx está corriendo
if pgrep nginx > /dev/null; then
    echo "🔄 Reiniciando nginx..."
    nginx -t && nginx -s reload
    if [ $? -eq 0 ]; then
        echo "✅ Nginx reiniciado correctamente"
    else
        echo "❌ Error reiniciando nginx"
        nginx -T
    fi
else
    echo "ℹ️ Nginx no está corriendo"
fi

# 5. Test de conectividad
echo "🧪 Probando conectividad HTTP..."

# Test básico
HTTP_TEST=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:80/ 2>/dev/null || echo "ERROR")
if [ "$HTTP_TEST" = "200" ]; then
    echo "✅ HTTP port 80 funciona"
else
    echo "❌ HTTP port 80 no funciona (código: $HTTP_TEST)"
fi

# Test Flask directo
FLASK_TEST=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5157/ 2>/dev/null || echo "ERROR")
if [ "$FLASK_TEST" = "200" ]; then
    echo "✅ Flask port 5157 funciona"
else
    echo "❌ Flask port 5157 no funciona (código: $FLASK_TEST)"
fi

# Test específico de imágenes
echo "🖼️ Probando endpoint de imágenes..."
IMG_TEST=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:5157/api/test-image" 2>/dev/null || echo "ERROR")
if [ "$IMG_TEST" = "200" ]; then
    echo "✅ Endpoint de imágenes funciona"
else
    echo "❌ Endpoint de imágenes no funciona (código: $IMG_TEST)"
fi

# 6. Verificar redirecciones específicas
echo "🔍 Verificando redirecciones específicas..."

# Test con curl siguiendo redirecciones
REDIRECT_TEST=$(curl -s -L -w "%{url_effective} %{http_code}" -o /dev/null "http://127.0.0.1:80/api/test-image" 2>/dev/null)
echo "Test de redirección: $REDIRECT_TEST"

if echo "$REDIRECT_TEST" | grep -q "https://"; then
    echo "❌ ¡REDIRECCIÓN A HTTPS DETECTADA!"
    echo "La URL final contiene HTTPS"
else
    echo "✅ No se detectaron redirecciones a HTTPS"
fi

# 7. Mostrar configuración actual
echo "📋 Configuración actual:"
echo "- Nginx status: $(systemctl is-active nginx 2>/dev/null || echo 'no systemctl')"
echo "- Puerto 80: $(netstat -ln 2>/dev/null | grep ':80 ' | wc -l) listeners"
echo "- Puerto 5157: $(netstat -ln 2>/dev/null | grep ':5157 ' | wc -l) listeners"
echo "- Procesos nginx: $(pgrep -c nginx 2>/dev/null || echo 0)"
echo "- Procesos python: $(pgrep -c python 2>/dev/null || echo 0)"

echo ""
echo "🎯 PRÓXIMOS PASOS:"
echo "1. Si ves redirecciones HTTPS, reinicia el contenedor:"
echo "   docker-compose restart music-web-explorer"
echo ""
echo "2. En el navegador, limpia HSTS:"
echo "   chrome://net-internals/#hsts"
echo "   Borrar: localhost y 127.0.0.1"
echo ""
echo "3. Usa modo incógnito o prueba con otro navegador"
echo ""
echo "4. En la consola del navegador, ejecuta:"
echo "   finalImageTest()"