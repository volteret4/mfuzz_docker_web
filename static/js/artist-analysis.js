// === BÚSQUEDA Y FILTRADO DE ARTISTAS ===

async function loadArtistsList() {
  try {
    console.log("🔄 Cargando lista de artistas...");

    // AÑADIR DEBUG: Verificar qué devuelve la BD
    const debugResponse = await fetch("/api/debug/artists");
    if (debugResponse.ok) {
      const debugData = await debugResponse.json();
      console.log("🔍 Debug info de la BD:", debugData);
    }

    const response = await fetch("/api/artists/list?limit=5000");
    const data = await response.json();

    console.log("📊 Respuesta completa del API:", data);

    if (data.error) {
      console.error("❌ Error en API:", data.error);
      console.error("🔧 Debug info:", data.debug);

      // Mostrar error en la UI
      const initialMessage = document.getElementById("initialMessage");
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
      console.log(
        `✅ Lista de artistas cargada: ${artistsList.length} artistas`,
      );
      console.log("👤 Primeros 5 artistas:", artistsList.slice(0, 5));
      console.log("👤 Últimos 5 artistas:", artistsList.slice(-5));

      // Actualizar mensaje inicial si existe
      const initialMessage = document.getElementById("initialMessage");
      if (initialMessage) {
        const smallText = initialMessage.querySelector("small");
        if (smallText) {
          smallText.textContent = `Escribe para buscar entre ${artistsList.length} artistas`;
        } else {
          initialMessage.innerHTML += `<p><small>Escribe para buscar entre ${artistsList.length} artistas</small></p>`;
        }
      }
    } else {
      console.warn("⚠️ No se encontraron artistas en la respuesta");
      console.warn("📄 Datos recibidos:", data);
      artistsList = [];

      // Mostrar información de debug en la UI
      const initialMessage = document.getElementById("initialMessage");
      if (initialMessage) {
        initialMessage.innerHTML = `
                    <i class="fas fa-search" style="font-size: 3rem; margin-bottom: 20px; display: block;"></i>
                    <p>No se encontraron artistas</p>
                    <p><small>Total en BD: ${data.debug?.total_in_db || "Desconocido"}</small></p>
                    <p><small>Processed: ${data.debug?.processed || 0}</small></p>
                `;
      }
    }
  } catch (error) {
    console.error("💥 Error cargando lista de artistas:", error);
    artistsList = [];

    // Mostrar error de conexión
    const initialMessage = document.getElementById("initialMessage");
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

// === CONFIGURAR EVENTOS DEL BUSCADOR DE ARTISTAS ===
function setupArtistSearchEvents() {
  const input = document.getElementById("artistSearchInput");
  const dropdown = document.getElementById("artistDropdown");

  if (!input || !dropdown) {
    console.error("❌ No se encontraron elementos del buscador de artistas");
    return;
  }

  console.log("🔧 Configurando eventos del buscador de artistas");

  let searchTimeout;

  // Evento de input (escribir)
  input.addEventListener("input", function (e) {
    const searchTerm = e.target.value.trim();
    console.log(`🔍 Búsqueda: "${searchTerm}"`);

    clearTimeout(searchTimeout);

    if (searchTerm.length >= 1) {
      searchTimeout = setTimeout(() => {
        searchArtists(searchTerm);
      }, 300);
    } else {
      dropdown.style.display = "none";
    }
  });

  // Evento de tecla Enter
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      e.preventDefault();
      clearTimeout(searchTimeout);
      const searchTerm = e.target.value.trim();

      if (searchTerm.length >= 2) {
        selectFirstArtistMatch(searchTerm);
      }
    }
  });

  // Evento de focus
  input.addEventListener("focus", function (e) {
    const searchTerm = e.target.value.trim();
    if (searchTerm.length >= 1) {
      searchArtists(searchTerm);
    }
  });

  // Evento de blur (ocultar dropdown con delay para permitir clicks)
  input.addEventListener("blur", function (e) {
    setTimeout(() => {
      dropdown.style.display = "none";
    }, 200);
  });
}

