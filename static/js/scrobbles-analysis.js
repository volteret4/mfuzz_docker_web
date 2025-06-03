// === ANÁLISIS DE ESCUCHAS/SCROBBLES ===

// Variables globales para escuchas
let currentScrobblesView = 'main';

// === CONFIGURACIÓN INICIAL ===

function setupScrobblesAnalysis() {
    currentScrobblesView = 'main';
    showScrobblesMainSection();
}

// === NAVEGACIÓN DE ESCUCHAS ===

function showScrobblesMainSection() {
    console.log('Mostrando sección principal de scrobbles');
    
    const content = `
        <div class="stats-section">
            <h2>Análisis de Escuchas</h2>
            <p style="margin-bottom: 30px; color: #ccc;">Explora patrones en tus hábitos de escucha y descubre insights sobre tu música.</p>
            
            <div class="system-overview" style="grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 25px;">
                <div class="system-card" style="cursor: pointer; transition: all 0.3s ease;" 
                    onclick="showScrobblesAnalysisTab('tiempo')" 
                    onmouseover="this.style.transform='translateY(-8px) scale(1.02)'" 
                    onmouseout="this.style.transform='translateY(0) scale(1)'">
                    <h3><i class="fas fa-clock"></i> Análisis Temporal</h3>
                    <div class="value" style="font-size: 1.2rem; color: #a8e6cf;">
                        <i class="fas fa-chart-line" style="font-size: 2.5rem; margin: 15px 0;"></i>
                    </div>
                    <div class="label">
                        Patrones temporales de escucha, evolución anual, 
                        tendencias mensuales y hábitos por día de la semana
                    </div>
                </div>
                
                <div class="system-card" style="cursor: pointer; transition: all 0.3s ease;" 
                    onclick="showScrobblesAnalysisTab('generos')" 
                    onmouseover="this.style.transform='translateY(-8px) scale(1.02)'" 
                    onmouseout="this.style.transform='translateY(0) scale(1)'">
                    <h3><i class="fas fa-music"></i> Géneros Musicales</h3>
                    <div class="value" style="font-size: 1.2rem; color: #a8e6cf;">
                        <i class="fas fa-chart-pie" style="font-size: 2.5rem; margin: 15px 0;"></i>
                    </div>
                    <div class="label">
                        Distribución de géneros escuchados, evolución temporal
                        y detección de géneros emergentes en tus gustos
                    </div>
                </div>
                
                <div class="system-card" style="cursor: pointer; transition: all 0.3s ease;" 
                    onclick="showScrobblesAnalysisTab('calidad')" 
                    onmouseover="this.style.transform='translateY(-8px) scale(1.02)'" 
                    onmouseout="this.style.transform='translateY(0) scale(1)'">
                    <h3><i class="fas fa-volume-up"></i> Calidad de Audio</h3>
                    <div class="value" style="font-size: 1.2rem; color: #a8e6cf;">
                        <i class="fas fa-equalizer" style="font-size: 2.5rem; margin: 15px 0;"></i>
                    </div>
                    <div class="label">
                        Análisis de bitrate, sample rate y formatos de audio
                        más reproducidos en tu biblioteca
                    </div>
                </div>
                
                <div class="system-card" style="cursor: pointer; transition: all 0.3s ease;" 
                    onclick="showScrobblesAnalysisTab('descubrimiento')" 
                    onmouseover="this.style.transform='translateY(-8px) scale(1.02)'" 
                    onmouseout="this.style.transform='translateY(0) scale(1)'">
                    <h3><i class="fas fa-search"></i> Descubrimiento Musical</h3>
                    <div class="value" style="font-size: 1.2rem; color: #a8e6cf;">
                        <i class="fas fa-lightbulb" style="font-size: 2.5rem; margin: 15px 0;"></i>
                    </div>
                    <div class="label">
                        Tiempo de descubrimiento de nuevas canciones,
                        redescubrimientos y patrones de exploración
                    </div>
                </div>
                
                <div class="system-card" style="cursor: pointer; transition: all 0.3s ease;" 
                    onclick="showScrobblesAnalysisTab('evolucion')" 
                    onmouseover="this.style.transform='translateY(-8px) scale(1.02)'" 
                    onmouseout="this.style.transform='translateY(0) scale(1)'">
                    <h3><i class="fas fa-trending-up"></i> Evolución de Artistas</h3>
                    <div class="value" style="font-size: 1.2rem; color: #a8e6cf;">
                        <i class="fas fa-chart-area" style="font-size: 2.5rem; margin: 15px 0;"></i>
                    </div>
                    <div class="label">
                        Artistas más escuchados, evolución temporal de preferencias
                        y detección de artistas en ascenso
                    </div>
                </div>
                
                <div class="system-card" style="cursor: pointer; transition: all 0.3s ease;" 
                    onclick="showScrobblesAnalysisTab('sellos')" 
                    onmouseover="this.style.transform='translateY(-8px) scale(1.02)'" 
                    onmouseout="this.style.transform='translateY(0) scale(1)'">
                    <h3><i class="fas fa-record-vinyl"></i> Sellos Discográficos</h3>
                    <div class="value" style="font-size: 1.2rem; color: #a8e6cf;">
                        <i class="fas fa-industry" style="font-size: 2.5rem; margin: 15px 0;"></i>
                    </div>
                    <div class="label">
                        Análisis de sellos más escuchados y su evolución
                        en tus preferencias musicales
                    </div>
                </div>
                
                <div class="system-card" style="cursor: pointer; transition: all 0.3s ease;" 
                    onclick="showScrobblesAnalysisTab('colaboradores')" 
                    onmouseover="this.style.transform='translateY(-8px) scale(1.02)'" 
                    onmouseout="this.style.transform='translateY(0) scale(1)'">
                    <h3><i class="fas fa-users"></i> Colaboradores</h3>
                    <div class="value" style="font-size: 1.2rem; color: #a8e6cf;">
                        <i class="fas fa-handshake" style="font-size: 2.5rem; margin: 15px 0;"></i>
                    </div>
                    <div class="label">
                        Productores e ingenieros más presentes en tu música
                        y análisis de diversidad colaborativa
                    </div>
                </div>
                
                <div class="system-card" style="cursor: pointer; transition: all 0.3s ease;" 
                    onclick="showScrobblesAnalysisTab('duracion')" 
                    onmouseover="this.style.transform='translateY(-8px) scale(1.02)'" 
                    onmouseout="this.style.transform='translateY(0) scale(1)'">
                    <h3><i class="fas fa-stopwatch"></i> Duración y Formato</h3>
                    <div class="value" style="font-size: 1.2rem; color: #a8e6cf;">
                        <i class="fas fa-hourglass-half" style="font-size: 2.5rem; margin: 15px 0;"></i>
                    </div>
                    <div class="label">
                        Preferencias por duración de canciones, álbumes
                        y evolución temporal de estos gustos
                    </div>
                </div>
                
                <div class="system-card" style="cursor: pointer; transition: all 0.3s ease;" 
                    onclick="showScrobblesAnalysisTab('idiomas')" 
                    onmouseover="this.style.transform='translateY(-8px) scale(1.02)'" 
                    onmouseout="this.style.transform='translateY(0) scale(1)'">
                    <h3><i class="fas fa-quote-right"></i> Letras e Idiomas</h3>
                    <div class="value" style="font-size: 1.2rem; color: #a8e6cf;">
                        <i class="fas fa-language" style="font-size: 2.5rem; margin: 15px 0;"></i>
                    </div>
                    <div class="label">
                        Análisis de letras, palabras frecuentes y preferencias
                        por canciones con o sin letra
                    </div>
                </div>
            </div>
        </div>
    `;
    
    const statsContent = document.getElementById('stats-content');
    if (statsContent) {
        statsContent.innerHTML = content;
    }
}

