// === CONFIGURACIÓN INICIAL ===

function setupAlbumAnalysis() {
    setupAlbumSearchEvents();
    showMainSection('search');
}

// === NAVEGACIÓN DE ÁLBUMES ===


// Mostrar sección principal
function showMainSection(section) {
    // Por ahora solo tenemos búsqueda
    console.log(`Mostrando sección: ${section}`);
}



// Cambiar a pestañas de análisis de álbum
function switchToAlbumDetailTabs() {
    const tabsContainer = document.getElementById('main-tabs');
    tabsContainer.innerHTML = `
        <button class="stats-tab back-tab" onclick="returnToMainTabsFromAlbum()">
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

function returnToMainTabsFromAlbum() {
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


// === ANÁLISIS DE ÁLBUMES ===


async function showAlbumAnalysisTab(tabName) {
    if (!currentAlbumId) {
        console.warn('❌ No hay álbum seleccionado');
        return;
    }
    
    console.log(`📊 Cargando análisis: ${tabName} para álbum ID ${currentAlbumId}`);
    
    // Actualizar pestañas activas en vista de álbum
    if (currentView === 'album-detail') {
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
    let content = document.getElementById('albumAnalysisContent');
    if (!content) {
        content = document.getElementById('selectedAlbumContent');
    }
    
    if (!content) {
        console.error('❌ No se encontró contenedor para el análisis de álbum');
        return;
    }
    
    content.innerHTML = '<div class="loading"><i class="fas fa-spinner"></i><p>Cargando análisis...</p></div>';
    
    try {
        console.log(`🌐 Haciendo petición a: /api/albums/${currentAlbumId}/analysis/${tabName}`);
        const response = await fetch(`/api/albums/${currentAlbumId}/analysis/${tabName}`);
        
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
        
        // Renderizar análisis de álbum
        renderAlbumAnalysisContent(tabName, data, content);
        
    } catch (error) {
        console.error(`💥 Error cargando análisis ${tabName}:`, error);
        content.innerHTML = `
            <div class="error-message">
                <i class="fas fa-exclamation-triangle"></i>
                <p><strong>Error de conexión:</strong> ${error.message}</p>
                <button class="btn" onclick="showAlbumAnalysisTab('${tabName}')" style="margin-top: 10px; background: #2a5298; color: white; border: none; padding: 8px 15px; border-radius: 8px; cursor: pointer;">
                    <i class="fas fa-redo"></i> Reintentar
                </button>
            </div>
        `;
    }
}


async function showAlbumAnalysis(container) {
    container.innerHTML = `
        <div class="stats-section">
            <h2>Análisis de Álbumes</h2>
            
            <!-- Selector de álbumes -->
            <div style="background: rgba(255, 255, 255, 0.05); border-radius: 15px; padding: 20px; margin: 20px 0;">
                <h3 style="color: #a8e6cf; margin-bottom: 15px;">Seleccionar Álbum</h3>
                <div style="position: relative;">
                    <input type="text" id="albumSearchInput" 
                        style="width: 100%; padding: 12px; border: 1px solid rgba(255,255,255,0.2); border-radius: 10px; background: rgba(255,255,255,0.1); color: white; outline: none;"
                        placeholder="Buscar por artista o álbum (ej: 'Pink Floyd' o 'Pink Floyd - Dark Side')" 
                        autocomplete="off">
                    <div id="albumDropdown" style="display: none; position: absolute; top: 100%; left: 0; right: 0; background: rgba(42,82,152,0.95); border: 1px solid rgba(255,255,255,0.2); border-radius: 10px; max-height: 200px; overflow-y: auto; margin-top: 5px; z-index: 1000; backdrop-filter: blur(10px);"></div>
                </div>
            </div>
            
            <!-- Mensaje inicial -->
            <div id="albumInitialMessage" style="text-align: center; padding: 40px; color: #a8e6cf;">
                <i class="fas fa-compact-disc" style="font-size: 3rem; margin-bottom: 20px; display: block;"></i>
                <p>Selecciona un álbum para ver su análisis detallado</p>
                <p><small>Escribe el nombre del artista o álbum para comenzar</small></p>
            </div>
            
            <!-- Información del álbum seleccionado -->
            <div id="selectedAlbumContent" style="display: none;">
                <!-- Se carga dinámicamente -->
            </div>
        </div>
    `;
    
    // Configurar eventos del buscador de álbumes
    setupAlbumSearchEvents();
}

// === RENDERIZADO DE ANÁLISIS ===


function renderAlbumAnalysisContent(tabName, data, container) {
    let html = `
        <div style="background: rgba(255,255,255,0.05); border-radius: 15px; padding: 20px; margin-bottom: 20px;">
            <h3 style="color: #a8e6cf; margin-bottom: 15px;">
                <i class="fas fa-chart-${getIconForAlbumTab(tabName)}"></i>
                Análisis de ${tabName.charAt(0).toUpperCase() + tabName.slice(1)}
            </h3>
    `;
    
    // Añadir estadísticas si existen
    if (data.stats && Object.keys(data.stats).length > 0) {
        html += '<div class="analysis-stats">';
        for (const [key, value] of Object.entries(data.stats)) {
            const displayKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            html += `
                <div class="analysis-stat-card">
                    <h5>${displayKey}</h5>
                    <p>${value}</p>
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
    
    // Añadir gráficos si existen
    if (data.charts && Object.keys(data.charts).length > 0) {
        html += '<div class="analysis-charts-grid">';
        
        Object.keys(data.charts).forEach(chartId => {
            const chartTitle = chartId.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            html += `
                <div class="analysis-chart-container">
                    <h4>${chartTitle}</h4>
                    <div id="chart-${chartId}" style="height: 350px;"></div>
                </div>
            `;
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
        console.log(`📊 Renderizando ${Object.keys(data.charts).length} gráficos de álbum...`);
        
        Object.keys(data.charts).forEach((chartId, index) => {
            setTimeout(() => {
                try {
                    const chartContainer = document.getElementById(`chart-${chartId}`);
                    if (chartContainer && data.charts[chartId]) {
                        console.log(`📈 Renderizando gráfico de álbum: ${chartId}`);
                        
                        const plotData = typeof data.charts[chartId] === 'string' ? 
                            JSON.parse(data.charts[chartId]) : data.charts[chartId];
                        
                        if (window.Plotly && plotData.data && plotData.layout) {
                            Plotly.newPlot(`chart-${chartId}`, plotData.data, plotData.layout, {
                                responsive: true,
                                displayModeBar: false
                            });
                            console.log(`✅ Gráfico de álbum ${chartId} renderizado correctamente`);
                        } else {
                            console.error(`❌ Datos de gráfico inválidos para ${chartId}:`, plotData);
                        }
                    }
                } catch (error) {
                    console.error(`💥 Error renderizando gráfico de álbum ${chartId}:`, error);
                    const container = document.getElementById(`chart-${chartId}`);
                    if (container) {
                        container.innerHTML = '<div style="text-align: center; color: #ff6b6b; padding: 20px;">Error renderizando gráfico</div>';
                    }
                }
            }, 100 * index);
        });
    }
    
    console.log(`✅ Análisis de álbum ${tabName} cargado correctamente`);
}



// Renderizar contenido del análisis
function renderAnalysisContent(tabName, data, container) {
    let html = `
        <div style="margin-bottom: 20px;">
            <h3 style="color: #a8e6cf; margin-bottom: 15px;">
                <i class="fas fa-chart-${getIconForTab(tabName)}"></i>
                Análisis de ${tabName.charAt(0).toUpperCase() + tabName.slice(1)}
            </h3>
        </div>
    `;

    // Añadir estadísticas si existen
    if (data.stats && Object.keys(data.stats).length > 0) {
        html += '<div class="analysis-stats">';
        for (const [key, value] of Object.entries(data.stats)) {
            const displayKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            html += `
                <div class="analysis-stat-card">
                    <h5>${displayKey}</h5>
                    <p>${value}</p>
                </div>
            `;
        }
        html += '</div>';
    }

    // Añadir gráficos si existen
    if (data.charts && Object.keys(data.charts).length > 0) {
        html += '<div class="analysis-charts-grid">';
        
        Object.keys(data.charts).forEach(chartId => {
            const chartTitle = chartId.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            html += `
                <div class="analysis-chart-container">
                    <h4>${chartTitle}</h4>
                    <div id="chart-${chartId}" style="height: 350px;"></div>
                </div>
            `;
        });
        
        html += '</div>';
    } else {
        html += `
            <div style="text-align: center; padding: 40px; color: #ccc;">
                <i class="fas fa-chart-bar" style="font-size: 2rem; margin-bottom: 15px; display: block; opacity: 0.5;"></i>
                <p>No hay gráficos disponibles para este análisis</p>
            </div>
        `;
    }

    // Añadir información adicional específica por tipo
    if (data.same_year_albums && data.same_year_albums.length > 0) {
        html += renderAdditionalData('Álbumes del mismo año', data.same_year_albums);
    }

    if (data.same_genre_albums && data.same_genre_albums.length > 0) {
        html += renderAdditionalData('Otros álbumes del género', data.same_genre_albums);
    }

    if (data.concerts_with_album && data.concerts_with_album.length > 0) {
        html += renderConcertsData(data.concerts_with_album);
    }

    if (data.recent_feeds && data.recent_feeds.length > 0) {
        html += renderFeedsData(data.recent_feeds);
    }

    if (data.top_words && data.top_words.length > 0) {
        html += renderWordsData(data.top_words);
    }

    container.innerHTML = html;

    // Renderizar gráficos si existen
    if (data.charts && Object.keys(data.charts).length > 0) {
        console.log(`📊 Renderizando ${Object.keys(data.charts).length} gráficos...`);
        
        Object.keys(data.charts).forEach((chartId, index) => {
            setTimeout(() => {
                try {
                    const chartContainer = document.getElementById(`chart-${chartId}`);
                    if (chartContainer && data.charts[chartId]) {
                        console.log(`📈 Renderizando gráfico: ${chartId}`);
                        
                        const plotData = typeof data.charts[chartId] === 'string' ? 
                            JSON.parse(data.charts[chartId]) : data.charts[chartId];
                        
                        if (window.Plotly && plotData.data && plotData.layout) {
                            Plotly.newPlot(`chart-${chartId}`, plotData.data, plotData.layout, {
                                responsive: true,
                                displayModeBar: false
                            });
                            console.log(`✅ Gráfico ${chartId} renderizado correctamente`);
                        } else {
                            console.error(`❌ Datos de gráfico inválidos para ${chartId}:`, plotData);
                        }
                    }
                } catch (error) {
                    console.error(`💥 Error renderizando gráfico ${chartId}:`, error);
                    const container = document.getElementById(`chart-${chartId}`);
                    if (container) {
                        container.innerHTML = '<div style="text-align: center; color: #ff6b6b; padding: 20px;">Error renderizando gráfico</div>';
                    }
                }
            }, 100 * index);
        });
    }

    console.log(`✅ Análisis de ${tabName} cargado correctamente`);
}


// === FUNCIONES DE UTILIDAD DE ANÁLISIS ===

// Obtener icono para cada pestaña
function getIconForTab(tabName) {
    const icons = {
        'tiempo': 'clock',
        'genero': 'music',
        'conciertos': 'microphone',
        'sellos': 'record-vinyl',
        'discografia': 'compact-disc',
        'escuchas': 'headphones',
        'colaboradores': 'users',
        'feeds': 'rss',
        'letras': 'quote-right'
    };
    return icons[tabName] || 'bar';
}

function getIconForAlbumTab(tabName) {
    const icons = {
        'tiempo': 'clock',
        'genero': 'music',
        'conciertos': 'microphone',
        'sellos': 'record-vinyl',
        'discografia': 'compact-disc',
        'escuchas': 'headphones',
        'colaboradores': 'users',
        'feeds': 'rss',
        'letras': 'quote-right'
    };
    return icons[tabName] || 'bar';
}




// Renderizar datos adicionales
function renderAdditionalData(title, data) {
    let html = `
        <div style="background: rgba(255,255,255,0.05); border-radius: 10px; padding: 15px; margin-top: 20px;">
            <h4 style="color: #a8e6cf; margin-bottom: 15px;">${title}</h4>
            <div style="max-height: 200px; overflow-y: auto;">
    `;
    
    data.slice(0, 10).forEach(item => {
        html += `
            <div style="padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.1);">
                <strong>${item.artist_name || item.name}</strong> - ${item.name || item.artist_name}
                ${item.year ? `<span style="color: #a8e6cf;"> (${item.year})</span>` : ''}
            </div>
        `;
    });
    
    html += '</div></div>';
    return html;
}


// Renderizar datos de conciertos
function renderConcertsData(concerts) {
    let html = `
        <div style="background: rgba(255,255,255,0.05); border-radius: 10px; padding: 15px; margin-top: 20px;">
            <h4 style="color: #a8e6cf; margin-bottom: 15px;">Conciertos con canciones del álbum</h4>
            <div style="max-height: 200px; overflow-y: auto;">
    `;
    
    concerts.forEach(concert => {
        html += `
            <div style="padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.1);">
                <strong>${concert.date}</strong> - ${concert.venue}
                <br><small style="color: #a8e6cf;">${concert.city}, ${concert.country}</small>
                <br><small>Canciones: ${concert.album_tracks.join(', ')}</small>
            </div>
        `;
    });
    
    html += '</div></div>';
    return html;
}


// Renderizar datos de feeds
function renderFeedsData(feeds) {
    let html = `
        <div style="background: rgba(255,255,255,0.05); border-radius: 10px; padding: 15px; margin-top: 20px;">
            <h4 style="color: #a8e6cf; margin-bottom: 15px;">Feeds recientes</h4>
            <div style="max-height: 200px; overflow-y: auto;">
    `;
    
    feeds.forEach(feed => {
        html += `
            <div style="padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.1);">
                <strong>${feed.post_title}</strong>
                <br><small style="color: #a8e6cf;">${feed.feed_name} - ${feed.post_date}</small>
                ${feed.post_url ? `<br><a href="${feed.post_url}" target="_blank" style="color: #a8e6cf; text-decoration: none;">Ver enlace</a>` : ''}
            </div>
        `;
    });
    
    html += '</div></div>';
    return html;
}



// Renderizar datos de palabras
function renderWordsData(words) {
    let html = `
        <div style="background: rgba(255,255,255,0.05); border-radius: 10px; padding: 15px; margin-top: 20px;">
            <h4 style="color: #a8e6cf; margin-bottom: 15px;">Palabras más frecuentes</h4>
            <div style="display: flex; flex-wrap: wrap; gap: 10px;">
    `;
    
    words.forEach(word => {
        const fontSize = Math.max(0.8, Math.min(1.5, word.count / words[0].count));
        html += `
            <span style="background: rgba(168,230,207,0.2); padding: 5px 10px; border-radius: 15px; font-size: ${fontSize}rem;">
                ${word.word} (${word.count})
            </span>
        `;
    });
    
    html += '</div></div>';
    return html;
}

// Configurar eventos globales
document.addEventListener('click', (e) => {
    const dropdown = document.getElementById('albumDropdown');
    if (dropdown && !e.target.closest('#albumSearchInput') && !e.target.closest('#albumDropdown')) {
        dropdown.style.display = 'none';
    }
});