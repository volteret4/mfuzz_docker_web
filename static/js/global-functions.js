// === FUNCIONES GLOBALES COMPARTIDAS ===

// Variables globales disponibles en todos los scripts
window.systemOverview = window.systemOverview || null;
window.currentArtistId = window.currentArtistId || null;
window.currentAlbumId = window.currentAlbumId || null;
window.artistsList = window.artistsList || [];
window.currentView = window.currentView || 'main';
window.navigationHistory = window.navigationHistory || [];

// === GESTIÓN DE PESTAÑAS ===

function switchToArtistDetailTabs() {
    const tabsContainer = document.getElementById('main-tabs');
    if (!tabsContainer) {
        console.error('❌ No se encontró contenedor main-tabs');
        return;
    }
    
    tabsContainer.innerHTML = `
        <button class="stats-tab back-tab" onclick="returnToMainTabs()">
            <i class="fas fa-arrow-left"></i> Atrás
        </button>
        <button class="stats-tab" onclick="showStatsCategory('detailed-analysis')">
            <i class="fas fa-chart-bar"></i> Análisis Detallado
        </button>
        <button class="stats-tab active" onclick="showArtistAnalysisTab('tiempo')">
            <i class="fas fa-clock"></i> Tiempo
        </button>
        <button class="stats-tab" onclick="showArtistAnalysisTab('conciertos')">
            <i class="fas fa-microphone"></i> Conciertos
        </button>
        <button class="stats-tab" onclick="showArtistAnalysisTab('generos')">
            <i class="fas fa-music"></i> Géneros
        </button>
        <button class="stats-tab" onclick="showArtistAnalysisTab('sellos')">
            <i class="fas fa-record-vinyl"></i> Sellos
        </button>
        <button class="stats-tab" onclick="showArtistAnalysisTab('discografia')">
            <i class="fas fa-compact-disc"></i> Discografía
        </button>
        <button class="stats-tab" onclick="showArtistAnalysisTab('escuchas')">
            <i class="fas fa-headphones"></i> Escuchas
        </button>
        <button class="stats-tab" onclick="showArtistAnalysisTab('colaboradores')">
            <i class="fas fa-users"></i> Colaboradores
        </button>
        <button class="stats-tab" onclick="showArtistAnalysisTab('feeds')">
            <i class="fas fa-rss"></i> Feeds
        </button>
    `;
    window.currentView = 'artist-detail';
}

function switchToAlbumDetailTabsInSistema() {
    const tabsContainer = document.getElementById('main-tabs');
    if (!tabsContainer) {
        console.error('❌ No se encontró contenedor main-tabs');
        return;
    }
    
    tabsContainer.innerHTML = `
        <button class="stats-tab back-tab" onclick="returnToMainTabs()">
            <i class="fas fa-arrow-left"></i> Atrás
        </button>
        <button class="stats-tab" onclick="showStatsCategory('detailed-analysis')">
            <i class="fas fa-chart-bar"></i> Análisis Detallado
        </button>
        <button class="stats-tab active" onclick="showAlbumAnalysisTab('tiempo')">
            <i class="fas fa-clock"></i> Tiempo
        </button>
        <button class="stats-tab" onclick="showAlbumAnalysisTab('genero')">
            <i class="fas fa-music"></i> Género
        </button>
        <button class="stats-tab" onclick="showAlbumAnalysisTab('conciertos')">
            <i class="fas fa-microphone"></i> Conciertos
        </button>
        <button class="stats-tab" onclick="showAlbumAnalysisTab('sellos')">
            <i class="fas fa-record-vinyl"></i> Sellos
        </button>
        <button class="stats-tab" onclick="showAlbumAnalysisTab('discografia')">
            <i class="fas fa-compact-disc"></i> Discografía
        </button>
        <button class="stats-tab" onclick="showAlbumAnalysisTab('escuchas')">
            <i class="fas fa-headphones"></i> Escuchas
        </button>
        <button class="stats-tab" onclick="showAlbumAnalysisTab('colaboradores')">
            <i class="fas fa-users"></i> Colaboradores
        </button>
        <button class="stats-tab" onclick="showAlbumAnalysisTab('feeds')">
            <i class="fas fa-rss"></i> Feeds
        </button>
        <button class="stats-tab" onclick="showAlbumAnalysisTab('letras')">
            <i class="fas fa-quote-right"></i> Letras
        </button>
    `;
    window.currentView = 'album-detail';
}