// Cambiar a pestañas de análisis de scrobbles
function switchToScrobblesDetailTabs() {
    const tabsContainer = document.getElementById('main-tabs');
    if (!tabsContainer) {
        console.error('❌ No se encontró contenedor main-tabs');
        return;
    }
    
    tabsContainer.innerHTML = `
        <button class="stats-tab back-tab" onclick="returnToMainTabsFromScrobbles()">
            <i class="fas fa-arrow-left"></i> Atrás
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
    currentScrobblesView = 'main';
    window.currentView = 'main';
    
    // Volver a mostrar análisis detallado
    showStatsCategory('detailed-analysis');
}

// === ANÁLISIS DE ESCUCHAS ===

async function showScrobblesAnalysis(container) {
    container.innerHTML = `
        <div class="stats-section">
            <h2>Análisis de Escuchas</h2>
            
            <div style="text-align: center; padding: 40px; color: #a8e6cf;">
                <i class="fas fa-headphones" style="font-size: 3rem; margin-bottom: 20px; display: block;"></i>
                <p>Selecciona un tipo de análisis para explorar tus patrones de escucha</p>
                <p><small>Descubre insights sobre tus hábitos musicales y tendencias</small></p>
            </div>
            
            <!-- Contenido del análisis seleccionado -->
            <div id="scrobblesAnalysisContent" style="display: none;">
                <!-- Se carga dinámicamente -->
            </div>
        </div>
    `;
    
    // Mostrar el menú principal de scrobbles
    showScrobblesMainSection();
}

async function showScrobblesAnalysisTab(tabName) {
    console.log(`📊 Cargando análisis de scrobbles: ${tabName}`);
    
    // Actualizar pestañas activas en vista de scrobbles
    if (currentScrobblesView === 'scrobbles-detail') {
        document.querySelectorAll('.stats-tab:not(.back-tab)').forEach(tab => tab.classList.remove('active'));
        
        // Buscar y activar la pestaña correspondiente
        document.querySelectorAll('.stats-tab').forEach(tab => {
            const onclickStr = tab.getAttribute('onclick') || '';
            if (onclickStr.includes(`'${tabName}'`)) {
                tab.classList.add('active');
            }
        });
    }
    
    // Buscar el contenedor correcto
    let content = document.getElementById('scrobblesAnalysisContent');
    if (!content) {
        content = document.getElementById('stats-content');
    }
    
    if (!content) {
        console.error('❌ No se encontró contenedor para el análisis de scrobbles');
        return;
    }
    
    content.innerHTML = '<div class="loading"><i class="fas fa-spinner"></i><p>Cargando análisis...</p></div>';
    content.style.display = 'block';
    
    try {
        console.log(`🌐 Haciendo petición a: /api/scrobbles/analysis/${tabName}`);
        const response = await fetch(`/api/scrobbles/analysis/${tabName}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('📄 Respuesta del servidor:', data);
        
        if (data.error) {
            content.innerHTML = `
                <div class="error-message">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p><strong>Error:</strong> ${data.error}</p>
                </div>
            `;
            return;
        }
        
        // Renderizar análisis de scrobbles
        renderScrobblesAnalysisContent(tabName, data, content);
        
    } catch (error) {
        console.error(`💥 Error cargando análisis ${tabName}:`, error);
        content.innerHTML = `
            <div class="error-message">
                <i class="fas fa-exclamation-triangle"></i>
                <p><strong>Error de conexión:</strong> ${error.message}</p>
                <button class="btn" onclick="showScrobblesAnalysisTab('${tabName}')" style="margin-top: 10px; background: #2a5298; color: white; border: none; padding: 8px 15px; border-radius: 8px; cursor: pointer;">
                    <i class="fas fa-redo"></i> Reintentar
                </button>
            </div>
        `;
    }
}

