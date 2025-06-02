#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import logging
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
import os



# Importaciones opcionales para gráficos
try:
    import plotly.graph_objects as go
    import plotly.express as px
    import pandas as pd
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    logging.warning("Plotly no disponible - los gráficos no estarán disponibles")

logger = logging.getLogger(__name__)

class StatsManager:
    """Manager principal para estadísticas de la base de datos musical"""
    
    def __init__(self, db_path: str, config: dict = None):
        self.db_path = db_path
        self.config = config or {}
        self.conn = None
        self.init_connection()
    
    def init_connection(self):
        """Inicializa la conexión a la base de datos"""
        try:
            if os.path.exists(self.db_path):
                self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
                self.conn.row_factory = sqlite3.Row
                logger.info(f"Conexión a BD establecida: {self.db_path}")
            else:
                logger.error(f"Base de datos no encontrada: {self.db_path}")
        except Exception as e:
            logger.error(f"Error conectando a BD: {e}")
            
    def get_connection(self):
        """Obtiene conexión a la BD con reconexión automática"""
        if not self.conn:
            self.init_connection()
        return self.conn
    
    def execute_query(self, query: str, params: tuple = None) -> List[sqlite3.Row]:
        """Ejecuta una consulta de forma segura"""
        try:
            conn = self.get_connection()
            if not conn:
                return []
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error ejecutando consulta: {e}")
            return []
    
    def get_database_info(self) -> Dict[str, Any]:
        """Obtiene información general de la base de datos"""
        try:
            # Obtener lista de tablas
            tables_query = """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """
            tables = self.execute_query(tables_query)
            
            db_info = {
                'tables': {},
                'total_tables': len(tables),
                'database_size': self._get_db_size(),
                'last_updated': datetime.now().isoformat()
            }
            
            # Para cada tabla, obtener información detallada
            for table_row in tables:
                table_name = table_row['name']
                
                # Contar registros
                count_query = f"SELECT COUNT(*) as count FROM {table_name}"
                count_result = self.execute_query(count_query)
                count = count_result[0]['count'] if count_result else 0
                
                # Obtener estructura
                structure_query = f"PRAGMA table_info({table_name})"
                columns = self.execute_query(structure_query)
                
                db_info['tables'][table_name] = {
                    'count': count,
                    'columns': len(columns),
                    'column_info': [{'name': col['name'], 'type': col['type']} for col in columns]
                }
            
            return db_info
            
        except Exception as e:
            logger.error(f"Error obteniendo info de BD: {e}")
            return {}
    
    def _get_db_size(self) -> int:
        """Obtiene el tamaño de la base de datos en bytes"""
        try:
            return os.path.getsize(self.db_path)
        except:
            return 0
    
    def get_artists_stats(self) -> Dict[str, Any]:
        """Estadísticas de artistas"""
        try:
            # Total de artistas
            total_query = "SELECT COUNT(*) as total FROM artists"
            total_result = self.execute_query(total_query)
            total_artists = total_result[0]['total'] if total_result else 0
            
            # Artistas por país
            country_query = """
                SELECT origin, COUNT(*) as count 
                FROM artists 
                WHERE origin IS NOT NULL AND origin != ''
                GROUP BY origin 
                ORDER BY count DESC 
                LIMIT 15
            """
            countries = self.execute_query(country_query)
            
            # Artistas con más álbumes
            albums_query = """
                SELECT ar.name, COUNT(al.id) as album_count
                FROM artists ar
                LEFT JOIN albums al ON ar.id = al.artist_id
                GROUP BY ar.id, ar.name
                ORDER BY album_count DESC
                LIMIT 15
            """
            top_artists = self.execute_query(albums_query)
            
            return {
                'total_artists': total_artists,
                'by_country': [dict(row) for row in countries],
                'top_artists': [dict(row) for row in top_artists]
            }
            
        except Exception as e:
            logger.error(f"Error en estadísticas de artistas: {e}")
            return {'total_artists': 0, 'by_country': [], 'top_artists': []}
    
    def get_albums_stats(self) -> Dict[str, Any]:
        """Estadísticas de álbumes"""
        try:
            # Total de álbumes
            total_query = "SELECT COUNT(*) as total FROM albums"
            total_result = self.execute_query(total_query)
            total_albums = total_result[0]['total'] if total_result else 0
            
            # Álbumes por década
            decades_query = """
                SELECT 
                    CASE 
                        WHEN year IS NULL OR year = '' THEN 'Desconocido'
                        WHEN CAST(year AS INTEGER) < 1950 THEN 'Pre-1950'
                        ELSE CAST(CAST(year AS INTEGER) / 10 * 10 AS TEXT) || 's'
                    END as decade,
                    COUNT(*) as count
                FROM albums
                WHERE year IS NOT NULL AND year != ''
                GROUP BY decade
                ORDER BY decade
            """
            decades = self.execute_query(decades_query)
            
            # Álbumes por género
            genres_query = """
                SELECT genre, COUNT(*) as count
                FROM albums
                WHERE genre IS NOT NULL AND genre != ''
                GROUP BY genre
                ORDER BY count DESC
                LIMIT 15
            """
            genres = self.execute_query(genres_query)
            
            # Sellos con más álbumes
            labels_query = """
                SELECT label, COUNT(*) as count
                FROM albums
                WHERE label IS NOT NULL AND label != ''
                GROUP BY label
                ORDER BY count DESC
                LIMIT 15
            """
            labels = self.execute_query(labels_query)
            
            return {
                'total_albums': total_albums,
                'by_decade': [dict(row) for row in decades],
                'by_genre': [dict(row) for row in genres],
                'by_label': [dict(row) for row in labels]
            }
            
        except Exception as e:
            logger.error(f"Error en estadísticas de álbumes: {e}")
            return {'total_albums': 0, 'by_decade': [], 'by_genre': [], 'by_label': []}
    
    def get_songs_stats(self) -> Dict[str, Any]:
        """Estadísticas de canciones"""
        try:
            # Total de canciones
            total_query = "SELECT COUNT(*) as total FROM songs"
            total_result = self.execute_query(total_query)
            total_songs = total_result[0]['total'] if total_result else 0
            
            # Canciones por género
            genres_query = """
                SELECT genre, COUNT(*) as count
                FROM songs
                WHERE genre IS NOT NULL AND genre != ''
                GROUP BY genre
                ORDER BY count DESC
                LIMIT 15
            """
            genres = self.execute_query(genres_query)
            
            # Duración total
            duration_query = """
                SELECT 
                    SUM(duration) as total_duration,
                    AVG(duration) as avg_duration,
                    MAX(duration) as max_duration,
                    MIN(duration) as min_duration
                FROM songs
                WHERE duration IS NOT NULL AND duration > 0
            """
            duration_result = self.execute_query(duration_query)
            duration_stats = dict(duration_result[0]) if duration_result else {}
            
            # Canciones con letras
            lyrics_query = """
                SELECT 
                    COUNT(CASE WHEN l.lyrics IS NOT NULL THEN 1 END) as with_lyrics,
                    COUNT(*) as total
                FROM songs s
                LEFT JOIN lyrics l ON s.lyrics_id = l.id
            """
            lyrics_result = self.execute_query(lyrics_query)
            lyrics_stats = dict(lyrics_result[0]) if lyrics_result else {}
            
            return {
                'total_songs': total_songs,
                'by_genre': [dict(row) for row in genres],
                'duration_stats': duration_stats,
                'lyrics_stats': lyrics_stats
            }
            
        except Exception as e:
            logger.error(f"Error en estadísticas de canciones: {e}")
            return {'total_songs': 0, 'by_genre': [], 'duration_stats': {}, 'lyrics_stats': {}}
    
    def get_missing_data_stats(self) -> Dict[str, Any]:
        """Analiza datos faltantes en la base de datos"""
        try:
            missing_data = {}
            
            # Analizar campos importantes de cada tabla
            tables_to_analyze = {
                'artists': ['bio', 'origin', 'formed_year', 'spotify_url', 'wikipedia_url'],
                'albums': ['year', 'genre', 'label', 'total_tracks'],
                'songs': ['genre', 'duration', 'track_number'],
                'lyrics': ['lyrics']
            }
            
            for table, fields in tables_to_analyze.items():
                # Total de registros en la tabla
                total_query = f"SELECT COUNT(*) as total FROM {table}"
                total_result = self.execute_query(total_query)
                total = total_result[0]['total'] if total_result else 0
                
                table_stats = {'total_records': total, 'fields': {}}
                
                for field in fields:
                    # Contar registros con datos
                    filled_query = f"""
                        SELECT COUNT(*) as filled 
                        FROM {table} 
                        WHERE {field} IS NOT NULL AND {field} != ''
                    """
                    filled_result = self.execute_query(filled_query)
                    filled = filled_result[0]['filled'] if filled_result else 0
                    
                    completeness = (filled / total * 100) if total > 0 else 0
                    table_stats['fields'][field] = {
                        'filled': filled,
                        'missing': total - filled,
                        'completeness': round(completeness, 2)
                    }
                
                missing_data[table] = table_stats
            
            return missing_data
            
        except Exception as e:
            logger.error(f"Error analizando datos faltantes: {e}")
            return {}
    
    def create_chart(self, chart_type: str, data: List[Dict], title: str = "", 
                 x_field: str = None, y_field: str = None) -> str:
        """Crea un gráfico interactivo usando Plotly - VERSION MEJORADA"""
        try:
            if not PLOTLY_AVAILABLE:
                return self._create_simple_chart_fallback(chart_type, data, title)
            
            if not data:
                return self._create_empty_chart(title)
            
            # Convertir a DataFrame para facilitar el manejo
            df = pd.DataFrame(data)
            
            if chart_type == 'pie':
                # Gráfico circular MEJORADO
                fig = px.pie(df, 
                        values=y_field or df.columns[1], 
                        names=x_field or df.columns[0],
                        title=title)
                
                # Configuración específica para gráficos circulares
                fig.update_traces(
                    textposition='inside',
                    textinfo='label+percent+value',
                    textfont_size=14,  # Texto más grande
                    marker=dict(line=dict(color='#000000', width=2)),
                    pull=[0.1 if i == 0 else 0 for i in range(len(data))]  # Destacar el primer sector
                )
                
                # Mejorar leyenda para gráficos circulares
                fig.update_layout(
                    legend=dict(
                        orientation="v",
                        yanchor="top",
                        y=1,
                        xanchor="left",
                        x=1.01,
                        font=dict(size=12)
                    )
                )
                
            elif chart_type == 'bar':
                # Gráfico de barras COMPLETAMENTE REDISEÑADO
                fig = px.bar(df, 
                        x=x_field or df.columns[0], 
                        y=y_field or df.columns[1],
                        title=title,
                        color_discrete_sequence=['#a8e6cf'])  # Color verde de tu tema
                
                # Configuración específica para barras
                fig.update_traces(
                    marker=dict(
                        line=dict(color='rgba(255,255,255,0.3)', width=1),
                        opacity=0.8
                    ),
                    texttemplate='%{y}',
                    textposition='outside',
                    textfont=dict(size=12, color='white')
                )
                
                # Rotar etiquetas del eje X si son largas
                fig.update_xaxes(
                    tickangle=45 if any(len(str(x)) > 10 for x in df.iloc[:, 0]) else 0,
                    tickfont=dict(size=11, color='white')
                )
                
                fig.update_yaxes(
                    tickfont=dict(size=11, color='white'),
                    gridcolor='rgba(255,255,255,0.2)'
                )
                
            elif chart_type == 'line':
                # Gráfico de líneas MEJORADO
                fig = px.line(df, 
                            x=x_field or df.columns[0], 
                            y=y_field or df.columns[1],
                            title=title,
                            markers=True)
                
                # Configuración específica para líneas
                fig.update_traces(
                    line=dict(color='#a8e6cf', width=3),
                    marker=dict(size=8, color='#2a5298', line=dict(width=2, color='white')),
                    textfont=dict(size=12, color='white')
                )
                
                fig.update_xaxes(
                    tickfont=dict(size=11, color='white'),
                    gridcolor='rgba(255,255,255,0.2)'
                )
                
                fig.update_yaxes(
                    tickfont=dict(size=11, color='white'),
                    gridcolor='rgba(255,255,255,0.2)'
                )
                
            elif chart_type == 'scatter':
                # Gráfico de dispersión MEJORADO
                fig = px.scatter(df, 
                            x=x_field or df.columns[0], 
                            y=y_field or df.columns[1],
                            title=title,
                            size_max=15)
                
                fig.update_traces(
                    marker=dict(
                        size=10,
                        color='#a8e6cf',
                        line=dict(width=2, color='white'),
                        opacity=0.8
                    )
                )
                
            else:
                return self._create_empty_chart(f"Tipo de gráfico no soportado: {chart_type}")
            
            # Configurar tema oscuro personalizado que coincida con tu webapp
            fig.update_layout(
                template='plotly_dark',
                plot_bgcolor='rgba(30, 60, 114, 0.1)',  # Fondo similar al de tu webapp
                paper_bgcolor='rgba(30, 60, 114, 0.05)',
                font=dict(
                    family="'Segoe UI', Tahoma, Geneva, Verdana, sans-serif", 
                    size=13,
                    color='white'
                ),
                title=dict(
                    font=dict(size=18, color='#a8e6cf'),  # Verde de tu tema
                    x=0.5,  # Centrar título
                    xanchor='center'
                ),
                showlegend=True,
                height=450,  # Un poco más alto
                margin=dict(l=60, r=60, t=80, b=60),
                # Añadir bordes y efectos
                shapes=[
                    dict(
                        type="rect",
                        xref="paper", yref="paper",
                        x0=0, y0=0, x1=1, y1=1,
                        line=dict(color="rgba(168, 230, 207, 0.3)", width=1)
                    )
                ]
            )
            
            # Configurar hover personalizado
            fig.update_traces(
                hovertemplate='<b>%{label}</b><br>Valor: %{value}<br><extra></extra>' if chart_type == 'pie' 
                            else '<b>%{x}</b><br>Valor: %{y}<br><extra></extra>',
            )
            
            # Convertir a JSON para el frontend
            return fig.to_json()
            
        except Exception as e:
            logger.error(f"Error creando gráfico: {e}")
            return self._create_empty_chart(f"Error: {str(e)}")
    
    def _create_simple_chart_fallback(self, chart_type: str, data: List[Dict], title: str) -> str:
        """Fallback simple cuando Plotly no está disponible"""
        # Crear un gráfico básico usando solo datos JSON
        fallback_data = {
            "data": data[:10],  # Limitar a 10 elementos
            "layout": {
                "title": title,
                "type": chart_type
            }
        }
        return json.dumps(fallback_data)
    

    def _create_empty_chart(self, message: str) -> str:
        """Crea un gráfico vacío con mensaje - VERSION MEJORADA"""
        if PLOTLY_AVAILABLE:
            fig = go.Figure()
            fig.add_annotation(
                text=message,
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=18, color='#a8e6cf')  # Texto más grande y en verde
            )
            fig.update_layout(
                template='plotly_dark',
                plot_bgcolor='rgba(30, 60, 114, 0.1)',
                paper_bgcolor='rgba(30, 60, 114, 0.05)',
                height=450,
                showlegend=False,
                font=dict(color='white')
            )
            return fig.to_json()
        else:
            return json.dumps({
                "data": [],
                "layout": {"title": message}
            })
    

    def get_chart_data_for_frontend(self, chart_type: str, category: str) -> Dict[str, Any]:
        """Prepara datos de gráficos específicos para el frontend - VERSION MEJORADA"""
        try:
            if category == 'artists':
                stats = self.get_artists_stats()
                if chart_type == 'countries':
                    # Limitar a top 8 países para mejor visualización
                    top_countries = stats['by_country'][:8]
                    return {
                        'chart': self.create_chart('pie', top_countries, 
                                                'Artistas por País (Top 8)', 'origin', 'count'),
                        'data': stats['by_country']
                    }
                elif chart_type == 'top':
                    # Limitar a top 12 artistas para mejor visualización
                    top_artists = stats['top_artists'][:12]
                    return {
                        'chart': self.create_chart('bar', top_artists, 
                                                'Top 12 Artistas por Álbumes', 'name', 'album_count'),
                        'data': stats['top_artists']
                    }
                    
            elif category == 'albums':
                stats = self.get_albums_stats()
                if chart_type == 'decades':
                    return {
                        'chart': self.create_chart('bar', stats['by_decade'], 
                                                'Álbumes por Década', 'decade', 'count'),
                        'data': stats['by_decade']
                    }
                elif chart_type == 'genres':
                    # Limitar a top 10 géneros para gráfico circular
                    top_genres = stats['by_genre'][:10]
                    return {
                        'chart': self.create_chart('pie', top_genres, 
                                                'Álbumes por Género (Top 10)', 'genre', 'count'),
                        'data': stats['by_genre']
                    }
                elif chart_type == 'labels':
                    # Limitar a top 12 sellos para mejor visualización
                    top_labels = stats['by_label'][:12]
                    return {
                        'chart': self.create_chart('bar', top_labels, 
                                                'Top 12 Sellos Discográficos', 'label', 'count'),
                        'data': stats['by_label']
                    }
                    
            elif category == 'songs':
                stats = self.get_songs_stats()
                if chart_type == 'genres':
                    # Limitar a top 10 géneros para gráfico circular
                    top_genres = stats['by_genre'][:10]
                    return {
                        'chart': self.create_chart('pie', top_genres, 
                                                'Canciones por Género (Top 10)', 'genre', 'count'),
                        'data': stats['by_genre']
                    }
                    
            return {'chart': self._create_empty_chart('No hay datos disponibles'), 'data': []}
            
        except Exception as e:
            logger.error(f"Error preparando datos para frontend: {e}")
            return {'chart': self._create_empty_chart(f'Error: {str(e)}'), 'data': []}
    
    def get_system_overview(self) -> Dict[str, Any]:
        """Resumen general del sistema"""
        try:
            db_info = self.get_database_info()
            artists_stats = self.get_artists_stats()
            albums_stats = self.get_albums_stats()
            songs_stats = self.get_songs_stats()
            
            return {
                'database': {
                    'size_mb': round(db_info.get('database_size', 0) / (1024 * 1024), 2),
                    'total_tables': db_info.get('total_tables', 0),
                    'last_updated': db_info.get('last_updated')
                },
                'content': {
                    'total_artists': artists_stats.get('total_artists', 0),
                    'total_albums': albums_stats.get('total_albums', 0),
                    'total_songs': songs_stats.get('total_songs', 0),
                    'total_duration_hours': round(
                        songs_stats.get('duration_stats', {}).get('total_duration', 0) / 3600, 2
                    )
                },
                'completeness': self._calculate_overall_completeness()
            }
            
        except Exception as e:
            logger.error(f"Error en resumen del sistema: {e}")
            return {}
    
    def _calculate_overall_completeness(self) -> float:
        """Calcula la completitud general de los datos"""
        try:
            missing_stats = self.get_missing_data_stats()
            if not missing_stats:
                return 0.0
            
            total_completeness = 0
            field_count = 0
            
            for table_stats in missing_stats.values():
                for field_stats in table_stats.get('fields', {}).values():
                    total_completeness += field_stats.get('completeness', 0)
                    field_count += 1
            
            return round(total_completeness / field_count, 2) if field_count > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculando completitud: {e}")
            return 0.0