function returnToMainTabs() {
    const tabsContainer = document.getElementById('main-tabs');
    if (!tabsContainer) {
        console.error('❌ No se encontró contenedor main-tabs');
        return;
    }
    
    tabsContainer.innerHTML = `
        <button class="stats-tab active" onclick="showStatsCategory('artists')">
            <i class="fas fa-user-friends"></i> Artistas
        </button>
        <button class="stats-tab" onclick="showStatsCategory('albums')">
            <i class="fas fa-compact-disc"></i> Álbumes
        </button>
        <button class="stats-tab" onclick="showStatsCategory('songs')">
            <i class="fas fa-music"></i> Canciones
        </button>
        <button class="stats-tab" onclick="showStatsCategory('database')">
            <i class="fas fa-database"></i> Base de Datos
        </button>
        <button class="stats-tab" onclick="showStatsCategory('missing')">
            <i class="fas fa-exclamation-triangle"></i> Datos Faltantes
        </button>
        <button class="stats-tab" onclick="showStatsCategory('detailed-analysis')">
            <i class="fas fa-chart-bar"></i> Análisis Detallado
        </button>
    `;
    window.currentView = 'main';
    window.currentArtistId = null;
    window.currentAlbumId = null;
    
    // Volver a la vista principal
    if (typeof showStatsCategory === 'function') {
        showStatsCategory('artists');
    }
}

// === FUNCIONES DE UTILIDAD ===

function getCompletenessClass(percentage) {
    if (percentage >= 80) return 'completeness-excellent';
    if (percentage >= 60) return 'completeness-good';
    return 'completeness-poor';
}

function showError(message) {
    console.error('❌ Error:', message);
    
    // Buscar posibles contenedores donde mostrar el error
    const containers = [
        'system-overview',
        'stats-content', 
        'content',
        'analysis-content',
        'albumAnalysisContent',
        'artistAnalysisContent'
    ];
    
    for (const containerId of containers) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `<div class="error-message">${message}</div>`;
            break;
        }
    }
}

function setupGlobalEvents() {
    // Prevenir múltiples registros del mismo evento
    if (window.globalEventsSetup) {
        return;
    }
    
    document.addEventListener('click', (e) => {
        // Cerrar dropdowns al hacer click fuera
        const artistDropdown = document.getElementById('artistDropdown');
        const albumDropdown = document.getElementById('albumDropdown');
        
        if (artistDropdown && !e.target.closest('#artistSearchInput') && !e.target.closest('#artistDropdown')) {
            artistDropdown.style.display = 'none';
        }
        
        if (albumDropdown && !e.target.closest('#albumSearchInput') && !e.target.closest('#albumDropdown')) {
            albumDropdown.style.display = 'none';
        }
    });
    
    // Marcar como configurado
    window.globalEventsSetup = true;
    console.log('🔧 Eventos globales configurados');
}

// === FUNCIONES DE FORMATO ===

