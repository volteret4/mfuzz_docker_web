// Variables para búsqueda de álbumes
let albumSearchTimeout = null;

// Configurar eventos del buscador de álbumes
function setupAlbumSearchEvents() {
    const input = document.getElementById('albumSearchInput');
    const dropdown = document.getElementById('albumDropdown');
    
    if (!input || !dropdown) {
        console.error('❌ No se encontraron elementos del buscador de álbumes');
        return;
    }
    
    console.log('🔧 Configurando eventos del buscador de álbumes');
    
    input.addEventListener('input', function(e) {
        const searchTerm = e.target.value;
        console.log(`🔍 Búsqueda de álbum: "${searchTerm}"`);
        
        clearTimeout(albumSearchTimeout);
        albumSearchTimeout = setTimeout(() => {
            filterAlbums(searchTerm);
        }, 300);
    });
    
    input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            const searchTerm = e.target.value.trim();
            console.log(`⏎ Enter presionado con: "${searchTerm}"`);
            
            if (searchTerm.length >= 2) {
                searchFirstAlbumMatch(searchTerm);
            }
        }
    });
    
    input.addEventListener('focus', function(e) {
        const searchTerm = e.target.value;
        if (searchTerm.length >= 1) {
            filterAlbums(searchTerm);
        }
    });
    
    input.addEventListener('blur', function(e) {
        setTimeout(() => {
            dropdown.style.display = 'none';
        }, 200);
    });
}

