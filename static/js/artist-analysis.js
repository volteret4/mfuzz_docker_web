// === BÚSQUEDA Y FILTRADO DE ARTISTAS ===

async function loadArtistsList() {
    try {
        console.log('🔄 Cargando lista de artistas...');
        
        // AÑADIR DEBUG: Verificar qué devuelve la BD
        const debugResponse = await fetch('/api/debug/artists');
        if (debugResponse.ok) {
            const debugData = await debugResponse.json();
            console.log('🔍 Debug info de la BD:', debugData);
        }
        
        const response = await fetch('/api/artists/list?limit=5000');
        const data = await response.json();
        
        console.log('📊 Respuesta completa del API:', data);
        
        if (data.error) {
            console.error('❌ Error en API:', data.error);
            console.error('🔧 Debug info:', data.debug);
            
            // Mostrar error en la UI
            const initialMessage = document.getElementById('initialMessage');
            if (initialMessage) {
                initialMessage.innerHTML = `
                    <i class="fas fa-exclamation-triangle" style="font-size: 3rem; margin-bottom: 20px; display: block; color: #ff6b6b;"></i>
                    <p>Error cargando artistas: ${data.error}</p>
                    <p><small>Debug: ${JSON.stringify(data.debug)}</small></p>
                `;
            }
            return;
        }
        
        if (data.artists && data.artists.length > 0) {
            artistsList = data.artists;
            console.log(`✅ Lista de artistas cargada: ${artistsList.length} artistas`);
            console.log('👤 Primeros 5 artistas:', artistsList.slice(0, 5));
            console.log('👤 Últimos 5 artistas:', artistsList.slice(-5));
            
            // Actualizar mensaje inicial si existe
            const initialMessage = document.getElementById('initialMessage');
            if (initialMessage) {
                const smallText = initialMessage.querySelector('small');
                if (smallText) {
                    smallText.textContent = `Escribe para buscar entre ${artistsList.length} artistas`;
                } else {
                    initialMessage.innerHTML += `<p><small>Escribe para buscar entre ${artistsList.length} artistas</small></p>`;
                }
            }
        } else {
            console.warn('⚠️ No se encontraron artistas en la respuesta');
            console.warn('📄 Datos recibidos:', data);
            artistsList = [];
            
            // Mostrar información de debug en la UI
            const initialMessage = document.getElementById('initialMessage');
            if (initialMessage) {
                initialMessage.innerHTML = `
                    <i class="fas fa-search" style="font-size: 3rem; margin-bottom: 20px; display: block;"></i>
                    <p>No se encontraron artistas</p>
                    <p><small>Total en BD: ${data.debug?.total_in_db || 'Desconocido'}</small></p>
                    <p><small>Processed: ${data.debug?.processed || 0}</small></p>
                `;
            }
        }
    } catch (error) {
        console.error('💥 Error cargando lista de artistas:', error);
        artistsList = [];
        
        // Mostrar error de conexión
        const initialMessage = document.getElementById('initialMessage');
        if (initialMessage) {
            initialMessage.innerHTML = `
                <i class="fas fa-exclamation-triangle" style="font-size: 3rem; margin-bottom: 20px; display: block; color: #ff6b6b;"></i>
                <p>Error de conexión cargando artistas</p>
                <p><small>${error.message}</small></p>
                <button onclick="loadArtistsList()" style="margin-top: 10px; background: #2a5298; color: white; border: none; padding: 8px 15px; border-radius: 8px; cursor: pointer;">
                    🔄 Reintentar
                </button>
            `;
        }
    }
}


