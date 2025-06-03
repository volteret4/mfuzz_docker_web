#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import json
import os
from collections import Counter, defaultdict
from flask import jsonify, request
import re
from datetime import datetime, timedelta
import sqlite3

logger = logging.getLogger(__name__)

class ScrobblesAnalysisEndpoints:
    """Endpoints específicos para análisis detallado de escuchas/scrobbles"""
    
    def __init__(self, app, db_manager, config):
        self.app = app
        self.db_manager = db_manager
        self.config = config
        self.setup_scrobbles_analysis_routes()
    
    def setup_scrobbles_analysis_routes(self):
        """Configura las rutas para análisis de escuchas"""
        
        @self.app.route('/api/scrobbles/analysis/<analysis_type>')
        def api_scrobbles_analysis(analysis_type):
            """Endpoint para análisis de escuchas/scrobbles"""
            try:
                logger.info(f"Análisis de scrobbles: tipo={analysis_type}")
                
                # Crear análisis según el tipo
                if analysis_type == 'tiempo':
                    return jsonify(self._get_scrobbles_time_analysis())
                elif analysis_type == 'generos':
                    return jsonify(self._get_scrobbles_genres_analysis())
                elif analysis_type == 'calidad':
                    return jsonify(self._get_scrobbles_quality_analysis())
                elif analysis_type == 'descubrimiento':
                    return jsonify(self._get_scrobbles_discovery_analysis())
                elif analysis_type == 'evolucion':
                    return jsonify(self._get_scrobbles_evolution_analysis())
                elif analysis_type == 'sellos':
                    return jsonify(self._get_scrobbles_labels_analysis())
                elif analysis_type == 'colaboradores':
                    return jsonify(self._get_scrobbles_collaborators_analysis())
                elif analysis_type == 'duracion':
                    return jsonify(self._get_scrobbles_duration_analysis())
                elif analysis_type == 'idiomas':
                    return jsonify(self._get_scrobbles_languages_analysis())
                else:
                    return jsonify({'error': f'Tipo de análisis no soportado: {analysis_type}'}), 400
                    
            except Exception as e:
                logger.error(f"Error en análisis {analysis_type} de scrobbles: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'error': str(e)}), 500
    
    def _get_scrobbles_time_analysis(self):
        """Análisis temporal de scrobbles"""
        try:
            # Evolución de scrobbles por año
            yearly_query = """
                SELECT substr(scrobble_date, 1, 4) as year, 
                       COUNT(*) as scrobbles
                FROM scrobbles_paqueradejere 
                WHERE scrobble_date IS NOT NULL 
                GROUP BY year
                ORDER BY year
            """
            yearly_data = self.db_manager.execute_query(yearly_query)
            
            # Scrobbles por mes del último año
            monthly_query = """
                SELECT substr(scrobble_date, 1, 7) as month,
                       COUNT(*) as scrobbles
                FROM scrobbles_paqueradejere 
                WHERE scrobble_date >= date('now', '-12 months')
                GROUP BY month
                ORDER BY month
            """
            monthly_data = self.db_manager.execute_query(monthly_query)
            
            # Patrones por día de la semana
            weekday_query = """
                SELECT 
                    CASE cast(strftime('%w', scrobble_date) as integer)
                        WHEN 0 THEN 'Domingo'
                        WHEN 1 THEN 'Lunes'
                        WHEN 2 THEN 'Martes'
                        WHEN 3 THEN 'Miércoles'
                        WHEN 4 THEN 'Jueves'
                        WHEN 5 THEN 'Viernes'
                        WHEN 6 THEN 'Sábado'
                    END as weekday,
                    COUNT(*) as scrobbles
                FROM scrobbles_paqueradejere 
                WHERE scrobble_date IS NOT NULL
                GROUP BY strftime('%w', scrobble_date)
                ORDER BY cast(strftime('%w', scrobble_date) as integer)
            """
            weekday_data = self.db_manager.execute_query(weekday_query)
            
            # Preparar datos para gráficos
            yearly_chart_data = [{'year': int(row['year']), 'scrobbles': row['scrobbles']} 
                               for row in yearly_data if row['year'].isdigit()]
            
            monthly_chart_data = [{'month': row['month'], 'scrobbles': row['scrobbles']} 
                                for row in monthly_data]
            
            weekday_chart_data = [{'weekday': row['weekday'], 'scrobbles': row['scrobbles']} 
                                for row in weekday_data]
            
            from stats_manager import StatsManager
            stats_manager = StatsManager(self.db_manager.db_path, self.config)
            
            charts = {}
            
            if yearly_chart_data:
                charts['yearly_evolution'] = stats_manager.create_chart('line', yearly_chart_data,
                                            'Evolución de Scrobbles por Año', 'year', 'scrobbles')
            
            if monthly_chart_data:
                charts['monthly_trend'] = stats_manager.create_chart('line', monthly_chart_data,
                                            'Scrobbles por Mes (Último Año)', 'month', 'scrobbles')
            
            if weekday_chart_data:
                charts['weekday_pattern'] = stats_manager.create_chart('bar', weekday_chart_data,
                                            'Patrones por Día de la Semana', 'weekday', 'scrobbles')
            
            return {
                'charts': charts,
                'stats': {
                    'total_scrobbles': sum(row['scrobbles'] for row in yearly_data),
                    'years_tracked': len(yearly_chart_data),
                    'peak_year': max(yearly_chart_data, key=lambda x: x['scrobbles'])['year'] if yearly_chart_data else 'N/A',
                    'avg_monthly_last_year': round(sum(row['scrobbles'] for row in monthly_data) / len(monthly_data), 1) if monthly_data else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error en análisis temporal de scrobbles: {e}")
            return {'error': str(e)}
    
    def _get_scrobbles_genres_analysis(self):
        """Análisis de géneros en scrobbles"""
        try:
            # Géneros más escuchados
            genres_query = """
                SELECT s.genre, COUNT(*) as scrobbles
                FROM scrobbles_paqueradejere sp
                JOIN songs s ON s.artist = sp.artist_name AND s.title = sp.track_name
                WHERE s.genre IS NOT NULL AND s.genre != ''
                GROUP BY s.genre
                ORDER BY scrobbles DESC
                LIMIT 15
            """
            genres_data = self.db_manager.execute_query(genres_query)
            
            # Evolución de géneros top en el tiempo
            genre_evolution_query = """
                SELECT s.genre, 
                       substr(sp.scrobble_date, 1, 4) as year,
                       COUNT(*) as scrobbles
                FROM scrobbles_paqueradejere sp
                JOIN songs s ON s.artist = sp.artist_name AND s.title = sp.track_name
                WHERE s.genre IN (
                    SELECT s2.genre 
                    FROM scrobbles_paqueradejere sp2
                    JOIN songs s2 ON s2.artist = sp2.artist_name AND s2.title = sp2.track_name
                    WHERE s2.genre IS NOT NULL 
                    GROUP BY s2.genre 
                    ORDER BY COUNT(*) DESC 
                    LIMIT 5
                )
                GROUP BY s.genre, year
                ORDER BY year, scrobbles DESC
            """
            evolution_data = self.db_manager.execute_query(genre_evolution_query)
            
            # Géneros emergentes (últimos 6 meses vs anteriores)
            emerging_query = """
                WITH recent AS (
                    SELECT s.genre, COUNT(*) as recent_count
                    FROM scrobbles_paqueradejere sp
                    JOIN songs s ON s.artist = sp.artist_name AND s.title = sp.track_name
                    WHERE sp.scrobble_date >= date('now', '-6 months')
                    AND s.genre IS NOT NULL
                    GROUP BY s.genre
                ), 
                previous AS (
                    SELECT s.genre, COUNT(*) as previous_count
                    FROM scrobbles_paqueradejere sp
                    JOIN songs s ON s.artist = sp.artist_name AND s.title = sp.track_name
                    WHERE sp.scrobble_date BETWEEN date('now', '-12 months') AND date('now', '-6 months')
                    AND s.genre IS NOT NULL
                    GROUP BY s.genre
                )
                SELECT r.genre,
                       r.recent_count,
                       COALESCE(p.previous_count, 0) as previous_count,
                       CASE 
                           WHEN COALESCE(p.previous_count, 0) = 0 THEN 100
                           ELSE ROUND((r.recent_count - p.previous_count) * 100.0 / p.previous_count, 1)
                       END as growth_percentage
                FROM recent r
                LEFT JOIN previous p ON r.genre = p.genre
                WHERE r.recent_count >= 5
                ORDER BY growth_percentage DESC
                LIMIT 10
            """
            emerging_data = self.db_manager.execute_query(emerging_query)
            
            # Preparar datos para gráficos
            genres_chart_data = [{'genre': row['genre'], 'scrobbles': row['scrobbles']} 
                               for row in genres_data]
            
            evolution_chart_data = [{'genre': row['genre'], 'year': int(row['year']), 'scrobbles': row['scrobbles']} 
                                  for row in evolution_data if row['year'].isdigit()]
            
            emerging_chart_data = [{'genre': row['genre'], 'growth': row['growth_percentage']} 
                                 for row in emerging_data]
            
            from stats_manager import StatsManager
            stats_manager = StatsManager(self.db_manager.db_path, self.config)
            
            charts = {
                'top_genres': stats_manager.create_chart('pie', genres_chart_data,
                                    'Géneros Más Escuchados', 'genre', 'scrobbles'),
                'genre_evolution': stats_manager.create_chart('line', evolution_chart_data,
                                    'Evolución de Top Géneros', 'year', 'scrobbles'),
                'emerging_genres': stats_manager.create_chart('bar', emerging_chart_data,
                                    'Géneros Emergentes (% Crecimiento)', 'genre', 'growth')
            }
            
            return {
                'charts': charts,
                'stats': {
                    'total_genres': len(genres_data),
                    'top_genre': genres_data[0]['genre'] if genres_data else 'N/A',
                    'top_genre_scrobbles': genres_data[0]['scrobbles'] if genres_data else 0,
                    'fastest_growing': emerging_data[0]['genre'] if emerging_data else 'N/A'
                }
            }
            
        except Exception as e:
            logger.error(f"Error en análisis de géneros de scrobbles: {e}")
            return {'error': str(e)}
    
    def _get_scrobbles_quality_analysis(self):
        """Análisis de calidad de audio vs scrobbles"""
        try:
            # Scrobbles por bitrate
            bitrate_query = """
                SELECT s.bitrate, COUNT(*) as scrobbles
                FROM scrobbles_paqueradejere sp
                JOIN songs s ON s.artist = sp.artist_name AND s.title = sp.track_name
                WHERE s.bitrate IS NOT NULL AND s.bitrate > 0
                GROUP BY s.bitrate
                ORDER BY scrobbles DESC
            """
            bitrate_data = self.db_manager.execute_query(bitrate_query)
            
            # Scrobbles por sample rate
            samplerate_query = """
                SELECT s.sample_rate, COUNT(*) as scrobbles
                FROM scrobbles_paqueradejere sp
                JOIN songs s ON s.artist = sp.artist_name AND s.title = sp.track_name
                WHERE s.sample_rate IS NOT NULL AND s.sample_rate > 0
                GROUP BY s.sample_rate
                ORDER BY scrobbles DESC
            """
            samplerate_data = self.db_manager.execute_query(samplerate_query)
            
            # Scrobbles por formato de archivo (extraído de file_path)
            format_query = """
                SELECT 
                    CASE 
                        WHEN s.file_path LIKE '%.mp3' THEN 'MP3'
                        WHEN s.file_path LIKE '%.flac' THEN 'FLAC'
                        WHEN s.file_path LIKE '%.ogg' THEN 'OGG'
                        WHEN s.file_path LIKE '%.m4a' THEN 'M4A'
                        WHEN s.file_path LIKE '%.wav' THEN 'WAV'
                        ELSE 'Otro'
                    END as format,
                    COUNT(*) as scrobbles
                FROM scrobbles_paqueradejere sp
                JOIN songs s ON s.artist = sp.artist_name AND s.title = sp.track_name
                WHERE s.file_path IS NOT NULL
                GROUP BY format
                ORDER BY scrobbles DESC
            """
            format_data = self.db_manager.execute_query(format_query)
            
            # Preparar datos para gráficos
            bitrate_chart_data = [{'bitrate': f"{row['bitrate']} kbps", 'scrobbles': row['scrobbles']} 
                                for row in bitrate_data]
            
            samplerate_chart_data = [{'sample_rate': f"{row['sample_rate']} Hz", 'scrobbles': row['scrobbles']} 
                                   for row in samplerate_data]
            
            format_chart_data = [{'format': row['format'], 'scrobbles': row['scrobbles']} 
                               for row in format_data]
            
            from stats_manager import StatsManager
            stats_manager = StatsManager(self.db_manager.db_path, self.config)
            
            charts = {
                'bitrate_distribution': stats_manager.create_chart('pie', bitrate_chart_data,
                                        'Distribución por Bitrate', 'bitrate', 'scrobbles'),
                'samplerate_distribution': stats_manager.create_chart('pie', samplerate_chart_data,
                                        'Distribución por Sample Rate', 'sample_rate', 'scrobbles'),
                'format_distribution': stats_manager.create_chart('pie', format_chart_data,
                                        'Distribución por Formato', 'format', 'scrobbles')
            }
            
            return {
                'charts': charts,
                'stats': {
                    'most_common_bitrate': bitrate_data[0]['bitrate'] if bitrate_data else 'N/A',
                    'most_common_samplerate': samplerate_data[0]['sample_rate'] if samplerate_data else 'N/A',
                    'most_common_format': format_data[0]['format'] if format_data else 'N/A',
                    'quality_variations': len(bitrate_data)
                }
            }
            
        except Exception as e:
            logger.error(f"Error en análisis de calidad de scrobbles: {e}")
            return {'error': str(e)}
    
    def _get_scrobbles_discovery_analysis(self):
        """Análisis de descubrimiento de música"""
        try:
            # Tiempo promedio entre añadir canción y primera escucha
            discovery_time_query = """
                SELECT 
                    AVG(julianday(MIN(sp.scrobble_date)) - julianday(s.added_timestamp)) as avg_discovery_days
                FROM songs s
                JOIN scrobbles_paqueradejere sp ON s.artist = sp.artist_name AND s.title = sp.track_name
                WHERE s.added_timestamp IS NOT NULL 
                AND sp.scrobble_date IS NOT NULL
                GROUP BY s.id
                HAVING avg_discovery_days >= 0
            """
            discovery_result = self.db_manager.execute_query(discovery_time_query)
            
            # Distribución de tiempo de descubrimiento
            discovery_dist_query = """
                WITH discovery_times AS (
                    SELECT 
                        s.id,
                        julianday(MIN(sp.scrobble_date)) - julianday(s.added_timestamp) as days_to_discover
                    FROM songs s
                    JOIN scrobbles_paqueradejere sp ON s.artist = sp.artist_name AND s.title = sp.track_name
                    WHERE s.added_timestamp IS NOT NULL 
                    AND sp.scrobble_date IS NOT NULL
                    GROUP BY s.id
                    HAVING days_to_discover >= 0
                )
                SELECT 
                    CASE 
                        WHEN days_to_discover <= 1 THEN 'Mismo día'
                        WHEN days_to_discover <= 7 THEN '1-7 días'
                        WHEN days_to_discover <= 30 THEN '1-4 semanas'
                        WHEN days_to_discover <= 90 THEN '1-3 meses'
                        WHEN days_to_discover <= 365 THEN '3-12 meses'
                        ELSE 'Más de 1 año'
                    END as time_range,
                    COUNT(*) as songs_count
                FROM discovery_times
                GROUP BY time_range
                ORDER BY 
                    CASE time_range
                        WHEN 'Mismo día' THEN 1
                        WHEN '1-7 días' THEN 2
                        WHEN '1-4 semanas' THEN 3
                        WHEN '1-3 meses' THEN 4
                        WHEN '3-12 meses' THEN 5
                        ELSE 6
                    END
            """
            discovery_dist_data = self.db_manager.execute_query(discovery_dist_query)
            
            # Canciones redescubiertas (con gaps largos entre scrobbles)
            rediscovery_query = """
                WITH scrobble_gaps AS (
                    SELECT 
                        sp.artist_name || ' - ' || sp.track_name as song,
                        julianday(sp.scrobble_date) - 
                        julianday(LAG(sp.scrobble_date) OVER (
                            PARTITION BY sp.artist_name, sp.track_name 
                            ORDER BY sp.scrobble_date
                        )) as gap_days
                    FROM scrobbles_paqueradejere sp
                )
                SELECT song, MAX(gap_days) as longest_gap
                FROM scrobble_gaps
                WHERE gap_days > 180  -- 6 meses o más
                GROUP BY song
                ORDER BY longest_gap DESC
                LIMIT 10
            """
            rediscovery_data = self.db_manager.execute_query(rediscovery_query)
            
            # Preparar datos para gráficos
            discovery_chart_data = [{'time_range': row['time_range'], 'count': row['songs_count']} 
                                  for row in discovery_dist_data]
            
            rediscovery_chart_data = [{'song': row['song'][:50] + '...' if len(row['song']) > 50 else row['song'], 
                                     'gap_days': round(row['longest_gap'])} 
                                    for row in rediscovery_data]
            
            from stats_manager import StatsManager
            stats_manager = StatsManager(self.db_manager.db_path, self.config)
            
            charts = {}
            
            if discovery_chart_data:
                charts['discovery_distribution'] = stats_manager.create_chart('bar', discovery_chart_data,
                                            'Tiempo de Descubrimiento', 'time_range', 'count')
            
            if rediscovery_chart_data:
                charts['rediscovery_gaps'] = stats_manager.create_chart('bar', rediscovery_chart_data,
                                            'Canciones Redescubiertas (días sin escuchar)', 'song', 'gap_days')
            
            avg_discovery = discovery_result[0]['avg_discovery_days'] if discovery_result else 0
            
            return {
                'charts': charts,
                'stats': {
                    'avg_discovery_days': round(avg_discovery, 1) if avg_discovery else 0,
                    'songs_analyzed': len(discovery_dist_data),
                    'rediscovered_songs': len(rediscovery_data),
                    'longest_rediscovery_gap': round(rediscovery_data[0]['longest_gap']) if rediscovery_data else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error en análisis de descubrimiento de scrobbles: {e}")
            return {'error': str(e)}
    
    def _get_scrobbles_evolution_analysis(self):
        """Análisis de evolución de artistas en el tiempo"""
        try:
            # Top artistas más escuchados
            top_artists_query = """
                SELECT artist_name, COUNT(*) as scrobbles
                FROM scrobbles_paqueradejere
                GROUP BY artist_name
                ORDER BY scrobbles DESC
                LIMIT 15
            """
            top_artists_data = self.db_manager.execute_query(top_artists_query)
            
            # Evolución temporal de top 5 artistas
            evolution_query = """
                SELECT 
                    artist_name,
                    substr(scrobble_date, 1, 7) as month,
                    COUNT(*) as monthly_scrobbles
                FROM scrobbles_paqueradejere
                WHERE artist_name IN (
                    SELECT artist_name 
                    FROM scrobbles_paqueradejere 
                    GROUP BY artist_name 
                    ORDER BY COUNT(*) DESC 
                    LIMIT 5
                )
                AND scrobble_date >= date('now', '-24 months')
                GROUP BY artist_name, month
                ORDER BY month, monthly_scrobbles DESC
            """
            evolution_data = self.db_manager.execute_query(evolution_query)
            
            # Artistas en ascenso (comparando último año vs anterior)
            rising_artists_query = """
                WITH recent AS (
                    SELECT artist_name, COUNT(*) as recent_scrobbles
                    FROM scrobbles_paqueradejere
                    WHERE scrobble_date >= date('now', '-12 months')
                    GROUP BY artist_name
                ), 
                previous AS (
                    SELECT artist_name, COUNT(*) as previous_scrobbles
                    FROM scrobbles_paqueradejere
                    WHERE scrobble_date BETWEEN date('now', '-24 months') AND date('now', '-12 months')
                    GROUP BY artist_name
                )
                SELECT 
                    r.artist_name,
                    r.recent_scrobbles,
                    COALESCE(p.previous_scrobbles, 0) as previous_scrobbles,
                    CASE 
                        WHEN COALESCE(p.previous_scrobbles, 0) = 0 THEN 999
                        ELSE ROUND((r.recent_scrobbles - p.previous_scrobbles) * 100.0 / p.previous_scrobbles, 1)
                    END as growth_percentage
                FROM recent r
                LEFT JOIN previous p ON r.artist_name = p.artist_name
                WHERE r.recent_scrobbles >= 10
                ORDER BY growth_percentage DESC
                LIMIT 10
            """
            rising_data = self.db_manager.execute_query(rising_artists_query)
            
            # Preparar datos para gráficos
            top_artists_chart_data = [{'artist': row['artist_name'], 'scrobbles': row['scrobbles']} 
                                    for row in top_artists_data]
            
            evolution_chart_data = [{'artist': row['artist_name'], 'month': row['month'], 'scrobbles': row['monthly_scrobbles']} 
                                  for row in evolution_data]
            
            rising_chart_data = [{'artist': row['artist_name'], 'growth': row['growth_percentage']} 
                               for row in rising_data if row['growth_percentage'] < 500]  # Filtrar crecimientos extremos
            
            from stats_manager import StatsManager
            stats_manager = StatsManager(self.db_manager.db_path, self.config)
            
            charts = {}
            
            if top_artists_chart_data:
                charts['top_artists'] = stats_manager.create_chart('bar', top_artists_chart_data,
                                        'Artistas Más Escuchados', 'artist', 'scrobbles')
            
            if evolution_chart_data:
                charts['artist_evolution'] = stats_manager.create_chart('line', evolution_chart_data,
                                            'Evolución Mensual (Top 5 Artistas)', 'month', 'scrobbles')
            
            if rising_chart_data:
                charts['rising_artists'] = stats_manager.create_chart('bar', rising_chart_data,
                                          'Artistas en Ascenso (% Crecimiento)', 'artist', 'growth')
            
            return {
                'charts': charts,
                'stats': {
                    'top_artist': top_artists_data[0]['artist_name'] if top_artists_data else 'N/A',
                    'top_artist_scrobbles': top_artists_data[0]['scrobbles'] if top_artists_data else 0,
                    'artists_tracked': len(top_artists_data),
                    'fastest_rising': rising_data[0]['artist_name'] if rising_data else 'N/A'
                }
            }
            
        except Exception as e:
            logger.error(f"Error en análisis de evolución de scrobbles: {e}")
            return {'error': str(e)}
    
    def _get_scrobbles_labels_analysis(self):
        """Análisis de sellos discográficos vs scrobbles"""
        try:
            # Scrobbles por sello
            labels_query = """
                SELECT a.label, COUNT(*) as scrobbles
                FROM scrobbles_paqueradejere sp
                JOIN songs s ON s.artist = sp.artist_name AND s.title = sp.track_name
                JOIN albums a ON a.artist_id = s.artist_id AND a.name = s.album
                WHERE a.label IS NOT NULL AND a.label != ''
                GROUP BY a.label
                ORDER BY scrobbles DESC
                LIMIT 15
            """
            labels_data = self.db_manager.execute_query(labels_query)
            
            # Evolución temporal de top sellos
            labels_evolution_query = """
                SELECT 
                    a.label,
                    substr(sp.scrobble_date, 1, 4) as year,
                    COUNT(*) as scrobbles
                FROM scrobbles_paqueradejere sp
                JOIN songs s ON s.artist = sp.artist_name AND s.title = sp.track_name
                JOIN albums a ON a.artist_id = s.artist_id AND a.name = s.album
                WHERE a.label IN (
                    SELECT a2.label
                    FROM scrobbles_paqueradejere sp2
                    JOIN songs s2 ON s2.artist = sp2.artist_name AND s2.title = sp2.track_name
                    JOIN albums a2 ON a2.artist_id = s2.artist_id AND a2.name = s2.album
                    WHERE a2.label IS NOT NULL 
                    GROUP BY a2.label 
                    ORDER BY COUNT(*) DESC 
                    LIMIT 5
                )
                GROUP BY a.label, year
                ORDER BY year, scrobbles DESC
            """
            evolution_data = self.db_manager.execute_query(labels_evolution_query)
            
            # Preparar datos para gráficos
            labels_chart_data = [{'label': row['label'], 'scrobbles': row['scrobbles']} 
                               for row in labels_data]
            
            evolution_chart_data = [{'label': row['label'], 'year': int(row['year']), 'scrobbles': row['scrobbles']} 
                                  for row in evolution_data if row['year'].isdigit()]
            
            from stats_manager import StatsManager
            stats_manager = StatsManager(self.db_manager.db_path, self.config)
            
            charts = {}
            
            if labels_chart_data:
                charts['top_labels'] = stats_manager.create_chart('pie', labels_chart_data,
                                      'Sellos Más Escuchados', 'label', 'scrobbles')
            
            if evolution_chart_data:
                charts['labels_evolution'] = stats_manager.create_chart('line', evolution_chart_data,
                                            'Evolución de Top Sellos', 'year', 'scrobbles')
            
            return {
                'charts': charts,
                'stats': {
                    'top_label': labels_data[0]['label'] if labels_data else 'N/A',
                    'top_label_scrobbles': labels_data[0]['scrobbles'] if labels_data else 0,
                    'labels_tracked': len(labels_data)
                }
            }
            
        except Exception as e:
            logger.error(f"Error en análisis de sellos de scrobbles: {e}")
            return {'error': str(e)}
    
    def _get_scrobbles_collaborators_analysis(self):
        """Análisis de colaboradores vs popularidad"""
        try:
            # Productores más asociados con canciones populares (simplificado)
            producers_query = """
                SELECT 
                    a.producers as producer_info,
                    COUNT(*) as scrobbles
                FROM scrobbles_paqueradejere sp
                JOIN songs s ON s.artist = sp.artist_name AND s.title = sp.track_name
                JOIN albums a ON a.artist_id = s.artist_id AND a.name = s.album
                WHERE a.producers IS NOT NULL AND a.producers != ''
                GROUP BY a.producers
                ORDER BY scrobbles DESC
                LIMIT 10
            """
            producers_data = self.db_manager.execute_query(producers_query)
            
            # Ingenieros más asociados con canciones populares
            engineers_query = """
                SELECT 
                    a.engineers as engineer_info,
                    COUNT(*) as scrobbles
                FROM scrobbles_paqueradejere sp
                JOIN songs s ON s.artist = sp.artist_name AND s.title = sp.track_name
                JOIN albums a ON a.artist_id = s.artist_id AND a.name = s.album
                WHERE a.engineers IS NOT NULL AND a.engineers != ''
                GROUP BY a.engineers
                ORDER BY scrobbles DESC
                LIMIT 10
            """
            engineers_data = self.db_manager.execute_query(engineers_query)
            
            # Análisis de diversidad de colaboradores por artista
            collaboration_diversity_query = """
                SELECT 
                    sp.artist_name,
                    COUNT(DISTINCT a.producers) + COUNT(DISTINCT a.engineers) as unique_collaborators,
                    COUNT(*) as total_scrobbles
                FROM scrobbles_paqueradejere sp
                JOIN songs s ON s.artist = sp.artist_name AND s.title = sp.track_name
                JOIN albums a ON a.artist_id = s.artist_id AND a.name = s.album
                WHERE (a.producers IS NOT NULL OR a.engineers IS NOT NULL)
                GROUP BY sp.artist_name
                HAVING total_scrobbles >= 20
                ORDER BY unique_collaborators DESC
                LIMIT 15
            """
            diversity_data = self.db_manager.execute_query(collaboration_diversity_query)
            
            # Preparar datos para gráficos
            producers_chart_data = []
            for row in producers_data:
                # Simplificar el nombre del productor
                producer_name = row['producer_info'][:30] + '...' if len(row['producer_info']) > 30 else row['producer_info']
                producers_chart_data.append({'producer': producer_name, 'scrobbles': row['scrobbles']})
            
            engineers_chart_data = []
            for row in engineers_data:
                engineer_name = row['engineer_info'][:30] + '...' if len(row['engineer_info']) > 30 else row['engineer_info']
                engineers_chart_data.append({'engineer': engineer_name, 'scrobbles': row['scrobbles']})
            
            diversity_chart_data = [{'artist': row['artist_name'], 'collaborators': row['unique_collaborators']} 
                                  for row in diversity_data]
            
            from stats_manager import StatsManager
            stats_manager = StatsManager(self.db_manager.db_path, self.config)
            
            charts = {}
            
            if producers_chart_data:
                charts['top_producers'] = stats_manager.create_chart('bar', producers_chart_data,
                                         'Productores Más Escuchados', 'producer', 'scrobbles')
            
            if engineers_chart_data:
                charts['top_engineers'] = stats_manager.create_chart('bar', engineers_chart_data,
                                         'Ingenieros Más Escuchados', 'engineer', 'scrobbles')
            
            if diversity_chart_data:
                charts['collaboration_diversity'] = stats_manager.create_chart('bar', diversity_chart_data,
                                                   'Diversidad de Colaboradores por Artista', 'artist', 'collaborators')
            
            return {
                'charts': charts,
                'stats': {
                    'top_producer_scrobbles': producers_data[0]['scrobbles'] if producers_data else 0,
                    'top_engineer_scrobbles': engineers_data[0]['scrobbles'] if engineers_data else 0,
                    'most_collaborative_artist': diversity_data[0]['artist_name'] if diversity_data else 'N/A',
                    'max_collaborators': diversity_data[0]['unique_collaborators'] if diversity_data else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error en análisis de colaboradores de scrobbles: {e}")
            return {'error': str(e)}
    
    def _get_scrobbles_duration_analysis(self):
        """Análisis de duración vs popularidad"""
        try:
            # Distribución de scrobbles por duración de canciones
            duration_distribution_query = """
                SELECT 
                    CASE 
                        WHEN s.duration <= 120 THEN '0-2 min'
                        WHEN s.duration <= 180 THEN '2-3 min'
                        WHEN s.duration <= 240 THEN '3-4 min'
                        WHEN s.duration <= 300 THEN '4-5 min'
                        WHEN s.duration <= 360 THEN '5-6 min'
                        WHEN s.duration <= 480 THEN '6-8 min'
                        ELSE '8+ min'
                    END as duration_range,
                    COUNT(*) as scrobbles,
                    AVG(s.duration) as avg_duration
                FROM scrobbles_paqueradejere sp
                JOIN songs s ON s.artist = sp.artist_name AND s.title = sp.track_name
                WHERE s.duration IS NOT NULL AND s.duration > 0
                GROUP BY duration_range
                ORDER BY 
                    CASE duration_range
                        WHEN '0-2 min' THEN 1
                        WHEN '2-3 min' THEN 2
                        WHEN '3-4 min' THEN 3
                        WHEN '4-5 min' THEN 4
                        WHEN '5-6 min' THEN 5
                        WHEN '6-8 min' THEN 6
                        ELSE 7
                    END
            """
            duration_data = self.db_manager.execute_query(duration_distribution_query)
            
            # Duración promedio de álbumes más escuchados
            album_duration_query = """
                SELECT 
                    s.album,
                    sp.artist_name,
                    SUM(s.duration) as total_duration,
                    COUNT(*) as scrobbles,
                    COUNT(DISTINCT s.id) as unique_tracks
                FROM scrobbles_paqueradejere sp
                JOIN songs s ON s.artist = sp.artist_name AND s.title = sp.track_name
                WHERE s.duration IS NOT NULL AND s.album IS NOT NULL
                GROUP BY s.album, sp.artist_name
                HAVING scrobbles >= 10
                ORDER BY scrobbles DESC
                LIMIT 15
            """
            album_duration_data = self.db_manager.execute_query(album_duration_query)
            
            # Evolución de preferencias de duración en el tiempo
            duration_evolution_query = """
                SELECT 
                    substr(sp.scrobble_date, 1, 4) as year,
                    AVG(s.duration) as avg_duration
                FROM scrobbles_paqueradejere sp
                JOIN songs s ON s.artist = sp.artist_name AND s.title = sp.track_name
                WHERE s.duration IS NOT NULL AND s.duration > 0
                AND sp.scrobble_date IS NOT NULL
                GROUP BY year
                ORDER BY year
            """
            evolution_data = self.db_manager.execute_query(duration_evolution_query)
            
            # Preparar datos para gráficos
            duration_chart_data = [{'range': row['duration_range'], 'scrobbles': row['scrobbles']} 
                                 for row in duration_data]
            
            album_chart_data = [{'album': f"{row['artist_name']} - {row['album']}"[:40] + '...' if len(f"{row['artist_name']} - {row['album']}") > 40 else f"{row['artist_name']} - {row['album']}", 
                               'duration_minutes': round(row['total_duration'] / 60, 1)} 
                              for row in album_duration_data]
            
            evolution_chart_data = [{'year': int(row['year']), 'avg_duration': round(row['avg_duration'], 1)} 
                                  for row in evolution_data if row['year'].isdigit()]
            
            from stats_manager import StatsManager
            stats_manager = StatsManager(self.db_manager.db_path, self.config)
            
            charts = {}
            
            if duration_chart_data:
                charts['duration_distribution'] = stats_manager.create_chart('bar', duration_chart_data,
                                                 'Distribución por Duración', 'range', 'scrobbles')
            
            if album_chart_data:
                charts['album_durations'] = stats_manager.create_chart('bar', album_chart_data,
                                           'Duración de Álbumes Más Escuchados (min)', 'album', 'duration_minutes')
            
            if evolution_chart_data:
                charts['duration_evolution'] = stats_manager.create_chart('line', evolution_chart_data,
                                             'Evolución de Duración Promedio', 'year', 'avg_duration')
            
            return {
                'charts': charts,
                'stats': {
                    'most_popular_duration': duration_data[0]['duration_range'] if duration_data else 'N/A',
                    'avg_song_duration': round(sum(row['avg_duration'] * row['scrobbles'] for row in duration_data) / sum(row['scrobbles'] for row in duration_data), 1) if duration_data else 0,
                    'longest_album': album_duration_data[0]['album'] if album_duration_data else 'N/A',
                    'albums_analyzed': len(album_duration_data)
                }
            }
            
        except Exception as e:
            logger.error(f"Error en análisis de duración de scrobbles: {e}")
            return {'error': str(e)}
    
    def _get_scrobbles_languages_analysis(self):
        """Análisis de idiomas en letras vs scrobbles"""
        try:
            # Análisis de letras disponibles vs scrobbles
            lyrics_analysis_query = """
                SELECT 
                    CASE WHEN l.lyrics IS NOT NULL THEN 'Con letras' ELSE 'Sin letras' END as has_lyrics,
                    COUNT(*) as scrobbles
                FROM scrobbles_paqueradejere sp
                JOIN songs s ON s.artist = sp.artist_name AND s.title = sp.track_name
                LEFT JOIN lyrics l ON s.lyrics_id = l.id
                GROUP BY has_lyrics
            """
            lyrics_data = self.db_manager.execute_query(lyrics_analysis_query)
            
            # Palabras más frecuentes en letras de canciones escuchadas
            frequent_words_query = """
                SELECT 
                    word,
                    word_count,
                    song_count
                FROM (
                    SELECT 
                        TRIM(LOWER(word.value)) as word,
                        COUNT(*) as word_count,
                        COUNT(DISTINCT l.id) as song_count
                    FROM scrobbles_paqueradejere sp
                    JOIN songs s ON s.artist = sp.artist_name AND s.title = sp.track_name
                    JOIN lyrics l ON s.lyrics_id = l.id
                    JOIN json_each(
                        '[' || REPLACE(
                            REPLACE(
                                REPLACE(
                                    REPLACE(l.lyrics, ' ', '","'),
                                    '.', ''
                                ),
                                ',', ''
                            ),
                            '"', ''
                        ) || ']'
                    ) as word
                    WHERE LENGTH(word.value) > 3
                    AND word.value NOT IN ('the', 'and', 'with', 'that', 'this', 'from', 'they', 'have', 'were', 'been', 'their', 'said', 'each', 'which', 'them', 'than', 'many', 'some', 'what', 'would', 'make', 'like', 'into', 'time', 'very', 'when', 'come', 'here', 'just', 'know', 'take', 'people', 'year', 'good', 'work', 'much', 'other', 'also', 'around', 'must', 'well', 'large', 'add', 'such', 'because', 'turn', 'why', 'ask', 'went', 'men', 'read', 'need', 'land', 'different', 'home', 'move', 'try', 'kind', 'hand', 'picture', 'again', 'change', 'off', 'play', 'spell', 'air', 'away', 'animal', 'house', 'point', 'page', 'letter', 'mother', 'answer', 'found', 'study', 'still', 'learn', 'should', 'america', 'world')
                    GROUP BY TRIM(LOWER(word.value))
                    HAVING word_count >= 5
                    ORDER BY word_count DESC
                    LIMIT 20
                )
            """
            words_data = self.db_manager.execute_query(frequent_words_query)
            
            # Análisis de longitud de letras vs popularidad
            lyrics_length_query = """
                SELECT 
                    CASE 
                        WHEN LENGTH(l.lyrics) <= 500 THEN 'Cortas'
                        WHEN LENGTH(l.lyrics) <= 1500 THEN 'Medianas'
                        WHEN LENGTH(l.lyrics) <= 3000 THEN 'Largas'
                        ELSE 'Muy largas'
                    END as lyrics_length,
                    COUNT(*) as scrobbles
                FROM scrobbles_paqueradejere sp
                JOIN songs s ON s.artist = sp.artist_name AND s.title = sp.track_name
                JOIN lyrics l ON s.lyrics_id = l.id
                WHERE l.lyrics IS NOT NULL
                GROUP BY lyrics_length
                ORDER BY 
                    CASE lyrics_length
                        WHEN 'Cortas' THEN 1
                        WHEN 'Medianas' THEN 2
                        WHEN 'Largas' THEN 3
                        ELSE 4
                    END
            """
            length_data = self.db_manager.execute_query(lyrics_length_query)
            
            # Preparar datos para gráficos
            lyrics_chart_data = [{'status': row['has_lyrics'], 'scrobbles': row['scrobbles']} 
                               for row in lyrics_data]
            
            words_chart_data = [{'word': row['word'], 'count': row['word_count']} 
                              for row in words_data[:15]]  # Top 15 palabras
            
            length_chart_data = [{'length': row['lyrics_length'], 'scrobbles': row['scrobbles']} 
                               for row in length_data]
            
            from stats_manager import StatsManager
            stats_manager = StatsManager(self.db_manager.db_path, self.config)
            
            charts = {}
            
            if lyrics_chart_data:
                charts['lyrics_availability'] = stats_manager.create_chart('pie', lyrics_chart_data,
                                               'Disponibilidad de Letras', 'status', 'scrobbles')
            
            if words_chart_data:
                charts['frequent_words'] = stats_manager.create_chart('bar', words_chart_data,
                                          'Palabras Más Frecuentes en Letras', 'word', 'count')
            
            if length_chart_data:
                charts['lyrics_length'] = stats_manager.create_chart('pie', length_chart_data,
                                         'Distribución por Longitud de Letras', 'length', 'scrobbles')
            
            return {
                'charts': charts,
                'stats': {
                    'songs_with_lyrics': lyrics_data[0]['scrobbles'] if lyrics_data and lyrics_data[0]['has_lyrics'] == 'Con letras' else 0,
                    'songs_without_lyrics': lyrics_data[1]['scrobbles'] if len(lyrics_data) > 1 else 0,
                    'most_frequent_word': words_data[0]['word'] if words_data else 'N/A',
                    'word_frequency': words_data[0]['word_count'] if words_data else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error en análisis de idiomas de scrobbles: {e}")
            return {'error': str(e)}