// === RENDERIZADO DE ANÁLISIS DE SCROBBLES ===

function renderScrobblesAnalysisContent(tabName, data, container) {
    let html = `
        <div style="background: rgba(255,255,255,0.05); border-radius: 15px; padding: 20px; margin-bottom: 20px;">
            <h3 style="color: #a8e6cf; margin-bottom: 15px;">
                <i class="fas fa-chart-${getIconForScrobblesTab(tabName)}"></i>
                Análisis de ${getScrobblesTabTitle(tabName)}
            </h3>
    `;
    
    // Añadir estadísticas si existen
    if (data.stats && Object.keys(data.stats).length > 0) {
        html += '<div class="analysis-stats" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0;">';
        for (const [key, value] of Object.entries(data.stats)) {
            const displayKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            html += `
                <div class="analysis-stat-card" style="background: rgba(255,255,255,0.1); border-radius: 10px; padding: 15px; text-align: center;">
                    <h5 style="color: #a8e6cf; margin-bottom: 8px; font-size: 0.85rem; text-transform: uppercase;">${displayKey}</h5>
                    <p style="color: white; font-size: 1.2rem; font-weight: bold; margin: 0;">${value}</p>
                </div>
            `;
        }
        html += '</div>';
    }
    
    // Añadir mensaje si existe
    if (data.message) {
        html += `
            <div style="text-align: center; padding: 30px; background: rgba(255,255,255,0.1); border-radius: 10px; margin: 20px 0;">
                <i class="fas fa-info-circle" style="font-size: 2rem; color: #a8e6cf; margin-bottom: 15px; display: block;"></i>
                <p style="color: #a8e6cf; font-size: 1.1rem;">${data.message}</p>
            </div>
        `;
    }
    
    // Añadir gráficos si existen - CON LAYOUTS ESPECÍFICOS
    if (data.charts && Object.keys(data.charts).length > 0) {
        // Determinar layout según el tipo de análisis
        let gridStyle = 'display: grid; gap: 20px; margin-top: 20px;';
        
        if (tabName === 'tiempo') {
            // Tiempo: gráficos lineales en columna, patrones en grid
            gridStyle += 'grid-template-columns: 1fr;';
        } else if (tabName === 'generos') {
            // Géneros: gráfico circular + evolución lineal + emergentes en barra
            gridStyle += 'grid-template-columns: repeat(2, 1fr);';
        } else if (tabName === 'calidad') {
            // Calidad: tres gráficos circulares en grid 2x2 (con uno centrado abajo)
            gridStyle += 'grid-template-columns: repeat(2, 1fr);';
        } else if (tabName === 'descubrimiento') {
            // Descubrimiento: gráficos de barras en columna
            gridStyle += 'grid-template-columns: 1fr;';
        } else if (tabName === 'evolucion') {
            // Evolución: gráfico de barras + línea + barras en grid
            gridStyle += 'grid-template-columns: repeat(2, 1fr);';
        } else if (tabName === 'sellos') {
            // Sellos: circular + evolución lineal
            gridStyle += 'grid-template-columns: repeat(2, 1fr);';
        } else if (tabName === 'colaboradores') {
            // Colaboradores: tres gráficos de barras en grid
            gridStyle += 'grid-template-columns: repeat(2, 1fr);';
        } else if (tabName === 'duracion') {
            // Duración: barras + barras + línea
            gridStyle += 'grid-template-columns: repeat(2, 1fr);';
        } else if (tabName === 'idiomas') {
            // Idiomas: circular + barras + circular
            gridStyle += 'grid-template-columns: repeat(2, 1fr);';
        } else {
            // Por defecto: auto-fit
            gridStyle += 'grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));';
        }
        
        html += `<div style="${gridStyle}">`;
        
        // Renderizar gráficos en orden específico para cada tipo
        const chartOrder = getScrobblesChartOrder(tabName, Object.keys(data.charts));
        
        chartOrder.forEach(chartId => {
            if (data.charts[chartId]) {
                const chartTitle = getScrobblesChartTitle(chartId);
                const isFullWidth = shouldScrobblesChartBeFullWidth(tabName, chartId);
                
                html += `
                    <div style="background: rgba(255,255,255,0.05); border-radius: 10px; padding: 15px; ${isFullWidth ? 'grid-column: 1 / -1;' : ''}">
                        <h4 style="color: #a8e6cf; text-align: center; margin-bottom: 10px; font-size: 1rem;">${chartTitle}</h4>
                        <div id="chart-${chartId}" style="height: ${isFullWidth ? '400px' : '350px'};"></div>
                    </div>
                `;
            }
        });
        
        html += '</div>';
    } else if (!data.message) {
        html += `
            <div style="text-align: center; padding: 40px; color: #ccc;">
                <i class="fas fa-chart-bar" style="font-size: 2rem; margin-bottom: 15px; display: block; opacity: 0.5;"></i>
                <p>No hay gráficos disponibles para este análisis</p>
            </div>
        `;
    }
    
    html += '</div>';
    
    container.innerHTML = html;
    
    // Renderizar gráficos si existen
    if (data.charts && Object.keys(data.charts).length > 0) {
        console.log(`📊 Renderizando ${Object.keys(data.charts).length} gráficos de scrobbles...`);
        
        Object.keys(data.charts).forEach((chartId, index) => {
            setTimeout(() => {
                try {
                    const chartContainer = document.getElementById(`chart-${chartId}`);
                    if (chartContainer && data.charts[chartId]) {
                        console.log(`📈 Renderizando gráfico de scrobbles: ${chartId}`);
                        
                        const plotData = typeof data.charts[chartId] === 'string' ? 
                            JSON.parse(data.charts[chartId]) : data.charts[chartId];
                        
                        if (window.Plotly && plotData.data && plotData.layout) {
                            Plotly.newPlot(`chart-${chartId}`, plotData.data, plotData.layout, {
                                responsive: true,
                                displayModeBar: false
                            });
                            console.log(`✅ Gráfico de scrobbles ${chartId} renderizado correctamente`);
                        } else {
                            console.error(`❌ Datos de gráfico inválidos para ${chartId}:`, plotData);
                        }
                    }
                } catch (error) {
                    console.error(`💥 Error renderizando gráfico de scrobbles ${chartId}:`, error);
                    const container = document.getElementById(`chart-${chartId}`);
                    if (container) {
                        container.innerHTML = '<div style="text-align: center; color: #ff6b6b; padding: 20px;">Error renderizando gráfico</div>';
                    }
                }
            }, 100 * index);
        });
    }
    
    console.log(`✅ Análisis de scrobbles ${tabName} cargado correctamente`);
}

