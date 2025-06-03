// Variables globales
let systemOverview = null;
let currentArtistId = null;
let currentAlbumId = null;
let artistsList = [];
let currentView = 'main'; // 'main', 'artist-detail', 'album-detail'

// Inicializar aplicación
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Iniciando Music Web Explorer');
    
    if (window.location.pathname.includes('sistema.html')) {
        loadSystemOverview();
        showStatsCategory('artists');
        setupGlobalEvents();
    } else if (window.location.pathname.includes('album_analysis.html')) {
        setupAlbumAnalysis();
    }
});

// Gestión de pestañas principales
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
    currentView = 'artist-detail';
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
    currentView = 'album-detail';
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
    currentView = 'main';
    currentArtistId = null;
    currentAlbumId = null;
    showStatsCategory('artists');
}


// Funciones de utilidad
function getCompletenessClass(percentage) {
    if (percentage >= 80) return 'completeness-excellent';
    if (percentage >= 60) return 'completeness-good';
    return 'completeness-poor';
}

function showError(message) {
    console.error('❌ Error:', message);
    const overviewContainer = document.getElementById('system-overview');
    if (overviewContainer) {
        overviewContainer.innerHTML = `<div class="error-message">${message}</div>`;
    }
    
    // También mostrar en el contenido principal si existe
    const statsContent = document.getElementById('stats-content');
    if (statsContent) {
        statsContent.innerHTML = `<div class="error-message">${message}</div>`;
    }
}

function setupGlobalEvents() {
    document.addEventListener('click', (e) => {
        const artistDropdown = document.getElementById('artistDropdown');
        const albumDropdown = document.getElementById('albumDropdown');
        
        if (artistDropdown && !e.target.closest('#artistSearchInput') && !e.target.closest('#artistDropdown')) {
            artistDropdown.style.display = 'none';
        }
        
        if (albumDropdown && !e.target.closest('#albumSearchInput') && !e.target.closest('#albumDropdown')) {
            albumDropdown.style.display = 'none';
        }
    });
    
    console.log('🔧 Eventos globales configurados');
}







// Variables para compatibilidad con otros scripts
window.systemOverview = systemOverview;
window.currentArtistId = currentArtistId;
window.currentAlbumId = currentAlbumId;
window.artistsList = artistsList;
window.currentView = currentView;