// === BUSCAR ARTISTAS EN LA API ===
async function searchArtists(searchTerm) {
  const dropdown = document.getElementById("artistDropdown");

  if (!dropdown) {
    console.error("❌ Dropdown no encontrado");
    return;
  }

  try {
    console.log(`🔍 Buscando artistas: "${searchTerm}"`);

    // Mostrar loading en dropdown
    dropdown.innerHTML =
      '<div style="padding: 15px; text-align: center; color: #a8e6cf;"><i class="fas fa-spinner fa-spin"></i> Buscando...</div>';
    dropdown.style.display = "block";

    // ACTUALIZADO: Usar endpoint de estadísticas
    const response = await fetch(
      `/api/stats/artists/search?q=${encodeURIComponent(searchTerm)}&limit=15`,
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    console.log(`📊 Respuesta de búsqueda:`, data);

    dropdown.innerHTML = "";

    if (data.error) {
      dropdown.innerHTML = `<div style="padding: 10px 15px; color: #ff6b6b;">${data.error}</div>`;
      dropdown.style.display = "block";
      return;
    }

    if (!data.results || data.results.length === 0) {
      dropdown.innerHTML =
        '<div style="padding: 10px 15px; color: #ff6b6b;">No se encontraron artistas</div>';
      dropdown.style.display = "block";
      return;
    }

    // Mostrar resultados
    data.results.forEach((artist, index) => {
      const item = document.createElement("div");
      item.style.cssText =
        "padding: 12px 15px; cursor: pointer; border-bottom: 1px solid rgba(255,255,255,0.1); transition: background 0.2s ease;";

      // Resaltar coincidencias
      const nameHtml = artist.name.replace(
        new RegExp(`(${searchTerm})`, "gi"),
        '<strong style="color: #a8e6cf;">$1</strong>',
      );
      item.innerHTML = nameHtml;

      item.addEventListener("mousedown", function (e) {
        e.preventDefault();
        console.log(`🖱️ Click en artista: ${artist.name}`);
        selectArtist(artist);
      });

      item.addEventListener("mouseover", function () {
        item.style.background = "rgba(168,230,207,0.2)";
      });

      item.addEventListener("mouseout", function () {
        item.style.background = "transparent";
      });

      dropdown.appendChild(item);
    });

    dropdown.style.display = "block";
    console.log(`✅ Mostrados ${data.results.length} artistas`);
  } catch (error) {
    console.error("💥 Error buscando artistas:", error);
    dropdown.innerHTML = `<div style="padding: 15px; text-align: center; color: #ff6b6b;">Error de conexión: ${error.message}</div>`;
    dropdown.style.display = "block";
  }
}

// === SELECCIONAR PRIMERA COINCIDENCIA ===

async function selectFirstArtistMatch(searchTerm) {
  try {
    // ACTUALIZADO: Usar endpoint de estadísticas
    const response = await fetch(
      `/api/stats/artists/search?q=${encodeURIComponent(searchTerm)}&limit=1`,
    );
    if (response.ok) {
      const data = await response.json();
      if (data.results && data.results.length > 0) {
        selectArtist(data.results[0]);
      } else {
        showArtistNotFound(searchTerm);
      }
    }
  } catch (error) {
    console.error("Error buscando primera coincidencia de artista:", error);
    showArtistNotFound(searchTerm);
  }
}

// === BÚSQUEDA Y FILTRADO DE ARTISTAS ===

function filterArtists(searchTerm) {
  const dropdown = document.getElementById("artistDropdown");

  if (!dropdown) {
    console.error("❌ Dropdown no encontrado");
    return;
  }

  if (!searchTerm || searchTerm.trim().length < 1) {
    dropdown.style.display = "none";
    return;
  }

  if (!artistsList || artistsList.length === 0) {
    console.warn("⚠️ Lista de artistas vacía");
    dropdown.innerHTML =
      '<div style="padding: 10px 15px; color: #ff6b6b;">No hay artistas cargados</div>';
    dropdown.style.display = "block";
    return;
  }

  const searchLower = searchTerm.toLowerCase();
  const filtered = artistsList
    .filter((artist) => artist.name.toLowerCase().includes(searchLower))
    .slice(0, 15); // Limitar a 15 resultados

  console.log(`🔍 Filtrado: "${searchTerm}" -> ${filtered.length} resultados`);

  dropdown.innerHTML = "";

  if (filtered.length === 0) {
    dropdown.innerHTML =
      '<div style="padding: 10px 15px; color: #ff6b6b;">No se encontraron artistas</div>';
    dropdown.style.display = "block";
    return;
  }

  filtered.forEach((artist, index) => {
    const item = document.createElement("div");
    item.style.cssText =
      "padding: 10px 15px; cursor: pointer; border-bottom: 1px solid rgba(255,255,255,0.1); transition: background 0.2s ease;";
    item.textContent = artist.name;

    // Resaltar coincidencias
    const nameHtml = artist.name.replace(
      new RegExp(`(${searchTerm})`, "gi"),
      '<strong style="color: #a8e6cf;">$1</strong>',
    );
    item.innerHTML = nameHtml;

    item.addEventListener("mousedown", function (e) {
      e.preventDefault(); // Prevenir blur del input
      console.log(`🖱️ Click en artista: ${artist.name}`);
      selectArtist(artist);
    });

    item.addEventListener("mouseover", function () {
      item.style.background = "rgba(168,230,207,0.2)";
    });

    item.addEventListener("mouseout", function () {
      item.style.background = "transparent";
    });

    dropdown.appendChild(item);
  });

  dropdown.style.display = "block";
}

// === MOSTRAR ARTISTA NO ENCONTRADO ===
function showArtistNotFound(searchTerm) {
  const dropdown = document.getElementById("artistDropdown");
  if (dropdown) {
    dropdown.innerHTML = `
            <div style="padding: 15px; text-align: center; color: #ff6b6b;">
                <i class="fas fa-search" style="margin-bottom: 10px; display: block;"></i>
                No se encontró "${searchTerm}"
                <br><small>Intenta con otro nombre</small>
            </div>
        `;
    dropdown.style.display = "block";

    setTimeout(() => {
      dropdown.style.display = "none";
    }, 3000);
  }
}

// === CARGAR ANÁLISIS DEL ARTISTA ===
async function loadArtistAnalysis(artistId) {
  const selectedContent = document.getElementById("selectedArtistContent");

  if (!selectedContent) {
    console.error("❌ No se encontró contenedor de contenido");
    return;
  }

  try {
    // Obtener información básica del artista
    const response = await fetch(`/api/artists/${artistId}`);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    const artist = data.artist;

    selectedContent.innerHTML = `
            <div style="background: rgba(168,230,207,0.1); border-radius: 10px; padding: 20px; margin: 20px 0;">
                <h3 style="color: #a8e6cf; margin-bottom: 15px;">
                    <i class="fas fa-user"></i> ${artist.name}
                </h3>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0;">
                    <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px;">
                        <strong>País:</strong> ${artist.origin || "Desconocido"}
                    </div>
                    <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px;">
                        <strong>Género:</strong> ${artist.genre || "Desconocido"}
                    </div>
                    <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px;">
                        <strong>ID:</strong> ${artist.id}
                    </div>
                </div>

                <div style="margin-top: 20px;">
                    <h4 style="color: #a8e6cf; margin-bottom: 15px;">Opciones de análisis disponibles:</h4>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px;">
                        <button onclick="loadArtistAlbums(${artist.id})" style="background: rgba(42,82,152,0.8); color: white; border: none; padding: 15px; border-radius: 8px; cursor: pointer; transition: background 0.3s;">
                            <i class="fas fa-record-vinyl"></i> Ver Álbumes (${artist.album_count || 0})
                        </button>
                        <button onclick="loadArtistStats(${artist.id})" style="background: rgba(42,82,152,0.8); color: white; border: none; padding: 15px; border-radius: 8px; cursor: pointer; transition: background 0.3s;">
                            <i class="fas fa-chart-bar"></i> Estadísticas Detalladas
                        </button>
                        <button onclick="loadArtistScrobbles(${artist.id})" style="background: rgba(42,82,152,0.8); color: white; border: none; padding: 15px; border-radius: 8px; cursor: pointer; transition: background 0.3s;">
                            <i class="fas fa-play"></i> Análisis de Reproducciones
                        </button>
                    </div>
                </div>
            </div>

            <div id="artistDetailContent">
                <!-- Se carga dinámicamente según la opción seleccionada -->
            </div>
        `;

    console.log(`✅ Análisis de artista cargado: ${artist.name}`);
  } catch (error) {
    console.error("💥 Error cargando análisis de artista:", error);
    selectedContent.innerHTML = `
            <div style="text-align: center; padding: 20px; background: rgba(255,107,107,0.1); border-radius: 10px; margin: 20px 0;">
                <h3 style="color: #ff6b6b; margin-bottom: 10px;">
                    <i class="fas fa-exclamation-triangle"></i> Error
                </h3>
                <p>No se pudo cargar el análisis del artista</p>
                <p><small>${error.message}</small></p>
                <button onclick="loadArtistAnalysis(${artistId})" style="margin-top: 15px; background: #2a5298; color: white; border: none; padding: 8px 15px; border-radius: 8px; cursor: pointer;">
                    🔄 Reintentar
                </button>
            </div>
        `;
  }
}

// === FUNCIONES SIMILARES PARA ÁLBUMES ===

async function showAlbumAnalysis(container) {
  console.log("🎯 Iniciando análisis de álbumes...");

  container.innerHTML = `
        <div class="stats-section">
            <h2>Análisis Detallado de Álbumes</h2>

            <!-- Selector de álbumes -->
            <div style="background: rgba(255, 255, 255, 0.05); border-radius: 15px; padding: 20px; margin: 20px 0;">
                <h3 style="color: #a8e6cf; margin-bottom: 15px;">
                    <i class="fas fa-record-vinyl"></i> Seleccionar Álbum
                </h3>
                <div style="position: relative;">
                    <input type="text" id="albumSearchInput"
                        style="width: 100%; padding: 12px; border: 1px solid rgba(255,255,255,0.2); border-radius: 10px; background: rgba(255,255,255,0.1); color: white; outline: none; font-size: 16px;"
                        placeholder="Buscar álbum..." autocomplete="off">
                    <div id="albumDropdown" style="display: none; position: absolute; top: 100%; left: 0; right: 0; background: rgba(42,82,152,0.95); border: 1px solid rgba(255,255,255,0.2); border-radius: 10px; max-height: 300px; overflow-y: auto; margin-top: 5px; z-index: 1000; backdrop-filter: blur(10px);"></div>
                </div>
            </div>

            <!-- Mensaje inicial -->
            <div id="albumInitialMessage" style="text-align: center; padding: 40px; color: #a8e6cf;">
                <i class="fas fa-record-vinyl" style="font-size: 3rem; margin-bottom: 20px; display: block;"></i>
                <p>Selecciona un álbum para ver su análisis detallado</p>
                <div class="loading" style="display: none;">
                    <i class="fas fa-spinner fa-spin"></i>
                    <p>Cargando álbumes...</p>
                </div>
            </div>

            <!-- Contenido del álbum seleccionado -->
            <div id="selectedAlbumContent" style="display: none;">
                <!-- Se carga dinámicamente -->
            </div>
        </div>
    `;

  // Configurar eventos del buscador de álbumes
  setupAlbumSearchEvents();

  console.log("✅ Vista de análisis de álbumes configurada");
}

// === CONFIGURAR EVENTOS DEL BUSCADOR DE ÁLBUMES ===
function setupAlbumSearchEvents() {
  const input = document.getElementById("albumSearchInput");
  const dropdown = document.getElementById("albumDropdown");

  if (!input || !dropdown) {
    console.error("❌ No se encontraron elementos del buscador de álbumes");
    return;
  }

  console.log("🔧 Configurando eventos del buscador de álbumes");

  let searchTimeout;

  // Evento de input (escribir)
  input.addEventListener("input", function (e) {
    const searchTerm = e.target.value.trim();
    console.log(`🔍 Búsqueda de álbum: "${searchTerm}"`);

    clearTimeout(searchTimeout);

    if (searchTerm.length >= 2) {
      searchTimeout = setTimeout(() => {
        searchAlbums(searchTerm);
      }, 300);
    } else {
      dropdown.style.display = "none";
    }
  });

  // Evento de tecla Enter
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      e.preventDefault();
      clearTimeout(searchTimeout);
      const searchTerm = e.target.value.trim();

      if (searchTerm.length >= 2) {
        selectFirstAlbumMatch(searchTerm);
      }
    }
  });

  // Evento de focus
  input.addEventListener("focus", function (e) {
    const searchTerm = e.target.value.trim();
    if (searchTerm.length >= 2) {
      searchAlbums(searchTerm);
    }
  });

  // Evento de blur
  input.addEventListener("blur", function (e) {
    setTimeout(() => {
      dropdown.style.display = "none";
    }, 200);
  });
}