function formatDuration(seconds) {
    if (!seconds || seconds === 0) return '';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function getStatusText(status) {
    const statusTexts = {
        'starting': 'Iniciando descarga...',
        'processing': 'Procesando archivos...',
        'completed': 'Completado',
        'error': 'Error',
        'ssh_preparing': 'Preparando transferencia SSH...',
        'ssh_transferring': 'Transfiriendo archivos con rsync...',
        'ssh_compressing': 'Comprimiendo en servidor remoto...',
        'ssh_cleaning': 'Limpiando archivos temporales...',
        'ssh_ready_download': 'Listo para descarga'
    };
    return statusTexts[status] || status;
}

// === FUNCIONES DE UI ===

function showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed; top: 20px; right: 20px; z-index: 1050;
        padding: 15px 20px; border-radius: 10px; color: white;
        font-weight: bold; max-width: 300px; word-wrap: break-word;
        transform: translateX(100%); transition: transform 0.3s ease;
    `;
    
    const colors = {
        'success': 'rgba(40, 167, 69, 0.9)',
        'error': 'rgba(220, 53, 69, 0.9)',
        'warning': 'rgba(255, 193, 7, 0.9)',
        'info': 'rgba(23, 162, 184, 0.9)'
    };
    
    toast.style.background = colors[type] || colors['info'];
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    // Animar entrada
    setTimeout(() => {
        toast.style.transform = 'translateX(0)';
    }, 100);
    
    // Remover después del tiempo especificado
    setTimeout(() => {
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, duration);
}

function showLoading(message = 'Cargando...', containerId = null) {
    const loadingHtml = `
        <div class="loading">
            <i class="fas fa-spinner"></i>
            <p>${message}</p>
        </div>
    `;
    
    if (containerId) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = loadingHtml;
        }
    } else {
        // Buscar contenedor automáticamente
        const containers = ['stats-content', 'content', 'analysis-content'];
        for (const id of containers) {
            const container = document.getElementById(id);
            if (container) {
                container.innerHTML = loadingHtml;
                break;
            }
        }
    }
}

// === FUNCIONES DE NAVEGACIÓN MEJORADAS ===

function pushHistory(item) {
    try {
        // Agregar al historial personalizado
        if (!window.navigationHistory) {
            window.navigationHistory = [];
        }
        
        // Evitar duplicados consecutivos
        const lastItem = window.navigationHistory[window.navigationHistory.length - 1];
        if (!lastItem || JSON.stringify(lastItem) !== JSON.stringify(item)) {
            window.navigationHistory.push(item);
            console.log('📝 Historia agregada:', item);
        }
        
        // Usar historial del navegador si está disponible
        if (window.history && window.history.pushState) {
            window.history.pushState(item, '', window.location.href);
        }
    } catch (error) {
        console.warn('⚠️ Error agregando al historial:', error);
    }
}

function goBack() {
    try {
        // Intentar usar historial personalizado primero
        if (window.navigationHistory && window.navigationHistory.length > 0) {
            const previousItem = window.navigationHistory.pop();
            console.log('🔙 Navegando atrás a:', previousItem);
            
            // Navegar según el tipo
            if (previousItem && previousItem.type) {
                if (previousItem.type === 'artist' && typeof window.app?.showArtist === 'function') {
                    window.app.showArtist(previousItem.id);
                    return;
                } else if (previousItem.type === 'album' && typeof window.app?.showAlbum === 'function') {
                    window.app.showAlbum(previousItem.id);
                    return;
                }
            }
        }
        
        // Fallback: usar historial del navegador
        if (window.history && window.history.length > 1) {
            window.history.back();
        } else {
            // Último fallback: volver a la vista principal
            if (window.currentView !== 'main') {
                returnToMainTabs();
            }
        }
    } catch (error) {
        console.warn('⚠️ Error navegando atrás:', error);
        // Fallback final
        if (window.currentView !== 'main') {
            returnToMainTabs();
        }
    }
}

// === FUNCIONES DE VALIDACIÓN ===

function safeExecute(functionName, ...args) {
    if (typeof window[functionName] === 'function') {
        try {
            return window[functionName](...args);
        } catch (error) {
            console.error(`Error ejecutando ${functionName}:`, error);
            return null;
        }
    } else {
        console.warn(`Función ${functionName} no está definida`);
        return null;
    }
}

// === FUNCIONES DE COMPATIBILIDAD PARA CLASES ===

// Crear wrapper functions para compatibilidad con métodos de clase
function createClassWrapper(instance, methodName) {
    return function(...args) {
        if (instance && typeof instance[methodName] === 'function') {
            return instance[methodName](...args);
        } else {
            // Fallback a función global si existe
            const globalFunction = window[methodName];
            if (typeof globalFunction === 'function') {
                return globalFunction(...args);
            } else {
                console.warn(`Método ${methodName} no disponible`);
                return null;
            }
        }
    };
}

// Hacer funciones disponibles globalmente
window.switchToArtistDetailTabs = switchToArtistDetailTabs;
window.switchToAlbumDetailTabsInSistema = switchToAlbumDetailTabsInSistema;
window.returnToMainTabs = returnToMainTabs;
window.getCompletenessClass = getCompletenessClass;
window.showError = showError;
window.setupGlobalEvents = setupGlobalEvents;
window.formatDuration = formatDuration;
window.formatBytes = formatBytes;
window.getStatusText = getStatusText;
window.showToast = showToast;
window.showLoading = showLoading;
window.goBack = goBack;
window.pushHistory = pushHistory;
window.safeExecute = safeExecute;
window.createClassWrapper = createClassWrapper;

// Configurar eventos al cargar
document.addEventListener('DOMContentLoaded', function() {
    setupGlobalEvents();
});