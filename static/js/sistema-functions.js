// === FUNCIONES DEL SISTEMA MOVIDAS DE sistema.html ===

// Variables globales del sistema
let systemOverview = null;
let currentArtistId = null;
let currentAlbumId = null;
let artistsList = [];
let currentView = 'main'; // 'main', 'artist-detail', 'album-detail', 'scrobbles-detail'

// === CARGA DE DATOS DEL SISTEMA ===

async function loadSystemOverview() {
    try {
        console.log('🔄 Cargando resumen del sistema...');
        const response = await fetch('/api/stats/overview');
        const data = await response.json();
        
        if (data.error) {
            showError('Error cargando resumen del sistema: ' + data.error);
            return;
        }
        
        systemOverview = data;
        renderSystemOverview(data);
        console.log('✅ Resumen del sistema cargado');
        
    } catch (error) {
        console.error('Error cargando estadísticas:', error);
        showError('Error cargando estadísticas del sistema');
    }
}

function renderSystemOverview(overview) {
    const overviewContainer = document.getElementById('system-overview');
    if (!overviewContainer) {
        console.warn('⚠️ Contenedor system-overview no encontrado');
        return;
    }
    
    overviewContainer.innerHTML = `
        <div class="system-card">
            <h3>Base de Datos</h3>
            <div class="value">${overview.database?.size_mb || 0} MB</div>
            <div class="label">${overview.database?.total_tables || 0} tablas</div>
        </div>
        
        <div class="system-card">
            <h3>Artistas</h3>
            <div class="value">${(overview.content?.total_artists || 0).toLocaleString()}</div>
            <div class="label">en la colección</div>
        </div>
        
        <div class="system-card">
            <h3>Álbumes</h3>
            <div class="value">${(overview.content?.total_albums || 0).toLocaleString()}</div>
            <div class="label">en la colección</div>
        </div>
        
        <div class="system-card">
            <h3>Canciones</h3>
            <div class="value">${(overview.content?.total_songs || 0).toLocaleString()}</div>
            <div class="label">${overview.content?.total_duration_hours || 0}h de música</div>
        </div>
        
        <div class="system-card">
            <h3>Completitud</h3>
            <div class="value">${overview.completeness || 0}%</div>
            <div class="label">datos completos</div>
            <div class="completeness-bar">
                <div class="completeness-fill ${getCompletenessClass(overview.completeness || 0)}" 
                    style="width: ${overview.completeness || 0}%">
                    ${overview.completeness || 0}%
                </div>
            </div>
        </div>
    `;
}

// === CATEGORÍAS DE ESTADÍSTICAS ===

async function showStatsCategory(category) {
    console.log(`📊 Mostrando categoría: ${category}`);
    
    // Actualizar pestañas activas solo si estamos en vista principal
    if (window.currentView === 'main') {
        document.querySelectorAll('.stats-tab').forEach(tab => tab.classList.remove('active'));
        // Buscar la pestaña que corresponde a esta categoría
        document.querySelectorAll('.stats-tab').forEach(tab => {
            const onclick = tab.getAttribute('onclick') || '';
            if (onclick.includes(`'${category}'`)) {
                tab.classList.add('active');
            }
        });
    }
    
    const statsContent = document.getElementById('stats-content');
    if (!statsContent) {
        console.error('❌ Contenedor stats-content no encontrado');
        return;
    }
    
    // NUEVO: Manejar "análisis detallado" como submenú
    if (category === 'detailed-analysis') {
        showDetailedAnalysisMenu();
        return;
    }
    
    // MODIFICADO: Manejar análisis de álbumes como tab interno
    if (category === 'album-analysis') {
        await showAlbumAnalysis(statsContent);
        return;
    }
    
    // NUEVO: Manejar análisis de artistas
    if (category === 'artist-analysis') {
        await showArtistAnalysis(statsContent);
        return;
    }
    
    // NUEVO: Manejar análisis de scrobbles
    if (category === 'scrobbles-analysis') {
        // Verificar si la función existe antes de llamarla
        if (typeof showScrobblesAnalysis === 'function') {
            await showScrobblesAnalysis(statsContent);
        } else {
            console.error('❌ showScrobblesAnalysis no está disponible');
            statsContent.innerHTML = `
                <div class="error-message">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Módulo de análisis de scrobbles no disponible</p>
                </div>
            `;
        }
        return;
    }
    
    statsContent.innerHTML = '<div class="loading"><i class="fas fa-spinner"></i><p>Cargando estadísticas...</p></div>';
    
    try {
        if (category === 'database') {
            await showDatabaseStats(statsContent);
        } else if (category === 'missing') {
            await showMissingDataStats(statsContent);
        } else {
            await showCategoryStats(category, statsContent);
        }
    } catch (error) {
        console.error(`Error cargando estadísticas de ${category}:`, error);
        statsContent.innerHTML = `<div class="error-message">Error cargando estadísticas de ${category}</div>`;
    }
}

