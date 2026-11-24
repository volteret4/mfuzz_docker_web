// === FUNCIONES DEL SISTEMA MOVIDAS DE sistema.html ===

// Variables globales del sistema
let systemOverview = null;
let currentArtistId = null;
let currentAlbumId = null;
let artistsList = [];
let currentView = "main"; // 'main', 'artist-detail', 'album-detail', 'scrobbles-detail'

// === CARGA DE DATOS DEL SISTEMA ===

async function loadSystemOverview() {
  try {
    console.log("🔄 Cargando resumen del sistema...");
    const response = await fetch("/api/stats/overview");
    const data = await response.json();

    if (data.error) {
      showError("Error cargando resumen del sistema: " + data.error);
      return;
    }

    systemOverview = data;
    renderSystemOverview(data);
    console.log("✅ Resumen del sistema cargado");
  } catch (error) {
    console.error("Error cargando estadísticas:", error);
    showError("Error cargando estadísticas del sistema");
  }
}

function renderSystemOverview(overview) {
  const overviewContainer = document.getElementById("system-overview");
  if (!overviewContainer) {
    console.warn("⚠️ Contenedor system-overview no encontrado");
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
  if (window.currentView === "main") {
    document
      .querySelectorAll(".stats-tab")
      .forEach((tab) => tab.classList.remove("active"));
    // Buscar la pestaña que corresponde a esta categoría
    document.querySelectorAll(".stats-tab").forEach((tab) => {
      const onclick = tab.getAttribute("onclick") || "";
      if (onclick.includes(`'${category}'`)) {
        tab.classList.add("active");
      }
    });
  }

  const statsContent = document.getElementById("stats-content");
  if (!statsContent) {
    console.error("❌ Contenedor stats-content no encontrado");
    return;
  }

  // NUEVO: Manejar "análisis detallado" como submenú
  if (category === "detailed-analysis") {
    showDetailedAnalysisMenu();
    return;
  }

  // MODIFICADO: Manejar análisis de álbumes como tab interno
  if (category === "album-analysis") {
    await showAlbumAnalysis(statsContent);
    return;
  }

  // NUEVO: Manejar análisis de artistas
  if (category === "artist-analysis") {
    await showArtistAnalysis(statsContent);
    return;
  }

  // NUEVO: Manejar análisis de scrobbles
  if (category === "scrobbles-analysis") {
    // Verificar si la función existe antes de llamarla
    if (typeof showScrobblesAnalysis === "function") {
      await showScrobblesAnalysis(statsContent);
    } else {
      console.error("❌ showScrobblesAnalysis no está disponible");
      statsContent.innerHTML = `
                <div class="error-message">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Módulo de análisis de scrobbles no disponible</p>
                </div>
            `;
    }
    return;
  }

  statsContent.innerHTML =
    '<div class="loading"><i class="fas fa-spinner"></i><p>Cargando estadísticas...</p></div>';

  try {
    if (category === "database") {
      await showDatabaseStats(statsContent);
    } else if (category === "missing") {
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
  const statsContent = document.getElementById("stats-content");

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

    let content = "";

    if (category === "artists") {
      content = renderArtistsStats(data);
    } else if (category === "albums") {
      content = renderAlbumsStats(data);
    } else if (category === "songs") {
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
                        ${data.by_country
                          .slice(0, 10)
                          .map(
                            (item) =>
                              `<tr><td>${item.origin}</td><td>${item.count.toLocaleString()}</td></tr>`,
                          )
                          .join("")}
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
  const lyricsPercentage = Math.round(
    (data.lyrics_stats?.with_lyrics / data.lyrics_stats?.total) * 100 || 0,
  );

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
    const response = await fetch("/api/stats/database");
    const data = await response.json();

    if (data.error) {
      container.innerHTML = `<div class="error-message">${data.error}</div>`;
      return;
    }

    let tablesHtml = "";
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
    console.error("Error cargando estadísticas de base de datos:", error);
    container.innerHTML = `<div class="error-message">Error cargando estadísticas de base de datos</div>`;
  }
}

async function showMissingDataStats(container) {
  try {
    const response = await fetch("/api/stats/missing-data");
    const data = await response.json();

    if (data.error) {
      container.innerHTML = `<div class="error-message">${data.error}</div>`;
      return;
    }

    let tablesHtml = "";
    for (const [tableName, tableStats] of Object.entries(data)) {
      for (const [fieldName, fieldStats] of Object.entries(
        tableStats.fields || {},
      )) {
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
    console.error("Error cargando análisis de datos faltantes:", error);
    container.innerHTML = `<div class="error-message">Error cargando análisis de datos faltantes</div>`;
  }
}

// === Estadisticas ===
function showStatisticsPage() {
  currentPage = "statistics";
  updateTabSelection("statistics");

  const container = document.getElementById("content");

  container.innerHTML = `
        <div class="stats-header">
            <h1>Estadísticas de tu Biblioteca Musical</h1>
            <p>Explora análisis detallados de tu colección</p>
        </div>

        <div class="stats-navigation">
            <button class="stats-tab active" onclick="showStatsOverview()">
                <i class="fas fa-home"></i> Resumen
            </button>
            <button class="stats-tab" onclick="showStatsCategory('artists')">
                <i class="fas fa-user"></i> Artistas
            </button>
            <button class="stats-tab" onclick="showStatsCategory('albums')">
                <i class="fas fa-record-vinyl"></i> Álbumes
            </button>
            <button class="stats-tab" onclick="showStatsCategory('songs')">
                <i class="fas fa-music"></i> Canciones
            </button>
            <button class="stats-tab" onclick="showStatsCategory('database')">
                <i class="fas fa-database"></i> Base de Datos
            </button>
            <button class="stats-tab" onclick="showStatsCategory('missing-data')">
                <i class="fas fa-exclamation-triangle"></i> Datos Faltantes
            </button>
            <button class="stats-tab" onclick="showStatsCategory('detailed')">
                <i class="fas fa-chart-line"></i> Datos Detallados
            </button>
        </div>

        <div id="statsContent">
            <div class="loading">
                <i class="fas fa-spinner"></i>
                <p>Cargando estadísticas...</p>
            </div>
        </div>
    `;

  // Cargar resumen inicial
  showStatsOverview();
}

// Función principal para mostrar categorías de estadísticas
async function showStatsCategory(category) {
  console.log(`📊 Mostrando categoría: ${category}`);

  // Actualizar pestañas activas
  document
    .querySelectorAll(".stats-tab")
    .forEach((tab) => tab.classList.remove("active"));
  event.target.classList.add("active");

  const container = document.getElementById("statsContent");

  // Mostrar loading
  container.innerHTML = `
        <div class="loading">
            <i class="fas fa-spinner fa-spin"></i>
            <p>Cargando ${category}...</p>
        </div>
    `;

  try {
    switch (category) {
      case "artists":
        // AQUÍ SE CONECTA CON EL NUEVO SISTEMA
        await handleArtistsStatsClick(container);
        break;

      case "albums":
        // AQUÍ SE CONECTA CON EL NUEVO SISTEMA
        await handleAlbumsStatsClick(container);
        break;

      case "songs":
        await showSongsStats(container);
        break;

      case "database":
        await showDatabaseStats(container);
        break;

      case "missing-data":
        await showMissingDataStats(container);
        break;

      case "detailed":
        await showDetailedStats(container);
        break;

      default:
        container.innerHTML = `
                    <div class="error-message">
                        <i class="fas fa-exclamation-triangle"></i>
                        <p>Categoría no reconocida: ${category}</p>
                    </div>
                `;
    }
  } catch (error) {
    console.error(`Error cargando estadísticas de ${category}:`, error);
    container.innerHTML = `
            <div class="error-message">
                <i class="fas fa-exclamation-triangle"></i>
                <p>Error cargando estadísticas de ${category}</p>
                <p><small>${error.message}</small></p>
                <button onclick="showStatsCategory('${category}')" style="margin-top: 10px; background: #2a5298; color: white; border: none; padding: 8px 15px; border-radius: 8px; cursor: pointer;">
                    🔄 Reintentar
                </button>
            </div>
        `;
  }
}

// Función para mostrar resumen general
async function showStatsOverview() {
  console.log("📊 Mostrando resumen de estadísticas");

  const container = document.getElementById("statsContent");

  // Actualizar pestaña activa
  document
    .querySelectorAll(".stats-tab")
    .forEach((tab) => tab.classList.remove("active"));
  document
    .querySelector('.stats-tab[onclick="showStatsOverview()"]')
    .classList.add("active");

  try {
    const response = await fetch("/api/stats/overview");

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();

    container.innerHTML = `
            <div class="stats-overview">
                <h2>Resumen General</h2>

                <div class="system-overview">
                    <div class="system-card">
                        <h3><i class="fas fa-user"></i> Artistas</h3>
                        <div class="value">${(data.content?.total_artists || 0).toLocaleString()}</div>
                        <div class="label">Total en la biblioteca</div>
                    </div>

                    <div class="system-card">
                        <h3><i class="fas fa-record-vinyl"></i> Álbumes</h3>
                        <div class="value">${(data.content?.total_albums || 0).toLocaleString()}</div>
                        <div class="label">Total en la biblioteca</div>
                    </div>

                    <div class="system-card">
                        <h3><i class="fas fa-music"></i> Canciones</h3>
                        <div class="value">${(data.content?.total_songs || 0).toLocaleString()}</div>
                        <div class="label">Total en la biblioteca</div>
                    </div>

                    <div class="system-card">
                        <h3><i class="fas fa-database"></i> Base de Datos</h3>
                        <div class="value">${data.database?.size_mb || 0} MB</div>
                        <div class="label">Tamaño total</div>
                    </div>
                </div>

                <div style="background: rgba(255,255,255,0.05); border-radius: 15px; padding: 20px; margin: 20px 0;">
                    <h3 style="color: #a8e6cf; margin-bottom: 15px;">Explorar Estadísticas</h3>
                    <p>Usa los botones de arriba para explorar análisis detallados de:</p>
                    <ul style="margin: 15px 0; padding-left: 20px;">
                        <li><strong>Artistas:</strong> Busca y analiza cualquier artista de tu biblioteca</li>
                        <li><strong>Álbumes:</strong> Explora estadísticas detalladas de álbumes específicos</li>
                        <li><strong>Canciones:</strong> Análisis general de tus canciones</li>
                        <li><strong>Base de Datos:</strong> Información técnica de tu biblioteca</li>
                        <li><strong>Datos Faltantes:</strong> Identifica información incompleta</li>
                        <li><strong>Datos Detallados:</strong> Análisis avanzados y reportes</li>
                    </ul>
                </div>
            </div>
        `;
  } catch (error) {
    console.error("Error cargando resumen de estadísticas:", error);
    container.innerHTML = `
            <div class="error-message">
                <i class="fas fa-exclamation-triangle"></i>
                <p>Error cargando resumen de estadísticas</p>
                <p><small>${error.message}</small></p>
                <button onclick="showStatsOverview()" style="margin-top: 10px; background: #2a5298; color: white; border: none; padding: 8px 15px; border-radius: 8px; cursor: pointer;">
                    🔄 Reintentar
                </button>
            </div>
        `;
  }
}

// Funciones para las otras categorías (puedes mantener las existentes o crear nuevas)
async function showSongsStats(container) {
  try {
    const response = await fetch("/api/stats/songs");
    const data = await response.json();
    container.innerHTML = renderSongsStats(data);
    // Llamar a funciones de gráficos si las tienes
    // createSongsCharts(data);
  } catch (error) {
    console.error("Error cargando estadísticas de canciones:", error);
    container.innerHTML =
      '<div class="error-message">Error cargando estadísticas de canciones</div>';
  }
}

async function showDatabaseStats(container) {
  try {
    const response = await fetch("/api/stats/database");
    const data = await response.json();
    container.innerHTML = renderDatabaseStats(data);
  } catch (error) {
    console.error("Error cargando estadísticas de base de datos:", error);
    container.innerHTML =
      '<div class="error-message">Error cargando estadísticas de base de datos</div>';
    1;
  }
}

async function showMissingDataStats(container) {
  try {
    const response = await fetch("/api/stats/missing-data");
    const data = await response.json();
    container.innerHTML = renderMissingDataStats(data);
  } catch (error) {
    console.error("Error cargando análisis de datos faltantes:", error);
    container.innerHTML =
      '<div class="error-message">Error cargando análisis de datos faltantes</div>';
  }
}

async function showDetailedStats(container) {
  container.innerHTML = `
        <div class="stats-section">
            <h2>Análisis Detallados</h2>
            <p>Funcionalidad en desarrollo - análisis avanzados y reportes personalizados</p>
        </div>
    `;
}

// Funciones de renderizado (si no las tienes ya)
function renderSongsStats(data) {
  const lyricsPercentage = Math.round(
    (data.lyrics_stats?.with_lyrics / data.lyrics_stats?.total) * 100 || 0,
  );

  return `
        <div class="stats-section">
            <h2>Estadísticas de Canciones</h2>

            <div class="system-overview">
                <div class="system-card">
                    <h3>Total de Canciones</h3>
                    <div class="value">${(data.total_songs || 0).toLocaleString()}</div>
                    <div class="label">En tu biblioteca</div>
                </div>

                <div class="system-card">
                    <h3>Con Letras</h3>
                    <div class="value">${lyricsPercentage}%</div>
                    <div class="label">${(data.lyrics_stats?.with_lyrics || 0).toLocaleString()} canciones</div>
                </div>

                <div class="system-card">
                    <h3>Duración Total</h3>
                    <div class="value">${Math.round((data.total_duration || 0) / 3600)} hrs</div>
                    <div class="label">Tiempo de reproducción</div>
                </div>
            </div>

            <div class="chart-container">
                <h3>Canciones por Género</h3>
                <div id="chart-songs-genres" style="height: 400px;"></div>
            </div>
        </div>
    `;
}

function renderDatabaseStats(data) {
  return `
        <div class="stats-section">
            <h2>Información de Base de Datos</h2>

            <div class="system-overview">
                <div class="system-card">
                    <h3>Tamaño</h3>
                    <div class="value">${data.size_mb || 0} MB</div>
                    <div class="label">Espacio ocupado</div>
                </div>

                <div class="system-card">
                    <h3>Tablas</h3>
                    <div class="value">${Object.keys(data.tables || {}).length}</div>
                    <div class="label">Total en la base</div>
                </div>

                <div class="system-card">
                    <h3>Última Actualización</h3>
                    <div class="value">${data.last_updated || "N/A"}</div>
                    <div class="label">Modificación</div>
                </div>
            </div>

            <div style="background: rgba(255,255,255,0.05); border-radius: 15px; padding: 20px; margin: 20px 0;">
                <h3 style="color: #a8e6cf; margin-bottom: 15px;">Detalle de Tablas</h3>
                <div style="display: grid; gap: 10px;">
                    ${Object.entries(data.tables || {})
                      .map(
                        ([table, info]) => `
                        <div style="background: rgba(255,255,255,0.05); border-radius: 8px; padding: 15px; display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong>${table}</strong>
                                <div style="font-size: 0.9rem; color: #ccc;">${info.columns || 0} columnas</div>
                            </div>
                            <div style="text-align: right; color: #a8e6cf;">
                                <strong>${(info.count || 0).toLocaleString()}</strong>
                                <div style="font-size: 0.9rem;">registros</div>
                            </div>
                        </div>
                    `,
                      )
                      .join("")}
                </div>
            </div>
        </div>
    `;
}

function renderMissingDataStats(data) {
  return `
        <div class="stats-section">
            <h2>Análisis de Datos Faltantes</h2>

            <div class="system-overview">
                <div class="system-card">
                    <h3>Artistas sin País</h3>
                    <div class="value">${(data.artists?.missing_origin || 0).toLocaleString()}</div>
                    <div class="label">De ${(data.artists?.total || 0).toLocaleString()} total</div>
                </div>

                <div class="system-card">
                    <h3>Álbumes sin Año</h3>
                    <div class="value">${(data.albums?.missing_year || 0).toLocaleString()}</div>
                    <div class="label">De ${(data.albums?.total || 0).toLocaleString()} total</div>
                </div>

                <div class="system-card">
                    <h3>Canciones sin Género</h3>
                    <div class="value">${(data.songs?.missing_genre || 0).toLocaleString()}</div>
                    <div class="label">De ${(data.songs?.total || 0).toLocaleString()} total</div>
                </div>
            </div>

            <div style="background: rgba(255,255,255,0.05); border-radius: 15px; padding: 20px; margin: 20px 0;">
                <h3 style="color: #a8e6cf; margin-bottom: 15px;">Recomendaciones de Limpieza</h3>
                <ul style="margin: 15px 0; padding-left: 20px; line-height: 1.6;">
                    <li>Completa información de país para ${(data.artists?.missing_origin || 0).toLocaleString()} artistas</li>
                    <li>Añade años de lanzamiento para ${(data.albums?.missing_year || 0).toLocaleString()} álbumes</li>
                    <li>Clasifica géneros para ${(data.songs?.missing_genre || 0).toLocaleString()} canciones</li>
                    <li>Revisa sellos discográficos faltantes en ${(data.albums?.missing_label || 0).toLocaleString()} álbumes</li>
                </ul>
            </div>
        </div>
    `;
}

// === FUNCIONES DE UTILIDAD ===

function getCompletenessClass(percentage) {
  if (percentage >= 80) return "completeness-excellent";
  if (percentage >= 60) return "completeness-good";
  return "completeness-poor";
}

function showError(message) {
  console.error("❌ Error:", message);
  const overviewContainer = document.getElementById("system-overview");
  if (overviewContainer) {
    overviewContainer.innerHTML = `<div class="error-message">${message}</div>`;
  }

  // También mostrar en el contenido principal si existe
  const statsContent = document.getElementById("stats-content");
  if (statsContent) {
    statsContent.innerHTML = `<div class="error-message">${message}</div>`;
  }
}

// === INICIALIZACIÓN ===

// Función de inicialización que se llama desde sistema.html
function initializeSistema() {
  console.log("🚀 Iniciando Sistema - Music Web Explorer");
  loadSystemOverview();
  showStatsCategory("artists");
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