// === FUNCIONES DE UTILIDAD PARA SCROBBLES ===

function getIconForScrobblesTab(tabName) {
    const icons = {
        'tiempo': 'clock',
        'generos': 'music',
        'calidad': 'volume-up',
        'descubrimiento': 'search',
        'evolucion': 'trending-up',
        'sellos': 'record-vinyl',
        'colaboradores': 'users',
        'duracion': 'stopwatch',
        'idiomas': 'quote-right'
    };
    return icons[tabName] || 'chart-bar';
}

function getScrobblesTabTitle(tabName) {
    const titles = {
        'tiempo': 'Patrones Temporales',
        'generos': 'Géneros Musicales',
        'calidad': 'Calidad de Audio',
        'descubrimiento': 'Descubrimiento Musical',
        'evolucion': 'Evolución de Artistas',
        'sellos': 'Sellos Discográficos',
        'colaboradores': 'Colaboradores',
        'duracion': 'Duración y Formato',
        'idiomas': 'Letras e Idiomas'
    };
    return titles[tabName] || tabName.charAt(0).toUpperCase() + tabName.slice(1);
}

function getScrobblesChartTitle(chartId) {
    const titles = {
        'yearly_evolution': 'Evolución Anual',
        'monthly_trend': 'Tendencia Mensual',
        'weekday_pattern': 'Patrones por Día',
        'top_genres': 'Géneros Principales',
        'genre_evolution': 'Evolución de Géneros',
        'emerging_genres': 'Géneros Emergentes',
        'bitrate_distribution': 'Distribución por Bitrate',
        'samplerate_distribution': 'Distribución por Sample Rate',
        'format_distribution': 'Distribución por Formato',
        'discovery_distribution': 'Tiempo de Descubrimiento',
        'rediscovery_gaps': 'Redescubrimientos',
        'top_artists': 'Artistas Principales',
        'artist_evolution': 'Evolución de Artistas',
        'rising_artists': 'Artistas en Ascenso',
        'top_labels': 'Sellos Principales',
        'labels_evolution': 'Evolución de Sellos',
        'top_producers': 'Productores Destacados',
        'top_engineers': 'Ingenieros Destacados',
        'collaboration_diversity': 'Diversidad Colaborativa',
        'duration_distribution': 'Distribución por Duración',
        'album_durations': 'Duración de Álbumes',
        'duration_evolution': 'Evolución de Duración',
        'lyrics_availability': 'Disponibilidad de Letras',
        'frequent_words': 'Palabras Frecuentes',
        'lyrics_length': 'Longitud de Letras'
    };
    return titles[chartId] || chartId.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function getScrobblesChartOrder(tabName, chartIds) {
    const orders = {
        'tiempo': ['yearly_evolution', 'monthly_trend', 'weekday_pattern'],
        'generos': ['top_genres', 'genre_evolution', 'emerging_genres'],
        'calidad': ['bitrate_distribution', 'samplerate_distribution', 'format_distribution'],
        'descubrimiento': ['discovery_distribution', 'rediscovery_gaps'],
        'evolucion': ['top_artists', 'artist_evolution', 'rising_artists'],
        'sellos': ['top_labels', 'labels_evolution'],
        'colaboradores': ['top_producers', 'top_engineers', 'collaboration_diversity'],
        'duracion': ['duration_distribution', 'album_durations', 'duration_evolution'],
        'idiomas': ['lyrics_availability', 'frequent_words', 'lyrics_length']
    };
    
    const order = orders[tabName] || chartIds;
    return order.filter(id => chartIds.includes(id));
}

function shouldScrobblesChartBeFullWidth(tabName, chartId) {
    const fullWidthCharts = {
        'tiempo': ['yearly_evolution', 'monthly_trend'],
        'descubrimiento': ['rediscovery_gaps'],
        'evolucion': ['artist_evolution'],
        'sellos': ['labels_evolution'],
        'duracion': ['duration_evolution'],
        'colaboradores': ['collaboration_diversity']
    };
    
    return fullWidthCharts[tabName] && fullWidthCharts[tabName].includes(chartId);
}



function returnToMainTabsFromScrobbles() {
    const tabsContainer = document.getElementById('main-tabs');
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
    currentAlbumId = null;
    
    // Volver a mostrar análisis detallado
    showStatsCategory('detailed-analysis');
}

// Exportar funciones para uso global
window.showScrobblesAnalysis = showScrobblesAnalysis;
window.showScrobblesAnalysisTab = showScrobblesAnalysisTab;
window.switchToScrobblesDetailTabs = switchToScrobblesDetailTabs;
window.returnToMainTabsFromScrobbles = returnToMainTabsFromScrobbles;