function showDetailedAnalysisMenu() {
    const statsContent = document.getElementById('stats-content');
    
    const content = `
        <div class="stats-section">
            <h2>Análisis Detallado</h2>
            <p style="margin-bottom: 30px; color: #ccc;">Selecciona el tipo de análisis que deseas realizar:</p>
            
            <div class="system-overview" style="grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 25px;">
                <div class="system-card" style="cursor: pointer; transition: all 0.3s ease;" 
                    onclick="showStatsCategory('artist-analysis')" 
                    onmouseover="this.style.transform='translateY(-8px) scale(1.02)'" 
                    onmouseout="this.style.transform='translateY(0) scale(1)'">
                    <h3><i class="fas fa-user-friends"></i> Análisis de Artistas</h3>
                    <div class="value" style="font-size: 1.2rem; color: #a8e6cf;">
                        <i class="fas fa-chart-line" style="font-size: 2.5rem; margin: 15px 0;"></i>
                    </div>
                    <div class="label">
                        Análisis detallado por artista con gráficos de tiempo, géneros, 
                        conciertos, sellos, discografía, escuchas y colaboradores
                    </div>
                </div>
                
                <div class="system-card" style="cursor: pointer; transition: all 0.3s ease;" 
                    onclick="showStatsCategory('album-analysis')" 
                    onmouseover="this.style.transform='translateY(-8px) scale(1.02)'" 
                    onmouseout="this.style.transform='translateY(0) scale(1)'">
                    <h3><i class="fas fa-compact-disc"></i> Análisis de Álbumes</h3>
                    <div class="value" style="font-size: 1.2rem; color: #a8e6cf;">
                        <i class="fas fa-chart-pie" style="font-size: 2.5rem; margin: 15px 0;"></i>
                    </div>
                    <div class="label">
                        Análisis detallado por álbum con datos de tiempo, género, 
                        conciertos, sellos, colaboradores, feeds y letras
                    </div>
                </div>
                
                <!-- NUEVA OPCIÓN DE SCROBBLES -->
                <div class="system-card" style="cursor: pointer; transition: all 0.3s ease;" 
                    onclick="showStatsCategory('scrobbles-analysis')" 
                    onmouseover="this.style.transform='translateY(-8px) scale(1.02)'" 
                    onmouseout="this.style.transform='translateY(0) scale(1)'">
                    <h3><i class="fas fa-headphones"></i> Análisis de Escuchas</h3>
                    <div class="value" style="font-size: 1.2rem; color: #a8e6cf;">
                        <i class="fas fa-chart-area" style="font-size: 2.5rem; margin: 15px 0;"></i>
                    </div>
                    <div class="label">
                        Análisis completo de patrones de escucha, géneros, calidad, 
                        descubrimiento musical y evolución temporal de gustos
                    </div>
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 40px; padding: 20px; 
                        background: rgba(255,255,255,0.05); border-radius: 15px;">
                <p style="color: #a8e6cf; margin-bottom: 10px;">
                    <i class="fas fa-info-circle"></i> Próximamente
                </p>
                <p style="color: #ccc; font-size: 0.9rem;">
                    • Análisis de géneros globales<br>
                    • Análisis de sellos discográficos<br>
                    • Análisis de tendencias temporales<br>
                    • Comparativas y correlaciones
                </p>
            </div>
        </div>
    `;
    
    statsContent.innerHTML = content;
}

