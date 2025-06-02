#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import logging
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
import os
from collections import defaultdict, Counter

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

class ArtistAnalyzer:
    """Analizador detallado para artistas individuales"""
    
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
                logger.info(f"Conexión a BD establecida para ArtistAnalyzer: {self.db_path}")
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
    
    def create_chart(self, chart_type: str, data: List[Dict], title: str = "", 
                     x_field: str = None, y_field: str = None, **kwargs) -> str:
        """Crea un gráfico personalizado para artistas"""
        try:
            if not PLOTLY_AVAILABLE or not data:
                return self._create_empty_chart(title)
            
            df = pd.DataFrame(data)
            
            if chart_type == 'pie':
                fig = px.pie(df, 
                           values=y_field or df.columns[1], 
                           names=x_field or df.columns[0],
                           title=title)
                
                fig.update_traces(
                    textposition='inside',
                    textinfo='label+percent',
                    textfont_size=12,
                    marker=dict(line=dict(color='#000000', width=1))
                )
                
            elif chart_type == 'line':
                fig = px.line(df, 
                            x=x_field or df.columns[0], 
                            y=y_field or df.columns[1],
                            title=title,
                            markers=True)
                
                fig.update_traces(
                    line=dict(color='#a8e6cf', width=3),
                    marker=dict(size=6, color='#2a5298')
                )
                
            elif chart_type == 'bar':
                fig = px.bar(df, 
                           x=x_field or df.columns[0], 
                           y=y_field or df.columns[1],
                           title=title,
                           color_discrete_sequence=['#a8e6cf'])
                
            elif chart_type == 'line_multi':
                # Gráfico de líneas múltiples para escuchas
                fig = go.Figure()
                
                # Agrupar por canción/artista
                if 'track_name' in df.columns:
                    for track in df['track_name'].unique()[:10]:  # Top 10 canciones
                        track_data = df[df['track_name'] == track]
                        fig.add_trace(go.Scatter(
                            x=track_data[x_field],
                            y=track_data[y_field],
                            mode='lines+markers',
                            name=track[:30] + '...' if len(track) > 30 else track,
                            line=dict(width=2),
                            marker=dict(size=4)
                        ))
                
                fig.update_layout(title=title)
                
            else:
                return self._create_empty_chart(f"Tipo de gráfico no soportado: {chart_type}")
            
            # Aplicar tema consistente
            fig.update_layout(
                template='plotly_dark',
                plot_bgcolor='rgba(30, 60, 114, 0.1)',
                paper_bgcolor='rgba(30, 60, 114, 0.05)',
                font=dict(
                    family="'Segoe UI', Tahoma, Geneva, Verdana, sans-serif", 
                    size=11,
                    color='white'
                ),
                title=dict(
                    font=dict(size=16, color='#a8e6cf'),
                    x=0.5,
                    xanchor='center'
                ),
                height=350,
                margin=dict(l=50, r=50, t=60, b=50)
            )
            
            return fig.to_json()
            
        except Exception as e:
            logger.error(f"Error creando gráfico de artista: {e}")
            return self._create_empty_chart(f"Error: {str(e)}")
    
    def _create_empty_chart(self, message: str) -> str:
        """Crea un gráfico vacío con mensaje"""
        if PLOTLY_AVAILABLE:
            fig = go.Figure()
            fig.add_annotation(
                text=message,
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=16, color='#a8e6cf')
            )
            fig.update_layout(
                template='plotly_dark',
                plot_bgcolor='rgba(30, 60, 114, 0.1)',
                paper_bgcolor='rgba(30, 60, 114, 0.05)',
                height=350,
                showlegend=False,
                font=dict(color='white')
            )
            return fig.to_json()
        else:
            return json.dumps({
                "data": [],
                "layout": {"title": message}
            })
    
    def get_time_analysis(self, artist_id: int) -> Dict[str, Any]:
        """Análisis temporal del artista"""
        try:
            # Obtener álbumes del artista con años
            albums_query = """
                SELECT year, COUNT(*) as count
                FROM albums 
                WHERE artist_id = ? AND year IS NOT NULL AND year != ''
                GROUP BY year 
                ORDER BY year
            """
            albums_data = self.execute_query(albums_query, (artist_id,))
            
            if not albums_data:
                return {
                    'error': 'No se encontraron datos temporales para este artista',
                    'charts': {},
                    'stats': {}
                }
            
            # Procesar datos por décadas
            decades_data = defaultdict(int)
            years_data = []
            total_albums = 0
            
            for row in albums_data:
                try:
                    year = int(row['year'])
                    count = row['count']
                    total_albums += count
                    
                    # Agrupar por décadas
                    decade = (year // 10) * 10
                    decades_data[f"{decade}s"] += count
                    
                    # Datos por año
                    years_data.append({
                        'year': year,
                        'albums': count
                    })
                    
                except (ValueError, TypeError):
                    continue
            
            # Preparar datos para gráficos
            decades_chart_data = [
                {'decade': decade, 'count': count}
                for decade, count in sorted(decades_data.items())
            ]
            
            # Estadísticas
            years = [d['year'] for d in years_data]
            most_productive_decade = max(decades_data.items(), key=lambda x: x[1])[0] if decades_data else 'N/A'
            
            stats = {
                'total_albums': total_albums,
                'first_year': min(years) if years else None,
                'last_year': max(years) if years else None,
                'most_productive_decade': most_productive_decade
            }
            
            # Crear gráficos
            charts = {
                'decades_pie': self.create_chart(
                    'pie', decades_chart_data, 
                    'Distribución por Décadas', 'decade', 'count'
                ),
                'albums_timeline': self.create_chart(
                    'line', years_data, 
                    'Álbumes por Año', 'year', 'albums'
                )
            }
            
            return {
                'charts': charts,
                'stats': stats
            }
            
        except Exception as e:
            logger.error(f"Error en análisis temporal para artista {artist_id}: {e}")
            return {'error': str(e), 'charts': {}, 'stats': {}}
    
    def get_concerts_analysis(self, artist_id: int) -> Dict[str, Any]:
        """Análisis de conciertos del artista"""
        try:
            # Obtener datos de conciertos desde setlist.fm
            concerts_query = """
                SELECT eventDate, COUNT(*) as concerts
                FROM artists_setlistfm 
                WHERE artist_id = ? AND eventDate IS NOT NULL
                GROUP BY substr(eventDate, 1, 4)
                ORDER BY eventDate
            """
            concerts_data = self.execute_query(concerts_query, (artist_id,))
            
            # Obtener canciones más tocadas
            songs_query = """
                SELECT sets, eventDate
                FROM artists_setlistfm 
                WHERE artist_id = ? AND sets IS NOT NULL
            """
            setlist_data = self.execute_query(songs_query, (artist_id,))
            
            if not concerts_data and not setlist_data:
                return {
                    'error': 'No se encontraron datos de conciertos para este artista',
                    'charts': {},
                    'stats': {}
                }
            
            # Procesar datos de conciertos por año
            concerts_by_year = []
            total_concerts = 0
            
            for row in concerts_data:
                try:
                    year = row['eventDate'][:4] if row['eventDate'] else 'Unknown'
                    count = row['concerts']
                    total_concerts += count
                    
                    concerts_by_year.append({
                        'year': int(year) if year != 'Unknown' else 0,
                        'concerts': count
                    })
                except:
                    continue
            
            # Procesar canciones más tocadas
            song_counts = Counter()
            countries = set()
            
            for row in setlist_data:
                try:
                    sets_data = json.loads(row['sets']) if row['sets'] else []
                    for set_data in sets_data:
                        if isinstance(set_data, dict) and 'song' in set_data:
                            songs = set_data['song']
                            if isinstance(songs, list):
                                for song in songs:
                                    if isinstance(song, dict) and 'name' in song:
                                        song_counts[song['name']] += 1
                except:
                    continue
            
            # Top canciones
            top_songs = [
                {'song': song, 'plays': count}
                for song, count in song_counts.most_common(15)
            ]
            
            # Obtener países únicos
            countries_query = """
                SELECT DISTINCT country_name
                FROM artists_setlistfm 
                WHERE artist_id = ? AND country_name IS NOT NULL
            """
            countries_data = self.execute_query(countries_query, (artist_id,))
            countries_visited = len(countries_data)
            
            # Último concierto
            last_concert_query = """
                SELECT eventDate
                FROM artists_setlistfm 
                WHERE artist_id = ? AND eventDate IS NOT NULL
                ORDER BY eventDate DESC
                LIMIT 1
            """
            last_concert = self.execute_query(last_concert_query, (artist_id,))
            last_concert_date = last_concert[0]['eventDate'] if last_concert else 'N/A'
            
            stats = {
                'total_concerts': total_concerts,
                'countries_visited': countries_visited,
                'last_concert_date': last_concert_date
            }
            
            charts = {
                'concerts_timeline': self.create_chart(
                    'line', concerts_by_year, 
                    'Conciertos por Año', 'year', 'concerts'
                ),
                'most_played_songs': self.create_chart(
                    'bar', top_songs, 
                    'Canciones Más Tocadas en Conciertos', 'song', 'plays'
                )
            }
            
            return {
                'charts': charts,
                'stats': stats
            }
            
        except Exception as e:
            logger.error(f"Error en análisis de conciertos para artista {artist_id}: {e}")
            return {'error': str(e), 'charts': {}, 'stats': {}}
    
    def get_genres_analysis(self, artist_id: int) -> Dict[str, Any]:
        """Análisis de géneros del artista"""
        try:
            # Géneros de álbumes
            album_genres_query = """
                SELECT genre, COUNT(*) as count
                FROM albums 
                WHERE artist_id = ? AND genre IS NOT NULL AND genre != ''
                GROUP BY genre 
                ORDER BY count DESC
                LIMIT 10
            """
            album_genres = self.execute_query(album_genres_query, (artist_id,))
            
            # Géneros y estilos de Discogs
            discogs_genres_query = """
                SELECT genres, styles
                FROM discogs_discography 
                WHERE artist_id = ?
            """
            discogs_data = self.execute_query(discogs_genres_query, (artist_id,))
            
            # Tags de Last.fm (desde la tabla artists)
            lastfm_tags_query = """
                SELECT tags
                FROM artists 
                WHERE id = ? AND tags IS NOT NULL AND tags != ''
            """
            lastfm_data = self.execute_query(lastfm_tags_query, (artist_id,))
            
            # Procesar datos de Discogs
            discogs_genres = Counter()
            discogs_styles = Counter()
            
            for row in discogs_data:
                try:
                    if row['genres']:
                        genres = json.loads(row['genres'])
                        for genre in genres:
                            discogs_genres[genre] += 1
                except:
                    pass
                
                try:
                    if row['styles']:
                        styles = json.loads(row['styles'])
                        for style in styles:
                            discogs_styles[style] += 1
                except:
                    pass
            
            # Procesar tags de Last.fm
            lastfm_tags = Counter()
            for row in lastfm_data:
                try:
                    if row['tags']:
                        # Asumir que tags está separado por comas
                        tags = [tag.strip() for tag in row['tags'].split(',')]
                        for tag in tags[:10]:  # Top 10 tags
                            lastfm_tags[tag] += 1
                except:
                    pass
            
            # Preparar datos para gráficos
            album_genres_data = [
                {'genre': row['genre'], 'count': row['count']}
                for row in album_genres
            ]
            
            discogs_genres_data = [
                {'genre': genre, 'count': count}
                for genre, count in discogs_genres.most_common(10)
            ]
            
            discogs_styles_data = [
                {'style': style, 'count': count}
                for style, count in discogs_styles.most_common(10)
            ]
            
            lastfm_tags_data = [
                {'tag': tag, 'count': count}
                for tag, count in lastfm_tags.most_common(10)
            ]
            
            charts = {
                'album_genres': self.create_chart(
                    'pie', album_genres_data, 
                    'Géneros de Álbumes', 'genre', 'count'
                ),
                'discogs_genres': self.create_chart(
                    'pie', discogs_genres_data, 
                    'Géneros Discogs', 'genre', 'count'
                ),
                'discogs_styles': self.create_chart(
                    'pie', discogs_styles_data, 
                    'Estilos Discogs', 'style', 'count'
                ),
                'lastfm_tags': self.create_chart(
                    'pie', lastfm_tags_data, 
                    'Tags Last.fm', 'tag', 'count'
                )
            }
            
            return {
                'charts': charts,
                'stats': {
                    'total_album_genres': len(album_genres_data),
                    'total_discogs_genres': len(discogs_genres_data),
                    'total_discogs_styles': len(discogs_styles_data),
                    'total_lastfm_tags': len(lastfm_tags_data)
                }
            }
            
        except Exception as e:
            logger.error(f"Error en análisis de géneros para artista {artist_id}: {e}")
            return {'error': str(e), 'charts': {}, 'stats': {}}
    
    def get_labels_analysis(self, artist_id: int) -> Dict[str, Any]:
        """Análisis de sellos discográficos del artista"""
        try:
            # Sellos por álbum
            labels_query = """
                SELECT label, year, COUNT(*) as count
                FROM albums 
                WHERE artist_id = ? AND label IS NOT NULL AND label != ''
                GROUP BY label, year
                ORDER BY year, count DESC
            """
            labels_data = self.execute_query(labels_query, (artist_id,))
            
            if not labels_data:
                return {
                    'error': 'No se encontraron datos de sellos para este artista',
                    'charts': {},
                    'stats': {}
                }
            
            # Procesar datos
            labels_count = Counter()
            labels_timeline = defaultdict(lambda: defaultdict(int))
            
            for row in labels_data:
                label = row['label']
                year = row['year']
                count = row['count']
                
                labels_count[label] += count
                
                try:
                    year_int = int(year) if year else 0
                    labels_timeline[year_int][label] += count
                except:
                    pass
            
            # Datos para gráfico circular
            labels_pie_data = [
                {'label': label, 'count': count}
                for label, count in labels_count.most_common(10)
            ]
            
            # Datos para gráfico de líneas acumulativas
            labels_cumulative = []
            cumulative_totals = defaultdict(int)
            
            for year in sorted(labels_timeline.keys()):
                for label, count in labels_timeline[year].items():
                    cumulative_totals[label] += count
                    if label in [item['label'] for item in labels_pie_data[:5]]:  # Top 5 sellos
                        labels_cumulative.append({
                            'year': year,
                            'label': label,
                            'cumulative': cumulative_totals[label]
                        })
            
            charts = {
                'labels_pie': self.create_chart(
                    'pie', labels_pie_data, 
                    'Distribución por Sellos', 'label', 'count'
                ),
                'labels_timeline': self.create_chart(
                    'line_multi', labels_cumulative, 
                    'Álbumes Acumulados por Sello', 'year', 'cumulative'
                )
            }
            
            stats = {
                'total_labels': len(labels_count),
                'main_label': labels_count.most_common(1)[0][0] if labels_count else 'N/A',
                'main_label_albums': labels_count.most_common(1)[0][1] if labels_count else 0
            }
            
            return {
                'charts': charts,
                'stats': stats
            }
            
        except Exception as e:
            logger.error(f"Error en análisis de sellos para artista {artist_id}: {e}")
            return {'error': str(e), 'charts': {}, 'stats': {}}
    
    def get_discography_analysis(self, artist_id: int) -> Dict[str, Any]:
        """Análisis de discografía del artista"""
        try:
            # Datos de Discogs
            discogs_query = """
                SELECT format, type, user_coll, user_wantlist, formats
                FROM discogs_discography 
                WHERE artist_id = ?
            """
            discogs_data = self.execute_query(discogs_query, (artist_id,))
            
            if not discogs_data:
                return {
                    'error': 'No se encontraron datos de discografía en Discogs para este artista',
                    'charts': {},
                    'stats': {}
                }
            
            # Procesar formatos
            formats_count = Counter()
            types_count = Counter()
            collection_data = {'En colección': 0, 'No en colección': 0}
            
            for row in discogs_data:
                # Formatos
                if row['format']:
                    formats_count[row['format']] += 1
                elif row['formats']:
                    try:
                        formats = json.loads(row['formats'])
                        for fmt in formats:
                            if isinstance(fmt, dict) and 'name' in fmt:
                                formats_count[fmt['name']] += 1
                    except:
                        pass
                
                # Tipos
                if row['type']:
                    types_count[row['type']] += 1
                
                # Colección
                if row['user_coll'] and int(row['user_coll']) > 0:
                    collection_data['En colección'] += 1
                else:
                    collection_data['No en colección'] += 1
            
            # Preparar datos para gráficos
            formats_data = [
                {'format': fmt, 'count': count}
                for fmt, count in formats_count.most_common(10)
            ]
            
            types_data = [
                {'type': typ, 'count': count}
                for typ, count in types_count.most_common(10)
            ]
            
            collection_chart_data = [
                {'status': status, 'count': count}
                for status, count in collection_data.items()
            ]
            
            charts = {
                'formats': self.create_chart(
                    'pie', formats_data, 
                    'Distribución por Formato', 'format', 'count'
                ),
                'types': self.create_chart(
                    'pie', types_data,