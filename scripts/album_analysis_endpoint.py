#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import json
import os  # Agregar este import
from collections import Counter, defaultdict
from flask import jsonify, request  # Agregar request aquí
import re
import requests

logger = logging.getLogger(__name__)

class AlbumAnalysisEndpoints:
    """Endpoints específicos para análisis detallado de álbumes"""
    
    def __init__(self, app, db_manager, config):
        self.app = app
        self.db_manager = db_manager
        self.config = config
        self.setup_album_analysis_routes()
    
    def setup_album_analysis_routes(self):
        """Configura las rutas para análisis de álbumes"""
        
        @self.app.route('/api/albums/search')
        def api_search_albums():
            """Buscar álbumes para el análisis detallado"""
            try:
                query = request.args.get('q', '').strip()
                limit = min(int(request.args.get('limit', 15)), 50)
                
                logger.info(f"Búsqueda de álbumes: query='{query}', limit={limit}")
                
                if len(query) < 2:
                    return jsonify({'error': 'Consulta muy corta', 'results': []})
                
                if not self.db_manager:
                    logger.error("db_manager no disponible")
                    return jsonify({'error': 'Base de datos no disponible', 'results': []}), 500
                
                # Test básico de conexión
                try:
                    test_result = self.db_manager.execute_query("SELECT COUNT(*) as total FROM albums LIMIT 1")
                    logger.info(f"✅ Test de conexión DB exitoso: {test_result}")
                except Exception as e:
                    logger.error(f"❌ Error test DB: {e}")
                    return jsonify({'error': f'Error de base de datos: {str(e)}', 'results': []}), 500
                


                # CONSULTA SQL CORREGIDA
                search_query = """
                    SELECT DISTINCT 
                        a.id,
                        a.name,
                        a.year,
                        a.genre,
                        a.label,
                        ar.name as artist_name,
                        (ar.name || ' - ' || a.name) as display_name
                    FROM albums a
                    LEFT JOIN artists ar ON a.artist_id = ar.id
                    WHERE (
                        a.name LIKE ? OR 
                        ar.name LIKE ? OR 
                        (ar.name || ' - ' || a.name) LIKE ?
                    )
                    AND a.name IS NOT NULL AND a.name != ''
                    AND ar.name IS NOT NULL AND ar.name != ''
                    ORDER BY ar.name, a.year, a.name
                    LIMIT ?
                """
                
                search_pattern = f"%{query}%"
                logger.debug(f"Ejecutando consulta con patrón: {search_pattern}")
                
                albums = self.db_manager.execute_query(search_query, 
                                                    (search_pattern, search_pattern, search_pattern, limit))
                
                logger.info(f"Encontrados {len(albums)} álbumes")
                
                results = []
                for album in albums:
                    album_data = {
                        'id': album['id'],
                        'name': album['name'] or 'Sin nombre',
                        'year': album['year'] or 'Desconocido',
                        'genre': album['genre'] or 'Desconocido',
                        'label': album['label'] or 'Desconocido',
                        'artist_name': album['artist_name'] or 'Artista desconocido',
                        'display_name': album['display_name'] or f"Album {album['id']}"
                    }
                    results.append(album_data)
                
                return jsonify({
                    'results': results, 
                    'total': len(results),
                    'query': query
                })
                
            except Exception as e:
                logger.error(f"Error buscando álbumes: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'error': str(e), 'results': []}), 500


        @self.app.route('/api/albums/<int:album_id>/analysis/<analysis_type>')
        def api_album_analysis(album_id, analysis_type):
            """Endpoint para análisis de álbumes"""
            try:
                logger.info(f"Análisis de álbum: ID={album_id}, tipo={analysis_type}")
                
                # Verificar que el álbum existe
                album = self.db_manager.get_album_by_id(album_id)
                if not album:
                    return jsonify({'error': 'Álbum no encontrado'}), 404
                
                # Crear análisis según el tipo - SIN pasar album como parámetro
                if analysis_type == 'tiempo':
                    return jsonify(self._get_album_time_analysis(album_id))
                elif analysis_type == 'genero':
                    return jsonify(self._get_album_genre_analysis(album_id))
                elif analysis_type == 'conciertos':
                    return jsonify(self._get_album_concerts_analysis(album_id))
                elif analysis_type == 'sellos':
                    return jsonify(self._get_album_labels_analysis(album_id))
                elif analysis_type == 'discografia':
                    return jsonify(self._get_album_discography_analysis(album_id))
                elif analysis_type == 'escuchas':
                    return jsonify(self._get_album_listens_analysis(album_id))
                elif analysis_type == 'colaboradores':
                    return jsonify(self._get_album_collaborators_analysis(album_id))
                elif analysis_type == 'feeds':
                    return jsonify(self._get_album_feeds_analysis(album_id))
                elif analysis_type == 'letras':
                    return jsonify(self._get_album_lyrics_analysis(album_id))
                else:
                    return jsonify({'error': f'Tipo de análisis no soportado: {analysis_type}'}), 400
                    
            except Exception as e:
                logger.error(f"Error en análisis {analysis_type} para álbum {album_id}: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'error': str(e)}), 500
    
    # DEGBUG DELETEME
        @self.app.route('/api/debug/albums-search')
        def debug_albums_search():
            """Debug de búsqueda de álbumes"""
            try:
                # Test básico de conexión
                test_query = "SELECT COUNT(*) as total FROM albums"
                total_result = self.db_manager.execute_query(test_query)
                total_albums = total_result[0]['total'] if total_result else 0
                
                # Test de primeros álbumes
                sample_query = """
                    SELECT a.id, a.name, a.year, ar.name as artist_name,
                        (ar.name || ' - ' || a.name) as display_name
                    FROM albums a
                    LEFT JOIN artists ar ON a.artist_id = ar.id
                    WHERE a.name IS NOT NULL AND a.name != ''
                    AND ar.name IS NOT NULL AND ar.name != ''
                    ORDER BY a.id
                    LIMIT 5
                """
                sample_albums = self.db_manager.execute_query(sample_query)
                
                # Test de búsqueda simple
                search_query = """
                    SELECT a.id, a.name, ar.name as artist_name,
                        (ar.name || ' - ' || a.name) as display_name
                    FROM albums a
                    LEFT JOIN artists ar ON a.artist_id = ar.id
                    WHERE (a.name LIKE '%a%' OR ar.name LIKE '%a%')
                    AND a.name IS NOT NULL AND a.name != ''
                    AND ar.name IS NOT NULL AND ar.name != ''
                    LIMIT 5
                """
                search_results = self.db_manager.execute_query(search_query)
                
                return jsonify({
                    'status': 'ok',
                    'total_albums': total_albums,
                    'sample_albums': [dict(row) for row in sample_albums],
                    'search_test': [dict(row) for row in search_results],
                    'db_path': getattr(self.db_manager, 'db_path', 'Unknown'),
                    'db_exists': os.path.exists(self.db_manager.db_path) if hasattr(self.db_manager, 'db_path') else 'Unknown'
                })
                
            except Exception as e:
                logger.error(f"Error en debug de álbumes: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({
                    'error': str(e),
                    'status': 'error',
                    'traceback': traceback.format_exc()
                }), 500
    
    



    def _get_album_time_analysis(self, album_id):
        """Análisis temporal del álbum"""
        try:
            album = self.db_manager.get_album_by_id(album_id)
            if not album:
                return {'error': 'Álbum no encontrado'}

            album_year = album.get('year')
            if not album_year:
                return {'error': 'El álbum no tiene año definido'}
            
            try:
                year_int = int(album_year)
            except:
                return {'error': 'Año del álbum inválido'}
            
            # Álbumes del mismo año
            same_year_query = """
                SELECT a.name, ar.name as artist_name, a.genre, a.label
                FROM albums a
                JOIN artists ar ON a.artist_id = ar.id
                WHERE a.year = ? AND a.id != ?
                ORDER BY ar.name, a.name
                LIMIT 20
            """
            same_year_albums = self.db_manager.execute_query(same_year_query, (album_year, album_id))
            
            # Distribución por género ese año
            genre_year_query = """
                SELECT genre, COUNT(*) as count
                FROM albums
                WHERE year = ? AND genre IS NOT NULL AND genre != ''
                GROUP BY genre
                ORDER BY count DESC
                LIMIT 10
            """
            genres_data = self.db_manager.execute_query(genre_year_query, (album_year,))
            
            # Distribución por sello ese año
            label_year_query = """
                SELECT label, COUNT(*) as count
                FROM albums
                WHERE year = ? AND label IS NOT NULL AND label != ''
                GROUP BY label
                ORDER BY count DESC
                LIMIT 10
            """
            labels_data = self.db_manager.execute_query(label_year_query, (album_year,))
            
            # Distribución por país (basado en artistas)
            country_year_query = """
                SELECT ar.origin, COUNT(*) as count
                FROM albums a
                JOIN artists ar ON a.artist_id = ar.id
                WHERE a.year = ? AND ar.origin IS NOT NULL AND ar.origin != ''
                GROUP BY ar.origin
                ORDER BY count DESC
                LIMIT 10
            """
            countries_data = self.db_manager.execute_query(country_year_query, (album_year,))
            
            # Preparar datos para gráficos
            genres_chart_data = [{'genre': row['genre'], 'count': row['count']} for row in genres_data]
            labels_chart_data = [{'label': row['label'], 'count': row['count']} for row in labels_data]
            countries_chart_data = [{'country': row['origin'], 'count': row['count']} for row in countries_data]
            
            from stats_manager import StatsManager
            stats_manager = StatsManager(self.db_manager.db_path, self.config)
            
            charts = {}
            
            if genres_chart_data:
                charts['genres_pie'] = stats_manager.create_chart('pie', genres_chart_data,
                                            f'Géneros más populares en {album_year}', 'genre', 'count')
            
            if labels_chart_data:
                charts['labels_pie'] = stats_manager.create_chart('pie', labels_chart_data,
                                            f'Sellos más activos en {album_year}', 'label', 'count')
            
            if countries_chart_data:
                charts['countries_pie'] = stats_manager.create_chart('pie', countries_chart_data,
                                            f'Países con más releases en {album_year}', 'country', 'count')
            
            return {
                'charts': charts,
                'stats': {
                    'album_year': year_int,
                    'same_year_albums': len(same_year_albums),
                    'total_genres': len(genres_data),
                    'total_labels': len(labels_data),
                    'total_countries': len(countries_data)
                },
                'same_year_albums': [dict(row) for row in same_year_albums]
            }
            
        except Exception as e:
            logger.error(f"Error en análisis temporal del álbum: {e}")
            return {'error': str(e)}
    
    def _get_album_genre_analysis(self, album_id):
        """Análisis de género del álbum"""
        try:
            album = self.db_manager.get_album_by_id(album_id)
            if not album:
                return {'error': 'Álbum no encontrado'}
                
            album_genre = album.get('genre')
            if not album_genre:
                return {'error': 'El álbum no tiene género definido'}
            
            # Álbumes del mismo género
            same_genre_query = """
                SELECT a.name, ar.name as artist_name, a.year, a.label
                FROM albums a
                JOIN artists ar ON a.artist_id = ar.id
                WHERE a.genre = ? AND a.id != ?
                ORDER BY a.year DESC, ar.name
                LIMIT 30
            """
            same_genre_albums = self.db_manager.execute_query(same_genre_query, (album_genre, album_id))
            
            # Distribución por año del género
            genre_years_query = """
                SELECT year, COUNT(*) as count
                FROM albums
                WHERE genre = ? AND year IS NOT NULL AND year != ''
                GROUP BY year
                ORDER BY year
            """
            years_data = self.db_manager.execute_query(genre_years_query, (album_genre,))
            
            # Artistas más prolíficos del género
            genre_artists_query = """
                SELECT ar.name, COUNT(*) as albums_count
                FROM albums a
                JOIN artists ar ON a.artist_id = ar.id
                WHERE a.genre = ?
                GROUP BY ar.name
                ORDER BY albums_count DESC
                LIMIT 15
            """
            artists_data = self.db_manager.execute_query(genre_artists_query, (album_genre,))
            
            # Preparar datos para gráficos
            years_chart_data = []
            for row in years_data:
                try:
                    year = int(row['year'])
                    if year > 1900 and year <= 2030:
                        years_chart_data.append({'year': year, 'count': row['count']})
                except:
                    continue
            
            artists_chart_data = [{'artist': row['name'], 'albums': row['albums_count']} for row in artists_data]
            
            from stats_manager import StatsManager
            stats_manager = StatsManager(self.db_manager.db_path, self.config)
            
            charts = {}
            
            if years_chart_data:
                charts['years_line'] = stats_manager.create_chart('line', years_chart_data,
                                            f'Evolución temporal del {album_genre}', 'year', 'count')
            
            if artists_chart_data:
                charts['artists_bar'] = stats_manager.create_chart('bar', artists_chart_data[:12],
                                            f'Artistas más prolíficos del {album_genre}', 'artist', 'albums')
            
            return {
                'charts': charts,
                'stats': {
                    'genre': album_genre,
                    'total_albums_genre': len(same_genre_albums),
                    'years_span': len(years_chart_data),
                    'top_artists': len(artists_data)
                },
                'same_genre_albums': [dict(row) for row in same_genre_albums[:15]]
            }
            
        except Exception as e:
            logger.error(f"Error en análisis de género del álbum: {e}")
            return {'error': str(e)}
    
    def _get_album_concerts_analysis(self, album_id):
        """Análisis de conciertos del álbum"""
        try:
            # Obtener el álbum primero
            album = self.db_manager.get_album_by_id(album_id)
            if not album:
                return {'error': 'Álbum no encontrado'}
                
            artist_id = album.get('artist_id')
            album_name = album.get('name', '')
            
            if not artist_id:
                return {'error': 'No se puede determinar el artista del álbum'}
            
            # Obtener canciones del álbum
            album_tracks = self.db_manager.get_album_tracks_by_id(album_id)
            if not album_tracks:
                return {'error': 'No se encontraron canciones para este álbum'}
            
            track_names = [track.get('title', '') for track in album_tracks if track.get('title')]
            
            # Buscar conciertos donde se tocaron canciones de este álbum
            concerts_query = """
                SELECT eventDate, venue_name, city_name, country_name, sets
                FROM artists_setlistfm
                WHERE artist_id = ? AND sets IS NOT NULL AND sets != ''
                ORDER BY eventDate DESC
            """
            concerts_data = self.db_manager.execute_query(concerts_query, (artist_id,))
            
            # Analizar qué canciones del álbum se tocaron en conciertos
            track_concert_counts = defaultdict(int)
            concerts_with_album_tracks = []
            
            for concert in concerts_data:
                try:
                    sets_data = json.loads(concert['sets'])
                    concert_tracks = set()
                    
                    if isinstance(sets_data, list):
                        for set_data in sets_data:
                            if isinstance(set_data, dict) and 'song' in set_data:
                                songs = set_data['song']
                                if isinstance(songs, list):
                                    for song in songs:
                                        if isinstance(song, dict) and 'name' in song:
                                            song_name = song['name'].strip()
                                            concert_tracks.add(song_name.lower())
                                        elif isinstance(song, str):
                                            concert_tracks.add(song.strip().lower())
                    
                    # Verificar qué canciones del álbum se tocaron
                    album_tracks_in_concert = []
                    for track_name in track_names:
                        track_lower = track_name.lower()
                        if any(track_lower in concert_track or concert_track in track_lower 
                               for concert_track in concert_tracks):
                            track_concert_counts[track_name] += 1
                            album_tracks_in_concert.append(track_name)
                    
                    if album_tracks_in_concert:
                        concerts_with_album_tracks.append({
                            'date': concert['eventDate'],
                            'venue': concert['venue_name'],
                            'city': concert['city_name'],
                            'country': concert['country_name'],
                            'album_tracks': album_tracks_in_concert
                        })
                        
                except (json.JSONDecodeError, TypeError, KeyError):
                    continue
            
            # Datos para gráficos
            tracks_chart_data = [{'track': track, 'concerts': count} 
                               for track, count in sorted(track_concert_counts.items(), 
                                                         key=lambda x: x[1], reverse=True)]
            
            # Timeline de conciertos con canciones del álbum
            concert_timeline = defaultdict(int)
            for concert in concerts_with_album_tracks:
                try:
                    year = concert['date'][:4] if concert['date'] else 'Unknown'
                    if year != 'Unknown':
                        concert_timeline[year] += len(concert['album_tracks'])
                except:
                    continue
            
            timeline_data = [{'year': year, 'tracks_played': count} 
                           for year, count in sorted(concert_timeline.items())]
            
            from stats_manager import StatsManager
            stats_manager = StatsManager(self.db_manager.db_path, self.config)
            
            charts = {}
            
            if tracks_chart_data:
                charts['tracks_concerts'] = stats_manager.create_chart('bar', tracks_chart_data,
                                            f'Canciones de "{album_name}" más tocadas en vivo', 'track', 'concerts')
            
            if timeline_data:
                charts['concerts_timeline'] = stats_manager.create_chart('line', timeline_data,
                                            f'Evolución de "{album_name}" en conciertos', 'year', 'tracks_played')
            
            return {
                'charts': charts,
                'stats': {
                    'total_album_tracks': len(track_names),
                    'tracks_played_live': len(track_concert_counts),
                    'concerts_with_album': len(concerts_with_album_tracks),
                    'most_played_track': max(track_concert_counts.items(), key=lambda x: x[1])[0] if track_concert_counts else 'N/A'
                },
                'concerts_with_album': concerts_with_album_tracks[:10]
            }
            
        except Exception as e:
            logger.error(f"Error en análisis de conciertos del álbum: {e}")
            return {'error': str(e)}
    
    def _get_album_labels_analysis(self, album_id):
        """Análisis de sellos del álbum"""
        try:
            # Obtener el álbum primero
            album = self.db_manager.get_album_by_id(album_id)
            if not album:
                return {'error': 'Álbum no encontrado'}
                
            album_label = album.get('label')
            if not album_label:
                return {'error': 'El álbum no tiene sello definido'}
            
            # Releases del sello por año
            label_releases_query = """
                SELECT year, COUNT(*) as releases, 
                       GROUP_CONCAT(name || ' (' || COALESCE(artist_name, 'Unknown') || ')') as albums
                FROM (
                    SELECT a.year, a.name, ar.name as artist_name
                    FROM albums a
                    LEFT JOIN artists ar ON a.artist_id = ar.id
                    WHERE a.label = ? AND a.year IS NOT NULL AND a.year != ''
                    ORDER BY a.year, a.name
                )
                GROUP BY year
                ORDER BY year
            """
            releases_data = self.db_manager.execute_query(label_releases_query, (album_label,))
            
            # Géneros del sello
            label_genres_query = """
                SELECT genre, COUNT(*) as count
                FROM albums
                WHERE label = ? AND genre IS NOT NULL AND genre != ''
                GROUP BY genre
                ORDER BY count DESC
                LIMIT 10
            """
            genres_data = self.db_manager.execute_query(label_genres_query, (album_label,))
            
            # Artistas del sello
            label_artists_query = """
                SELECT ar.name, COUNT(*) as albums_count
                FROM albums a
                JOIN artists ar ON a.artist_id = ar.id
                WHERE a.label = ?
                GROUP BY ar.name
                ORDER BY albums_count DESC
                LIMIT 15
            """
            artists_data = self.db_manager.execute_query(label_artists_query, (album_label,))
            
            # Preparar datos para gráficos
            releases_chart_data = []
            for row in releases_data:
                try:
                    year = int(row['year'])
                    if year > 1900 and year <= 2030:
                        # Marcar el año del álbum actual
                        is_current_album = (str(year) == str(album.get('year')))
                        releases_chart_data.append({
                            'year': year, 
                            'releases': row['releases'],
                            'highlight': is_current_album
                        })
                except:
                    continue
            
            genres_chart_data = [{'genre': row['genre'], 'count': row['count']} for row in genres_data]
            artists_chart_data = [{'artist': row['name'], 'albums': row['albums_count']} for row in artists_data]
            
            from stats_manager import StatsManager
            stats_manager = StatsManager(self.db_manager.db_path, self.config)
            
            charts = {}
            
            if releases_chart_data:
                charts['releases_timeline'] = stats_manager.create_chart('line', releases_chart_data,
                                            f'Releases de {album_label} por año', 'year', 'releases')
            
            if genres_chart_data:
                charts['genres_pie'] = stats_manager.create_chart('pie', genres_chart_data,
                                            f'Géneros de {album_label}', 'genre', 'count')
            
            if artists_chart_data:
                charts['artists_bar'] = stats_manager.create_chart('bar', artists_chart_data[:10],
                                            f'Artistas de {album_label}', 'artist', 'albums')
            
            return {
                'charts': charts,
                'stats': {
                    'label': album_label,
                    'total_releases': sum(row['releases'] for row in releases_data),
                    'years_active': len(releases_chart_data),
                    'total_artists': len(artists_data),
                    'total_genres': len(genres_data)
                }
            }
            
        except Exception as e:
            logger.error(f"Error en análisis de sellos del álbum: {e}")
            return {'error': str(e)}
    
    def _get_album_discography_analysis(self, album_id):
        """Análisis de discografía del álbum"""
        try:
            # Obtener el álbum primero
            album = self.db_manager.get_album_by_id(album_id)
            if not album:
                return {'error': 'Álbum no encontrado'}
                
            artist_id = album.get('artist_id')
            album_name = album.get('name', '')
            
            if not artist_id:
                return {'error': 'No se puede determinar el artista del álbum'}
            
            # Obtener canciones del álbum actual
            album_tracks = self.db_manager.get_album_tracks_by_id(album_id)
            track_names = [track.get('title', '') for track in album_tracks if track.get('title')]
            
            # Buscar en discografía de Discogs qué canciones aparecen en otros releases
            discogs_query = """
                SELECT album_name, year, tracklist, type
                FROM discogs_discography
                WHERE artist_id = ? AND tracklist IS NOT NULL AND tracklist != ''
                ORDER BY year DESC
            """
            discogs_data = self.db_manager.execute_query(discogs_query, (artist_id,))
            
            # Analizar en cuántos releases aparece cada canción
            track_appearances = defaultdict(int)
            releases_with_tracks = defaultdict(int)
            
            for release in discogs_data:
                try:
                    tracklist = json.loads(release['tracklist'])
                    release_tracks = set()
                    
                    if isinstance(tracklist, list):
                        for track in tracklist:
                            if isinstance(track, dict) and 'title' in track:
                                release_tracks.add(track['title'].lower().strip())
                    
                    # Contar apariciones de canciones del álbum actual
                    tracks_found = 0
                    for track_name in track_names:
                        track_lower = track_name.lower().strip()
                        if any(track_lower in release_track or release_track in track_lower 
                               for release_track in release_tracks):
                            track_appearances[track_name] += 1
                            tracks_found += 1
                    
                    if tracks_found > 0:
                        releases_with_tracks[release['album_name']] = tracks_found
                        
                except (json.JSONDecodeError, TypeError, KeyError):
                    continue
            
            # Datos para gráficos
            tracks_chart_data = [{'track': track, 'appearances': count} 
                               for track, count in sorted(track_appearances.items(), 
                                                         key=lambda x: x[1], reverse=True)]
            
            releases_chart_data = [{'release': release, 'tracks': count} 
                                 for release, count in sorted(releases_with_tracks.items(), 
                                                             key=lambda x: x[1], reverse=True)]
            
            from stats_manager import StatsManager
            stats_manager = StatsManager(self.db_manager.db_path, self.config)
            
            charts = {}
            
            if tracks_chart_data:
                charts['tracks_appearances'] = stats_manager.create_chart('pie', tracks_chart_data,
                                            f'Canciones de "{album_name}" en otros releases', 'track', 'appearances')
            
            if releases_chart_data:
                charts['releases_tracks'] = stats_manager.create_chart('bar', releases_chart_data[:15],
                                            f'Releases con más canciones de "{album_name}"', 'release', 'tracks')
            
            return {
                'charts': charts,
                'stats': {
                    'total_album_tracks': len(track_names),
                    'tracks_in_other_releases': len(track_appearances),
                    'other_releases_count': len(releases_with_tracks),
                    'most_reused_track': max(track_appearances.items(), key=lambda x: x[1])[0] if track_appearances else 'N/A'
                }
            }
            
        except Exception as e:
            logger.error(f"Error en análisis de discografía del álbum: {e}")
            return {'error': str(e)}
    
    def _get_album_listens_analysis(self, album_id):
        """Análisis de escuchas del álbum"""
        try:
            # Obtener el álbum primero
            album = self.db_manager.get_album_by_id(album_id)
            if not album:
                return {'error': 'Álbum no encontrado'}
                
            artist_id = album.get('artist_id')
            album_name = album.get('name', '')
            
            # Obtener canciones del álbum
            album_tracks = self.db_manager.get_album_tracks_by_id(album_id)
            track_names = [track.get('title', '') for track in album_tracks if track.get('title')]
            
            # Escuchas en Last.fm
            lastfm_query = """
                SELECT track_name, scrobble_date, COUNT(*) as plays
                FROM scrobbles_paqueradejere
                WHERE artist_id = ? AND track_name IN ({})
                GROUP BY track_name, DATE(scrobble_date)
                ORDER BY scrobble_date
            """.format(','.join(['?' for _ in track_names]))
            
            lastfm_params = [artist_id] + track_names
            lastfm_data = self.db_manager.execute_query(lastfm_query, lastfm_params) if track_names else []
            
            # Escuchas en ListenBrainz
            listenbrainz_query = """
                SELECT track_name, listen_date, COUNT(*) as plays
                FROM listens_guevifrito
                WHERE artist_id = ? AND track_name IN ({})
                GROUP BY track_name, DATE(listen_date)
                ORDER BY listen_date
            """.format(','.join(['?' for _ in track_names]))
            
            listenbrainz_params = [artist_id] + track_names
            listenbrainz_data = self.db_manager.execute_query(listenbrainz_query, listenbrainz_params) if track_names else []
            
            # Procesar datos por canciones
            lastfm_tracks = defaultdict(int)
            lastfm_monthly = defaultdict(int)
            
            for row in lastfm_data:
                lastfm_tracks[row['track_name']] += row['plays']
                try:
                    month = row['scrobble_date'][:7]  # YYYY-MM
                    lastfm_monthly[month] += row['plays']
                except:
                    pass
            
            listenbrainz_tracks = defaultdict(int)
            listenbrainz_monthly = defaultdict(int)
            
            for row in listenbrainz_data:
                listenbrainz_tracks[row['track_name']] += row['plays']
                try:
                    month = row['listen_date'][:7]  # YYYY-MM
                    listenbrainz_monthly[month] += row['plays']
                except:
                    pass
            
            # Datos para gráficos
            lastfm_tracks_data = [{'track': t, 'plays': p} for t, p in sorted(lastfm_tracks.items(), key=lambda x: x[1], reverse=True)]
            lastfm_timeline_data = [{'month': m, 'plays': p} for m, p in sorted(lastfm_monthly.items())]
            
            listenbrainz_tracks_data = [{'track': t, 'plays': p} for t, p in sorted(listenbrainz_tracks.items(), key=lambda x: x[1], reverse=True)]
            listenbrainz_timeline_data = [{'month': m, 'plays': p} for m, p in sorted(listenbrainz_monthly.items())]
            
            from stats_manager import StatsManager
            stats_manager = StatsManager(self.db_manager.db_path, self.config)
            
            charts = {}
            
            if lastfm_tracks_data:
                charts['lastfm_tracks'] = stats_manager.create_chart('bar', lastfm_tracks_data[:10],
                                        f'Top canciones de "{album_name}" en Last.fm', 'track', 'plays')
            
            if lastfm_timeline_data:
                charts['lastfm_timeline'] = stats_manager.create_chart('line', lastfm_timeline_data,
                                        f'Escuchas de "{album_name}" en Last.fm por mes', 'month', 'plays')
            
            if listenbrainz_tracks_data:
                charts['listenbrainz_tracks'] = stats_manager.create_chart('bar', listenbrainz_tracks_data[:10],
                                        f'Top canciones de "{album_name}" en ListenBrainz', 'track', 'plays')
            
            if listenbrainz_timeline_data:
                charts['listenbrainz_timeline'] = stats_manager.create_chart('line', listenbrainz_timeline_data,
                                        f'Escuchas de "{album_name}" en ListenBrainz por mes', 'month', 'plays')
            
            return {
                'charts': charts,
                'stats': {
                    'total_lastfm_plays': sum(lastfm_tracks.values()),
                    'total_listenbrainz_plays': sum(listenbrainz_tracks.values()),
                    'tracks_with_lastfm_plays': len(lastfm_tracks),
                    'tracks_with_listenbrainz_plays': len(listenbrainz_tracks),
                    'top_lastfm_track': max(lastfm_tracks.items(), key=lambda x: x[1])[0] if lastfm_tracks else 'N/A',
                    'top_listenbrainz_track': max(listenbrainz_tracks.items(), key=lambda x: x[1])[0] if listenbrainz_tracks else 'N/A'
                }
            }
            
        except Exception as e:
            logger.error(f"Error en análisis de escuchas del álbum: {e}")
            return {'error': str(e)}
    
    def _get_album_collaborators_analysis(self, album_id):
        """Análisis de colaboradores del álbum"""
        try:
            # Obtener el álbum primero
            album = self.db_manager.get_album_by_id(album_id)
            if not album:
                return {'error': 'Álbum no encontrado'}
                
            artist_id = album.get('artist_id')
            album_name = album.get('name', '')
            
            # Obtener colaboradores del álbum actual
            album_collaborators = self._extract_album_collaborators(album)
            
            if not album_collaborators:
                return {'error': 'No se encontraron colaboradores para este álbum'}
            
            # Obtener colaboradores de todos los álbumes del artista
            artist_albums_query = """
                SELECT id, name, producers, engineers, credits
                FROM albums
                WHERE artist_id = ? AND id != ?
            """
            other_albums = self.db_manager.execute_query(artist_albums_query, (artist_id, album_id))
            
            # Analizar colaboradores en toda la discografía
            all_collaborators = Counter()
            album_collaborators_count = Counter(album_collaborators)
            
            for other_album in other_albums:
                other_collaborators = self._extract_album_collaborators(dict(other_album))
                for collaborator in other_collaborators:
                    all_collaborators[collaborator] += 1
            
            # Datos para gráficos
            album_collab_data = [{'collaborator': c, 'count': count} 
                               for c, count in album_collaborators_count.most_common(15)]
            
            artist_collab_data = [{'collaborator': c, 'albums': count} 
                                for c, count in all_collaborators.most_common(15)]
            
            from stats_manager import StatsManager
            stats_manager = StatsManager(self.db_manager.db_path, self.config)
            
            charts = {}
            
            if album_collab_data:
                charts['album_collaborators'] = stats_manager.create_chart('pie', album_collab_data,
                                            f'Colaboradores en "{album_name}"', 'collaborator', 'count')
            
            if artist_collab_data:
                charts['artist_collaborators'] = stats_manager.create_chart('bar', artist_collab_data,
                                            f'Colaboradores frecuentes del artista', 'collaborator', 'albums')
            
            return {
                'charts': charts,
                'stats': {
                    'album_collaborators': len(album_collaborators_count),
                    'artist_total_collaborators': len(all_collaborators),
                    'most_frequent_in_album': album_collaborators_count.most_common(1)[0][0] if album_collaborators_count else 'N/A',
                    'most_frequent_in_artist': all_collaborators.most_common(1)[0][0] if all_collaborators else 'N/A'
                }
            }
            
        except Exception as e:
            logger.error(f"Error en análisis de colaboradores del álbum: {e}")
            return {'error': str(e)}
    
    def _extract_album_collaborators(self, album):
        """Extrae colaboradores de un álbum desde los campos JSON"""
        collaborators = []
        
        for field in ['producers', 'engineers', 'credits']:
            value = album.get(field)
            if not value:
                continue
            
            try:
                if value.strip().startswith('{') or value.strip().startswith('['):
                    data = json.loads(value)
                    if isinstance(data, dict):
                        for role, names in data.items():
                            if isinstance(names, list):
                                collaborators.extend([name.strip() for name in names[:3] if isinstance(name, str)])
                            elif isinstance(names, str):
                                collaborators.append(names.strip())
                    elif isinstance(data, list):
                        collaborators.extend([str(item).strip() for item in data[:5]])
                else:
                    # Fallback: tratar como string separado por comas
                    items = [item.strip() for item in value.split(',')]
                    collaborators.extend(items[:5])
            except (json.JSONDecodeError, TypeError):
                # Fallback final
                items = [item.strip() for item in str(value).split(',')]
                collaborators.extend(items[:3])
        
        # Filtrar colaboradores válidos
        return [c for c in collaborators if c and len(c) > 2]
    
    def _get_album_feeds_analysis(self, album_id):
        """Análisis de feeds del álbum"""
        try:
            # Obtener el álbum primero
            album = self.db_manager.get_album_by_id(album_id)
            if not album:
                return {'error': 'Álbum no encontrado'}
                
            artist_id = album.get('artist_id')
            album_name = album.get('name', '')
            
            # Buscar menciones del álbum en feeds
            feeds_query = """
                SELECT f.feed_name, f.post_title, f.post_url, f.post_date
                FROM feeds f
                JOIN menciones m ON f.id = m.feed_id
                WHERE m.artist_id = ? AND (
                    f.post_title LIKE ? OR f.content LIKE ?
                )
                ORDER BY f.post_date DESC
                LIMIT 50
            """
            
            album_search = f"%{album_name}%"
            feeds_data = self.db_manager.execute_query(feeds_query, (artist_id, album_search, album_search))
            
            if not feeds_data:
                return {'error': f'No se encontraron feeds mencionando "{album_name}"'}
            
            # Analizar feeds por año y fuente
            feeds_by_year = defaultdict(int)
            feeds_by_source = Counter()
            feeds_list = []
            
            for row in feeds_data:
                feeds_list.append({
                    'feed_name': row['feed_name'],
                    'post_title': row['post_title'],
                    'post_url': row['post_url'],
                    'post_date': row['post_date']
                })
                
                feeds_by_source[row['feed_name']] += 1
                
                try:
                    year = row['post_date'][:4] if row['post_date'] else 'Unknown'
                    if year != 'Unknown':
                        feeds_by_year[year] += 1
                except:
                    pass
            
            # Datos para gráficos
            years_data = [{'year': year, 'count': count} for year, count in sorted(feeds_by_year.items())]
            sources_data = [{'source': source, 'count': count} for source, count in feeds_by_source.most_common(10)]
            
            from stats_manager import StatsManager
            stats_manager = StatsManager(self.db_manager.db_path, self.config)
            
            charts = {}
            
            if years_data:
                charts['feeds_timeline'] = stats_manager.create_chart('line', years_data,
                                        f'Menciones de "{album_name}" por año', 'year', 'count')
            
            if sources_data:
                charts['feeds_sources'] = stats_manager.create_chart('pie', sources_data,
                                        f'Fuentes que mencionan "{album_name}"', 'source', 'count')
            
            return {
                'charts': charts,
                'stats': {
                    'total_mentions': len(feeds_data),
                    'total_sources': len(feeds_by_source),
                    'years_mentioned': len(feeds_by_year),
                    'most_active_source': feeds_by_source.most_common(1)[0][0] if feeds_by_source else 'N/A'
                },
                'recent_feeds': feeds_list[:10]
            }
            
        except Exception as e:
            logger.error(f"Error en análisis de feeds del álbum: {e}")
            return {'error': str(e)}
    
    def _get_album_lyrics_analysis(self, album_id):
        """Análisis de letras del álbum"""
        try:
            # Obtener el álbum primero
            album = self.db_manager.get_album_by_id(album_id)
            if not album:
                return {'error': 'Álbum no encontrado'}
                
            album_name = album.get('name', '')
            
            # Obtener letras de las canciones del álbum
            lyrics_query = """
                SELECT s.title, l.lyrics
                FROM songs s
                JOIN lyrics l ON s.lyrics_id = l.id
                WHERE s.album = ? AND s.artist = ?
                AND l.lyrics IS NOT NULL AND l.lyrics != ''
            """
            
            artist_name = album.get('artist_name', '')
            lyrics_data = self.db_manager.execute_query(lyrics_query, (album_name, artist_name))
            
            if not lyrics_data:
                return {'error': f'No se encontraron letras para las canciones de "{album_name}"'}
            
            # Analizar palabras en las letras
            all_words = []
            
            # Palabras a excluir (artículos y palabras comunes en inglés y español)
            stop_words = {
                'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must', 'shall',
                'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'de', 'del', 'en', 'con', 'por', 'para', 'que', 'es', 'son', 'fue', 'era', 'estar', 'estoy', 'estas', 'esta', 'esto', 'ese', 'esa', 'esos', 'esas', 'su', 'sus', 'mi', 'mis', 'tu', 'tus',
                'you', 'me', 'my', 'your', 'his', 'her', 'its', 'our', 'their', 'i', 'he', 'she', 'it', 'we', 'they', 'this', 'that', 'these', 'those', 'a', 'an',
                'yo', 'tu', 'él', 'ella', 'nosotros', 'nosotras', 'vosotros', 'vosotras', 'ellos', 'ellas', 'mi', 'tu', 'su', 'nuestro', 'nuestra', 'vuestro', 'vuestra'
            }
            
            for row in lyrics_data:
                lyrics = row['lyrics'].lower()
                # Limpiar y extraer palabras
                words = re.findall(r'\b[a-záéíóúñü]{3,}\b', lyrics)
                # Filtrar palabras válidas
                valid_words = [word for word in words if word not in stop_words]
                all_words.extend(valid_words)
            
            if not all_words:
                return {'error': 'No se encontraron palabras válidas en las letras'}
            
            # Contar palabras más frecuentes
            word_counts = Counter(all_words)
            most_common = word_counts.most_common(20)
            
            # Análisis por canción
            songs_word_count = []
            for row in lyrics_data:
                lyrics = row['lyrics'].lower()
                words = re.findall(r'\b[a-záéíóúñü]{3,}\b', lyrics)
                valid_words = [word for word in words if word not in stop_words]
                songs_word_count.append({
                    'song': row['title'],
                    'words': len(valid_words),
                    'unique_words': len(set(valid_words))
                })
            
            # Datos para gráficos
            words_chart_data = [{'word': word, 'count': count} for word, count in most_common]
            songs_chart_data = sorted(songs_word_count, key=lambda x: x['words'], reverse=True)
            
            from stats_manager import StatsManager
            stats_manager = StatsManager(self.db_manager.db_path, self.config)
            
            charts = {}
            
            if words_chart_data:
                charts['most_common_words'] = stats_manager.create_chart('pie', words_chart_data[:15],
                                            f'Palabras más frecuentes en "{album_name}"', 'word', 'count')
            
            if songs_chart_data:
                charts['songs_wordcount'] = stats_manager.create_chart('bar', songs_chart_data,
                                            f'Cantidad de palabras por canción', 'song', 'words')
            
            return {
                'charts': charts,
                'stats': {
                    'songs_with_lyrics': len(lyrics_data),
                    'total_words': len(all_words),
                    'unique_words': len(word_counts),
                    'most_common_word': most_common[0][0] if most_common else 'N/A',
                    'average_words_per_song': round(len(all_words) / len(lyrics_data), 1) if lyrics_data else 0
                },
                'top_words': [{'word': word, 'count': count} for word, count in most_common[:10]]
            }
            
        except Exception as e:
            logger.error(f"Error en análisis de letras del álbum: {e}")
            return {'error': str(e)}