// === RENDERIZADO DE ESTADÍSTICAS ===

async function showCategoryStats(category, container) {
    try {
        const response = await fetch(`/api/stats/${category}`);
        const data = await response.json();
        
        if (data.error) {
            container.innerHTML = `<div class="error-message">${data.error}</div>`;
            return;
        }
        
        let content = '';
        
        if (category === 'artists') {
            content = renderArtistsStats(data);
        } else if (category === 'albums') {
            content = renderAlbumsStats(data);
        } else if (category === 'songs') {
            content = renderSongsStats(data);
        }
        
        container.innerHTML = content;
        
        // Cargar gráficos específicos
        await loadCategoryCharts(category);
    } catch (error) {
        console.error(`Error cargando estadísticas de ${category}:`, error);
        container.innerHTML = `<div class="error-message">Error cargando estadísticas</div>`;
    }
}

function renderArtistsStats(data) {
    return `
        <div class="stats-section">
            <h2>Estadísticas de Artistas</h2>
            
            <div class="chart-container">
                <h3>Artistas por País</h3>
                <div id="chart-artists-countries" style="height: 400px;"></div>
            </div>
            
            <div class="chart-container">
                <h3>Top Artistas por Álbumes</h3>
                <div id="chart-artists-top" style="height: 400px;"></div>
            </div>
            
            <div class="data-table">
                <h3>Países con más artistas</h3>
                <table>
                    <thead>
                        <tr>
                            <th>País</th>
                            <th>Artistas</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.by_country.slice(0, 10).map(item => 
                            `<tr><td>${item.origin}</td><td>${item.count.toLocaleString()}</td></tr>`
                        ).join('')}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

function renderAlbumsStats(data) {
    return `
        <div class="stats-section">
            <h2>Estadísticas de Álbumes</h2>
            
            <div class="chart-container">
                <h3>Álbumes por Década</h3>
                <div id="chart-albums-decades" style="height: 400px;"></div>
            </div>
            
            <div class="chart-container">
                <h3>Álbumes por Género</h3>
                <div id="chart-albums-genres" style="height: 400px;"></div>
            </div>
            
            <div class="chart-container">
                <h3>Top Sellos Discográficos</h3>
                <div id="chart-albums-labels" style="height: 400px;"></div>
            </div>
        </div>
    `;
}

function renderSongsStats(data) {
    const lyricsPercentage = Math.round((data.lyrics_stats?.with_lyrics / data.lyrics_stats?.total) * 100 || 0);
    
    return `
        <div class="stats-section">
            <h2>Estadísticas de Canciones</h2>
            
            <div class="chart-container">
                <h3>Canciones por Género</h3>
                <div id="chart-songs-genres" style="height: 400px;"></div>
            </div>
            
            <div class="system-overview">
                <div class="system-card">
                    <h3>Duración Total</h3>
                    <div class="value">${Math.round((data.duration_stats?.total_duration || 0) / 3600)} h</div>
                    <div class="label">de música</div>
                </div>
                
                <div class="system-card">
                    <h3>Duración Promedio</h3>
                    <div class="value">${Math.round(data.duration_stats?.avg_duration || 0)} s</div>
                    <div class="label">por canción</div>
                </div>
                
                <div class="system-card">
                    <h3>Con Letras</h3>
                    <div class="value">${(data.lyrics_stats?.with_lyrics || 0).toLocaleString()}</div>
                    <div class="label">de ${(data.lyrics_stats?.total || 0).toLocaleString()} canciones</div>
                    <div class="completeness-bar">
                        <div class="completeness-fill ${getCompletenessClass(lyricsPercentage)}" 
                            style="width: ${lyricsPercentage}%">
                            ${lyricsPercentage}%
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

async function showDatabaseStats(container) {
    try {
        const response = await fetch('/api/stats/database');
        const data = await response.json();
        
        if (data.error) {
            container.innerHTML = `<div class="error-message">${data.error}</div>`;
            return;
        }
        
        let tablesHtml = '';
        for (const [tableName, tableInfo] of Object.entries(data.tables || {})) {
            tablesHtml += `
                <tr>
                    <td>${tableName}</td>
                    <td>${tableInfo.count.toLocaleString()}</td>
                    <td>${tableInfo.columns}</td>
                </tr>
            `;
        }
        
        container.innerHTML = `
            <div class="stats-section">
                <h2>Información de la Base de Datos</h2>
                
                <div class="system-overview">
                    <div class="system-card">
                        <h3>Tamaño Total</h3>
                        <div class="value">${Math.round(data.database_size / (1024 * 1024))} MB</div>
                        <div class="label">en disco</div>
                    </div>
                    
                    <div class="system-card">
                        <h3>Total Tablas</h3>
                        <div class="value">${data.total_tables}</div>
                        <div class="label">en la base de datos</div>
                    </div>
                    
                    <div class="system-card">
                        <h3>Última Actualización</h3>
                        <div class="value" style="font-size: 1rem;">${new Date(data.last_updated).toLocaleDateString()}</div>
                        <div class="label">${new Date(data.last_updated).toLocaleTimeString()}</div>
                    </div>
                </div>
                
                <div class="data-table">
                    <h3>Tablas de la Base de Datos</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>Tabla</th>
                                <th>Registros</th>
                                <th>Columnas</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${tablesHtml}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Error cargando estadísticas de base de datos:', error);
        container.innerHTML = `<div class="error-message">Error cargando estadísticas de base de datos</div>`;
    }
}

async function showMissingDataStats(container) {
    try {
        const response = await fetch('/api/stats/missing-data');
        const data = await response.json();
        
        if (data.error) {
            container.innerHTML = `<div class="error-message">${data.error}</div>`;
            return;
        }
        
        let tablesHtml = '';
        for (const [tableName, tableStats] of Object.entries(data)) {
            for (const [fieldName, fieldStats] of Object.entries(tableStats.fields || {})) {
                const completenessClass = getCompletenessClass(fieldStats.completeness);
                tablesHtml += `
                    <tr>
                        <td>${tableName}</td>
                        <td>${fieldName}</td>
                        <td>${fieldStats.filled.toLocaleString()}</td>
                        <td>${fieldStats.missing.toLocaleString()}</td>
                        <td>
                            <div class="completeness-bar">
                                <div class="completeness-fill ${completenessClass}" 
                                    style="width: ${fieldStats.completeness}%">
                                    ${fieldStats.completeness}%
                                </div>
                            </div>
                        </td>
                    </tr>
                `;
            }
        }
        
        container.innerHTML = `
            <div class="stats-section">
                <h2>Análisis de Datos Faltantes</h2>
                
                <div class="data-table">
                    <table>
                        <thead>
                            <tr>
                                <th>Tabla</th>
                                <th>Campo</th>
                                <th>Completos</th>
                                <th>Faltantes</th>
                                <th>Completitud</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${tablesHtml}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Error cargando análisis de datos faltantes:', error);
        container.innerHTML = `<div class="error-message">Error cargando análisis de datos faltantes</div>`;
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

// === INICIALIZACIÓN ===

// Función de inicialización que se llama desde sistema.html
function initializeSistema() {
    console.log('🚀 Iniciando Sistema - Music Web Explorer');
    loadSystemOverview();
    showStatsCategory('artists');
}

// Hacer funciones disponibles globalmente
window.loadSystemOverview = loadSystemOverview;
window.showStatsCategory = showStatsCategory;
window.showDetailedAnalysisMenu = showDetailedAnalysisMenu;
window.initializeSistema = initializeSistema;
window.systemOverview = systemOverview;
window.currentArtistId = currentArtistId;
window.currentAlbumId = currentAlbumId;
window.artistsList = artistsList;
window.currentView = currentView;