function setupArtistSearchEvents() {
    const input = document.getElementById('artistSearchInput');
    const dropdown = document.getElementById('artistDropdown');
    
    if (!input || !dropdown) {
        console.error('❌ No se encontraron elementos del buscador de artistas');
        return;
    }
    
    console.log('🔧 Configurando eventos del buscador de artistas');
    
    // Evento de input (escribir)
    input.addEventListener('input', function(e) {
        const searchTerm = e.target.value;
        console.log(`🔍 Búsqueda: "${searchTerm}"`);
        filterArtists(searchTerm);
    });
    
    // Evento de tecla Enter
    input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            const searchTerm = e.target.value.trim();
            console.log(`⏎ Enter presionado con: "${searchTerm}"`);
            
            if (searchTerm.length >= 2) {
                // Buscar coincidencia exacta o primera coincidencia
                const exactMatch = artistsList.find(artist => 
                    artist.name.toLowerCase() === searchTerm.toLowerCase()
                );
                
                if (exactMatch) {
                    console.log(`🎯 Coincidencia exacta encontrada: ${exactMatch.name}`);
                    selectArtist(exactMatch);
                } else {
                    // Buscar primera coincidencia parcial
                    const partialMatch = artistsList.find(artist => 
                        artist.name.toLowerCase().includes(searchTerm.toLowerCase())
                    );
                    
                    if (partialMatch) {
                        console.log(`🎯 Coincidencia parcial encontrada: ${partialMatch.name}`);
                        selectArtist(partialMatch);
                    } else {
                        console.log(`❌ No se encontró artista para: "${searchTerm}"`);
                        showArtistNotFound(searchTerm);
                    }
                }
            }
        }
    });
    
    // Evento de focus (mostrar dropdown si hay texto)
    input.addEventListener('focus', function(e) {
        const searchTerm = e.target.value;
        if (searchTerm.length >= 1) {
            filterArtists(searchTerm);
        }
    });
    
    // Evento de blur (ocultar dropdown con delay para permitir clicks)
    input.addEventListener('blur', function(e) {
        setTimeout(() => {
            dropdown.style.display = 'none';
        }, 200);
    });
}


// === BÚSQUEDA Y FILTRADO DE ARTISTAS ===

function filterArtists(searchTerm) {
    const dropdown = document.getElementById('artistDropdown');
    
    if (!dropdown) {
        console.error('❌ Dropdown no encontrado');
        return;
    }
    
    if (!searchTerm || searchTerm.trim().length < 1) {
        dropdown.style.display = 'none';
        return;
    }
    
    if (!artistsList || artistsList.length === 0) {
        console.warn('⚠️ Lista de artistas vacía');
        dropdown.innerHTML = '<div style="padding: 10px 15px; color: #ff6b6b;">No hay artistas cargados</div>';
        dropdown.style.display = 'block';
        return;
    }
    
    const searchLower = searchTerm.toLowerCase();
    const filtered = artistsList.filter(artist => 
        artist.name.toLowerCase().includes(searchLower)
    ).slice(0, 15); // Limitar a 15 resultados
    
    console.log(`🔍 Filtrado: "${searchTerm}" -> ${filtered.length} resultados`);
    
    dropdown.innerHTML = '';
    
    if (filtered.length === 0) {
        dropdown.innerHTML = '<div style="padding: 10px 15px; color: #ff6b6b;">No se encontraron artistas</div>';
        dropdown.style.display = 'block';
        return;
    }
    
    filtered.forEach((artist, index) => {
        const item = document.createElement('div');
        item.style.cssText = 'padding: 10px 15px; cursor: pointer; border-bottom: 1px solid rgba(255,255,255,0.1); transition: background 0.2s ease;';
        item.textContent = artist.name;
        
        // Resaltar coincidencias
        const nameHtml = artist.name.replace(
            new RegExp(`(${searchTerm})`, 'gi'),
            '<strong style="color: #a8e6cf;">$1</strong>'
        );
        item.innerHTML = nameHtml;
        
        item.addEventListener('mousedown', function(e) {
            e.preventDefault(); // Prevenir blur del input
            console.log(`🖱️ Click en artista: ${artist.name}`);
            selectArtist(artist);
        });
        
        item.addEventListener('mouseover', function() {
            item.style.background = 'rgba(168,230,207,0.2)';
        });
        
        item.addEventListener('mouseout', function() {
            item.style.background = 'transparent';
        });
        
        dropdown.appendChild(item);
    });
    
    dropdown.style.display = 'block';
}




function showArtistNotFound(searchTerm) {
    const dropdown = document.getElementById('artistDropdown');
    if (dropdown) {
        dropdown.innerHTML = `
            <div style="padding: 15px; text-align: center; color: #ff6b6b;">
                <i class="fas fa-search" style="margin-bottom: 10px; display: block;"></i>
                No se encontró "${searchTerm}"
                <br><small>Intenta con otro nombre</small>
            </div>
        `;
        dropdown.style.display = 'block';
        
        setTimeout(() => {
            dropdown.style.display = 'none';
        }, 3000);
    }
}




