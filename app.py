#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, jsonify, request, send_from_directory
import sqlite3
import json
import os
from pathlib import Path
import configparser
import logging
from datetime import datetime
import subprocess
import threading
import time as time_module
import shutil
import mimetypes
from telegram_notifier import create_notifier


download_status = {}

class ImageManager:
    """Gestor de imágenes locales copiadas - VERSIÓN CORREGIDA PARA USAR FILENAMES"""
    
    def __init__(self, images_dir='/app/images'):
        self.images_dir = Path(images_dir)
        self.master_index = {}
        self.artists_dir = self.images_dir / 'artists'
        self.albums_dir = self.images_dir / 'albums'
        self.load_master_index()
    
    # En la función load_master_index, añadir verificación de rutas obsoletas
    def load_master_index(self):
        """Cargar índice maestro de imágenes"""
        index_file = self.images_dir / 'master_index.json'
        if index_file.exists():
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    self.master_index = json.load(f)
                
                # NUEVA VERIFICACIÓN: Limpiar entradas con rutas obsoletas
                self._clean_obsolete_paths()
                
                # Extraer información de metadatos si existe
                metadata = self.master_index.get('metadata', {})
                artists_count = len(self.master_index.get('artists', {}))
                albums_count = len(self.master_index.get('albums', {}))
                
                logging.info(f"Índice maestro cargado: {artists_count} artistas, {albums_count} álbumes")
                if metadata:
                    logging.info(f"Fecha extracción: {metadata.get('extraction_date', 'N/A')}")
                    
            except Exception as e:
                logging.warning(f"Error cargando índice de imágenes: {e}")
                self.master_index = {'artists': {}, 'albums': {}}
        else:
            logging.warning(f"Índice maestro no encontrado en {index_file}")
            self.master_index = {'artists': {}, 'albums': {}}

    def _clean_obsolete_paths(self):
        """Limpiar entradas con rutas obsoletas que ya no existen"""
        obsolete_prefixes = [
            '/mnt/NFS/moode/moode',
            '/home/huan/gits/pollo/music-fuzzy/.content'
        ]
        
        # Limpiar artistas
        artists_data = self.master_index.get('artists', {})
        cleaned_artists = {}
        
        for artist_id, artist_info in artists_data.items():
            original_path = artist_info.get('original_path', '')
            filename = artist_info.get('filename', '')
            
            # Verificar si la ruta original es obsoleta
            is_obsolete = any(original_path.startswith(prefix) for prefix in obsolete_prefixes)
            
            # Verificar si el archivo físico existe
            if filename:
                file_path = self.artists_dir / filename
                file_exists = file_path.exists()
            else:
                file_exists = False
            
            # Solo mantener si el archivo existe físicamente
            if file_exists:
                cleaned_artists[artist_id] = artist_info
            elif is_obsolete:
                logging.debug(f"Eliminando artista {artist_id} con ruta obsoleta: {original_path}")
        
        # Limpiar álbumes
        albums_data = self.master_index.get('albums', {})
        cleaned_albums = {}
        
        for album_id, album_info in albums_data.items():
            original_path = album_info.get('original_path', '')
            filename = album_info.get('filename', '')
            
            # Verificar si la ruta original es obsoleta
            is_obsolete = any(original_path.startswith(prefix) for prefix in obsolete_prefixes)
            
            # Verificar si el archivo físico existe
            if filename:
                file_path = self.albums_dir / filename
                file_exists = file_path.exists()
            else:
                file_exists = False
            
            # Solo mantener si el archivo existe físicamente
            if file_exists:
                cleaned_albums[album_id] = album_info
            elif is_obsolete:
                logging.debug(f"Eliminando álbum {album_id} con ruta obsoleta: {original_path}")
        
        # Actualizar el índice
        self.master_index['artists'] = cleaned_artists
        self.master_index['albums'] = cleaned_albums
        
        logging.info(f"Índice limpiado: {len(cleaned_artists)} artistas, {len(cleaned_albums)} álbumes válidos")
    
    def get_artist_image(self, artist_id):
        """Obtener URL de imagen de artista usando filename del índice"""
        artists_data = self.master_index.get('artists', {})
        artist_info = artists_data.get(str(artist_id))
        
        if not artist_info or not artist_info.get('filename'):
            return None
        
        filename = artist_info['filename']
        
        # Verificar que el archivo existe físicamente
        file_path = self.artists_dir / filename
        if not file_path.exists():
            logging.warning(f"Archivo de artista no existe: {file_path}")
            return None
        
        # Generar URL usando el endpoint de imágenes locales
        image_url = f"/api/local-image/artists/{filename}"
        logging.debug(f"URL generada para artista {artist_id}: {image_url}")
        
        return image_url
    
    
    def get_artist_info(self, artist_id):
        """Obtener información completa del artista desde el índice"""
        artists_data = self.master_index.get('artists', {})
        return artists_data.get(str(artist_id))
    
    def get_album_info(self, album_id):
        """Obtener información completa del álbum desde el índice"""
        albums_data = self.master_index.get('albums', {})
        return albums_data.get(str(album_id))
    
    def verify_image_file(self, image_type, filename):
        """Verificar si el archivo de imagen existe físicamente"""
        if image_type == 'artist':
            file_path = self.artists_dir / filename
        elif image_type == 'album':
            file_path = self.albums_dir / filename
        else:
            return False
        
        return file_path.exists() and file_path.is_file()
    
    def get_stats(self):
        """Obtener estadísticas de imágenes"""
        artists_data = self.master_index.get('artists', {})
        albums_data = self.master_index.get('albums', {})
        metadata = self.master_index.get('metadata', {})
        
        # Verificar archivos físicos
        artists_verified = 0
        albums_verified = 0
        
        for artist_id, artist_info in artists_data.items():
            if artist_info.get('filename') and self.verify_image_file('artist', artist_info['filename']):
                artists_verified += 1
        
        for album_id, album_info in albums_data.items():
            if album_info.get('filename') and self.verify_image_file('album', album_info['filename']):
                albums_verified += 1
        
        return {
            'artists_in_index': len(artists_data),
            'albums_in_index': len(albums_data),
            'artists_verified': artists_verified,
            'albums_verified': albums_verified,
            'extraction_date': metadata.get('extraction_date'),
            'total_images_in_index': metadata.get('total_images', len(artists_data) + len(albums_data)),
            'images_directory': str(self.images_dir),
            'artists_directory': str(self.artists_dir),
            'albums_directory': str(self.albums_dir)
        }




