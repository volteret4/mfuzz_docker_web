#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from flask import render_template_string

logger = logging.getLogger(__name__)

class TemplateRoutes:
    """Maneja las rutas de templates HTML embebidos"""
    
    def __init__(self, app, config):
        self.app = app
        self.config = config
        self.setup_template_routes()
    
    def setup_template_routes(self):
        """Configura las rutas de templates"""
        
        @self.app.route('/album_analysis.html')
        def album_analysis():
            """Página de análisis de álbumes"""
            try:
                # Cargar el template embebido
                return render_template_string(self.get_album_analysis_template())
            except Exception as e:
                logger.error(f"Error renderizando album_analysis.html: {e}")
                return self._get_error_template('Análisis de Álbumes', str(e)), 500
    
    def get_album_analysis_template(self):
        """Template HTML para análisis de álbumes"""
        return '''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Análisis de Álbumes - Music Web Explorer</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/plotly.js/2.26.0/plotly.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72, #2a5298);
            color: #fff;
            min-height: 100vh;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }

        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #fff, #a8e6cf);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .back-button {
            position: absolute;
            top: 20px;
            left: 20px;
            background: rgba(255, 255, 255, 0.1);
            border: none;
            color: white;
            padding: 10px 15px;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }

        .back-button:hover {
            background: rgba(255, 255, 255, 0.2);
            transform: translateX(-3px);
        }

        /* Estilos del buscador de álbumes */
        .album-search-container {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 20px;
            margin: 20px 0;
            backdrop-filter: blur(5px);
        }

        .album-search-container h3 {
            color: #a8e6cf;
            margin-bottom: 15px;
            font-size: 1.2rem;
        }

        .album-search-wrapper {
            position: relative;
            width: 100%;
        }

        .album-search-input {
            width: 100%;
            padding: 12px;
            font-size: 1rem;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.1);
            color: white;
            outline: none;
        }

        .album-search-input::placeholder {
            color: rgba(255, 255, 255, 0.6);
        }

        .album-search-dropdown {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: rgba(42, 82, 152, 0.95);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            max-height: 300px;
            overflow-y: auto;
            z-index: 1000;
            backdrop-filter: blur(10px);
            margin-top: 5px;
        }

        .album-search-item {
            padding: 12px 15px;
            cursor: pointer;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            transition: background 0.3s ease;
        }

        .album-search-item:hover {
            background: rgba(168, 230, 207, 0.2);
        }

        .album-search-item .album-display-name {
            font-weight: bold;
            margin-bottom: 5px;
        }

        .album-search-item .album-details {
            font-size: 0.85rem;
            color: #a8e6cf;
        }

        /* Pestañas principales */
        .main-tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
            justify-content: center;
        }

        .main-tab {
            background: rgba(255, 255, 255, 0.1);
            border: none;
            padding: 10px 20px;
            border-radius: 20px;
            color: white;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 0.9rem;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .main-tab:hover {
            background: rgba(255, 255, 255, 0.2);
            transform: translateY(-1px);
        }

        .main-tab.active {
            background: #2a5298;
            transform: translateY(-1px);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        }

        .main-tab.back-tab {
            background: rgba(168, 230, 207, 0.2);
            border: 1px solid rgba(168, 230, 207, 0.4);
        }

        .main-tab.back-tab:hover {
            background: rgba(168, 230, 207, 0.3);
            transform: translateX(-3px) translateY(-1px);
        }

        /* Contenedor principal */
        .main-content {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 20px;
            padding: 30px;
            backdrop-filter: blur(10px);
            min-height: 400px;
        }

        .loading {
            text-align: center;
            padding: 40px;
            font-size: 1.2rem;
            color: #a8e6cf;
        }

        .loading i {
            font-size: 2rem;
            animation: spin 1s linear infinite;
            margin-bottom: 10px;
            display: block;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .error-message {
            background: rgba(220, 53, 69, 0.2);
            color: #ff6b6b;
            padding: 15px;
            border-radius: 10px;
            margin: 20px 0;
            text-align: center;
        }

        /* Información del álbum seleccionado */
        .selected-album-info {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 20px;
            margin: 20px 0;
            display: none;
        }

        .album-header {
            display: flex;
            align-items: center;
            gap: 20px;
            margin-bottom: 20px;
        }

        .album-cover {
            width: 100px;
            height: 100px;
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.1);
            overflow: hidden;
        }

        .album-cover img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .album-details h3 {
            color: #a8e6cf;
            margin-bottom: 10px;
            font-size: 1.5rem;
        }

        .album-details p {
            margin: 5px 0;
            color: #ccc;
        }

        /* Pestañas de análisis específico */
        .analysis-tabs {
            display: flex;
            gap: 8px;
            margin: 20px 0;
            flex-wrap: wrap;
            justify-content: center;
        }

        .analysis-tab {
            background: rgba(255, 255, 255, 0.1);
            border: none;
            padding: 8px 15px;
            border-radius: 20px;
            color: white;
            cursor: pointer;
            font-size: 0.85rem;
            transition: all 0.3s ease;
            backdrop-filter: blur(5px);
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .analysis-tab:hover {
            background: rgba(255, 255, 255, 0.2);
            transform: translateY(-1px);
        }

        .analysis-tab.active {
            background: #2a5298;
            transform: translateY(-1px);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        }

        /* Contenido del análisis */
        .analysis-content {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(5px);
            min-height: 400px;
        }

        .analysis-charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }

        .analysis-chart-container {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 15px;
            backdrop-filter: blur(5px);
        }

        .analysis-chart-container h4 {
            color: #a8e6cf;
            margin-bottom: 10px;
            font-size: 1rem;
            text-align: center;
        }

        /* Estadísticas del análisis */
        .analysis-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }

        .analysis-stat-card {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 15px;
            text-align: center;
            backdrop-filter: blur(5px);
        }

        .analysis-stat-card h5 {
            color: #a8e6cf;
            margin-bottom: 8px;
            font-size: 0.85rem;
            text-transform: uppercase;
        }

        .analysis-stat-card p {
            color: white;
            font-size: 1.2rem;
            font-weight: bold;
            margin: 0;
        }

        /* Mensaje inicial */
        .initial-message {
            text-align: center;
            padding: 40px;
            color: #a8e6cf;
        }

        .initial-message i {
            font-size: 3rem;
            margin-bottom: 20px;
            display: block;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }

            .header h1 {
                font-size: 2rem;
            }

            .main-tabs, .analysis-tabs {
                gap: 6px;
            }

            .main-tab, .analysis-tab {
                padding: 6px 10px;
                font-size: 0.8rem;
            }

            .analysis-charts-grid {
                grid-template-columns: 1fr;
                gap: 15px;
            }

            .album-header {
                flex-direction: column;
                text-align: center;
            }
        }
    </style>
</head>
<body>
    <a href="/" class="back-button">
        <i class="fas fa-arrow-left"></i> Volver al Inicio
    </a>

    <div class="container">
        <div class="header">
            <h1><i class="fas fa-compact-disc"></i> Análisis de Álbumes</h1>
            <p>Análisis detallado y visualizaciones para álbumes musicales</p>
        </div>

        <!-- Pestañas principales -->
        <div class="main-tabs" id="main-tabs">
            <button class="main-tab active" onclick="showMainSection('search')">
                <i class="fas fa-search"></i> Buscar Álbum
            </button>
        </div>

        <!-- Contenido principal -->
        <div class="main-content">
            <div id="content">
                <!-- Sección de búsqueda de álbumes -->
                <div id="search-section">
                    <div class="album-search-container">
                        <h3>Buscar Álbum para Analizar</h3>
                        <div class="album-search-wrapper">
                            <input type="text" id="albumSearchInput" class="album-search-input"
                                   placeholder="Buscar por artista o álbum (ej: 'Pink Floyd' o 'Pink Floyd - Dark Side')" 
                                   autocomplete="off">
                            <div id="albumDropdown" style="display: none;" class="album-search-dropdown"></div>
                        </div>
                    </div>
                    
                    <div class="initial-message">
                        <i class="fas fa-compact-disc"></i>
                        <p>Busca un álbum para ver su análisis detallado</p>
                        <p><small>Escribe el nombre del artista o álbum para comenzar</small></p>
                    </div>
                </div>

                <!-- Información del álbum seleccionado -->
                <div id="selected-album-info" class="selected-album-info">
                    <div class="album-header">
                        <div class="album-cover">
                            <img id="album-cover-img" src="" alt="Carátula del álbum">
                        </div>
                        <div class="album-details">
                            <h3 id="album-title">Nombre del Álbum</h3>
                            <p><strong>Artista:</strong> <span id="album-artist">Nombre del Artista</span></p>
                            <p><strong>Año:</strong> <span id="album-year">Año</span></p>
                            <p><strong>Género:</strong> <span id="album-genre">Género</span></p>
                            <p><strong>Sello:</strong> <span id="album-label">Sello</span></p>
                        </div>
                    </div>

                    <!-- Pestañas de análisis específico -->
                    <div class="analysis-tabs" id="analysis-tabs">
                        <button class="analysis-tab active" onclick="showAnalysisTab('tiempo')">
                            <i class="fas fa-clock"></i> Tiempo
                        </button>
                        <button class="analysis-tab" onclick="showAnalysisTab('genero')">
                            <i class="fas fa-music"></i> Género
                        </button>
                        <button class="analysis-tab" onclick="showAnalysisTab('conciertos')">
                            <i class="fas fa-microphone"></i> Conciertos
                        </button>
                        <button class="analysis-tab" onclick="showAnalysisTab('sellos')">
                            <i class="fas fa-record-vinyl"></i> Sellos
                        </button>
                        <button class="analysis-tab" onclick="showAnalysisTab('discografia')">
                            <i class="fas fa-compact-disc"></i> Discografía
                        </button>
                        <button class="analysis-tab" onclick="showAnalysisTab('escuchas')">
                            <i class="fas fa-headphones"></i> Escuchas
                        </button>
                        <button class="analysis-tab" onclick="showAnalysisTab('colaboradores')">
                            <i class="fas fa-users"></i> Colaboradores
                        </button>
                        <button class="analysis-tab" onclick="showAnalysisTab('feeds')">
                            <i class="fas fa-rss"></i> Feeds
                        </button>
                        <button class="analysis-tab" onclick="showAnalysisTab('letras')">
                            <i class="fas fa-quote-right"></i> Letras
                        </button>
                    </div>

                    <!-- Contenido del análisis -->
                    <div class="analysis-content" id="analysis-content">
                        <div class="loading">
                            <i class="fas fa-spinner"></i>
                            <p>Preparando análisis...</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Variables globales
        let currentAlbumId = null;
        let currentView = 'search';

        // Inicializar al cargar la página
        document.addEventListener('DOMContentLoaded', function() {
            setupAlbumSearchEvents();
            showMainSection('search');
        });

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
                filterAlbums(searchTerm);
            });
            
            input.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    const searchTerm = e.target.value.trim();
                    console.log(`⏎ Enter presionado con: "${searchTerm}"`);
                    
                    if (searchTerm.length >= 2) {
                        searchFirstMatch(searchTerm);
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
        async function searchFirstMatch(searchTerm) {
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
                console.error('Error buscando primera coincidencia:', error);
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
            
            showAlbumInfo(album);
            switchToAlbumDetailTabs();
            
            setTimeout(() => {
                showAlbumAnalysisTab('tiempo');
            }, 100);
        }

        // Mostrar información del álbum
        function showAlbumInfo(album) {
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
                        <p style="margin-top: 15px;">Álbum seleccionado. Las pestañas han cambiado para mostrar análisis detallados.</p>
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


        // Cambiar a pestañas de análisis
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

        // Volver a la búsqueda
        function returnToSearch() {
            const tabsContainer = document.getElementById('main-tabs');
            tabsContainer.innerHTML = `
                <button class="main-tab active" onclick="showMainSection('search')">
                    <i class="fas fa-search"></i> Buscar Álbum
                </button>
            `;
            
            
            const albumInfo = document.getElementById('selected-album-info');
            const searchSection = document.getElementById('search-section');
            
            if (albumInfo && searchSection) {
                albumInfo.style.display = 'none';
                searchSection.style.display = 'block';
            }
            
            const input = document.getElementById('albumSearchInput');
            if (input) {
                input.value = '';
            }
        }

        // Mostrar sección principal
        function showMainSection(section) {
            console.log(`Mostrando sección: ${section}`);
        }

        // Mostrar pestaña de análisis
        async function showAnalysisTab(tabName) {
            if (!currentAlbumId) {
                console.warn('❌ No hay álbum seleccionado');
                return;
            }
            
            console.log(`📊 Cargando análisis: ${tabName} para álbum ID ${currentAlbumId}`);
            
            document.querySelectorAll('.analysis-tab').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.analysis-tab').forEach(tab => {
                const onclickStr = tab.getAttribute('onclick') || '';
                if (onclickStr.includes(`'${tabName}'`)) {
                    tab.classList.add('active');
                }
            });
            
            const content = document.getElementById('analysis-content');
            if (!content) {
                console.error('❌ No se encontró contenedor para el análisis');
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
                
                renderAnalysisContent(tabName, data, content);
                
            } catch (error) {
                console.error(`💥 Error cargando análisis ${tabName}:`, error);
                content.innerHTML = `
                    <div class="error-message">
                        <i class="fas fa-exclamation-triangle"></i>
                        <p><strong>Error de conexión:</strong> ${error.message}</p>
                        <button class="main-tab" onclick="showAnalysisTab('${tabName}')" style="margin-top: 10px; background: #2a5298; color: white; border: none; padding: 8px 15px; border-radius: 8px; cursor: pointer;">
                            <i class="fas fa-redo"></i> Reintentar
                        </button>
                    </div>
                `;
            }
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
            
            if (data.stats && Object.keys(data.stats).length > 0) {
                html += '<div class="analysis-stats">';
                for (const [key, value] of Object.entries(data.stats)) {
                    const displayKey = key.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase());
                    html += `
                        <div class="analysis-stat-card">
                            <h5>${displayKey}</h5>
                            <p>${value}</p>
                        </div>
                    `;
                }
                html += '</div>';
            }
            
            if (data.charts && Object.keys(data.charts).length > 0) {
                html += '<div class="analysis-charts-grid">';
                
                Object.keys(data.charts).forEach(chartId => {
                    const chartTitle = chartId.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase());
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
            
            // Información adicional específica
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
            
            // Renderizar gráficos
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

    </script>
</body>
</html>'''
    
    def _get_error_template(self, page_title, error_msg):
        """Template de error genérico"""
        return f'''
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <title>{page_title} - Music Web Explorer</title>
            <style>body {{ font-family: Arial, sans-serif; margin: 20px; }}</style>
        </head>
        <body>
            <h1>{page_title} - Music Web Explorer</h1>
            <p>Error cargando la página: {error_msg}</p>
            <p><a href="/">← Volver al inicio</a></p>
        </body>
        </html>
        '''