function selectArtist(artist) {
    console.log(`🎯 Seleccionando artista: ${artist.name} (ID: ${artist.id})`);
    
    currentArtistId = artist.id;
    
    // Actualizar input y ocultar dropdown
    const input = document.getElementById('artistSearchInput');
    const dropdown = document.getElementById('artistDropdown');
    
    if (input) {
        input.value = artist.name;
    }
    if (dropdown) {
        dropdown.style.display = 'none';
    }
    
    // Ocultar mensaje inicial y mostrar contenido
    const initialMessage = document.getElementById('initialMessage');
    const selectedContent = document.getElementById('selectedArtistContent');
    
    if (initialMessage) {
        initialMessage.style.display = 'none';
    }
    if (selectedContent) {
        selectedContent.style.display = 'block';
        selectedContent.innerHTML = `
            <div style="text-align: center; padding: 20px; background: rgba(168,230,207,0.1); border-radius: 10px; margin: 20px 0;">
                <h3 style="color: #a8e6cf; margin-bottom: 10px;">
                    <i class="fas fa-user"></i> ${artist.name}
                </h3>
                <p>Artista seleccionado. Las pestañas han cambiado para mostrar análisis detallados.</p>
            </div>
            <div id="artistAnalysisContent">
                <div class="loading">
                    <i class="fas fa-spinner"></i>
                    <p>Preparando análisis...</p>
                </div>
            </div>
        `;
    }
    
    console.log('📊 Cambiando a pestañas de artista...');
    // NUEVO: Cambiar pestañas a modo artista
    switchToArtistDetailTabs();
    
    // Mostrar primera pestaña (tiempo) con un pequeño delay para que se renderice la UI
    setTimeout(() => {
        console.log('⏰ Cargando análisis de tiempo...');
        showArtistAnalysisTab('tiempo');
    }, 100);
}



// === ANÁLISIS DE ARTISTAS ===


async function showArtistAnalysis(container) {
    container.innerHTML = `
        <div class="stats-section">
            <h2>Análisis Detallado de Artistas</h2>
            
            <!-- Selector de artistas -->
            <div style="background: rgba(255, 255, 255, 0.05); border-radius: 15px; padding: 20px; margin: 20px 0;">
                <h3 style="color: #a8e6cf; margin-bottom: 15px;">Seleccionar Artista</h3>
                <div style="position: relative;">
                    <input type="text" id="artistSearchInput" 
                        style="width: 100%; padding: 12px; border: 1px solid rgba(255,255,255,0.2); border-radius: 10px; background: rgba(255,255,255,0.1); color: white; outline: none;"
                        placeholder="Buscar artista..." autocomplete="off">
                    <div id="artistDropdown" style="display: none; position: absolute; top: 100%; left: 0; right: 0; background: rgba(42,82,152,0.95); border: 1px solid rgba(255,255,255,0.2); border-radius: 10px; max-height: 200px; overflow-y: auto; margin-top: 5px; z-index: 1000; backdrop-filter: blur(10px);"></div>
                </div>
            </div>
            
            <!-- Mensaje inicial -->
            <div id="initialMessage" style="text-align: center; padding: 40px; color: #a8e6cf;">
                <i class="fas fa-chart-line" style="font-size: 3rem; margin-bottom: 20px; display: block;"></i>
                <p>Selecciona un artista para ver su análisis detallado</p>
                <p><small>Escribe para buscar entre ${artistsList.length} artistas</small></p>
            </div>
            
            <!-- Contenido del artista seleccionado -->
            <div id="selectedArtistContent" style="display: none;">
                <!-- Se carga dinámicamente -->
            </div>
        </div>
    `;
    
    // Cargar lista de artistas y configurar eventos
    await loadArtistsList();
    setupArtistSearchEvents();
}