// === BUSCAR ÁLBUMES EN LA API ===
async function searchAlbums(searchTerm) {
  const dropdown = document.getElementById("albumDropdown");

  if (!dropdown) {
    console.error("❌ Dropdown de álbumes no encontrado");
    return;
  }

  try {
    console.log(`🔍 Buscando álbumes: "${searchTerm}"`);

    // Mostrar loading en dropdown
    dropdown.innerHTML =
      '<div style="padding: 15px; text-align: center; color: #a8e6cf;"><i class="fas fa-spinner fa-spin"></i> Buscando...</div>';
    dropdown.style.display = "block";

    // ACTUALIZADO: Usar endpoint de estadísticas
    const response = await fetch(
      `/api/stats/albums/search?q=${encodeURIComponent(searchTerm)}&limit=15`,
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    console.log(`📊 Respuesta de búsqueda de álbumes:`, data);

    dropdown.innerHTML = "";

    if (data.error) {
      dropdown.innerHTML = `<div style="padding: 10px 15px; color: #ff6b6b;">${data.error}</div>`;
      dropdown.style.display = "block";
      return;
    }

    if (!data.results || data.results.length === 0) {
      dropdown.innerHTML =
        '<div style="padding: 10px 15px; color: #ff6b6b;">No se encontraron álbumes</div>';
      dropdown.style.display = "block";
      return;
    }

    // Mostrar resultados
    data.results.forEach((album, index) => {
      const item = document.createElement("div");
      item.style.cssText =
        "padding: 12px 15px; cursor: pointer; border-bottom: 1px solid rgba(255,255,255,0.1); transition: background 0.2s ease;";

      item.innerHTML = `
                <div style="font-weight: bold; margin-bottom: 5px;">${album.display_name}</div>
                <div style="font-size: 0.85rem; color: #a8e6cf;">
                    ${album.year !== "Desconocido" ? `${album.year}` : "Año desconocido"} •
                    ${album.genre !== "Desconocido" ? album.genre : "Género desconocido"} •
                    ${album.label !== "Desconocido" ? album.label : "Sello desconocido"}
                </div>
            `;

      item.addEventListener("mousedown", function (e) {
        e.preventDefault();
        console.log(`🖱️ Click en álbum: ${album.display_name}`);
        selectAlbum(album);
      });

      item.addEventListener("mouseover", function () {
        item.style.background = "rgba(168,230,207,0.2)";
      });

      item.addEventListener("mouseout", function () {
        item.style.background = "transparent";
      });

      dropdown.appendChild(item);
    });

    dropdown.style.display = "block";
    console.log(`✅ Mostrados ${data.results.length} álbumes`);
  } catch (error) {
    console.error("💥 Error buscando álbumes:", error);
    dropdown.innerHTML = `<div style="padding: 15px; text-align: center; color: #ff6b6b;">Error de conexión: ${error.message}</div>`;
    dropdown.style.display = "block";
  }
}

// === SELECCIONAR PRIMERA COINCIDENCIA DE ÁLBUM ===
async function selectFirstAlbumMatch(searchTerm) {
  try {
    // ACTUALIZADO: Usar endpoint de estadísticas
    const response = await fetch(
      `/api/stats/albums/search?q=${encodeURIComponent(searchTerm)}&limit=1`,
    );
    if (response.ok) {
      const data = await response.json();
      if (data.results && data.results.length > 0) {
        selectAlbum(data.results[0]);
      } else {
        showAlbumNotFound(searchTerm);
      }
    }
  } catch (error) {
    console.error("Error buscando primera coincidencia de álbum:", error);
    showAlbumNotFound(searchTerm);
  }
}

// === CARGAR ANÁLISIS DE ARTISTA CON NUEVOS ENDPOINTS ===
async function loadArtistAnalysisTab(tabName) {
  if (!currentArtistId) {
    console.warn("❌ No hay artista seleccionado");
    return;
  }

  console.log(
    `📊 Cargando análisis: ${tabName} para artista ID ${currentArtistId}`,
  );

  const content = document.getElementById("artistAnalysisContent");
  if (!content) {
    console.error("❌ No se encontró contenedor de análisis");
    return;
  }

  // Mostrar loading
  content.innerHTML = `
        <div class="loading" style="text-align: center; padding: 40px;">
            <i class="fas fa-spinner fa-spin"></i>
            <p>Cargando análisis de ${tabName}...</p>
        </div>
    `;

  try {
    // ACTUALIZADO: Usar endpoint de estadísticas
    const response = await fetch(
      `/api/stats/artists/${currentArtistId}/analysis/${tabName}`,
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    if (data.error) {
      throw new Error(data.error);
    }

    // Renderizar análisis
    content.innerHTML = renderAlbumAnalysis(tabName, data);

    console.log(`✅ Análisis de ${tabName} cargado correctamente`);
  } catch (error) {
    console.error(`💥 Error cargando análisis de ${tabName}:`, error);
    content.innerHTML = `
            <div style="text-align: center; padding: 40px; background: rgba(255,107,107,0.1); border-radius: 10px;">
                <h3 style="color: #ff6b6b; margin-bottom: 10px;">
                    <i class="fas fa-exclamation-triangle"></i> Error
                </h3>
                <p>No se pudo cargar el análisis de ${tabName}</p>
                <p><small>${error.message}</small></p>
                <button onclick="loadAlbumAnalysisTab('${tabName}')" style="margin-top: 15px; background: #2a5298; color: white; border: none; padding: 8px 15px; border-radius: 8px; cursor: pointer;">
                    🔄 Reintentar
                </button>
            </div>
        `;
  }
}

// === FUNCIONES DE RENDERIZADO ===

function renderArtistAnalysis(tabName, data) {
  switch (tabName) {
    case "tiempo":
      return renderTimeAnalysis(data);
    case "conciertos":
      return renderConcertsAnalysis(data);
    case "generos":
      return renderGenresAnalysis(data);
    case "sellos":
      return renderLabelsAnalysis(data);
    case "discografia":
      return renderDiscographyAnalysis(data);
    case "escuchas":
      return renderListensAnalysis(data);
    case "colaboradores":
      return renderCollaboratorsAnalysis(data);
    case "feeds":
      return renderFeedsAnalysis(data);
    default:
      return `<div class="error-message">Tipo de análisis no soportado: ${tabName}</div>`;
  }
}

function renderAlbumAnalysis(tabName, data) {
  switch (tabName) {
    case "tracks":
      return renderTracksAnalysis(data);
    case "technical":
      return renderTechnicalAnalysis(data);
    case "listening":
      return renderListeningAnalysis(data);
    case "credits":
      return renderCreditsAnalysis(data);
    default:
      return `<div class="error-message">Tipo de análisis no soportado: ${tabName}</div>`;
  }
}

// === RENDERIZADORES ESPECÍFICOS PARA ARTISTAS ===

function renderTimeAnalysis(data) {
  if (data.error) {
    return `<div class="error-message"><i class="fas fa-exclamation-triangle"></i> ${data.error}</div>`;
  }

  const stats = data.stats || {};

  return `
        <div class="analysis-content">
            <h3><i class="fas fa-clock"></i> Análisis Temporal</h3>

            <div class="stats-grid">
                <div class="stat-card">
                    <h4>Total de Álbumes</h4>
                    <div class="stat-value">${stats.total_albums || 0}</div>
                </div>
                <div class="stat-card">
                    <h4>Primer Año</h4>
                    <div class="stat-value">${stats.first_year || "N/A"}</div>
                </div>
                <div class="stat-card">
                    <h4>Último Año</h4>
                    <div class="stat-value">${stats.last_year || "N/A"}</div>
                </div>
                <div class="stat-card">
                    <h4>Década Más Productiva</h4>
                    <div class="stat-value">${stats.most_productive_decade || "N/A"}</div>
                </div>
            </div>

            <div class="charts-container">
                ${
                  data.charts
                    ? Object.entries(data.charts)
                        .map(
                          ([key, chart]) =>
                            `<div class="chart-container">
                        <h4>${chart.title || key}</h4>
                        <div class="chart-placeholder">${chart.html || "Gráfico no disponible"}</div>
                    </div>`,
                        )
                        .join("")
                    : "<p>No hay gráficos disponibles</p>"
                }
            </div>
        </div>
    `;
}

function renderConcertsAnalysis(data) {
  if (data.error) {
    return `<div class="error-message"><i class="fas fa-exclamation-triangle"></i> ${data.error}</div>`;
  }

  const stats = data.stats || {};

  return `
        <div class="analysis-content">
            <h3><i class="fas fa-microphone"></i> Análisis de Conciertos</h3>

            <div class="stats-grid">
                <div class="stat-card">
                    <h4>Total Conciertos</h4>
                    <div class="stat-value">${stats.total_concerts || 0}</div>
                </div>
                <div class="stat-card">
                    <h4>Países Visitados</h4>
                    <div class="stat-value">${stats.countries_visited || 0}</div>
                </div>
                <div class="stat-card">
                    <h4>Canciones Únicas</h4>
                    <div class="stat-value">${stats.unique_songs_played || 0}</div>
                </div>
                <div class="stat-card">
                    <h4>Total Setlists</h4>
                    <div class="stat-value">${stats.total_setlists || 0}</div>
                </div>
            </div>

            ${
              stats.last_concert_date
                ? `
                <div class="info-section">
                    <h4>Último Concierto</h4>
                    <p><strong>Fecha:</strong> ${stats.last_concert_date}</p>
                    <p><strong>Lugar:</strong> ${stats.last_concert_venue || "N/A"}</p>
                </div>
            `
                : ""
            }

            <div class="charts-container">
                ${
                  data.charts
                    ? Object.entries(data.charts)
                        .map(
                          ([key, chart]) =>
                            `<div class="chart-container">
                        <h4>${chart.title || key}</h4>
                        <div class="chart-placeholder">${chart.html || "Gráfico no disponible"}</div>
                    </div>`,
                        )
                        .join("")
                    : "<p>No hay gráficos disponibles</p>"
                }
            </div>
        </div>
    `;
}

function renderGenresAnalysis(data) {
  if (data.error) {
    return `<div class="error-message"><i class="fas fa-exclamation-triangle"></i> ${data.error}</div>`;
  }

  const stats = data.stats || {};

  return `
        <div class="analysis-content">
            <h3><i class="fas fa-music"></i> Análisis de Géneros</h3>

            <div class="stats-grid">
                <div class="stat-card">
                    <h4>Géneros de Álbumes</h4>
                    <div class="stat-value">${stats.total_album_genres || 0}</div>
                </div>
                <div class="stat-card">
                    <h4>Géneros Discogs</h4>
                    <div class="stat-value">${stats.total_discogs_genres || 0}</div>
                </div>
                <div class="stat-card">
                    <h4>Estilos Discogs</h4>
                    <div class="stat-value">${stats.total_discogs_styles || 0}</div>
                </div>
                <div class="stat-card">
                    <h4>Tags Last.fm</h4>
                    <div class="stat-value">${stats.total_lastfm_tags || 0}</div>
                </div>
            </div>

            <div class="charts-container">
                ${
                  data.charts
                    ? Object.entries(data.charts)
                        .map(
                          ([key, chart]) =>
                            `<div class="chart-container">
                        <h4>${chart.title || key}</h4>
                        <div class="chart-placeholder">${chart.html || "Gráfico no disponible"}</div>
                    </div>`,
                        )
                        .join("")
                    : "<p>No hay gráficos disponibles</p>"
                }
            </div>
        </div>
    `;
}


function renderLabelsAnalysis(data) {
    if (data.error) {
        return `<div class="error-message"><i class="fas fa-exclamation-triangle"></i> ${data.error}</div>`;
    }

    const stats = data.stats || {};

    return `
        <div class="analysis-content">
            <h3><i class="fas fa-record-vinyl"></i> Análisis de Sellos</h3>

            <div class="stats-grid">
                <div class="stat-card">
                    <h4>Total Sellos</h4>
                    <div class="stat-value">${stats.total_labels || 0}</div>
                </div>
                <div class="stat-card">
                    <h4>Sello Principal</h4>
                    <div class="stat-value" style="font-size: 0.9rem;">${stats.main_label || 'N/A'}</div>
                </div>
                <div class="stat-card">
                    <h4>Álbumes en Sello Principal</h4>
                    <div class="stat-value">${stats.main_label_albums || 0}</div>
                </div>
                <div class="stat-card">
                    <h4>Años Activos</h4>
                    <div class="stat-value">${stats.years_active || 0}</div>
                </div>
            </div>

            <div class="charts-container">
                ${data.charts ? Object.entries(data.charts).map(([key, chart]) =>
                    `<div class="chart-container">
                        <h4>${chart.title || key}</h4>
                        <div class="chart-placeholder">${chart.html || 'Gráfico no disponible'}</div>
                    </div>`
                ).join('') : '<p>No hay gráficos disponibles</p>'}
            </div>
        </div>
    `;
}

function renderDiscographyAnalysis(data) {
    if (data.error) {
        return `<div class="error-message"><i class="fas fa-exclamation-triangle"></i> ${data.error}</div>`;
    }

    const stats = data.stats || {};

    return `
        <div class="analysis-content">
            <h3><i class="fas fa-compact-disc"></i> Análisis de Discografía</h3>

            <div class="stats-grid">
                <div class="stat-card">
                    <h4>Total Lanzamientos</h4>
                    <div class="stat-value">${stats.total_releases || 0}</div>
                </div>
                <div class="stat-card">
                    <h4>En Colección</h4>
                    <div class="stat-value">${stats.in_collection || 0}</div>
                </div>
                <div class="stat-card">
                    <h4>Formatos Diferentes</h4>
                    <div class="stat-value">${stats.formats_count || 0}</div>
                </div>
            </div>

            <div class="charts-container">
                ${data.charts ? Object.entries(data.charts).map(([key, chart]) =>
                    `<div class="chart-container">
                        <h4>${chart.title || key}</h4>
                        <div class="chart-placeholder">${chart.html || 'Gráfico no disponible'}</div>
                    </div>`
                ).join('') : '<p>No hay gráficos disponibles</p>'}
            </div>
        </div>
    `;
}

function renderListensAnalysis(data) {
    if (data.error) {
        return `<div class="error-message"><i class="fas fa-exclamation-triangle"></i> ${data.error}</div>`;
    }

    const stats = data.stats || {};

    return `
        <div class="analysis-content">
            <h3><i class="fas fa-headphones"></i> Análisis de Escuchas</h3>

            <div class="stats-grid">
                <div class="stat-card">
                    <h4>Last.fm Scrobbles</h4>
                    <div class="stat-value">${stats.total_lastfm_scrobbles || 0}</div>
                </div>
                <div class="stat-card">
                    <h4>ListenBrainz Listens</h4>
                    <div class="stat-value">${stats.total_listenbrainz_listens || 0}</div>
                </div>
                <div class="stat-card">
                    <h4>Top Track Last.fm</h4>
                    <div class="stat-value" style="font-size: 0.8rem;">${stats.top_lastfm_track || 'N/A'}</div>
                </div>
                <div class="stat-card">
                    <h4>Top Track ListenBrainz</h4>
                    <div class="stat-value" style="font-size: 0.8rem;">${stats.top_listenbrainz_track || 'N/A'}</div>
                </div>
            </div>

            <div class="charts-container">
                ${data.charts ? Object.entries(data.charts).map(([key, chart]) =>
                    `<div class="chart-container">
                        <h4>${chart.title || key}</h4>
                        <div class="chart-placeholder">${chart.html || 'Gráfico no disponible'}</div>
                    </div>`
                ).join('') : '<p>No hay gráficos disponibles</p>'}
            </div>
        </div>
    `;
}

function renderCollaboratorsAnalysis(data) {
    if (data.error) {
        return `<div class="error-message"><i class="fas fa-exclamation-triangle"></i> ${data.error}</div>`;
    }

    const stats = data.stats || {};

    return `
        <div class="analysis-content">
            <h3><i class="fas fa-users"></i> Análisis de Colaboradores</h3>

            <div class="stats-grid">
                <div class="stat-card">
                    <h4>Total Productores</h4>
                    <div class="stat-value">${stats.total_producers || 0}</div>
                </div>
                <div class="stat-card">
                    <h4>Total Ingenieros</h4>
                    <div class="stat-value">${stats.total_engineers || 0}</div>
                </div>
                <div class="stat-card">
                    <h4>Total Colaboradores</h4>
                    <div class="stat-value">${stats.total_collaborators || 0}</div>
                </div>
                <div class="stat-card">
                    <h4>Colaboradores Únicos</h4>
                    <div class="stat-value">${stats.unique_collaborators || 0}</div>
                </div>
            </div>

            <div class="charts-container">
                ${data.charts ? Object.entries(data.charts).map(([key, chart]) =>
                    `<div class="chart-container">
                        <h4>${chart.title || key}</h4>
                        <div class="chart-placeholder">${chart.html || 'Gráfico no disponible'}</div>
                    </div>`
                ).join('') : '<p>No hay gráficos disponibles</p>'}
            </div>
        </div>
    `;
}

function renderFeedsAnalysis(data) {
    if (data.error) {
        return `<div class="error-message"><i class="fas fa-exclamation-triangle"></i> ${data.error}</div>`;
    }

    const stats = data.stats || {};
    const feeds = data.feeds || [];

    return `
        <div class="analysis-content">
            <h3><i class="fas fa-rss"></i> Análisis de Feeds</h3>

            <div class="stats-grid">
                <div class="stat-card">
                    <h4>Total Feeds</h4>
                    <div class="stat-value">${stats.total_feeds || 0}</div>
                </div>
                <div class="stat-card">
                    <h4>Fuentes Diferentes</h4>
                    <div class="stat-value">${stats.total_sources || 0}</div>
                </div>
                <div class="stat-card">
                    <h4>Fuente Más Activa</h4>
                    <div class="stat-value" style="font-size: 0.8rem;">${stats.most_active_source || 'N/A'}</div>
                </div>
            </div>

            <div class="charts-container">
                ${data.charts ? Object.entries(data.charts).map(([key, chart]) =>
                    `<div class="chart-container">
                        <h4>${chart.title || key}</h4>
                        <div class="chart-placeholder">${chart.html || 'Gráfico no disponible'}</div>
                    </div>`
                ).join('') : '<p>No hay gráficos disponibles</p>'}
            </div>

            ${feeds.length > 0 ? `
                <div class="feeds-list">
                    <h4>Feeds Recientes</h4>
                    <div class="feeds-container">
                        ${feeds.slice(0, 10).map(feed => `
                            <div class="feed-item">
                                <h5>${feed.post_title || 'Sin título'}</h5>
                                <p><strong>Fuente:</strong> ${feed.feed_name}</p>
                                <p><strong>Fecha:</strong> ${feed.post_date || 'N/A'}</p>
                                ${feed.post_url ? `<a href="${feed.post_url}" target="_blank">Ver más</a>` : ''}
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
        </div>
    `;
}

// === RENDERIZADORES ESPECÍFICOS PARA ÁLBUMES ===

function renderTracksAnalysis(data) {
    if (data.error) {
        return `<div class="error-message"><i class="fas fa-exclamation-triangle"></i> ${data.error}</div>`;
    }

    const stats = data.stats || {};
    const tracks = data.tracks || [];

    return `
        <div class="analysis-content">
            <h3><i class="fas fa-list"></i> Análisis de Canciones</h3>

            <div class="stats-grid">
                <div class="stat-card">
                    <h4>Total Canciones</h4>
                    <div class="stat-value">${stats.total_tracks || 0}</div>
                </div>
                <div class="stat-card">
                    <h4>Duración Total</h4>
                    <div class="stat-value">${stats.total_duration_minutes || 0} min</div>
                </div>
                <div class="stat-card">
                    <h4>Duración Promedio</h4>
                    <div class="stat-value">${stats.average_track_duration || 0} seg</div>
                </div>
                <div class="stat-card">
                    <h4>Bitrate Promedio</h4>
                    <div class="stat-value">${stats.average_bitrate || 0} kbps</div>
                </div>
            </div>

            ${tracks.length > 0 ? `
                <div class="tracks-list">
                    <h4>Lista de Canciones</h4>
                    <div class="tracks-container">
                        ${tracks.map((track, index) => `
                            <div class="track-item">
                                <span class="track-number">${track.track_number || index + 1}</span>
                                <span class="track-title">${track.title || 'Sin título'}</span>
                                <span class="track-duration">${track.duration ? Math.floor(track.duration / 60) + ':' + (track.duration % 60).toString().padStart(2, '0') : 'N/A'}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
        </div>
    `;
}

function renderTechnicalAnalysis(data) {
    if (data.error) {
        return `<div class="error-message"><i class="fas fa-exclamation-triangle"></i> ${data.error}</div>`;
    }

    const technical = data.technical_info || {};
    const stats = data.stats || {};

    return `
        <div class="analysis-content">
            <h3><i class="fas fa-cog"></i> Análisis Técnico</h3>

            <div class="info-grid">
                <div class="info-item">
                    <h4>Formato</h4>
                    <p>${technical.format || 'Desconocido'}</p>
                </div>
                <div class="info-item">
                    <h4>Año</h4>
                    <p>${technical.year || 'Desconocido'}</p>
                </div>
                <div class="info-item">
                    <h4>Género</h4>
                    <p>${technical.genre || 'Desconocido'}</p>
                </div>
                <div class="info-item">
                    <h4>Sello</h4>
                    <p>${technical.label || 'Desconocido'}</p>
                </div>
            </div>

            <div class="completeness-info">
                <h4>Completitud de Datos</h4>
                <div class="completeness-grid">
                    <div class="completeness-item ${stats.has_year ? 'complete' : 'incomplete'}">
                        <i class="fas fa-${stats.has_year ? 'check' : 'times'}"></i>
                        Año ${stats.has_year ? 'Completo' : 'Faltante'}
                    </div>
                    <div class="completeness-item ${stats.has_genre ? 'complete' : 'incomplete'}">
                        <i class="fas fa-${stats.has_genre ? 'check' : 'times'}"></i>
                        Género ${stats.has_genre ? 'Completo' : 'Faltante'}
                    </div>
                    <div class="completeness-item ${stats.has_label ? 'complete' : 'incomplete'}">
                        <i class="fas fa-${stats.has_label ? 'check' : 'times'}"></i>
                        Sello ${stats.has_label ? 'Completo' : 'Faltante'}
                    </div>
                </div>
            </div>
        </div>
    `;
}

function renderListeningAnalysis(data) {
    if (data.error) {
        return `<div class="error-message"><i class="fas fa-exclamation-triangle"></i> ${data.error}</div>`;
    }

    const listening = data.listening_stats || {};

    return `
        <div class="analysis-content">
            <h3><i class="fas fa-headphones"></i> Análisis de Escuchas</h3>

            <div class="stats-grid">
                <div class="stat-card">
                    <h4>Last.fm Scrobbles</h4>
                    <div class="stat-value">${listening.lastfm_scrobbles || 0}</div>
                </div>
                <div class="stat-card">
                    <h4>ListenBrainz Listens</h4>
                    <div class="stat-value">${listening.listenbrainz_listens || 0}</div>
                </div>
                <div class="stat-card">
                    <h4>Total Reproducciones</h4>
                    <div class="stat-value">${listening.total_plays || 0}</div>
                </div>
            </div>

            ${listening.total_plays > 0 ? `
                <div class="listening-info">
                    <p>Este álbum ha sido reproducido un total de <strong>${listening.total_plays}</strong> veces across diferentes plataformas.</p>
                </div>
            ` : `
                <div class="no-listening-info">
                    <p>No se encontraron datos de reproducciones para este álbum.</p>
                </div>
            `}
        </div>
    `;
}

function renderCreditsAnalysis(data) {
    if (data.error) {
        return `<div class="error-message"><i class="fas fa-exclamation-triangle"></i> ${data.error}</div>`;
    }

    const credits = data.credits || {};
    const stats = data.stats || {};

    return `
        <div class="analysis-content">
            <h3><i class="fas fa-award"></i> Análisis de Créditos</h3>

            <div class="credits-grid">
                <div class="credit-item">
                    <h4><i class="fas fa-user-tie"></i> Productores</h4>
                    <p>${credits.producers || 'No especificado'}</p>
                </div>
                <div class="credit-item">
                    <h4><i class="fas fa-tools"></i> Ingenieros</h4>
                    <p>${credits.engineers || 'No especificado'}</p>
                </div>
                <div class="credit-item">
                    <h4><i class="fas fa-users"></i> Créditos Adicionales</h4>
                    <p>${credits.credits || 'No especificado'}</p>
                </div>
            </div>

            <div class="completeness-info">
                <h4>Completitud de Créditos</h4>
                <div class="completeness-grid">
                    <div class="completeness-item ${stats.has_producers ? 'complete' : 'incomplete'}">
                        <i class="fas fa-${stats.has_producers ? 'check' : 'times'}"></i>
                        Productores ${stats.has_producers ? 'Especificados' : 'Faltantes'}
                    </div>
                    <div class="completeness-item ${stats.has_engineers ? 'complete' : 'incomplete'}">
                        <i class="fas fa-${stats.has_engineers ? 'check' : 'times'}"></i>
                        Ingenieros ${stats.has_engineers ? 'Especificados' : 'Faltantes'}
                    </div>
                    <div class="completeness-item ${stats.has_credits ? 'complete' : 'incomplete'}">
                        <i class="fas fa-${stats.has_credits ? 'check' : 'times'}"></i>
                        Créditos ${stats.has_credits ? 'Especificados' : 'Faltantes'}
                    </div>
                </div>
            </div>
        </div>
    `;
}


// === FUNCIONES DE PRUEBA PARA ENDPOINTS DE ESTADÍSTICAS ===

async function testStatsEndpoints() {
    console.log('🧪 Probando endpoints de estadísticas...');

    const endpoints = [
        '/api/stats/artists/search?q=test&limit=5',
        '/api/stats/albums/search?q=test&limit=5',
        '/api/stats/debug/artists'
    ];

    for (const endpoint of endpoints) {
        try {
            console.log(`📡 Probando: ${endpoint}`);
            const response = await fetch(endpoint);
            const data = await response.json();
            console.log(`✅ ${endpoint}: OK`, data);
        } catch (error) {
            console.error(`❌ ${endpoint}: ERROR`, error);
        }
    }

    console.log('🎯 Prueba de endpoints completada');
}

// === FUNCIONES ADICIONALES NECESARIAS ===

// === FUNCIÓN PRINCIPAL PARA MOSTRAR ANÁLISIS DE ARTISTAS ===
async function showArtistAnalysis(container) {
    console.log('🎯 Iniciando análisis de artistas...');

    container.innerHTML = `
        <div class="stats-section">
            <h2>Análisis Detallado de Artistas</h2>

            <!-- Selector de artistas -->
            <div style="background: rgba(255, 255, 255, 0.05); border-radius: 15px; padding: 20px; margin: 20px 0;">
                <h3 style="color: #a8e6cf; margin-bottom: 15px;">
                    <i class="fas fa-user"></i> Seleccionar Artista
                </h3>
                <div style="position: relative;">
                    <input type="text" id="artistSearchInput"
                        style="width: 100%; padding: 12px; border: 1px solid rgba(255,255,255,0.2); border-radius: 10px; background: rgba(255,255,255,0.1); color: white; outline: none; font-size: 16px;"
                        placeholder="Buscar artista..." autocomplete="off">
                    <div id="artistDropdown" style="display: none; position: absolute; top: 100%; left: 0; right: 0; background: rgba(42,82,152,0.95); border: 1px solid rgba(255,255,255,0.2); border-radius: 10px; max-height: 300px; overflow-y: auto; margin-top: 5px; z-index: 1000; backdrop-filter: blur(10px);"></div>
                </div>
            </div>

            <!-- Mensaje inicial -->
            <div id="initialMessage" style="text-align: center; padding: 40px; color: #a8e6cf;">
                <i class="fas fa-chart-line" style="font-size: 3rem; margin-bottom: 20px; display: block;"></i>
                <p>Selecciona un artista para ver su análisis detallado</p>
                <div class="loading" style="display: none;">
                    <i class="fas fa-spinner fa-spin"></i>
                    <p>Cargando artistas...</p>
                </div>
            </div>

            <!-- Contenido del artista seleccionado -->
            <div id="selectedArtistContent" style="display: none;">
                <!-- Se carga dinámicamente -->
            </div>
        </div>
    `;

    // Configurar eventos del buscador
    setupArtistSearchEvents();

    console.log('✅ Vista de análisis de artistas configurada');
}

// === FUNCIÓN PRINCIPAL PARA MOSTRAR ANÁLISIS DE ÁLBUMES ===
async function showAlbumAnalysis(container) {
    console.log('🎯 Iniciando análisis de álbumes...');

    container.innerHTML = `
        <div class="stats-section">
            <h2>Análisis Detallado de Álbumes</h2>

            <!-- Selector de álbumes -->
            <div style="background: rgba(255, 255, 255, 0.05); border-radius: 15px; padding: 20px; margin: 20px 0;">
                <h3 style="color: #a8e6cf; margin-bottom: 15px;">
                    <i class="fas fa-record-vinyl"></i> Seleccionar Álbum
                </h3>
                <div style="position: relative;">
                    <input type="text" id="albumSearchInput"
                        style="width: 100%; padding: 12px; border: 1px solid rgba(255,255,255,0.2); border-radius: 10px; background: rgba(255,255,255,0.1); color: white; outline: none; font-size: 16px;"
                        placeholder="Buscar álbum..." autocomplete="off">
                    <div id="albumDropdown" style="display: none; position: absolute; top: 100%; left: 0; right: 0; background: rgba(42,82,152,0.95); border: 1px solid rgba(255,255,255,0.2); border-radius: 10px; max-height: 300px; overflow-y: auto; margin-top: 5px; z-index: 1000; backdrop-filter: blur(10px);"></div>
                </div>
            </div>

            <!-- Mensaje inicial -->
            <div id="albumInitialMessage" style="text-align: center; padding: 40px; color: #a8e6cf;">
                <i class="fas fa-record-vinyl" style="font-size: 3rem; margin-bottom: 20px; display: block;"></i>
                <p>Selecciona un álbum para ver su análisis detallado</p>
            </div>

            <!-- Contenido del álbum seleccionado -->
            <div id="selectedAlbumContent" style="display: none;">
                <!-- Se carga dinámicamente -->
            </div>
        </div>
    `;

    // Configurar eventos del buscador de álbumes
    setupAlbumSearchEvents();

    console.log('✅ Vista de análisis de álbumes configurada');
}

// === CONFIGURAR EVENTOS DEL BUSCADOR DE ARTISTAS ===
function setupArtistSearchEvents() {
    const input = document.getElementById('artistSearchInput');
    const dropdown = document.getElementById('artistDropdown');

    if (!input || !dropdown) {
        console.error('❌ No se encontraron elementos del buscador de artistas');
        return;
    }

    console.log('🔧 Configurando eventos del buscador de artistas');

    let searchTimeout;

    // Evento de input (escribir)
    input.addEventListener('input', function(e) {
        const searchTerm = e.target.value.trim();
        console.log(`🔍 Búsqueda: "${searchTerm}"`);

        clearTimeout(searchTimeout);

        if (searchTerm.length >= 1) {
            searchTimeout = setTimeout(() => {
                searchArtists(searchTerm);
            }, 300);
        } else {
            dropdown.style.display = 'none';
        }
    });

    // Evento de tecla Enter
    input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            clearTimeout(searchTimeout);
            const searchTerm = e.target.value.trim();

            if (searchTerm.length >= 2) {
                selectFirstArtistMatch(searchTerm);
            }
        }
    });

    // Evento de focus
    input.addEventListener('focus', function(e) {
        const searchTerm = e.target.value.trim();
        if (searchTerm.length >= 1) {
            searchArtists(searchTerm);
        }
    });

    // Evento de blur (ocultar dropdown con delay para permitir clicks)
    input.addEventListener('blur', function(e) {
        setTimeout(() => {
            dropdown.style.display = 'none';
        }, 200);
    });
}

// === CONFIGURAR EVENTOS DEL BUSCADOR DE ÁLBUMES ===
function setupAlbumSearchEvents() {
    const input = document.getElementById('albumSearchInput');
    const dropdown = document.getElementById('albumDropdown');

    if (!input || !dropdown) {
        console.error('❌ No se encontraron elementos del buscador de álbumes');
        return;
    }

    console.log('🔧 Configurando eventos del buscador de álbumes');

    let searchTimeout;

    // Evento de input (escribir)
    input.addEventListener('input', function(e) {
        const searchTerm = e.target.value.trim();
        console.log(`🔍 Búsqueda de álbum: "${searchTerm}"`);

        clearTimeout(searchTimeout);

        if (searchTerm.length >= 2) {
            searchTimeout = setTimeout(() => {
                searchAlbums(searchTerm);
            }, 300);
        } else {
            dropdown.style.display = 'none';
        }
    });

    // Evento de tecla Enter
    input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            clearTimeout(searchTimeout);
            const searchTerm = e.target.value.trim();

            if (searchTerm.length >= 2) {
                selectFirstAlbumMatch(searchTerm);
            }
        }
    });

    // Evento de focus
    input.addEventListener('focus', function(e) {
        const searchTerm = e.target.value.trim();
        if (searchTerm.length >= 2) {
            searchAlbums(searchTerm);
        }
    });

    // Evento de blur
    input.addEventListener('blur', function(e) {
        setTimeout(() => {
            dropdown.style.display = 'none';
        }, 200);
    });
}

