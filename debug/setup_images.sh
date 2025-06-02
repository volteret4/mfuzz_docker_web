#!/bin/bash
# setup_images.sh - Script para preparar imágenes en el contenedor

echo "🖼️  Configurando imágenes en el contenedor..."

IMAGES_SOURCE="/tmp/container_images"
IMAGES_DEST="/app/images"

if [ -d "$IMAGES_SOURCE" ]; then
    echo "📁 Copiando imágenes desde $IMAGES_SOURCE a $IMAGES_DEST"
    
    # Crear directorio destino
    mkdir -p "$IMAGES_DEST"
    
    # Copiar con rsync para mejor rendimiento
    if command -v rsync >/dev/null 2>&1; then
        rsync -av "$IMAGES_SOURCE/" "$IMAGES_DEST/"
    else
        cp -r "$IMAGES_SOURCE/"* "$IMAGES_DEST/"
    fi
    
    # Establecer permisos
    chown -R www-data:www-data "$IMAGES_DEST" 2>/dev/null || true
    chmod -R 755 "$IMAGES_DEST"
    
    # Contar archivos
    IMAGE_COUNT=$(find "$IMAGES_DEST" -type f \( -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" -o -name "*.webp" \) | wc -l)
    TOTAL_SIZE=$(du -sh "$IMAGES_DEST" 2>/dev/null | cut -f1)
    
    echo "✅ Imágenes configuradas:"
    echo "   📊 Total de archivos: $IMAGE_COUNT"
    echo "   💾 Tamaño total: $TOTAL_SIZE"
    
    # Verificar índice maestro
    if [ -f "$IMAGES_DEST/master_index.json" ]; then
        echo "✅ Índice maestro encontrado"
    else
        echo "⚠️  Índice maestro no encontrado"
    fi
    
else
    echo "⚠️  No se encontró directorio de imágenes en $IMAGES_SOURCE"
    echo "   Las imágenes no estarán disponibles"
    echo "   Ejecuta extract_images.py antes de construir el contenedor"
fi

echo "🖼️  Configuración de imágenes completada"