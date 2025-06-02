#!/bin/bash
# build.sh - Script completo para build del Music Web Explorer con imágenes

set -e

echo "🎵 Music Web Explorer - Build Completo con Imágenes"
echo "=================================================="

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para mostrar mensajes
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Función para verificar dependencias
check_dependencies() {
    log_info "Verificando dependencias..."
    
    # Verificar Python 3
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 no está instalado"
        exit 1
    fi
    
    # Verificar Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker no está instalado"
        exit 1
    fi
    
    # Verificar docker-compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "docker-compose no está instalado"
        exit 1
    fi
    
    # Verificar archivos necesarios
    required_files=("extract_images.py" "config.ini" "app.py" "docker-compose.yml")
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            log_error "Archivo faltante: $file"
            exit 1
        fi
    done
    
    # Verificar Pillow para Python
    if ! python3 -c "import PIL" 2>/dev/null; then
        log_warning "Pillow no está instalado, instalando..."
        pip3 install Pillow
    fi
    
    log_success "Todas las dependencias están disponibles"
}

# Función para extraer imágenes
extract_images() {
    log_info "Extrayendo imágenes desde la base de datos..."
    
    # Verificar si ya existe el directorio
    if [ -d "container_images" ] && [ "$FORCE_EXTRACT" != "true" ]; then
        echo -n "El directorio container_images ya existe. ¿Sobrescribir? (y/N): "
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            log_warning "Extracción cancelada. Usando imágenes existentes."
            return 0
        fi
        rm -rf container_images
    elif [ "$FORCE_EXTRACT" = "true" ] && [ -d "container_images" ]; then
        log_info "Forzando nueva extracción..."
        rm -rf container_images
    fi
    
    # Ejecutar extracción
    log_info "Ejecutando extract_images.py..."
    if python3 extract_images.py --output ./container_images; then
        # Verificar resultados
        if [ -d "container_images" ]; then
            IMAGE_COUNT=$(find container_images -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" | wc -l)
            TOTAL_SIZE=$(du -sh container_images 2>/dev/null | cut -f1)
            log_success "Extracción completada: $IMAGE_COUNT imágenes ($TOTAL_SIZE)"
            
            # Verificar índice maestro
            if [ -f "container_images/master_index.json" ]; then
                log_success "Índice maestro creado correctamente"
            else
                log_warning "Índice maestro no encontrado"
            fi
        else
            log_error "No se creó el directorio de imágenes"
            exit 1
        fi
    else
        log_error "Error durante la extracción de imágenes"
        exit 1
    fi
}

# Función para preparar directorios del host
prepare_host_directories() {
    log_info "Preparando directorios del host..."
    
    # Directorios que necesita el contenedor
    HOST_DIRS=(
        "$HOME/contenedores/mfuzz/logs"
        "$HOME/contenedores/mfuzz/images"
        "$HOME/Musica"  # Directorio de descargas
    )
    
    for dir in "${HOST_DIRS[@]}"; do
        if [ ! -d "$dir" ]; then
            log_info "Creando directorio: $dir"
            mkdir -p "$dir"
        fi
    done
    
    log_success "Directorios del host preparados"
}

# Función para construir contenedor
build_container() {
    log_info "Construyendo contenedor Docker..."
    
    # Parar contenedor si está corriendo
    if docker-compose ps | grep -q "Up"; then
        log_info "Parando contenedor existente..."
        docker-compose down
    fi
    
    # Build sin cache para asegurar que se incluyan las imágenes
    log_info "Ejecutando docker-compose build..."
    if docker-compose build --no-cache; then
        log_success "Contenedor construido exitosamente"
    else
        log_error "Error construyendo el contenedor"
        exit 1
    fi
}

# Función para desplegar contenedor
deploy_container() {
    log_info "Desplegando contenedor..."
    
    # Iniciar contenedor
    if docker-compose up -d; then
        log_info "Esperando a que el contenedor esté listo..."
        sleep 15
        
        # Verificar que está corriendo
        if docker-compose ps | grep -q "Up"; then
            log_success "Contenedor desplegado exitosamente"
            log_success "🌐 Acceso web: http://localhost:8447"
            log_success "🔌 API directa: http://localhost:5157"
            
            # Verificar imágenes en el contenedor
            log_info "Verificando imágenes en el contenedor..."
            IMAGE_COUNT_CONTAINER=$(docker-compose exec -T music-web-explorer find /app/images -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" \) 2>/dev/null | wc -l || echo "0")
            
            if [ "$IMAGE_COUNT_CONTAINER" -gt 0 ]; then
                log_success "Imágenes en contenedor: $IMAGE_COUNT_CONTAINER archivos"
            else
                log_warning "No se detectaron imágenes en el contenedor"
            fi
            
        else
            log_error "El contenedor no está corriendo correctamente"
            log_info "Mostrando logs:"
            docker-compose logs --tail=20
            exit 1
        fi
    else
        log_error "Error desplegando el contenedor"
        exit 1
    fi
}

# Función para mostrar estado
show_status() {
    echo "📊 Estado actual del Music Web Explorer"
    echo "======================================="
    
    # Estado de imágenes extraídas
    if [ -d "container_images" ]; then
        IMAGE_COUNT=$(find container_images -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" | wc -l)
        TOTAL_SIZE=$(du -sh container_images 2>/dev/null | cut -f1)
        log_success "Imágenes extraídas: $IMAGE_COUNT archivos ($TOTAL_SIZE)"
        
        if [ -f "container_images/master_index.json" ]; then
            # Leer estadísticas del índice maestro
            ARTISTS_COUNT=$(python3 -c "import json; data=json.load(open('container_images/master_index.json')); print(len(data.get('artists', {})))" 2>/dev/null || echo "?")
            ALBUMS_COUNT=$(python3 -c "import json; data=json.load(open('container_images/master_index.json')); print(len(data.get('albums', {})))" 2>/dev/null || echo "?")
            log_success "Índice maestro: $ARTISTS_COUNT artistas, $ALBUMS_COUNT álbumes"
        else
            log_warning "Índice maestro no encontrado"
        fi
    else
        log_warning "Imágenes no extraídas (ejecuta: $0 extract)"
    fi
    
    # Estado del contenedor
    if command -v docker-compose &> /dev/null; then
        if docker-compose ps | grep -q "Up"; then
            log_success "Contenedor: Corriendo"
            
            # Verificar imágenes en contenedor
            IMAGE_COUNT_CONTAINER=$(docker-compose exec -T music-web-explorer find /app/images -type f \( -name "*.jpg" -o -name "*.png" \) 2>/dev/null | wc -l || echo "0")
            if [ "$IMAGE_COUNT_CONTAINER" -gt 0 ]; then
                log_success "Imágenes en contenedor: $IMAGE_COUNT_CONTAINER archivos"
            else
                log_warning "No hay imágenes en el contenedor"
            fi
        else
            log_warning "Contenedor: No está corriendo"
        fi
    else
        log_warning "Docker no disponible"
    fi
    
    # Directorios del host
    log_info "Directorios del host:"
    HOST_DIRS=(
        "$HOME/contenedores/mfuzz/logs"
        "$HOME/contenedores/mfuzz/images"
        "$HOME/Musica"
    )
    
    for dir in "${HOST_DIRS[@]}"; do
        if [ -d "$dir" ]; then
            echo "  ✅ $dir"
        else
            echo "  ❌ $dir (no existe)"
        fi
    done
}

# Función para limpiar
clean() {
    log_info "Limpiando archivos temporales..."
    
    # Limpiar imágenes extraídas
    if [ -d "container_images" ]; then
        rm -rf container_images
        log_success "Eliminado: container_images/"
    fi
    
    if [ "$FULL_CLEAN" = "true" ]; then
        log_info "Limpieza completa: parando y eliminando contenedor..."
        
        # Parar contenedor
        docker-compose down 2>/dev/null || true
        
        # Eliminar imagen Docker
        docker rmi mfuzz_docker_web_music-web-explorer 2>/dev/null || true
        
        log_success "Contenedor y imagen Docker eliminados"
    fi
    
    log_success "Limpieza completada"
}

# Función principal
main() {
    case "${1:-}" in
        "extract")
            check_dependencies
            extract_images
            ;;
        "build")
            check_dependencies
            build_container
            ;;
        "deploy")
            check_dependencies
            deploy_container
            ;;
        "full")
            check_dependencies
            extract_images
            prepare_host_directories
            build_container
            deploy_container
            echo
            log_success "🎉 ¡Proceso completado exitosamente!"
            log_success "🌐 Tu Music Web Explorer está listo en: http://localhost:8447"
            ;;
        "status")
            show_status
            ;;
        "clean")
            clean
            ;;
        "clean-full")
            FULL_CLEAN="true"
            clean
            ;;
        *)
            echo "🎵 Music Web Explorer - Build Script"
            echo "==================================="
            echo
            echo "Uso: $0 <comando> [opciones]"
            echo
            echo "Comandos disponibles:"
            echo "  extract     - Extraer imágenes de la base de datos"
            echo "  build       - Construir contenedor Docker"
            echo "  deploy      - Desplegar contenedor"
            echo "  full        - Proceso completo (extract + build + deploy)"
            echo "  status      - Mostrar estado actual"
            echo "  clean       - Limpiar archivos temporales"
            echo "  clean-full  - Limpiar todo incluyendo contenedor"
            echo
            echo "Variables de entorno:"
            echo "  FORCE_EXTRACT=true  - Forzar nueva extracción de imágenes"
            echo
            echo "Ejemplos:"
            echo "  $0 full                    # Proceso completo"
            echo "  FORCE_EXTRACT=true $0 extract  # Forzar nueva extracción"
            echo "  $0 status                  # Ver estado actual"
            echo
            exit 1
            ;;
    esac
}

# Ejecutar función principal con todos los argumentos
main "$@"