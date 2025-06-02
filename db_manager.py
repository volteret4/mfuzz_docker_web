#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import logging
import os
from typing import List, Dict, Optional, Tuple
import json

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Gestor de base de datos SQLite para Music Web Explorer"""
    
    def __init__(self, config):
        self.config = config
        self.db_path = config.get('database', {}).get('path', '/app/data/musica.sqlite')
        self.timeout = config.get('database', {}).get('timeout', 30)
        
        # Verificar que la base de datos existe
        if not os.path.exists(self.db_path):
            logger.warning(f"Base de datos no encontrada en: {self.db_path}")
        else:
            logger.info(f"Base de datos conectada: {self.db_path}")
    
    def get_connection(self):
        """Obtiene una conexión a la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=self.timeout)
            conn.row_factory = sqlite3.Row  # Para acceso por nombre de columna
            return conn
        except Exception as e:
            logger.error(f"Error conectando a la base de datos: {e}")
            raise
    
    def test_connection(self):
        """Prueba la conexión a la base de datos"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT 1")
                cursor.fetchone()
                return True
        except Exception as e:
            logger.error(f"Error en test de conexión: {e}")
            return False
    
    def get_database_info(self):
        """Obtiene información sobre la estructura de la base de datos"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' 
                    ORDER BY name
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                info = {'tables': {}}
                for table in tables:
                    cursor = conn.execute(f"PRAGMA table_info({table})")
                    columns = [{'name': row[1], 'type': row[2]} for row in cursor.fetchall()]
                    
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    
                    info['tables'][table] = {
                        'columns': columns,
                        'count': count
                    }
                
                return info
                
        except Exception as e:
            logger.error(f"Error obteniendo info de la base de datos: {e}")
            return None
    
    def search_artists(self, query: str, limit: int = 50) -> List[Dict]:
        """Busca artistas por nombre usando FTS o LIKE"""
        try:
            with self.get_connection() as conn:
                search_term = f"%{query}%"
                
                # Primero intentar búsqueda FTS para mejor rendimiento
                try:
                    cursor = conn.execute("""
                        SELECT a.* FROM artists a
                        JOIN artist_fts fts ON a.id = fts.id
                        WHERE artist_fts MATCH ?
                        ORDER BY a.name
                        LIMIT ?
                    """, (query, limit))
                    results = [dict(row) for row in cursor.fetchall()]
                    if results:
                        logger.debug(f"Encontrados {len(results)} artistas con FTS")
                        return results
                except sqlite3.Error:
                    pass
                
                # Fallback a búsqueda normal
                cursor = conn.execute("""
                    SELECT * FROM artists 
                    WHERE name LIKE ? 
                    ORDER BY name 
                    LIMIT ?
                """, (search_term, limit))
                results = [dict(row) for row in cursor.fetchall()]
                
                logger.debug(f"Encontrados {len(results)} artistas con LIKE")
                return results
                
        except Exception as e:
            logger.error(f"Error buscando artistas: {e}")
            return []
    
    def get_artist_albums(self, artist_name: str) -> List[Dict]:
        """Obtiene los álbumes de un artista por nombre"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT a.*, ar.name as artist_name
                    FROM albums a
                    JOIN artists ar ON a.artist_id = ar.id
                    WHERE ar.name = ?
                    ORDER BY a.year DESC, a.name
                """, (artist_name,))
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error obteniendo álbumes del artista {artist_name}: {e}")
            return []
    
    def get_artist_albums_by_id(self, artist_id: int) -> List[Dict]:
        """Obtiene los álbumes de un artista por ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT a.*, ar.name as artist_name
                    FROM albums a
                    JOIN artists ar ON a.artist_id = ar.id
                    WHERE a.artist_id = ?
                    ORDER BY a.year DESC, a.name
                """, (artist_id,))
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error obteniendo álbumes del artista {artist_id}: {e}")
            return []
    
    def get_artist_by_id(self, artist_id: int) -> Optional[Dict]:
        """Obtiene un artista por ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT * FROM artists WHERE id = ?", (artist_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
                
        except Exception as e:
            logger.error(f"Error obteniendo artista {artist_id}: {e}")
            return None
    
    def get_album_tracks(self, album_id: int = None, artist_name: str = None, album_name: str = None) -> List[Dict]:
        """Obtiene las canciones de un álbum"""
        try:
            with self.get_connection() as conn:
                if album_id:
                    cursor = conn.execute("""
                        SELECT s.*, a.name as album_name, ar.name as artist_name
                        FROM songs s
                        JOIN albums a ON s.album = a.name
                        JOIN artists ar ON a.artist_id = ar.id
                        WHERE a.id = ?
                        ORDER BY s.track_number
                    """, (album_id,))
                else:
                    cursor = conn.execute("""
                        SELECT s.*, a.name as album_name, ar.name as artist_name
                        FROM songs s
                        JOIN albums a ON s.album = a.name
                        JOIN artists ar ON a.artist_id = ar.id
                        WHERE ar.name = ? AND a.name = ?
                        ORDER BY s.track_number
                    """, (artist_name, album_name))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error obteniendo canciones del álbum: {e}")
            return []
    
    def get_album_tracks_by_id(self, album_id: int) -> List[Dict]:
        """Obtiene las canciones de un álbum por ID - VERSION CORREGIDA"""
        try:
            with self.get_connection() as conn:
                # Obtener información del álbum primero
                album_info = self.get_album_by_id(album_id)
                if not album_info:
                    logger.error(f"Álbum {album_id} no encontrado")
                    return []
                
                album_name = album_info.get('name')
                artist_name = album_info.get('artist_name')
                
                # Buscar canciones por nombre de álbum y artista
                if album_name and artist_name:
                    cursor = conn.execute("""
                        SELECT * FROM songs 
                        WHERE album = ? AND artist = ?
                        ORDER BY track_number
                    """, (album_name, artist_name))
                    tracks = [dict(row) for row in cursor.fetchall()]
                    
                    if tracks:
                        # Añadir información del álbum y artista
                        for track in tracks:
                            track['album_name'] = album_name
                            track['artist_name'] = artist_name
                        
                        logger.debug(f"Encontradas {len(tracks)} canciones para álbum {album_id}")
                        return tracks
                
                # Fallback: búsqueda flexible
                if album_name:
                    cursor = conn.execute("""
                        SELECT * FROM songs 
                        WHERE album LIKE ?
                        ORDER BY track_number
                    """, (f"%{album_name}%",))
                    tracks = [dict(row) for row in cursor.fetchall()]
                    
                    # Añadir información del álbum y artista
                    for track in tracks:
                        track['album_name'] = album_name
                        track['artist_name'] = artist_name
                    
                    if tracks:
                        logger.debug(f"Encontradas {len(tracks)} canciones (fallback) para álbum {album_id}")
                        return tracks
                
                logger.warning(f"No se encontraron canciones para el álbum {album_id}")
                return []
                
        except Exception as e:
            logger.error(f"Error obteniendo canciones del álbum {album_id}: {e}")
            return []
    
    def get_album_by_id(self, album_id: int) -> Optional[Dict]:
        """Obtiene un álbum por ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT a.*, ar.name as artist_name
                    FROM albums a
                    JOIN artists ar ON a.artist_id = ar.id
                    WHERE a.id = ?
                """, (album_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
                
        except Exception as e:
            logger.error(f"Error obteniendo álbum {album_id}: {e}")
            return None
    
    def get_song_by_id(self, song_id: int) -> Optional[Dict]:
        """Obtiene una canción por ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT * FROM songs WHERE id = ?", (song_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
                
        except Exception as e:
            logger.error(f"Error obteniendo canción {song_id}: {e}")
            return None
    
    def get_song_lyrics(self, song_id: int = None, artist: str = None, title: str = None) -> Optional[str]:
        """Obtiene las letras de una canción"""
        try:
            with self.get_connection() as conn:
                if song_id:
                    # Buscar por lyrics_id en la tabla songs
                    cursor = conn.execute("SELECT lyrics_id FROM songs WHERE id = ?", (song_id,))
                    result = cursor.fetchone()
                    if result and result[0]:
                        lyrics_id = result[0]
                        cursor = conn.execute("SELECT lyrics FROM lyrics WHERE id = ?", (lyrics_id,))
                        lyrics_result = cursor.fetchone()
                        if lyrics_result:
                            return lyrics_result[0]
                else:
                    # Buscar por artista y título
                    cursor = conn.execute("""
                        SELECT l.lyrics FROM lyrics l
                        JOIN songs s ON l.track_id = s.id
                        WHERE s.artist = ? AND s.title = ?
                    """, (artist, title))
                    result = cursor.fetchone()
                    if result:
                        return result[0]
                
                return None
                
        except Exception as e:
            logger.error(f"Error obteniendo letras: {e}")
            return None
    
    def get_song_lyrics_by_id(self, song_id: int) -> Optional[str]:
        """Obtiene las letras de una canción por ID"""
        return self.get_song_lyrics(song_id=song_id)
    
    def get_recent_searches(self, limit: int = 10) -> List[Dict]:
        """Obtiene las búsquedas recientes"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT search_term, search_date 
                    FROM recent_searches 
                    ORDER BY search_date DESC 
                    LIMIT ?
                """, (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.debug(f"Tabla recent_searches no existe o error: {e}")
            return []
    
    def add_recent_search(self, search_term: str):
        """Añade una búsqueda reciente"""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO recent_searches (search_term, search_date) 
                    VALUES (?, datetime('now'))
                """, (search_term,))
                conn.commit()
        except Exception as e:
            logger.debug(f"No se pudo guardar búsqueda reciente: {e}")
    
    def get_popular_artists(self, limit: int = 20) -> List[Dict]:
        """Obtiene los artistas más populares basado en reproducciones"""
        try:
            with self.get_connection() as conn:
                # Usar tabla de scrobbles para obtener artistas más escuchados
                cursor = conn.execute("""
                    SELECT a.*, COUNT(s.id) as play_count
                    FROM artists a
                    LEFT JOIN scrobbles s ON a.name = s.artist_name
                    GROUP BY a.id, a.name
                    ORDER BY play_count DESC, a.name
                    LIMIT ?
                """, (limit,))
                results = [dict(row) for row in cursor.fetchall()]
                
                if not results:
                    # Fallback: obtener artistas por orden alfabético
                    cursor = conn.execute("""
                        SELECT * FROM artists 
                        ORDER BY name 
                        LIMIT ?
                    """, (limit,))
                    results = [dict(row) for row in cursor.fetchall()]
                
                return results
                
        except Exception as e:
            logger.error(f"Error obteniendo artistas populares: {e}")
            return []
    
    def search_global(self, query: str, limit: int = 50) -> Dict:
        """Búsqueda global en artistas, álbumes y canciones usando FTS cuando esté disponible"""
        results = {
            'artists': [],
            'albums': [],
            'tracks': []
        }
        
        try:
            with self.get_connection() as conn:
                search_term = f"%{query}%"
                
                # Buscar artistas (ya implementado arriba)
                results['artists'] = self.search_artists(query, limit)
                
                # Buscar álbumes usando FTS si está disponible
                try:
                    cursor = conn.execute("""
                        SELECT a.*, ar.name as artist_name FROM albums a
                        JOIN album_fts fts ON a.id = fts.id
                        JOIN artists ar ON a.artist_id = ar.id
                        WHERE album_fts MATCH ?
                        ORDER BY a.name
                        LIMIT ?
                    """, (query, limit))
                    albums = [dict(row) for row in cursor.fetchall()]
                    if albums:
                        results['albums'] = albums
                except sqlite3.Error:
                    # Fallback a búsqueda normal en álbumes
                    cursor = conn.execute("""
                        SELECT a.*, ar.name as artist_name FROM albums a
                        JOIN artists ar ON a.artist_id = ar.id
                        WHERE a.name LIKE ? OR ar.name LIKE ?
                        ORDER BY a.name
                        LIMIT ?
                    """, (search_term, search_term, limit))
                    results['albums'] = [dict(row) for row in cursor.fetchall()]
                
                # Buscar canciones usando FTS si está disponible
                try:
                    cursor = conn.execute("""
                        SELECT s.* FROM songs s
                        JOIN song_fts fts ON s.id = fts.id
                        WHERE song_fts MATCH ?
                        ORDER BY s.title
                        LIMIT ?
                    """, (query, limit))
                    tracks = [dict(row) for row in cursor.fetchall()]
                    if tracks:
                        results['tracks'] = tracks
                except sqlite3.Error:
                    # Fallback a búsqueda normal en canciones
                    cursor = conn.execute("""
                        SELECT * FROM songs 
                        WHERE title LIKE ? OR artist LIKE ? OR album LIKE ?
                        ORDER BY title
                        LIMIT ?
                    """, (search_term, search_term, search_term, limit))
                    results['tracks'] = [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error en búsqueda global: {e}")
        
        return results
    
    def get_album_tracks_with_paths(self, album_id: int) -> List[Dict]:
        """Obtiene las canciones de un álbum con información detallada de rutas - VERSIÓN CORREGIDA PARA ESQUEMA REAL"""
        try:
            with self.get_connection() as conn:
                logger.debug(f"Obteniendo canciones para álbum {album_id}")
                
                # La tabla songs NO tiene album_id, pero sí tiene campos album y artist
                # Primero obtenemos información del álbum
                album_info = self.get_album_by_id(album_id)
                if not album_info:
                    logger.error(f"Álbum {album_id} no encontrado")
                    return []
                
                album_name = album_info.get('name')
                artist_name = album_info.get('artist_name')
                
                logger.debug(f"Buscando canciones para: {artist_name} - {album_name}")
                
                # Estrategia 1: Búsqueda exacta por álbum y artista
                tracks = []
                if album_name and artist_name:
                    cursor = conn.execute("""
                        SELECT * FROM songs 
                        WHERE album = ? AND artist = ?
                        ORDER BY track_number
                    """, (album_name, artist_name))
                    tracks = [dict(row) for row in cursor.fetchall()]
                    
                    if tracks:
                        logger.debug(f"Estrategia 1 exitosa: {len(tracks)} canciones encontradas")
                
                # Estrategia 2: Búsqueda flexible por álbum (si la primera no funciona)
                if not tracks and album_name:
                    cursor = conn.execute("""
                        SELECT * FROM songs 
                        WHERE album LIKE ?
                        ORDER BY track_number
                    """, (f"%{album_name}%",))
                    all_tracks = [dict(row) for row in cursor.fetchall()]
                    
                    # Filtrar por artista si es necesario
                    if artist_name and all_tracks:
                        tracks = [t for t in all_tracks if artist_name.lower() in t.get('artist', '').lower()]
                    else:
                        tracks = all_tracks
                    
                    if tracks:
                        logger.debug(f"Estrategia 2 exitosa: {len(tracks)} canciones encontradas")
                
                # Estrategia 3: Búsqueda por artista similar (último recurso)
                if not tracks and artist_name:
                    cursor = conn.execute("""
                        SELECT * FROM songs 
                        WHERE artist LIKE ?
                        ORDER BY album, track_number
                    """, (f"%{artist_name}%",))
                    all_tracks = [dict(row) for row in cursor.fetchall()]
                    
                    # Filtrar manualmente por álbum
                    if album_name and all_tracks:
                        tracks = [t for t in all_tracks if album_name.lower() in t.get('album', '').lower()]
                    
                    if tracks:
                        logger.debug(f"Estrategia 3 exitosa: {len(tracks)} canciones encontradas")
                
                if not tracks:
                    logger.warning(f"No se encontraron canciones para el álbum {album_id}")
                    return []
                
                # Enriquecer con información de rutas y metadatos
                for track in tracks:
                    # Añadir información del álbum
                    track['album_name'] = album_name
                    track['artist_name'] = artist_name
                    
                    # Procesar información de rutas
                    file_path = track.get('file_path', '')
                    track['available_paths'] = {}
                    
                    if file_path:
                        track['available_paths']['file_path'] = file_path
                        track['best_path'] = file_path
                    else:
                        track['best_path'] = None
                    
                    # Log de debug para las primeras canciones
                    if tracks.index(track) < 3:
                        logger.debug(f"Canción: {track.get('title')} - Ruta: {track.get('best_path')}")
                
                logger.info(f"Obtenidas {len(tracks)} canciones para álbum {album_id} ({artist_name} - {album_name})")
                return tracks
                
        except Exception as e:
            logger.error(f"Error obteniendo canciones con rutas del álbum {album_id}: {e}")
            return []
    
    def _determine_best_path(self, track: Dict, path_fields: List[str]) -> Optional[str]:
        """Determina la mejor ruta de archivo para una canción - VERSION MEJORADA"""
        
        # Prioridad de campos (del más probable al menos probable)
        priority_fields = [
            'file_path', 'filepath', 'path', 'location', 'file', 
            'filename', 'url', 'uri', 'source', 'src'
        ]
        
        # Buscar por prioridad
        for field in priority_fields:
            if field in path_fields and track.get(field):
                path_value = track[field]
                if isinstance(path_value, str) and path_value.strip():
                    path_value = path_value.strip()
                    
                    # Filtrar URLs que no son archivos locales
                    if path_value.startswith(('http://', 'https://', 'ftp://')):
                        continue
                    
                    # Verificar que parece ser una ruta de archivo
                    if any(ext in path_value.lower() for ext in ['.mp3', '.flac', '.ogg', '.m4a', '.wav', '.wma']):
                        return path_value
                    
                    # Si no tiene extensión pero parece ser una ruta, también la consideramos
                    if '/' in path_value or '\\' in path_value:
                        return path_value
        
        # Fallback: primer campo disponible que contenga algo útil
        for field in path_fields:
            if track.get(field):
                path_value = str(track[field]).strip()
                if path_value and not path_value.startswith(('http://', 'https://')):
                    return path_value
        
        return None