class MusicExplorer:
    def __init__(self, config_file='config.ini'):
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        
        # Solo necesitamos acceso a la base de datos
        self.db_path = self.config.get('database', 'path')
        
        # Directorio de descarga local
        self.download_path = self.config.get('download', 'path', fallback='/downloads')
        
        # Configuración de logging
        log_level = self.config.get('logging', 'level', fallback='INFO')
        log_file = self.config.get('logging', 'file', fallback='/app/logs/music_web.log')
        
        # Crear directorio de logs si no existe
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        os.makedirs(self.download_path, exist_ok=True)
        
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Inicializar notificador de Telegram
        self.notifier = create_notifier(self.logger)
        
        # ELIMINAR COMPLETAMENTE: No más sistema montado
        # self.local_access_enabled = False
        # self.mounted_paths = []
        
        # Método de descarga preferido (solo SSH)
        self.preferred_download_method = 'ssh'

        # Inicializar gestor de imágenes LOCALES únicamente
        images_dir = self.config.get('images', 'local_dir', fallback='/app/images')
        self.image_manager = ImageManager(images_dir)
        
        # Log de verificación
        self.logger.info(f"=== SISTEMA DE IMÁGENES INICIALIZADO ===")
        self.logger.info(f"Directorio imágenes: {images_dir}")
        stats = self.image_manager.get_stats()
        self.logger.info(f"Artistas en índice: {stats['artists_in_index']}")
        self.logger.info(f"Álbumes en índice: {stats['albums_in_index']}")
        self.logger.info(f"Verificados físicamente: {stats['artists_verified']} artistas, {stats['albums_verified']} álbumes")
 

    def perform_local_download(self, album_name, artist_name, download_id, local_info):
        """Realizar descarga local (copia de archivos montados)"""
        try:
            download_status[download_id]['status'] = 'downloading_local'
            download_status[download_id]['message'] = f'Copiando archivos locales de "{album_name}"...'
            
            # Crear directorio de destino
            dest_path = Path(self.download_path) / artist_name / album_name
            dest_path.mkdir(parents=True, exist_ok=True)
            
            self.logger.info(f"=== DESCARGA LOCAL ===")
            self.logger.info(f"Origen: {local_info['album_local_path']}")
            self.logger.info(f"Destino: {dest_path}")
            self.logger.info(f"Archivos disponibles: {local_info['available_tracks']}/{local_info['total_tracks']}")
            
            # Copiar archivos disponibles
            copied_count = 0
            total_files = len(local_info['local_files'])
            
            for i, src_file in enumerate(local_info['local_files']):
                try:
                    src_path = Path(src_file)
                    dst_path = dest_path / src_path.name
                    
                    download_status[download_id]['message'] = f'Copiando: {src_path.name} ({i+1}/{total_files})'
                    download_status[download_id]['progress'] = int((i / total_files) * 100)
                    
                    self.logger.info(f"Copiando: {src_path} → {dst_path}")
                    shutil.copy2(src_path, dst_path)
                    copied_count += 1
                    
                except Exception as e:
                    self.logger.warning(f"Error copiando {src_path}: {e}")
            
            # Resultado final
            if copied_count > 0:
                message_parts = [f'Álbum copiado localmente: {copied_count}/{total_files} archivos']
                if local_info['missing_tracks'] > 0:
                    message_parts.append(f'{local_info["missing_tracks"]} archivos no disponibles localmente')
                
                download_status[download_id].update({
                    'status': 'completed',
                    'progress': 100,
                    'message': '. '.join(message_parts),
                    'download_path': str(dest_path),
                    'file_count': copied_count,
                    'method': 'local'
                })
                
                # 🔔 NOTIFICAR DESCARGA LOCAL COMPLETADA
                self.notifier.notify_download_completed(
                    album_name, 
                    artist_name, 
                    copied_count, 
                    str(dest_path),
                    method='local'
                )
                
                self.logger.info(f"✅ Descarga local completada: {copied_count} archivos")
            else:
                raise Exception("No se pudo copiar ningún archivo local")
                
        except Exception as e:
            error_msg = f'Error en descarga local: {str(e)}'
            download_status[download_id].update({
                'status': 'error',
                'progress': 0,
                'message': error_msg,
                'method': 'local'
            })
            
            # 🔔 NOTIFICAR ERROR LOCAL
            self.notifier.notify_download_error(album_name, artist_name, error_msg)
            self.logger.error(f"❌ Error en descarga local {download_id}: {e}")
            raise



    def get_db_connection(self):
        """Obtiene conexión a la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            self.logger.error(f"Error conectando a la base de datos: {e}")
            return None



    def search_artists(self, query, limit=50):
        """Busca artistas por nombre - SOLO SISTEMA LOCAL"""
        conn = self.get_db_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT a.id, a.name, a.bio, a.origin, a.formed_year, 
                    a.wikipedia_content,
                    COUNT(DISTINCT al.id) as album_count,
                    COUNT(DISTINCT s.id) as song_count
                FROM artists a
                LEFT JOIN albums al ON a.id = al.artist_id AND al.origen = 'local'
                LEFT JOIN songs s ON a.name = s.artist AND s.origen = 'local'
                WHERE a.name LIKE ? AND a.origen = 'local'
                GROUP BY a.id, a.name
                ORDER BY a.name COLLATE NOCASE
                LIMIT ?
            """, (f'%{query}%', limit))
            
            results = []
            for row in cursor.fetchall():
                artist_data = dict(row)
                
                # USAR SISTEMA CORRECTO DE IMÁGENES LOCALES
                artist_data['img'] = self.image_manager.get_artist_image(row['id'])
                
                # Debug log
                if artist_data['img']:
                    self.logger.debug(f"Artista {row['name']} -> imagen: {artist_data['img']}")
                
                results.append(artist_data)
            
            conn.close()
            self.logger.info(f"Búsqueda '{query}': {len(results)} resultados")
            return results
            
        except Exception as e:
            self.logger.error(f"Error buscando artistas: {e}")
            if conn:
                conn.close()
            return []

    def get_artist_details(self, artist_id):
        """Obtiene detalles completos de un artista - SOLO SISTEMA LOCAL"""
        conn = self.get_db_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            
            # Información del artista
            cursor.execute("""
                SELECT * FROM artists 
                WHERE id = ? AND origen = 'local'
            """, (artist_id,))
            
            artist = cursor.fetchone()
            if not artist:
                conn.close()
                return None
            
            # Álbumes del artista
            cursor.execute("""
                SELECT al.*,
                    COUNT(s.id) as track_count,
                    MIN(s.file_path) as sample_path
                FROM albums al
                LEFT JOIN songs s ON (al.name = s.album AND s.artist = ? AND s.origen = 'local')
                WHERE al.artist_id = ? AND al.origen = 'local'
                GROUP BY al.id, al.name
                ORDER BY al.year DESC, al.name
            """, (artist['name'], artist_id))
            
            albums = []
            for album_row in cursor.fetchall():
                album_dict = dict(album_row)
                
                # USAR SISTEMA CORRECTO DE IMÁGENES LOCALES
                album_dict['best_album_art'] = self.image_manager.get_album_image(album_dict['id'])
                
                # Debug log
                if album_dict['best_album_art']:
                    self.logger.debug(f"Álbum {album_dict['name']} -> imagen: {album_dict['best_album_art']}")
                
                albums.append(album_dict)
            
            # Canciones populares
            cursor.execute("""
                SELECT s.*, COALESCE(s.reproducciones, 1) as play_count
                FROM songs s
                WHERE s.artist = ? AND s.origen = 'local'
                ORDER BY play_count DESC, s.title
                LIMIT 20
            """, (artist['name'],))
            
            popular_songs = []
            for song_row in cursor.fetchall():
                popular_songs.append(dict(song_row))
            
            conn.close()
            
            # USAR SISTEMA CORRECTO DE IMÁGENES LOCALES
            artist_dict = dict(artist)
            artist_dict['img'] = self.image_manager.get_artist_image(artist_id)
            
            # Debug log
            self.logger.info(f"Artista {artist_dict['name']}: {len(albums)} álbumes")
            if artist_dict['img']:
                self.logger.debug(f"Imagen artista: {artist_dict['img']}")
            
            return {
                'artist': artist_dict,
                'albums': albums,
                'popular_songs': popular_songs
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo detalles del artista: {e}")
            if conn:
                conn.close()
            return None


    def get_artist_image(self, artist_dict):
        """Obtener imagen de artista usando solo sistema local"""
        if not artist_dict:
            return None
        artist_id = artist_dict.get('id')
        if artist_id:
            return self.image_manager.get_artist_image(artist_id)
        return None

    def get_album_image(self, album_dict):
        """Obtener imagen de álbum usando solo sistema local"""
        if not album_dict:
            return None
        album_id = album_dict.get('id')
        if album_id:
            return self.image_manager.get_album_image(album_id)
        return None

    def get_album_details(self, album_id):
        """Obtiene detalles de un álbum - SOLO SISTEMA LOCAL"""
        conn = self.get_db_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            
            # Información del álbum y artista
            cursor.execute("""
                SELECT al.*, ar.name as artist_name, ar.id as artist_id
                FROM albums al
                JOIN artists ar ON al.artist_id = ar.id
                WHERE al.id = ? AND al.origen = 'local'
            """, (album_id,))
            
            album = cursor.fetchone()
            if not album:
                conn.close()
                return None
            
            # Canciones del álbum
            cursor.execute("""
                SELECT s.*
                FROM songs s
                WHERE s.album = ? AND s.artist = ? AND s.origen = 'local'
                ORDER BY s.track_number, s.title
            """, (album['name'], album['artist_name']))
            
            tracks = []
            for track_row in cursor.fetchall():
                tracks.append(dict(track_row))
            
            conn.close()
            
            # USAR SISTEMA CORRECTO DE IMÁGENES LOCALES
            album_dict = dict(album)
            album_dict['best_album_art'] = self.image_manager.get_album_image(album_id)
            
            # Debug log
            self.logger.info(f"Álbum {album_dict['name']}: {len(tracks)} canciones")
            if album_dict['best_album_art']:
                self.logger.debug(f"Imagen álbum: {album_dict['best_album_art']}")
            
            return {
                'album': album_dict,
                'tracks': tracks
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo detalles del álbum: {e}")
            if conn:
                conn.close()
            return None
    
    def get_folder_structure(self, path=""):
        """Obtiene la estructura de carpetas desde la base de datos"""
        conn = self.get_db_connection()
        if not conn:
            return {'error': 'Error de base de datos'}
        
        try:
            cursor = conn.cursor()
            
            # Obtener carpetas únicas desde las rutas de archivos en la BD
            if not path:
                # Nivel raíz: obtener directorios principales de artistas
                cursor.execute("""
                    SELECT DISTINCT 
                        SUBSTR(file_path, 1, INSTR(file_path, '/') - 1) as folder_name,
                        SUBSTR(file_path, 1, INSTR(file_path, '/') - 1) as folder_path
                    FROM songs 
                    WHERE origen = 'local' AND file_path LIKE '%/%'
                    ORDER BY folder_name
                """)
            else:
                # Subdirectorios: buscar dentro del path especificado
                cursor.execute("""
                    SELECT DISTINCT 
                        SUBSTR(SUBSTR(file_path, LENGTH(?) + 2), 1, 
                               INSTR(SUBSTR(file_path, LENGTH(?) + 2), '/') - 1) as folder_name,
                        ? || '/' || SUBSTR(SUBSTR(file_path, LENGTH(?) + 2), 1, 
                                          INSTR(SUBSTR(file_path, LENGTH(?) + 2), '/') - 1) as folder_path
                    FROM songs 
                    WHERE origen = 'local' 
                    AND file_path LIKE ? || '/%'
                    AND LENGTH(SUBSTR(file_path, LENGTH(?) + 2)) > 0
                    AND INSTR(SUBSTR(file_path, LENGTH(?) + 2), '/') > 0
                    ORDER BY folder_name
                """, (path, path, path, path, path, path, path, path))
            
            items = []
            for row in cursor.fetchall():
                if row[0]:  # Solo si hay nombre de carpeta
                    items.append({
                        'name': row[0],
                        'type': 'folder',
                        'path': row[1],
                        'full_path': f"Desde BD: {row[1]}"
                    })
            
            conn.close()
            
            return {
                'current_path': path,
                'items': items,
                'parent_path': str(Path(path).parent) if path and path != '.' else None
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo estructura de carpetas: {e}")
            conn.close()
            return {'error': str(e)}



        


    def download_album_local(self, album_id, download_id):
        """Descarga álbum desde archivos locales montados"""
        try:
            download_status[download_id]['status'] = 'analyzing'
            download_status[download_id]['message'] = 'Analizando disponibilidad local...'
            
            # Obtener información de archivos
            files_info = self.get_album_files_info(album_id)
            if not files_info:
                raise Exception("No se pudo obtener información del álbum")
            
            album = files_info['album']
            local_files = files_info['local_files']
            missing_files = files_info['missing_files']
            
            if not local_files:
                raise Exception("No hay archivos disponibles localmente")
            
            # Crear directorio de destino
            dest_path = Path(self.download_path) / album['artist_name'] / album['name']
            dest_path.mkdir(parents=True, exist_ok=True)
            
            download_status[download_id].update({
                'status': 'downloading',
                'message': f'Copiando {len(local_files)} archivos...',
                'total_files': len(local_files),
                'copied_files': 0
            })
            
            # Copiar archivos disponibles
            copied_count = 0
            for file_info in local_files:
                try:
                    src_path = Path(file_info['local_path'])
                    dst_path = dest_path / src_path.name
                    
                    download_status[download_id]['message'] = f'Copiando: {src_path.name}'
                    
                    shutil.copy2(src_path, dst_path)
                    copied_count += 1
                    
                    download_status[download_id]['copied_files'] = copied_count
                    download_status[download_id]['progress'] = int((copied_count / len(local_files)) * 100)
                    
                except Exception as e:
                    self.logger.warning(f"Error copiando {src_path}: {e}")
            
            # Resultado final
            if copied_count > 0:
                message_parts = [f'Álbum copiado: {copied_count}/{len(local_files)} archivos']
                if missing_files:
                    message_parts.append(f'{len(missing_files)} archivos no disponibles localmente')
                
                download_status[download_id].update({
                    'status': 'completed',
                    'progress': 100,
                    'message': '. '.join(message_parts),
                    'download_path': str(dest_path),
                    'copied_files': copied_count,
                    'missing_files': len(missing_files)
                })
            else:
                raise Exception("No se pudo copiar ningún archivo")
                
        except Exception as e:
            download_status[download_id].update({
                'status': 'error',
                'progress': 0,
                'message': f'Error en descarga local: {str(e)}'
            })
            self.logger.error(f"Error en descarga local {download_id}: {e}")



    def get_system_user(self):
        """Obtener el usuario del sistema desde configuración o variable de entorno"""
        # Prioridad: config.ini > variable de entorno > por defecto
        config_user = self.config.get('system', 'user', fallback=None)
        if config_user:
            return config_user
        
        env_user = os.environ.get('USER')
        if env_user:
            return env_user
        
        return 'dietpi'  # Usuario por defecto

# Crear instancia de la aplicación Flask
app = Flask(__name__)

explorer = MusicExplorer()

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@app.route('/api/search/artists')
def search_artists():
    """API para buscar artistas"""
    query = request.args.get('q', '')
    limit = request.args.get('limit', 50, type=int)
    
    if len(query) < 2:
        return jsonify([])
    
    results = explorer.search_artists(query, limit)
    return jsonify(results)

@app.route('/api/artist/<int:artist_id>')
def get_artist(artist_id):
    """API para obtener detalles de un artista"""
    details = explorer.get_artist_details(artist_id)
    if details:
        return jsonify(details)
    else:
        return jsonify({'error': 'Artista no encontrado'}), 404

@app.route('/api/album/<int:album_id>')
def get_album(album_id):
    """API para obtener detalles de un álbum"""
    details = explorer.get_album_details(album_id)
    if details:
        return jsonify(details)
    else:
        return jsonify({'error': 'Álbum no encontrado'}), 404

@app.route('/api/folders')
def get_folders():
    """API para obtener estructura de carpetas"""
    path = request.args.get('path', '')
    structure = explorer.get_folder_structure(path)
    return jsonify(structure)

@app.route('/api/stats')
def get_stats():
    """API para obtener estadísticas generales"""
    conn = explorer.get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de base de datos'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Estadísticas básicas
        cursor.execute("SELECT COUNT(*) FROM artists WHERE origen = 'local'")
        artist_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM albums WHERE origen = 'local'")
        album_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM songs WHERE origen = 'local'")
        song_count = cursor.fetchone()[0]
        
        # Artistas más escuchados
        cursor.execute("""
            SELECT s.artist, SUM(COALESCE(s.reproducciones, 1)) as total_plays
            FROM songs s
            WHERE s.origen = 'local'
            GROUP BY s.artist
            ORDER BY total_plays DESC
            LIMIT 10
        """)
        
        top_artists = []
        for row in cursor.fetchall():
            top_artists.append({
                'artist': row[0],
                'plays': row[1]
            })
        
        conn.close()
        
        return jsonify({
            'artist_count': artist_count,
            'album_count': album_count,
            'song_count': song_count,
            'top_artists': top_artists
        })
        
    except Exception as e:
        explorer.logger.error(f"Error obteniendo estadísticas: {e}")
        conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/album/<int:album_id>/download', methods=['POST'])
def download_album(album_id):
    """Endpoint para descargar álbum - VERSIÓN SIMPLIFICADA SOLO SSH"""
    
    # Verificar que el álbum existe y obtener información
    conn = explorer.get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de base de datos'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Obtener información del álbum y artista
        cursor.execute("""
            SELECT al.*, ar.name as artist_name, ar.id as artist_id
            FROM albums al
            JOIN artists ar ON al.artist_id = ar.id
            WHERE al.id = ? AND al.origen = 'local'
        """, (album_id,))
        
        album = cursor.fetchone()
        if not album:
            conn.close()
            return jsonify({'error': 'Álbum no encontrado'}), 404
        
        # Obtener ruta del álbum desde las canciones
        cursor.execute("""
            SELECT DISTINCT file_path
            FROM songs s
            WHERE s.album = ? AND s.artist = ? AND s.origen = 'local'
            LIMIT 1
        """, (album['name'], album['artist_name']))
        
        song_result = cursor.fetchone()
        conn.close()
        
        if not song_result or not song_result['file_path']:
            return jsonify({'error': 'No se encontró ruta del álbum'}), 404
        
        # Extraer directorio del álbum de la ruta del archivo
        song_path = Path(song_result['file_path'])
        album_path = song_path.parent
        
        download_id = f"album_{album_id}_{int(time_module.time())}"
        
        # Logging para debug
        explorer.logger.info(f"=== INICIO DESCARGA SSH ===")
        explorer.logger.info(f"Álbum: {album['name']}, Artista: {album['artist_name']}")
        explorer.logger.info(f"Ruta remota: {album_path}")
        explorer.logger.info(f"Download ID: {download_id}")
        
        # 🔔 NOTIFICAR INICIO DE DESCARGA
        user_info = request.headers.get('X-User-Info', 'Usuario Web')
        explorer.notifier.notify_download_started(
            album['name'], 
            album['artist_name'], 
            user_info,
            method='ssh'
        )
        explorer.logger.info(f"📱 Notificación enviada: Descarga iniciada")
        
        # Inicializar estado de descarga
        download_status[download_id] = {
            'status': 'initializing',
            'progress': 0,
            'message': f'Iniciando descarga SSH de "{album["name"]}"...',
            'album_name': album['name'],
            'artist_name': album['artist_name'],
            'method': 'ssh'
        }
        
        # Iniciar descarga SSH en hilo separado
        def perform_ssh_download():
            # TODO TU CÓDIGO SSH EXISTENTE - NO LO MODIFICO
            pass
        
        # Iniciar descarga en hilo separado
        download_thread = threading.Thread(target=perform_ssh_download)
        download_thread.daemon = True
        download_thread.start()
        
        return jsonify({
            'success': True,
            'download_id': download_id,
            'message': 'Descarga SSH iniciada',
            'album_name': album['name'],
            'artist_name': album['artist_name'],
            'album_path': str(album_path),
            'method': 'ssh'
        })
        
    except Exception as e:
        explorer.logger.error(f"Error iniciando descarga del álbum {album_id}: {e}")
        if conn:
            conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/debug/container-paths')
def debug_container_paths():
    """Debug de rutas y archivos en el contenedor"""
    try:
        result = {
            'timestamp': datetime.now().isoformat(),
            'images_directory': str(explorer.image_manager.images_dir),
            'paths_check': {},
            'files_check': {}
        }
        
        # Verificar directorios principales
        dirs_to_check = [
            explorer.image_manager.images_dir,
            explorer.image_manager.artists_dir,
            explorer.image_manager.albums_dir,
            Path('/app/data'),
            Path('/downloads')
        ]
        
        for dir_path in dirs_to_check:
            result['paths_check'][str(dir_path)] = {
                'exists': dir_path.exists(),
                'is_dir': dir_path.is_dir() if dir_path.exists() else False,
                'readable': os.access(str(dir_path), os.R_OK) if dir_path.exists() else False
            }
        
        # Verificar archivos específicos
        files_to_check = [
            explorer.image_manager.images_dir / 'master_index.json',
            Path('/app/data/musica.sqlite'),
            Path('/app/config.ini')
        ]
        
        for file_path in files_to_check:
            result['files_check'][str(file_path)] = {
                'exists': file_path.exists(),
                'is_file': file_path.is_file() if file_path.exists() else False,
                'readable': os.access(str(file_path), os.R_OK) if file_path.exists() else False,
                'size': file_path.stat().st_size if file_path.exists() else 0
            }
        
        # Contar archivos de imagen
        if explorer.image_manager.artists_dir.exists():
            result['artists_files_count'] = len(list(explorer.image_manager.artists_dir.glob('*.*')))
        
        if explorer.image_manager.albums_dir.exists():
            result['albums_files_count'] = len(list(explorer.image_manager.albums_dir.glob('*.*')))
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# AÑADIR ENDPOINT PARA TESTING DE TELEGRAM
@app.route('/api/telegram/test')
def test_telegram():
    """Endpoint para probar notificaciones de Telegram"""
    try:
        success, message = explorer.notifier.test_connection()
        return jsonify({
            'success': success,
            'message': message,
            'enabled': explorer.notifier.enabled
        })
    except Exception as e:
        explorer.logger.error(f"Error probando Telegram: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'enabled': False
        }), 500


@app.route('/api/download/<download_id>/status')
def get_download_status(download_id):
    """Obtener estado de una descarga"""
    if download_id in download_status:
        return jsonify(download_status[download_id])
    else:
        return jsonify({'error': 'Descarga no encontrada'}), 404

@app.route('/api/downloads/active')
def get_active_downloads():
    """Obtener todas las descargas activas"""
    active = {k: v for k, v in download_status.items() 
              if v['status'] in ['downloading', 'completed']}
    return jsonify(active)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/api/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    """Manejar requests OPTIONS para CORS"""
    response = app.make_default_options_response()
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response





# CANCIONES


@app.route('/api/album/<int:album_id>/details')
def get_album_details_with_tracks(album_id):
    """Obtener detalles completos del álbum con tracklist - VERSIÓN CORREGIDA"""
    conn = explorer.get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de base de datos'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Información del álbum
        cursor.execute("""
            SELECT al.*, ar.name as artist_name, ar.id as artist_id
            FROM albums al
            JOIN artists ar ON al.artist_id = ar.id
            WHERE al.id = ? AND al.origen = 'local'
        """, (album_id,))
        
        album = cursor.fetchone()
        if not album:
            conn.close()
            return jsonify({'error': 'Álbum no encontrado'}), 404
        
        # Canciones del álbum con información completa
        cursor.execute("""
            SELECT s.*, 
                   CASE WHEN l.lyrics IS NOT NULL THEN 1 ELSE 0 END as has_lyrics,
                   sl.spotify_url, sl.youtube_url, sl.bandcamp_url
            FROM songs s
            LEFT JOIN lyrics l ON s.id = l.track_id
            LEFT JOIN song_links sl ON s.id = sl.song_id
            WHERE s.album = ? AND s.artist = ? AND s.origen = 'local'
            ORDER BY s.track_number, s.title
        """, (album['name'], album['artist_name']))
        
        tracks = []
        for track_row in cursor.fetchall():
            track_dict = dict(track_row)
            tracks.append(track_dict)
        
        # USAR SISTEMA CORRECTO DE IMÁGENES LOCALES
        album_dict = dict(album)
        album_dict['best_album_art'] = explorer.image_manager.get_album_image(album_id)
        
        conn.close()
        
        return jsonify({
            'album': album_dict,
            'tracks': tracks,
            'track_count': len(tracks)
        })
        
    except Exception as e:
        explorer.logger.error(f"Error obteniendo detalles del álbum: {e}")
        if conn:
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/song/<int:song_id>/details')
def get_song_details(song_id):
    """Obtener detalles completos de una canción incluyendo letras y enlaces"""
    conn = explorer.get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de base de datos'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Información de la canción
        cursor.execute("""
            SELECT s.*, 
                   CASE WHEN l.lyrics IS NOT NULL THEN 1 ELSE 0 END as has_lyrics,
                   l.lyrics, l.source as lyrics_source
            FROM songs s
            LEFT JOIN lyrics l ON s.id = l.track_id
            WHERE s.id = ? AND s.origen = 'local'
        """, (song_id,))
        
        song = cursor.fetchone()
        if not song:
            conn.close()
            return jsonify({'error': 'Canción no encontrada'}), 404
        
        # Enlaces de la canción
        cursor.execute("""
            SELECT spotify_url, youtube_url, bandcamp_url, soundcloud_url, 
                   lastfm_url, musicbrainz_url, preview_url
            FROM song_links
            WHERE song_id = ?
        """, (song_id,))
        
        links = cursor.fetchone()
        links_dict = dict(links) if links else {}
        
        conn.close()
        
        song_dict = dict(song)
        song_dict['links'] = links_dict
        
        return jsonify(song_dict)
        
    except Exception as e:
        explorer.logger.error(f"Error obteniendo detalles de la canción: {e}")
        if conn:
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/icons/<icon_name>')
def serve_icon(icon_name):
    """Servir iconos SVG desde el directorio local"""
    try:
        icons_path = '/home/huan/gits/pollo/music-fuzzy/ui/svg'
        
        # Validar que el archivo existe y es SVG
        if not icon_name.endswith('.svg'):
            icon_name += '.svg'
        
        icon_path = os.path.join(icons_path, icon_name)
        if not os.path.exists(icon_path):
            return jsonify({'error': 'Icono no encontrado'}), 404
        
        return send_from_directory(icons_path, icon_name, mimetype='image/svg+xml')
        
    except Exception as e:
        explorer.logger.error(f"Error sirviendo icono {icon_name}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/test-image')
def test_image():
    """Endpoint de test simple para verificar que HTTP funciona"""
    try:
        # Crear una imagen dummy en memoria
        from io import BytesIO
        import base64
        
        # Imagen PNG 1x1 transparente en base64
        png_data = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==')
        
        response = app.response_class(
            png_data,
            mimetype='image/png',
            headers={
                'Content-Type': 'image/png',
                'Cache-Control': 'no-cache',
                'Strict-Transport-Security': 'max-age=0',
                'Access-Control-Allow-Origin': '*',
                'X-Test-Image': 'true'
            }
        )
        
        explorer.logger.info("Test image served successfully")
        return response
        
    except Exception as e:
        explorer.logger.error(f"Error serving test image: {e}")
        return jsonify({'error': str(e)}), 500


@app.after_request
def add_http_headers(response):
    """Headers HTTP simplificados para evitar duplicados"""
    
    # Solo añadir headers si no existen ya
    if 'Access-Control-Allow-Origin' not in response.headers:
        response.headers['Access-Control-Allow-Origin'] = '*'
    
    if 'Access-Control-Allow-Methods' not in response.headers:
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, PUT, DELETE'
    
    if 'Access-Control-Allow-Headers' not in response.headers:
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    
    # Headers anti-HTTPS
    response.headers['Strict-Transport-Security'] = 'max-age=0'
    response.headers['X-Force-HTTP'] = 'true'
    
    return response





@app.route('/api/local-image/<path:image_path>')
def serve_local_image(image_path):
    """Servir imágenes desde el directorio local del contenedor"""
    try:
        # Decodificar la ruta
        import urllib.parse
        decoded_path = urllib.parse.unquote(image_path)
        
        # Construir ruta completa
        full_path = explorer.image_manager.images_dir / decoded_path
        
        # Verificaciones de seguridad
        if not full_path.exists():
            explorer.logger.warning(f"Imagen no encontrada: {full_path}")
            return jsonify({'error': 'Imagen no encontrada'}), 404
        
        if not full_path.is_file():
            explorer.logger.warning(f"La ruta no es un archivo: {full_path}")
            return jsonify({'error': 'Ruta no es un archivo'}), 400
        
        # Verificar que está dentro del directorio permitido
        try:
            full_path.resolve().relative_to(explorer.image_manager.images_dir.resolve())
        except ValueError:
            explorer.logger.warning(f"Acceso no permitido a: {full_path}")
            return jsonify({'error': 'Acceso no permitido'}), 403
        
        # Detectar tipo MIME
        mime_type, _ = mimetypes.guess_type(str(full_path))
        if not mime_type or not mime_type.startswith('image/'):
            mime_type = 'image/jpeg'  # fallback
        
        # Servir archivo
        directory = str(full_path.parent)
        filename = full_path.name
        
        explorer.logger.debug(f"Sirviendo imagen local: {full_path}")
        
        response = send_from_directory(directory, filename, mimetype=mime_type)
        
        # Headers de cache
        response.headers['Cache-Control'] = 'public, max-age=86400'  # 1 día
        response.headers['ETag'] = f'"{hash(str(full_path.stat().st_mtime))}"'
        
        return response
        
    except Exception as e:
        explorer.logger.error(f"Error sirviendo imagen local {image_path}: {e}")
        return jsonify({'error': str(e)}), 500




@app.route('/api/artist/<int:artist_id>/images')
def get_artist_images(artist_id):
    """Obtener todas las imágenes de un artista"""
    images = explorer.image_manager.get_all_artist_images(artist_id)
    return jsonify({
        'artist_id': artist_id,
        'images': images
    })





@app.route('/api/images/stats')
def get_images_stats():
    """Obtener estadísticas de imágenes disponibles"""
    try:
        stats = explorer.image_manager.get_stats()
        return jsonify(stats)
    except Exception as e:
        explorer.logger.error(f"Error obteniendo estadísticas de imágenes: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/debug/images-system')
def debug_images_system():
    """Debug completo del sistema de imágenes"""
    try:
        debug_info = {
            'images_directory': str(explorer.image_manager.images_dir),
            'master_index_file': str(explorer.image_manager.images_dir / 'master_index.json'),
            'master_index_exists': (explorer.image_manager.images_dir / 'master_index.json').exists(),
            'artists_dir': str(explorer.image_manager.artists_dir),
            'albums_dir': str(explorer.image_manager.albums_dir),
            'artists_dir_exists': explorer.image_manager.artists_dir.exists(),
            'albums_dir_exists': explorer.image_manager.albums_dir.exists(),
            'stats': explorer.image_manager.get_stats(),
            'sample_data': {}
        }
        
        # Mostrar algunas entradas del índice
        artists_data = explorer.image_manager.master_index.get('artists', {})
        albums_data = explorer.image_manager.master_index.get('albums', {})
        
        debug_info['sample_data']['first_3_artists'] = dict(list(artists_data.items())[:3])
        debug_info['sample_data']['first_3_albums'] = dict(list(albums_data.items())[:3])
        
        # Verificar archivos físicos de muestra
        if artists_data:
            first_artist_id = list(artists_data.keys())[0]
            first_artist = artists_data[first_artist_id]
            if first_artist.get('filename'):
                artist_file_path = explorer.image_manager.artists_dir / first_artist['filename']
                debug_info['sample_data']['first_artist_file_exists'] = artist_file_path.exists()
                debug_info['sample_data']['first_artist_file_path'] = str(artist_file_path)
        
        if albums_data:
            first_album_id = list(albums_data.keys())[0]
            first_album = albums_data[first_album_id]
            if first_album.get('filename'):
                album_file_path = explorer.image_manager.albums_dir / first_album['filename']
                debug_info['sample_data']['first_album_file_exists'] = album_file_path.exists()
                debug_info['sample_data']['first_album_file_path'] = str(album_file_path)
        
        return jsonify(debug_info)
        
    except Exception as e:
        explorer.logger.error(f"Error en debug del sistema de imágenes: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug/list-image-files')
def list_image_files():
    """Listar archivos físicos en los directorios de imágenes"""
    try:
        result = {
            'artists_dir': str(explorer.image_manager.artists_dir),
            'albums_dir': str(explorer.image_manager.albums_dir),
            'artists_files': [],
            'albums_files': []
        }
        
        # Listar archivos en directorio de artistas
        if explorer.image_manager.artists_dir.exists():
            for file_path in explorer.image_manager.artists_dir.glob('*'):
                if file_path.is_file():
                    result['artists_files'].append({
                        'filename': file_path.name,
                        'size': file_path.stat().st_size,
                        'extension': file_path.suffix
                    })
        
        # Listar archivos en directorio de álbumes  
        if explorer.image_manager.albums_dir.exists():
            for file_path in explorer.image_manager.albums_dir.glob('*'):
                if file_path.is_file():
                    result['albums_files'].append({
                        'filename': file_path.name,
                        'size': file_path.stat().st_size,
                        'extension': file_path.suffix
                    })
        
        result['artists_count'] = len(result['artists_files'])
        result['albums_count'] = len(result['albums_files'])
        
        return jsonify(result)
        
    except Exception as e:
        explorer.logger.error(f"Error listando archivos de imágenes: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/debug/images-system-check')
def debug_images_system_check():
    """Verificar que el sistema de imágenes esté funcionando correctamente"""
    try:
        result = {
            'system_status': 'checking',
            'master_index_loaded': bool(explorer.image_manager.master_index),
            'images_directory': str(explorer.image_manager.images_dir),
            'artists_dir_exists': explorer.image_manager.artists_dir.exists(),
            'albums_dir_exists': explorer.image_manager.albums_dir.exists(),
            'artists_in_index': len(explorer.image_manager.master_index.get('artists', {})),
            'albums_in_index': len(explorer.image_manager.master_index.get('albums', {})),
            'test_results': {}
        }
        
        # Test con primer artista disponible
        artists_data = explorer.image_manager.master_index.get('artists', {})
        if artists_data:
            first_artist_id = list(artists_data.keys())[0]
            artist_url = explorer.image_manager.get_artist_image(first_artist_id)
            artist_info = explorer.image_manager.get_artist_info(first_artist_id)
            
            result['test_results']['first_artist'] = {
                'id': first_artist_id,
                'name': artist_info.get('name') if artist_info else 'Unknown',
                'filename': artist_info.get('filename') if artist_info else None,
                'generated_url': artist_url,
                'file_exists': explorer.image_manager.verify_image_file('artist', artist_info.get('filename')) if artist_info and artist_info.get('filename') else False
            }
        
        # Test con primer álbum disponible
        albums_data = explorer.image_manager.master_index.get('albums', {})
        if albums_data:
            first_album_id = list(albums_data.keys())[0]
            album_url = explorer.image_manager.get_album_image(first_album_id)
            album_info = explorer.image_manager.get_album_info(first_album_id)
            
            result['test_results']['first_album'] = {
                'id': first_album_id,
                'name': album_info.get('name') if album_info else 'Unknown',
                'filename': album_info.get('filename') if album_info else None,
                'generated_url': album_url,
                'file_exists': explorer.image_manager.verify_image_file('album', album_info.get('filename')) if album_info and album_info.get('filename') else False
            }
        
        # Estado general del sistema
        has_working_images = False
        if result['test_results'].get('first_artist', {}).get('file_exists'):
            has_working_images = True
        if result['test_results'].get('first_album', {}).get('file_exists'):
            has_working_images = True
        
        result['system_status'] = 'ok' if has_working_images else 'no_working_images' if result['test_results'] else 'no_data'
        
        return jsonify(result)
        
    except Exception as e:
        explorer.logger.error(f"Error en check del sistema de imágenes: {e}")
        return jsonify({
            'system_status': 'error',
            'error': str(e)
        }), 500




@app.route('/api/debug/image-info/artist/<int:artist_id>')
def debug_artist_image_info(artist_id):
    """Debug específico para imagen de artista"""
    try:
        artist_info = explorer.image_manager.get_artist_info(artist_id)
        generated_url = explorer.image_manager.get_artist_image(artist_id)
        
        result = {
            'artist_id': artist_id,
            'artist_info': artist_info,
            'generated_url': generated_url,
            'file_exists': False
        }
        
        if artist_info and artist_info.get('filename'):
            file_path = explorer.image_manager.artists_dir / artist_info['filename']
            result['file_exists'] = file_path.exists()
            result['file_path'] = str(file_path)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug/image-info/album/<int:album_id>')
def debug_album_image_info(album_id):
    """Debug específico para imagen de álbum"""
    try:
        album_info = explorer.image_manager.get_album_info(album_id)
        generated_url = explorer.image_manager.get_album_image(album_id)
        
        result = {
            'album_id': album_id,
            'album_info': album_info,
            'generated_url': generated_url,
            'file_exists': False
        }
        
        if album_info and album_info.get('filename'):
            file_path = explorer.image_manager.albums_dir / album_info['filename']
            result['file_exists'] = file_path.exists()
            result['file_path'] = str(file_path)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug/test-first-image')
def debug_test_first_image():
    """Test con la primera imagen disponible"""
    try:
        artists_data = explorer.image_manager.master_index.get('artists', {})
        albums_data = explorer.image_manager.master_index.get('albums', {})
        
        result = {
            'artists_in_index': len(artists_data),
            'albums_in_index': len(albums_data),
            'test_results': {}
        }
        
        # Test con primer artista
        if artists_data:
            first_artist_id = list(artists_data.keys())[0]
            artist_url = explorer.image_manager.get_artist_image(first_artist_id)
            artist_info = explorer.image_manager.get_artist_info(first_artist_id)
            
            result['test_results']['first_artist'] = {
                'id': first_artist_id,
                'name': artist_info.get('name') if artist_info else 'Unknown',
                'filename': artist_info.get('filename') if artist_info else None,
                'original_path': artist_info.get('original_path') if artist_info else None,
                'generated_url': artist_url,
                'file_exists': explorer.image_manager.verify_image_file('artist', artist_info.get('filename')) if artist_info and artist_info.get('filename') else False
            }
        
        # Test con primer álbum
        if albums_data:
            first_album_id = list(albums_data.keys())[0]
            album_url = explorer.image_manager.get_album_image(first_album_id)
            album_info = explorer.image_manager.get_album_info(first_album_id)
            
            result['test_results']['first_album'] = {
                'id': first_album_id,
                'name': album_info.get('name') if album_info else 'Unknown',
                'filename': album_info.get('filename') if album_info else None,
                'original_path': album_info.get('original_path') if album_info else None,
                'generated_url': album_url,
                'file_exists': explorer.image_manager.verify_image_file('album', album_info.get('filename')) if album_info and album_info.get('filename') else False
            }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug/system-status')
def debug_system_status():
    """Debug completo del estado del sistema"""
    try:
        result = {
            'timestamp': datetime.now().isoformat(),
            'images_system': {},
            'database': {},
            'config': {}
        }
        
        # Estado del sistema de imágenes
        try:
            result['images_system'] = explorer.image_manager.get_stats()
            result['images_system']['master_index_loaded'] = bool(explorer.image_manager.master_index)
            result['images_system']['directories_exist'] = {
                'base': explorer.image_manager.images_dir.exists(),
                'artists': explorer.image_manager.artists_dir.exists(),
                'albums': explorer.image_manager.albums_dir.exists()
            }
        except Exception as e:
            result['images_system']['error'] = str(e)
        
        # Estado de la base de datos
        try:
            conn = explorer.get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM artists WHERE origen = 'local'")
                result['database']['artists_count'] = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM albums WHERE origen = 'local'")
                result['database']['albums_count'] = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM songs WHERE origen = 'local'")
                result['database']['songs_count'] = cursor.fetchone()[0]
                conn.close()
                result['database']['status'] = 'ok'
            else:
                result['database']['status'] = 'connection_failed'
        except Exception as e:
            result['database']['error'] = str(e)
        
        # Configuración
        result['config']['images_local_enabled'] = explorer.config.getboolean('images', 'local_enabled', fallback=False)
        result['config']['images_directory'] = explorer.config.get('images', 'local_dir', fallback='/app/images')
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Configuración del servidor - FLASK DIRECTO
    host = explorer.config.get('web', 'host', fallback='0.0.0.0')
    port = explorer.config.getint('web', 'port', fallback=8447)  # Puerto 8447
    debug = explorer.config.getboolean('web', 'debug', fallback=False)
    
    explorer.logger.info(f"Iniciando servidor Flask DIRECTO en {host}:{port}")
    explorer.logger.info("MODO: Sin Nginx, sin SSL/TLS, solo HTTP")
    
    app.run(
        host=host, 
        port=port, 
        debug=debug,
        ssl_context=None,
        threaded=True
    )