// === SELECCIONAR ARTISTA ===
function selectArtist(artist) {
    console.log(`🎯 Seleccionando artista: ${artist.name} (ID: ${artist.id})`);

    currentArtistId = artist.id;

    // Actualizar input y ocultar dropdown
    const input = document.getElementById('artistSearchInput');
    const dropdown = document.getElementById('artistDropdown');

    if (input) input.value = artist.name;
    if (dropdown) dropdown.style.display = 'none';

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
                <p>Artista seleccionado. Cargando análisis...</p>
                <div class="loading" style="margin-top: 15px;">
                    <i class="fas fa-spinner fa-spin"></i>
                </div>
            </div>

            <!-- Pestañas de análisis -->
            <div class="analysis-tabs">
                <button class="analysis-tab active" onclick="loadArtistAnalysisTab('tiempo')">
                    <i class="fas fa-clock"></i> Análisis Temporal
                </button>
                <button class="analysis-tab" onclick="loadArtistAnalysisTab('conciertos')">
                    <i class="fas fa-microphone"></i> Conciertos
                </button>
                <button class="analysis-tab" onclick="loadArtistAnalysisTab('generos')">
                    <i class="fas fa-music"></i> Géneros
                </button>
                <button class="analysis-tab" onclick="loadArtistAnalysisTab('sellos')">
                    <i class="fas fa-record-vinyl"></i> Sellos
                </button>
                <button class="analysis-tab" onclick="loadArtistAnalysisTab('discografia')">
                    <i class="fas fa-compact-disc"></i> Discografía
                </button>
                <button class="analysis-tab" onclick="loadArtistAnalysisTab('escuchas')">
                    <i class="fas fa-headphones"></i> Escuchas
                </button>
                <button class="analysis-tab" onclick="loadArtistAnalysisTab('colaboradores')">
                    <i class="fas fa-users"></i> Colaboradores
                </button>
                <button class="analysis-tab" onclick="loadArtistAnalysisTab('feeds')">
                    <i class="fas fa-rss"></i> Feeds
                </button>
            </div>

            <!-- Contenido del análisis -->
            <div id="artistAnalysisContent">
                <!-- Se carga dinámicamente -->
            </div>
        `;
    }

    // Cargar primer análisis automáticamente
    setTimeout(() => {
        loadArtistAnalysisTab('tiempo');
    }, 500);
}

// === SELECCIONAR ÁLBUM ===
function selectAlbum(album) {
    console.log(`🎯 Seleccionando álbum: ${album.display_name} (ID: ${album.id})`);

    currentAlbumId = album.id;

    // Actualizar input y ocultar dropdown
    const input = document.getElementById('albumSearchInput');
    const dropdown = document.getElementById('albumDropdown');

    if (input) input.value = album.display_name;
    if (dropdown) dropdown.style.display = 'none';

    // Ocultar mensaje inicial y mostrar contenido
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
                    <i class="fas fa-record-vinyl"></i> ${album.display_name}
                </h3>
                <p>Álbum seleccionado. Cargando análisis...</p>
                <div class="loading" style="margin-top: 15px;">
                    <i class="fas fa-spinner fa-spin"></i>
                </div>
            </div>

            <!-- Pestañas de análisis -->
            <div class="analysis-tabs">
                <button class="analysis-tab active" onclick="loadAlbumAnalysisTab('tracks')">
                    <i class="fas fa-list"></i> Canciones
                </button>
                <button class="analysis-tab" onclick="loadAlbumAnalysisTab('technical')">
                    <i class="fas fa-cog"></i> Información Técnica
                </button>
                <button class="analysis-tab" onclick="loadAlbumAnalysisTab('listening')">
                    <i class="fas fa-headphones"></i> Escuchas
                </button>
                <button class="analysis-tab" onclick="loadAlbumAnalysisTab('credits')">
                    <i class="fas fa-award"></i> Créditos
                </button>
            </div>

            <!-- Contenido del análisis -->
            <div id="albumAnalysisContent">
                <!-- Se carga dinámicamente -->
            </div>
        `;
    }

    // Cargar primer análisis automáticamente
    setTimeout(() => {
        loadAlbumAnalysisTab('tracks');
    }, 500);
}

