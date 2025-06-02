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
        """Obtiene las canciones de un álbum por ID - VERSION MEJORADA"""
        try:
            with self.get_connection() as conn:
                # Primero intentar con la relación album_id directa
                cursor = conn.execute("""
                    SELECT s.*, a.name as album_name, ar.name as artist_name
                    FROM songs s
                    JOIN albums a ON s.album_id = a.id
                    JOIN artists ar ON a.artist_id = ar.id
                    WHERE a.id = ?
                    ORDER BY s.track_number
                """, (album_id,))
                tracks = [dict(row) for row in cursor.fetchall()]
                
                if tracks:
                    logger.debug(f"Encontradas {len(tracks)} canciones con album_id para álbum {album_id}")
                    return tracks
                
                # Fallback: intentar con la relación por nombre de álbum
                cursor = conn.execute("""
                    SELECT s.*, a.name as album_name, ar.name as artist_name
                    FROM songs s
                    JOIN albums a ON s.album = a.name
                    JOIN artists ar ON a.artist_id = ar.id
                    WHERE a.id = ?
                    ORDER BY s.track_number
                """, (album_id,))
                tracks = [dict(row) for row in cursor.fetchall()]
                
                if tracks:
                    logger.debug(f"Encontradas {len(tracks)} canciones con album name para álbum {album_id}")
                    return tracks
                
                # Último intento: buscar directamente por album_id si existe esa columna
                try:
                    cursor = conn.execute("PRAGMA table_info(songs)")
                    columns = [col[1] for col in cursor.fetchall()]
                    
                    if 'album_id' in columns:
                        cursor = conn.execute("""
                            SELECT s.*, 
                                   (SELECT name FROM albums WHERE id = s.album_id) as album_name,
                                   (SELECT ar.name FROM albums a JOIN artists ar ON a.artist_id = ar.id WHERE a.id = s.album_id) as artist_name
                            FROM songs s
                            WHERE s.album_id = ?
                            ORDER BY s.track_number
                        """, (album_id,))
                        tracks = [dict(row) for row in cursor.fetchall()]
                        
                        if tracks:
                            logger.debug(f"Encontradas {len(tracks)} canciones con album_id directo para álbum {album_id}")
                            return tracks
                
                except sqlite3.Error as e:
                    logger.debug(f"Error en último intento de búsqueda: {e}")
                
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
        """Obtiene las canciones de un álbum con información detallada de rutas - VERSION MEJORADA"""
        try:
            with self.get_connection() as conn:
                # Obtener información de columnas de la tabla songs
                cursor = conn.execute("PRAGMA table_info(songs)")
                columns = [col[1] for col in cursor.fetchall()]
                
                logger.debug(f"Columnas disponibles en songs: {columns}")
                
                # Construir query dinámicamente basado en columnas disponibles
                path_fields = []
                for col in columns:
                    if any(keyword in col.lower() for keyword in ['path', 'file', 'location', 'url']):
                        path_fields.append(col)
                
                logger.debug(f"Campos de ruta encontrados: {path_fields}")
                
                # Intentar diferentes estrategias para obtener las canciones
                tracks = []
                
                # Estrategia 1: album_id directo
                if 'album_id' in columns:
                    try:
                        cursor = conn.execute("""
                            SELECT s.*, a.name as album_name, ar.name as artist_name
                            FROM songs s
                            JOIN albums a ON s.album_id = a.id
                            JOIN artists ar ON a.artist_id = ar.id
                            WHERE a.id = ?
                            ORDER BY s.track_number
                        """, (album_id,))
                        tracks = [dict(row) for row in cursor.fetchall()]
                        if tracks:
                            logger.debug(f"Estrategia 1 exitosa: {len(tracks)} canciones")
                    except sqlite3.Error as e:
                        logger.debug(f"Estrategia 1 falló: {e}")
                
                # Estrategia 2: por nombre de álbum
                if not tracks:
                    try:
                        cursor = conn.execute("""
                            SELECT s.*, a.name as album_name, ar.name as artist_name
                            FROM songs s
                            JOIN albums a ON s.album = a.name
                            JOIN artists ar ON a.artist_id = ar.id
                            WHERE a.id = ?
                            ORDER BY s.track_number
                        """, (album_id,))
                        tracks = [dict(row) for row in cursor.fetchall()]
                        if tracks:
                            logger.debug(f"Estrategia 2 exitosa: {len(tracks)} canciones")
                    except sqlite3.Error as e:
                        logger.debug(f"Estrategia 2 falló: {e}")
                
                # Estrategia 3: búsqueda más amplia usando información del álbum
                if not tracks:
                    try:
                        # Primero obtener información del álbum
                        album_info = self.get_album_by_id(album_id)
                        if album_info:
                            album_name = album_info.get('name')
                            artist_name = album_info.get('artist_name')
                            
                            if album_name and artist_name:
                                cursor = conn.execute("""
                                    SELECT s.*
                                    FROM songs s
                                    WHERE s.album = ? AND s.artist = ?
                                    ORDER BY s.track_number
                                """, (album_name, artist_name))
                                tracks = [dict(row) for row in cursor.fetchall()]
                                
                                # Añadir información del álbum y artista
                                for track in tracks:
                                    track['album_name'] = album_name
                                    track['artist_name'] = artist_name
                                
                                if tracks:
                                    logger.debug(f"Estrategia 3 exitosa: {len(tracks)} canciones")
                    except sqlite3.Error as e:
                        logger.debug(f"Estrategia 3 falló: {e}")
                
                # Estrategia 4: búsqueda por LIKE (menos precisa pero más flexible)
                if not tracks:
                    try:
                        album_info = self.get_album_by_id(album_id)
                        if album_info:
                            album_name = album_info.get('name')
                            artist_name = album_info.get('artist_name')
                            
                            if album_name:
                                cursor = conn.execute("""
                                    SELECT s.*
                                    FROM songs s
                                    WHERE s.album LIKE ?
                                    ORDER BY s.track_number
                                """, (f"%{album_name}%",))
                                tracks = [dict(row) for row in cursor.fetchall()]
                                
                                # Filtrar por artista si está disponible
                                if artist_name and tracks:
                                    tracks = [t for t in tracks if artist_name.lower() in t.get('artist', '').lower()]
                                
                                # Añadir información del álbum y artista
                                for track in tracks:
                                    track['album_name'] = album_name
                                    track['artist_name'] = artist_name
                                
                                if tracks:
                                    logger.debug(f"Estrategia 4 exitosa: {len(tracks)} canciones")
                    except sqlite3.Error as e:
                        logger.debug(f"Estrategia 4 falló: {e}")
                
                if not tracks:
                    logger.warning(f"No se pudieron obtener canciones para álbum {album_id}")
                    return []
                
                # Enriquecer con información de rutas
                for track in tracks:
                    # Recopilar todas las rutas disponibles
                    track['available_paths'] = {}
                    for field in path_fields:
                        if field in track and track[field]:
                            path_value = track[field]
                            if isinstance(path_value, str) and path_value.strip():
                                track['available_paths'][field] = path_value.strip()
                    
                    # Determinar la mejor ruta
                    track['best_path'] = self._determine_best_path(track, path_fields)
                    
                    # Log de debug para la primera canción
                    if track == tracks[0]:
                        logger.debug(f"Ejemplo de canción - Título: {track.get('title')}")
                        logger.debug(f"Rutas disponibles: {track['available_paths']}")
                        logger.debug(f"Mejor ruta: {track['best_path']}")
                
                logger.info(f"Obtenidas {len(tracks)} canciones para álbum {album_id}")
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