async function showArtistAnalysisTab(tabName) {
    if (!currentArtistId) {
        console.warn('❌ No hay artista seleccionado');
        return;
    }
    
    console.log(`📊 Cargando análisis: ${tabName} para artista ID ${currentArtistId}`);
    
    // Actualizar pestañas activas en vista de artista - CORREGIDO
    if (currentView === 'artist-detail') {
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
    let content = document.getElementById('artistAnalysisContent');
    if (!content) {
        content = document.getElementById('selectedArtistContent');
    }
    
    if (!content) {
        console.error('❌ No se encontró contenedor para el análisis');
        return;
    }
    
    content.innerHTML = '<div class="loading"><i class="fas fa-spinner"></i><p>Cargando análisis...</p></div>';
    
    try {
        console.log(`🌐 Haciendo petición a: /api/artists/${currentArtistId}/analysis/${tabName}`);
        const response = await fetch(`/api/artists/${currentArtistId}/analysis/${tabName}`);
        
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
        
        // Renderizar análisis
        let html = `
            <div style="background: rgba(255,255,255,0.05); border-radius: 15px; padding: 20px; margin-bottom: 20px;">
                <h3 style="color: #a8e6cf; margin-bottom: 15px;">
                    <i class="fas fa-chart-${tabName === 'tiempo' ? 'line' : tabName === 'conciertos' ? 'microphone' : 'bar'}"></i>
                    Análisis de ${tabName.charAt(0).toUpperCase() + tabName.slice(1)}
                </h3>
        `;
        
        // Añadir estadísticas si existen
        if (data.stats && Object.keys(data.stats).length > 0) {
            html += '<div class="artist-stats-summary">';
            for (const [key, value] of Object.entries(data.stats)) {
                const displayKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                html += `
                    <div class="artist-stat-card">
                        <h5>${displayKey}</h5>
                        <p>${value}</p>
                    </div>
                `;
            }
            html += '</div>';
        }
        
        // Añadir gráficos si existen
        if (data.charts && Object.keys(data.charts).length > 0) {
            // Diferentes layouts según el tipo de análisis
            let gridStyle = 'display: grid; gap: 20px; margin-top: 20px;';
            
            if (tabName === 'conciertos') {
                // Conciertos: una columna (uno sobre otro)
                gridStyle += 'grid-template-columns: 1fr;';
            } else if (tabName === 'generos') {
                // Géneros: 2x2
                gridStyle += 'grid-template-columns: repeat(2, 1fr);';
            } else if (tabName === 'escuchas') {
                // Escuchas: una sola columna con 4 filas
                gridStyle += 'grid-template-columns: 1fr;';
            } else if (tabName === 'colaboradores') {
                // Colaboradores: 2x2
                gridStyle += 'grid-template-columns: repeat(2, 1fr);';
            } else {
                // Por defecto: auto-fit
                gridStyle += 'grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));';
            }
            
            html += `<div style="${gridStyle}">`;
            
            Object.keys(data.charts).forEach(chartId => {
                const chartTitle = chartId.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                html += `
                    <div style="background: rgba(255,255,255,0.05); border-radius: 10px; padding: 15px;">
                        <h4 style="color: #a8e6cf; text-align: center; margin-bottom: 10px;">${chartTitle}</h4>
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
        
        html += '</div>';
        
        content.innerHTML = html;
        
        // Renderizar gráficos si existen
        if (data.charts && Object.keys(data.charts).length > 0) {
            console.log(`📊 Renderizando ${Object.keys(data.charts).length} gráficos...`);
            
            Object.keys(data.charts).forEach(chartId => {
                setTimeout(() => {
                    try {
                        const container = document.getElementById(`chart-${chartId}`);
                        if (container && data.charts[chartId]) {
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
                }, 100 * Object.keys(data.charts).indexOf(chartId)); // Stagger chart rendering
            });
        }
        
        console.log(`✅ Análisis de ${tabName} cargado correctamente`);
        
    } catch (error) {
        console.error(`💥 Error cargando análisis ${tabName}:`, error);
        content.innerHTML = `
            <div class="error-message">
                <i class="fas fa-exclamation-triangle"></i>
                <p><strong>Error de conexión:</strong> ${error.message}</p>
                <button class="btn" onclick="showArtistAnalysisTab('${tabName}')" style="margin-top: 10px; background: #2a5298; color: white; border: none; padding: 8px 15px; border-radius: 8px; cursor: pointer;">
                    <i class="fas fa-redo"></i> Reintentar
                </button>
            </div>
        `;
    }
}


// === FUNCIONES DE ANÁLISIS ESPECÍFICAS ===