// === MOSTRAR MENSAJES DE ERROR ===
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

function showAlbumNotFound(searchTerm) {
    const dropdown = document.getElementById('albumDropdown');
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

// === FUNCIONES DE INTEGRACIÓN CON EL SISTEMA PRINCIPAL ===

// Función que se llama desde sistema-functions.js cuando se hace clic en "Artistas"
function handleArtistsStatsClick(container) {
    console.log('🎯 Manejando click en estadísticas de artistas');
    showArtistAnalysis(container);
}

// Función que se llama desde sistema-functions.js cuando se hace clic en "Álbumes"
function handleAlbumsStatsClick(container) {
    console.log('🎯 Manejando click en estadísticas de álbumes');
    showAlbumAnalysis(container);
} análisis
        content.innerHTML = renderArtistAnalysis(tabName, data);

        console.log(`✅ Análisis de ${tabName} cargado correctamente`);

    } catch (error) {
        console.error(`💥 Error cargando análisis de ${tabName}:`, error);
        content.innerHTML = `
            <div style="text-align: center; padding: 40px; background: rgba(255,107,107,0.1); border-radius: 10px;">
                <h3 style="color: #ff6b6b; margin-bottom: 10px;">
                    <i class="fas fa-exclamation-triangle"></i> Error
                </h3>
                <p>No se pudo cargar el análisis de ${tabName}</p>
                <p><small>${error.message}</small></p>
                <button onclick="loadArtistAnalysisTab('${tabName}')" style="margin-top: 15px; background: #2a5298; color: white; border: none; padding: 8px 15px; border-radius: 8px; cursor: pointer;">
                    🔄 Reintentar
                </button>
            </div>
        `;
    }
}