// Filtrar álbumes
async function filterAlbums(searchTerm) {
    const dropdown = document.getElementById('albumDropdown');
    
    if (!dropdown) {
        console.error('❌ Dropdown no encontrado');
        return;
    }
    
    if (!searchTerm || searchTerm.trim().length < 1) {
        dropdown.style.display = 'none';
        return;
    }
    
    try {
        console.log(`🔍 Buscando álbumes: "${searchTerm}"`);
        
        const response = await fetch(`/api/albums/search?q=${encodeURIComponent(searchTerm)}&limit=15`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log(`📊 Respuesta de búsqueda:`, data);
        
        dropdown.innerHTML = '';
        
        if (data.error) {
            dropdown.innerHTML = `<div style="padding: 10px 15px; color: #ff6b6b;">${data.error}</div>`;
            dropdown.style.display = 'block';
            return;
        }
        
        if (!data.results || data.results.length === 0) {
            dropdown.innerHTML = '<div style="padding: 10px 15px; color: #ff6b6b;">No se encontraron álbumes</div>';
            dropdown.style.display = 'block';
            return;
        }
        
        data.results.forEach((album, index) => {
            const item = document.createElement('div');
            item.style.cssText = 'padding: 12px 15px; cursor: pointer; border-bottom: 1px solid rgba(255,255,255,0.1); transition: background 0.2s ease;';
            
            item.innerHTML = `
                <div style="font-weight: bold; margin-bottom: 5px;">${album.display_name}</div>
                <div style="font-size: 0.85rem; color: #a8e6cf;">
                    ${album.year ? `${album.year}` : 'Año desconocido'} • 
                    ${album.genre || 'Género desconocido'} • 
                    ${album.label || 'Sello desconocido'}
                </div>
            `;
            
            item.addEventListener('mousedown', function(e) {
                e.preventDefault();
                console.log(`🖱️ Click en álbum: ${album.display_name}`);
                selectAlbum(album);
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
        console.log(`✅ Mostrados ${data.results.length} álbumes`);
        
    } catch (error) {
        console.error('💥 Error buscando álbumes:', error);
        dropdown.innerHTML = `<div style="padding: 15px; text-align: center; color: #ff6b6b;">Error de conexión: ${error.message}</div>`;
        dropdown.style.display = 'block';
    }
}

// Buscar primera coincidencia
async function searchFirstAlbumMatch(searchTerm) {
    try {
        const response = await fetch(`/api/albums/search?q=${encodeURIComponent(searchTerm)}&limit=1`);
        if (response.ok) {
            const data = await response.json();
            if (data.results && data.results.length > 0) {
                selectAlbum(data.results[0]);
            } else {
                showAlbumNotFound(searchTerm);
            }
        }
    } catch (error) {
        console.error('Error buscando primera coincidencia de álbum:', error);
        showAlbumNotFound(searchTerm);
    }
}


// Mostrar mensaje de álbum no encontrado
function showAlbumNotFound(searchTerm) {
    const dropdown = document.getElementById('albumDropdown');
    if (dropdown) {
        dropdown.innerHTML = `
            <div style="padding: 15px; text-align: center; color: #ff6b6b;">
                <i class="fas fa-search" style="margin-bottom: 10px; display: block;"></i>
                No se encontró "${searchTerm}"
                <br><small>Intenta con otro término</small>
            </div>
        `;
        dropdown.style.display = 'block';
        
        setTimeout(() => {
            dropdown.style.display = 'none';
        }, 3000);
    }
}

// Seleccionar álbum
function selectAlbum(album) {
    console.log(`🎯 Seleccionando álbum: ${album.display_name} (ID: ${album.id})`);
    
    currentAlbumId = album.id;
    
    const input = document.getElementById('albumSearchInput');
    const dropdown = document.getElementById('albumDropdown');
    
    if (input) {
        input.value = album.display_name;
    }
    if (dropdown) {
        dropdown.style.display = 'none';
    }
    
    // Lógica específica según la página
    if (window.location.pathname.includes('album_analysis.html')) {
        showAlbumInfo(album);
        switchToAlbumDetailTabs();
        setTimeout(() => showAlbumAnalysisTab('tiempo'), 100);
    } else if (window.location.pathname.includes('sistema.html')) {
        showAlbumInfoInSistema(album);
        switchToAlbumDetailTabsInSistema();
        setTimeout(() => showAlbumAnalysisTab('tiempo'), 100);
    }
}

// Funciones específicas para cada página
function showAlbumInfo(album) {
    // Para album_analysis.html
    const initialMessage = document.querySelector('.initial-message');
    const albumInfo = document.getElementById('selected-album-info');
    
    if (initialMessage) {
        initialMessage.style.display = 'none';
    }
    if (albumInfo) {
        albumInfo.style.display = 'block';
        // Actualizar información del álbum
        document.getElementById('album-title').textContent = album.name;
        document.getElementById('album-artist').textContent = album.artist_name;
        document.getElementById('album-year').textContent = album.year || 'Desconocido';
        document.getElementById('album-genre').textContent = album.genre || 'Desconocido';
        document.getElementById('album-label').textContent = album.label || 'Desconocido';
    }
}

function showAlbumInfoInSistema(album) {
    // Para sistema.html
    const initialMessage = document.getElementById('albumInitialMessage');
    const selectedContent = document.getElementById('selectedAlbumContent');
    
    if (initialMessage) {
        initialMessage.style.display = 'none';
    }
    
    if (selectedContent) {
        selectedContent.style.display = 'block';
        selectedContent.innerHTML = `
            <div style="text-align: center; padding: 20px; background: rgba(168,230,207,0.1); border-radius: 10px; margin: 20px 0;">
                <h3 style="color: #a8e6cf; margin-bottom: 10px;">
                    <i class="fas fa-compact-disc"></i> ${album.name}
                </h3>
                <p><strong>Artista:</strong> ${album.artist_name}</p>
                <p><strong>Año:</strong> ${album.year || 'Desconocido'}</p>
                <p><strong>Género:</strong> ${album.genre || 'Desconocido'}</p>
                <p><strong>Sello:</strong> ${album.label || 'Desconocido'}</p>
                <p style="margin-top: 15px;">Álbum seleccionado para análisis detallado.</p>
            </div>
            <div id="albumAnalysisContent">
                <div class="loading">
                    <i class="fas fa-spinner"></i>
                    <p>Preparando análisis...</p>
                </div>
            </div>
        `;
    }
}