// === CARGAR ANÁLISIS DE ÁLBUM CON NUEVOS ENDPOINTS ===
async function loadAlbumAnalysisTab(tabName) {
    if (!currentAlbumId) {
        console.warn('❌ No hay álbum seleccionado');
        return;
    }

    console.log(`📊 Cargando análisis: ${tabName} para álbum ID ${currentAlbumId}`);

    const content = document.getElementById('albumAnalysisContent');
    if (!content) {
        console.error('❌ No se encontró contenedor de análisis de álbum');
        return;
    }

    // Mostrar loading
    content.innerHTML = `
        <div class="loading" style="text-align: center; padding: 40px;">
            <i class="fas fa-spinner fa-spin"></i>
            <p>Cargando análisis de ${tabName}...</p>
        </div>
    `;

    try {
        // ACTUALIZADO: Usar endpoint de estadísticas
        const response = await fetch(`/api/stats/albums/${currentAlbumId}/analysis/${tabName}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        // Renderizar análisis
        content.innerHTML = renderAlbumAnalysis(tabName, data);

        console.log(`✅ Análisis de álbum ${tabName} cargado correctamente`);

    } catch (error) {
        console.error(`💥 Error cargando análisis de álbum ${tabName}:`, error);
        content.innerHTML = `
            <div style="text-align: center; padding: 40px; background: rgba(255,107,107,0.1); border-radius: 10px;">
                <h3 style="color: #ff6b6b; margin-bottom: 10px;">
                    <i class="fas fa-exclamation-triangle"></i> Error
                </h3>
                <p>No se pudo cargar el análisis de ${tabName}</p>
                <p><small>${error.message}</small></p>
                <button onclick="loadAlbumAnalysisTab('${tabName}')" style="margin-top: 15px; background: #2a5298; color: white; border: none; padding: 8px 15px; border-radius: 8px; cursor: pointer;">
                    🔄 Reintentar
                </button>
            </div>
        `;
    }
}



// === SELECCIONAR ÁLBUM ===
function selectAlbum(album) {
  console.log(
    `🎯 Seleccionando álbum: ${album.display_name} (ID: ${album.id})`,
  );

  currentAlbumId = album.id;

  // Actualizar input y ocultar dropdown
  const input = document.getElementById("albumSearchInput");
  const dropdown = document.getElementById("albumDropdown");

  if (input) input.value = album.display_name;
  if (dropdown) dropdown.style.display = "none";

  // Ocultar mensaje inicial y mostrar contenido
  const initialMessage = document.getElementById("albumInitialMessage");
  const selectedContent = document.getElementById("selectedAlbumContent");

  if (initialMessage) {
    initialMessage.style.display = "none";
  }

  if (selectedContent) {
    selectedContent.style.display = "block";
    selectedContent.innerHTML = `
            <div style="text-align: center; padding: 20px; background: rgba(168,230,207,0.1); border-radius: 10px; margin: 20px 0;">
                <h3 style="color: #a8e6cf; margin-bottom: 10px;">
                    <i class="fas fa-record-vinyl"></i> ${album.display_name}
                </h3>
                <p>Álbum seleccionado. Cargando análisis...</p>
                <div class="loading" style="margin-top: 15px;">
                    <i class="fas fa-spinner fa-spin"></i>
                </div>
            </div>
        `;
  }

  // Cargar análisis del álbum
  setTimeout(() => {
    loadAlbumAnalysis(album.id);
  }, 500);
}

// === MOSTRAR ÁLBUM NO ENCONTRADO ===
function showAlbumNotFound(searchTerm) {
  const dropdown = document.getElementById("albumDropdown");
  if (dropdown) {
    dropdown.innerHTML = `
            <div style="padding: 15px; text-align: center; color: #ff6b6b;">
                <i class="fas fa-search" style="margin-bottom: 10px; display: block;"></i>
                No se encontró "${searchTerm}"
                <br><small>Intenta con otro nombre</small>
            </div>
        `;
    dropdown.style.display = "block";

    setTimeout(() => {
      dropdown.style.display = "none";
    }, 3000);
  }
}

// === CARGAR ANÁLISIS DEL ÁLBUM ===
async function loadAlbumAnalysis(albumId) {
  const selectedContent = document.getElementById("selectedAlbumContent");

  if (!selectedContent) {
    console.error("❌ No se encontró contenedor de contenido de álbum");
    return;
  }

  try {
    // Obtener información básica del álbum
    const response = await fetch(`/api/albums/${albumId}`);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    const album = data.album;

    selectedContent.innerHTML = `
            <div style="background: rgba(168,230,207,0.1); border-radius: 10px; padding: 20px; margin: 20px 0;">
                <h3 style="color: #a8e6cf; margin-bottom: 15px;">
                    <i class="fas fa-record-vinyl"></i> ${album.name}
                </h3>
                <h4 style="color: #a8e6cf; margin-bottom: 20px;">por ${album.artist_name || "Artista desconocido"}</h4>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0;">
                    <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px;">
                        <strong>Año:</strong> ${album.year || "Desconocido"}
                    </div>
                    <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px;">
                        <strong>Género:</strong> ${album.genre || "Desconocido"}
                    </div>
                    <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px;">
                        <strong>Sello:</strong> ${album.label || "Desconocido"}
                    </div>
                    <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px;">
                        <strong>Canciones:</strong> ${album.track_count || 0}
                    </div>
                </div>

                <div style="margin-top: 20px;">
                    <h4 style="color: #a8e6cf; margin-bottom: 15px;">Opciones de análisis disponibles:</h4>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px;">
                        <button onclick="loadAlbumTracks(${album.id})" style="background: rgba(42,82,152,0.8); color: white; border: none; padding: 15px; border-radius: 8px; cursor: pointer; transition: background 0.3s;">
                            <i class="fas fa-music"></i> Ver Canciones (${album.track_count || 0})
                        </button>
                        <button onclick="loadAlbumStats(${album.id})" style="background: rgba(42,82,152,0.8); color: white; border: none; padding: 15px; border-radius: 8px; cursor: pointer; transition: background 0.3s;">
                            <i class="fas fa-chart-bar"></i> Estadísticas Detalladas
                        </button>
                        <button onclick="loadAlbumScrobbles(${album.id})" style="background: rgba(42,82,152,0.8); color: white; border: none; padding: 15px; border-radius: 8px; cursor: pointer; transition: background 0.3s;">
                            <i class="fas fa-play"></i> Análisis de Reproducciones
                        </button>
                    </div>
                </div>
            </div>

            <div id="albumDetailContent">
                <!-- Se carga dinámicamente según la opción seleccionada -->
            </div>
        `;

    console.log(`✅ Análisis de álbum cargado: ${album.name}`);
  } catch (error) {
    console.error("💥 Error cargando análisis de álbum:", error);
    selectedContent.innerHTML = `
            <div style="text-align: center; padding: 20px; background: rgba(255,107,107,0.1); border-radius: 10px; margin: 20px 0;">
                <h3 style="color: #ff6b6b; margin-bottom: 10px;">
                    <i class="fas fa-exclamation-triangle"></i> Error
                </h3>
                <p>No se pudo cargar el análisis del álbum</p>
                <p><small>${error.message}</small></p>
                <button onclick="loadAlbumAnalysis(${albumId})" style="margin-top: 15px; background: #2a5298; color: white; border: none; padding: 8px 15px; border-radius: 8px; cursor: pointer;">
                    🔄 Reintentar
                </button>
            </div>
        `;
  }
}

// === FUNCIONES AUXILIARES PARA ANÁLISIS DETALLADO ===

// Cargar canciones del álbum
async function loadAlbumTracks(albumId) {
  const detailContent = document.getElementById("albumDetailContent");

  detailContent.innerHTML = `
        <div class="loading" style="text-align: center; padding: 20px;">
            <i class="fas fa-spinner fa-spin"></i>
            <p>Cargando canciones...</p>
        </div>
    `;

  try {
    const response = await fetch(`/api/albums/${albumId}/tracks`);
    const data = await response.json();

    if (data.error) {
      throw new Error(data.error);
    }

    const tracks = data.tracks || [];

    detailContent.innerHTML = `
            <div style="background: rgba(255,255,255,0.05); border-radius: 10px; padding: 20px; margin: 20px 0;">
                <h4 style="color: #a8e6cf; margin-bottom: 20px;">
                    <i class="fas fa-music"></i> Canciones (${tracks.length})
                </h4>

                ${
                  tracks.length === 0
                    ? '<p style="text-align: center; color: #999;">No se encontraron canciones</p>'
                    : `<div style="display: grid; gap: 10px;">
                        ${tracks
                          .map(
                            (track, index) => `
                            <div style="background: rgba(255,255,255,0.05); border-radius: 8px; padding: 15px; display: flex; align-items: center; gap: 15px;">
                                <div style="color: #a8e6cf; font-weight: bold; min-width: 30px;">${track.track_number || index + 1}</div>
                                <div style="flex: 1;">
                                    <div style="font-weight: bold; margin-bottom: 5px;">${track.title}</div>
                                    <div style="font-size: 0.9rem; color: #ccc;">
                                        ${track.duration ? `Duración: ${formatDuration(track.duration)}` : ""}
                                        ${track.genre ? ` • Género: ${track.genre}` : ""}
                                    </div>
                                </div>
                            </div>
                        `,
                          )
                          .join("")}
                    </div>`
                }
            </div>
        `;
  } catch (error) {
    console.error("Error cargando canciones del álbum:", error);
    detailContent.innerHTML = `
            <div style="background: rgba(255,107,107,0.1); border-radius: 10px; padding: 20px; margin: 20px 0;">
                <p style="color: #ff6b6b; text-align: center;">
                    <i class="fas fa-exclamation-triangle"></i>
                    Error cargando canciones: ${error.message}
                </p>
            </div>
        `;
  }
}

// Formatear duración en segundos a mm:ss
function formatDuration(seconds) {
  if (!seconds) return "Desconocido";
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
}

// Función para seleccionar álbum desde vista de artista
function selectAlbumFromArtist(albumId, albumName) {
  console.log(
    `🎯 Seleccionando álbum desde artista: ${albumName} (ID: ${albumId})`,
  );
  // Cambiar a vista de álbumes y cargar el análisis
  // Esta función conecta el análisis de artistas con el de álbumes
  currentAlbumId = albumId;
  loadAlbumAnalysis(albumId);
}

// === INTEGRACIÓN CON EL SISTEMA DE ESTADÍSTICAS PRINCIPAL ===

// Función que se llama desde sistema-functions.js cuando se hace clic en "Artistas"
function handleArtistsStatsClick(container) {
  console.log("🎯 Manejando click en estadísticas de artistas");
  showArtistAnalysis(container);
}

// Función que se llama desde sistema-functions.js cuando se hace clic en "Álbumes"
function handleAlbumsStatsClick(container) {
  console.log("🎯 Manejando click en estadísticas de álbumes");
  showAlbumAnalysis(container);
}

// === CARGAR ÁLBUMES DEL ARTISTA ===
async function loadArtistAlbums(artistId) {
  const detailContent = document.getElementById("artistDetailContent");

  detailContent.innerHTML = `
        <div class="loading" style="text-align: center; padding: 20px;">
            <i class="fas fa-spinner fa-spin"></i>
            <p>Cargando álbumes...</p>
        </div>
    `;

  try {
    const response = await fetch(`/api/artists/${artistId}/albums`);
    const data = await response.json();

    if (data.error) {
      throw new Error(data.error);
    }

    const albums = data.albums || [];

    detailContent.innerHTML = `
            <div style="background: rgba(255,255,255,0.05); border-radius: 10px; padding: 20px; margin: 20px 0;">
                <h4 style="color: #a8e6cf; margin-bottom: 20px;">
                    <i class="fas fa-record-vinyl"></i> Álbumes (${albums.length})
                </h4>

                ${
                  albums.length === 0
                    ? '<p style="text-align: center; color: #999;">No se encontraron álbumes</p>'
                    : `<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px;">
                        ${albums
                          .map(
                            (album) => `
                            <div style="background: rgba(255,255,255,0.05); border-radius: 8px; padding: 15px; cursor: pointer; transition: background 0.3s;" onclick="selectAlbumFromArtist(${album.id}, '${album.name.replace(/'/g, "\\'")}')">
                                <h5 style="color: #a8e6cf; margin-bottom: 10px;">${album.name}</h5>
                                <div style="font-size: 0.9rem; color: #ccc;">
                                    <div><strong>Año:</strong> ${album.year || "Desconocido"}</div>
                                    <div><strong>Género:</strong> ${album.genre || "Desconocido"}</div>
                                    <div><strong>Sello:</strong> ${album.label || "Desconocido"}</div>
                                    <div><strong>Canciones:</strong> ${album.track_count || 0}</div>
                                </div>
                            </div>
                        `,
                          )
                          .join("")}
                    </div>`
                }
            </div>
        `;
  } catch (error) {
    console.error("Error cargando álbumes del artista:", error);
    detailContent.innerHTML = `
            <div style="background: rgba(255,107,107,0.1); border-radius: 10px; padding: 20px; margin: 20px 0;">
                <p style="color: #ff6b6b; text-align: center;">
                    <i class="fas fa-exclamation-triangle"></i>
                    Error cargando álbumes: ${error.message}
                </p>
            </div>
        `;
  }
}

// === SELECCIONAR ARTISTA ===

function selectArtist(artist) {
  console.log(`🎯 Seleccionando artista: ${artist.name} (ID: ${artist.id})`);

  currentArtistId = artist.id;

  // Actualizar input y ocultar dropdown
  const input = document.getElementById("artistSearchInput");
  const dropdown = document.getElementById("artistDropdown");

  if (input) input.value = artist.name;
  if (dropdown) dropdown.style.display = "none";

  // Ocultar mensaje inicial y mostrar contenido
  const initialMessage = document.getElementById("initialMessage");
  const selectedContent = document.getElementById("selectedArtistContent");

  if (initialMessage) {
    initialMessage.style.display = "none";
  }

  if (selectedContent) {
    selectedContent.style.display = "block";
    selectedContent.innerHTML = `
            <div style="text-align: center; padding: 20px; background: rgba(168,230,207,0.1); border-radius: 10px; margin: 20px 0;">
                <h3 style="color: #a8e6cf; margin-bottom: 10px;">
                    <i class="fas fa-user"></i> ${artist.name}
                </h3>
                <p>Artista seleccionado. Cargando análisis...</p>
                <div class="loading" style="margin-top: 15px;">
                    <i class="fas fa-spinner fa-spin"></i>
                </div>
            </div>
        `;
  }

  // Cargar análisis del artista
  setTimeout(() => {
    loadArtistAnalysis(artist.id);
  }, 500);
}

// === ANÁLISIS DE ARTISTAS ===

async function showArtistAnalysis(container) {
  console.log("🎯 Iniciando análisis de artistas...");

  container.innerHTML = `
        <div class="stats-section">
            <h2>Análisis Detallado de Artistas</h2>

            <!-- Selector de artistas -->
            <div style="background: rgba(255, 255, 255, 0.05); border-radius: 15px; padding: 20px; margin: 20px 0;">
                <h3 style="color: #a8e6cf; margin-bottom: 15px;">
                    <i class="fas fa-user"></i> Seleccionar Artista
                </h3>
                <div style="position: relative;">
                    <input type="text" id="artistSearchInput"
                        style="width: 100%; padding: 12px; border: 1px solid rgba(255,255,255,0.2); border-radius: 10px; background: rgba(255,255,255,0.1); color: white; outline: none; font-size: 16px;"
                        placeholder="Buscar artista..." autocomplete="off">
                    <div id="artistDropdown" style="display: none; position: absolute; top: 100%; left: 0; right: 0; background: rgba(42,82,152,0.95); border: 1px solid rgba(255,255,255,0.2); border-radius: 10px; max-height: 300px; overflow-y: auto; margin-top: 5px; z-index: 1000; backdrop-filter: blur(10px);"></div>
                </div>
            </div>

            <!-- Mensaje inicial -->
            <div id="initialMessage" style="text-align: center; padding: 40px; color: #a8e6cf;">
                <i class="fas fa-chart-line" style="font-size: 3rem; margin-bottom: 20px; display: block;"></i>
                <p>Selecciona un artista para ver su análisis detallado</p>
                <div class="loading" style="display: none;">
                    <i class="fas fa-spinner fa-spin"></i>
                    <p>Cargando artistas...</p>
                </div>
            </div>

            <!-- Contenido del artista seleccionado -->
            <div id="selectedArtistContent" style="display: none;">
                <!-- Se carga dinámicamente -->
            </div>
        </div>
    `;

  // Configurar eventos del buscador
  setupArtistSearchEvents();

  // Mostrar indicador de carga
  const initialMessage = document.getElementById("initialMessage");
  const loadingDiv = initialMessage.querySelector(".loading");
  loadingDiv.style.display = "block";

  console.log("✅ Vista de análisis de artistas configurada");
}

async function showArtistAnalysisTab(tabName) {
  if (!currentArtistId) {
    console.warn("❌ No hay artista seleccionado");
    return;
  }

  console.log(
    `📊 Cargando análisis: ${tabName} para artista ID ${currentArtistId}`,
  );

  // Actualizar pestañas activas en vista de artista - CORREGIDO
  if (currentView === "artist-detail") {
    document
      .querySelectorAll(".stats-tab:not(.back-tab)")
      .forEach((tab) => tab.classList.remove("active"));

    // Buscar y activar la pestaña correspondiente
    document.querySelectorAll(".stats-tab").forEach((tab) => {
      const onclickStr = tab.getAttribute("onclick") || "";
      if (onclickStr.includes(`'${tabName}'`)) {
        tab.classList.add("active");
      }
    });
  }

  // Buscar el contenedor correcto
  let content = document.getElementById("artistAnalysisContent");
  if (!content) {
    content = document.getElementById("selectedArtistContent");
  }

  if (!content) {
    console.error("❌ No se encontró contenedor para el análisis");
    return;
  }

  content.innerHTML =
    '<div class="loading"><i class="fas fa-spinner"></i><p>Cargando análisis...</p></div>';

  try {
    console.log(
      `🌐 Haciendo petición a: /api/artists/${currentArtistId}/analysis/${tabName}`,
    );
    const response = await fetch(
      `/api/artists/${currentArtistId}/analysis/${tabName}`,
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    console.log("📄 Respuesta del servidor:", data);

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
                    <i class="fas fa-chart-${tabName === "tiempo" ? "line" : tabName === "conciertos" ? "microphone" : "bar"}"></i>
                    Análisis de ${tabName.charAt(0).toUpperCase() + tabName.slice(1)}
                </h3>
        `;

    // Añadir estadísticas si existen
    if (data.stats && Object.keys(data.stats).length > 0) {
      html += '<div class="artist-stats-summary">';
      for (const [key, value] of Object.entries(data.stats)) {
        const displayKey = key
          .replace(/_/g, " ")
          .replace(/\b\w/g, (l) => l.toUpperCase());
        html += `
                    <div class="artist-stat-card">
                        <h5>${displayKey}</h5>
                        <p>${value}</p>
                    </div>
                `;
      }
      html += "</div>";
    }

    // Añadir gráficos si existen
    if (data.charts && Object.keys(data.charts).length > 0) {
      // Diferentes layouts según el tipo de análisis
      let gridStyle = "display: grid; gap: 20px; margin-top: 20px;";

      if (tabName === "conciertos") {
        // Conciertos: una columna (uno sobre otro)
        gridStyle += "grid-template-columns: 1fr;";
      } else if (tabName === "generos") {
        // Géneros: 2x2
        gridStyle += "grid-template-columns: repeat(2, 1fr);";
      } else if (tabName === "escuchas") {
        // Escuchas: una sola columna con 4 filas
        gridStyle += "grid-template-columns: 1fr;";
      } else if (tabName === "colaboradores") {
        // Colaboradores: 2x2
        gridStyle += "grid-template-columns: repeat(2, 1fr);";
      } else {
        // Por defecto: auto-fit
        gridStyle +=
          "grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));";
      }

      html += `<div style="${gridStyle}">`;

      Object.keys(data.charts).forEach((chartId) => {
        const chartTitle = chartId
          .replace(/_/g, " ")
          .replace(/\b\w/g, (l) => l.toUpperCase());
        html += `
                    <div style="background: rgba(255,255,255,0.05); border-radius: 10px; padding: 15px;">
                        <h4 style="color: #a8e6cf; text-align: center; margin-bottom: 10px;">${chartTitle}</h4>
                        <div id="chart-${chartId}" style="height: 350px;"></div>
                    </div>
                `;
      });

      html += "</div>";
    } else {
      html += `
                <div style="text-align: center; padding: 40px; color: #ccc;">
                    <i class="fas fa-chart-bar" style="font-size: 2rem; margin-bottom: 15px; display: block; opacity: 0.5;"></i>
                    <p>No hay gráficos disponibles para este análisis</p>
                </div>
            `;
    }

    html += "</div>";

    content.innerHTML = html;

    // Renderizar gráficos si existen
    if (data.charts && Object.keys(data.charts).length > 0) {
      console.log(
        `📊 Renderizando ${Object.keys(data.charts).length} gráficos...`,
      );

      Object.keys(data.charts).forEach((chartId) => {
        setTimeout(
          () => {
            try {
              const container = document.getElementById(`chart-${chartId}`);
              if (container && data.charts[chartId]) {
                console.log(`📈 Renderizando gráfico: ${chartId}`);

                const plotData =
                  typeof data.charts[chartId] === "string"
                    ? JSON.parse(data.charts[chartId])
                    : data.charts[chartId];

                if (window.Plotly && plotData.data && plotData.layout) {
                  Plotly.newPlot(
                    `chart-${chartId}`,
                    plotData.data,
                    plotData.layout,
                    {
                      responsive: true,
                      displayModeBar: false,
                    },
                  );
                  console.log(
                    `✅ Gráfico ${chartId} renderizado correctamente`,
                  );
                } else {
                  console.error(
                    `❌ Datos de gráfico inválidos para ${chartId}:`,
                    plotData,
                  );
                }
              }
            } catch (error) {
              console.error(`💥 Error renderizando gráfico ${chartId}:`, error);
              const container = document.getElementById(`chart-${chartId}`);
              if (container) {
                container.innerHTML =
                  '<div style="text-align: center; color: #ff6b6b; padding: 20px;">Error renderizando gráfico</div>';
              }
            }
          },
          100 * Object.keys(data.charts).indexOf(chartId),
        ); // Stagger chart rendering
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
