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
from telegram_notifier import create_notifier

download_status = {}

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
        
        # Configuración para acceso local
        self.local_access_enabled = self.config.getboolean('music', 'local_access_enabled', fallback=False)
        self.mounted_paths = []
        if self.local_access_enabled:
            mounted_paths_str = self.config.get('music', 'mounted_paths', fallback='')
            self.mounted_paths = [path.strip() for path in mounted_paths_str.split(',') if path.strip()]
            self.logger.info(f"Acceso local habilitado para rutas: {self.mounted_paths}")

        # Método de descarga preferido
        self.preferred_download_method = self.config.get('download', 'preferred_method', fallback='ssh')

    def check_local_file_exists(self, file_path):
        """Versión simple de verificación de archivos"""
        if not self.local_access_enabled or not file_path:
            return False
        
        try:
            # 1. Verificar ruta completa
            if os.path.exists(file_path) and os.access(file_path, os.R_OK):
                return True
            
            # 2. Verificar en rutas montadas
            for mounted_path in self.mounted_paths:
                if file_path.startswith(mounted_path) and os.path.exists(file_path):
                    return True
            
            return False
        except Exception as e:
            self.logger.debug(f"Error verificando {file_path}: {e}")
            return False

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


    def check_album_local_availability(self, album_name, artist_name):
        """Verifica disponibilidad local de un álbum completo"""
        if not self.local_access_enabled:
            return {'available': False, 'reason': 'Local access disabled'}
        
        conn = self.get_db_connection()
        if not conn:
            return {'available': False, 'reason': 'Database error'}
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT file_path FROM songs s
                WHERE s.album = ? AND s.artist = ? AND s.origen = 'local'
            """, (album_name, artist_name))
            
            tracks = cursor.fetchall()
            conn.close()
            
            if not tracks:
                return {'available': False, 'reason': 'No tracks found'}
            
            # Verificar archivos locales
            local_files = []
            missing_files = []
            album_local_path = None
            
            for track in tracks:
                if track['file_path']:
                    local_path = self.check_local_file_exists(track['file_path'])
                    if local_path:
                        local_files.append(local_path)
                        if not album_local_path:
                            album_local_path = str(Path(local_path).parent)
                    else:
                        missing_files.append(track['file_path'])
            
            total_tracks = len(tracks)
            available_tracks = len(local_files)
            percentage = (available_tracks / total_tracks * 100) if total_tracks > 0 else 0
            
            return {
                'available': available_tracks > 0,
                'total_tracks': total_tracks,
                'available_tracks': available_tracks,
                'missing_tracks': len(missing_files),
                'percentage': percentage,
                'album_local_path': album_local_path,
                'local_files': local_files,
                'missing_files': missing_files
            }
            
        except Exception as e:
            self.logger.error(f"Error verificando disponibilidad local: {e}")
            if conn:
                conn.close()
            return {'available': False, 'reason': f'Error: {str(e)}'}

    def get_db_connection(self):
        """Obtiene conexión a la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            self.logger.error(f"Error conectando a la base de datos: {e}")
            return None
    
    def get_album_image(self, album_dict):
        """Función simple para obtener imagen de álbum"""
        # 1. album_art_path
        if album_dict.get('album_art_path') and self.check_local_file_exists(album_dict['album_art_path']):
            return album_dict['album_art_path']
        
        # 2. Buscar cover.jpg/png en directorio
        if album_dict.get('sample_path'):
            album_dir = str(Path(album_dict['sample_path']).parent)
            for cover_name in ['cover.jpg', 'cover.png', 'folder.jpg', 'folder.png']:
                cover_path = os.path.join(album_dir, cover_name)
                if self.check_local_file_exists(cover_path):
                    return cover_path
        
        return None



    def search_artists(self, query, limit=50):
        """Busca artistas por nombre"""
        conn = self.get_db_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT a.id, a.name, a.bio, a.origin, a.formed_year, 
                    a.img, a.img_urls, a.img_paths, a.wikipedia_content,
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
                # Obtener la mejor imagen
                best_image = None
                
                # Primero img
                if row['img'] and os.path.exists(row['img']):
                    best_image = row['img']
                # Luego img_paths
                elif row['img_paths']:
                    try:
                        import json
                        paths = json.loads(row['img_paths'])
                        if isinstance(paths, list) and len(paths) > 0:
                            first_path = paths[0]
                            if first_path and os.path.exists(first_path):
                                best_image = first_path
                    except:
                        pass
                
                results.append({
                    'id': row['id'],
                    'name': row['name'],
                    'bio': row['bio'],
                    'origin': row['origin'],
                    'formed_year': row['formed_year'],
                    'img': best_image,
                    'wikipedia_content': row['wikipedia_content'],
                    'album_count': row['album_count'] or 0,
                    'song_count': row['song_count'] or 0
                })
            
            conn.close()
            return results
            
        except Exception as e:
            self.logger.error(f"Error buscando artistas: {e}")
            if conn:
                conn.close()
            return []

    
   

    def get_artist_details(self, artist_id):
        """Obtiene detalles completos de un artista"""
        conn = self.get_db_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            
            # Información del artista
            cursor.execute("""
                SELECT *, img, img_urls, img_paths FROM artists 
                WHERE id = ? AND origen = 'local'
            """, (artist_id,))
            
            artist = cursor.fetchone()
            if not artist:
                conn.close()
                return None
            
            # Álbumes del artista
            cursor.execute("""
                SELECT al.*, al.album_art_path,
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
                
                # Buscar imagen del álbum
                best_album_art = None
                
                # 1. album_art_path
                if album_dict.get('album_art_path') and os.path.exists(album_dict['album_art_path']):
                    best_album_art = album_dict['album_art_path']
                # 2. Buscar en directorio
                elif album_dict.get('sample_path'):
                    from pathlib import Path
                    album_dir = str(Path(album_dict['sample_path']).parent)
                    for cover_name in ['cover.jpg', 'cover.png', 'folder.jpg', 'folder.png']:
                        cover_path = os.path.join(album_dir, cover_name)
                        if os.path.exists(cover_path):
                            best_album_art = cover_path
                            break
                
                album_dict['best_album_art'] = best_album_art
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
            
            # Obtener imagen del artista
            artist_dict = dict(artist)
            best_artist_image = None
            
            # Primero img
            if artist_dict.get('img') and os.path.exists(artist_dict['img']):
                best_artist_image = artist_dict['img']
            # Luego img_paths
            elif artist_dict.get('img_paths'):
                try:
                    import json
                    paths = json.loads(artist_dict['img_paths'])
                    if isinstance(paths, list) and len(paths) > 0:
                        first_path = paths[0]
                        if first_path and os.path.exists(first_path):
                            best_artist_image = first_path
                except:
                    pass
            
            artist_dict['img'] = best_artist_image
            
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

    def get_artist_image(self, artist_row):
        """Función simple para obtener imagen de artista"""
        if not artist_row:
            return None
        
        # 1. Columna img
        if artist_row.get('img') and self.check_local_file_exists_simple(artist_row['img']):
            return artist_row['img']
        
        # 2. img_paths como JSON
        if artist_row.get('img_paths'):
            try:
                import json
                paths = json.loads(artist_row['img_paths'])
                if isinstance(paths, list) and len(paths) > 0:
                    first_path = paths[0]
                    if first_path and self.check_local_file_exists_simple(first_path):
                        return first_path
            except:
                pass
        
        # 3. img_urls como JSON (buscar campo 'path')
        if artist_row.get('img_urls'):
            try:
                import json
                urls = json.loads(artist_row['img_urls'])
                if isinstance(urls, list) and len(urls) > 0:
                    first_item = urls[0]
                    if isinstance(first_item, dict) and 'path' in first_item:
                        path = first_item['path']
                        if path and self.check_local_file_exists_simple(path):
                            return path
            except:
                pass
        
        return None


    def generate_image_url(image_path):
        """Genera URL para servir imagen local"""
        if not image_path:
            return None
        
        import urllib.parse
        encoded_path = urllib.parse.quote(image_path.encode('utf-8'))
        return f"/api/image/{encoded_path}"

    
    def get_album_details(self, album_id):
        """Obtiene detalles de un álbum"""
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
            
            return {
                'album': dict(album),
                'tracks': tracks
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo detalles del álbum: {e}")
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


    def get_album_files_info(self, album_id):
        """Obtiene información de archivos del álbum, incluyendo disponibilidad local"""
        details = self.get_album_details(album_id)
        if not details:
            return None
        
        album = details['album']
        tracks = details['tracks']
        
        # Analizar disponibilidad de archivos
        local_files = []
        missing_files = []
        album_path = None
        
        for track in tracks:
            if track.get('file_path'):
                local_path = self.check_local_file_exists(track['file_path'])
                if local_path:
                    local_files.append({
                        'track': track,
                        'local_path': local_path,
                        'exists': True
                    })
                    # Obtener directorio del álbum
                    if not album_path:
                        album_path = str(Path(local_path).parent)
                else:
                    missing_files.append({
                        'track': track,
                        'expected_path': track['file_path'],
                        'exists': False
                    })
        
        return {
            'album': album,
            'tracks': tracks,
            'local_files': local_files,
            'missing_files': missing_files,
            'album_path': album_path,
            'local_availability': {
                'total_tracks': len(tracks),
                'available_locally': len(local_files),
                'missing_locally': len(missing_files),
                'percentage': (len(local_files) / len(tracks) * 100) if tracks else 0
            }
        }

    def get_best_artist_image(self, artist_row):
        """Helper para obtener la mejor imagen de un artista"""
        if not artist_row or not self.local_access_enabled:
            return None
        
        # 1. Columna img (ruta principal)
        if artist_row.get('img'):
            img_path = artist_row['img']
            if self.check_local_file_exists(img_path):
                return img_path
        
        # 2. Columna img_paths (JSON con múltiples rutas)
        if artist_row.get('img_paths'):
            try:
                import json
                paths = json.loads(artist_row['img_paths'])
                if isinstance(paths, list):
                    for path in paths:
                        if path and self.check_local_file_exists(path):
                            return path
            except (json.JSONDecodeError, TypeError):
                # Si no es JSON, intentar como CSV
                paths = [p.strip() for p in str(artist_row['img_paths']).split(',') if p.strip()]
                for path in paths:
                    if self.check_local_file_exists(path):
                        return path
        
        # 3. Columna img_urls (solo rutas locales)
        if artist_row.get('img_urls'):
            try:
                import json
                urls = json.loads(artist_row['img_urls'])
                if isinstance(urls, list):
                    for item in urls:
                        # Puede ser string o dict con 'path'
                        path = item.get('path') if isinstance(item, dict) else item
                        if path and not str(path).startswith(('http://', 'https://')) and self.check_local_file_exists(path):
                            return path
            except (json.JSONDecodeError, TypeError):
                # Si no es JSON, intentar como CSV
                urls = [u.strip() for u in str(artist_row['img_urls']).split(',') if u.strip()]
                for url in urls:
                    if not url.startswith(('http://', 'https://')) and self.check_local_file_exists(url):
                        return url
        
        return None


    def get_best_album_image(self, album_dict):
        """Helper para obtener la mejor imagen de un álbum"""
        # 1. album_art_path del álbum
        if album_dict.get('album_art_path'):
            if self.check_local_file_exists(album_dict['album_art_path']):
                self.logger.info(f"Imagen de álbum encontrada: {album_dict['album_art_path']}")
                return album_dict['album_art_path']
        
        # 2. album_art_path_denorm de canciones
        if album_dict.get('song_album_art'):
            if self.check_local_file_exists(album_dict['song_album_art']):
                self.logger.info(f"Imagen de canción encontrada: {album_dict['song_album_art']}")
                return album_dict['song_album_art']
        
        # 3. Buscar en el directorio del álbum
        if album_dict.get('album_directory'):
            common_names = [
                'cover.jpg', 'cover.png', 'folder.jpg', 'folder.png',
                'album.jpg', 'album.png', 'front.jpg', 'front.png',
                'albumart.jpg', 'albumartsmall.jpg', 'thumb.jpg'
            ]
            for img_name in common_names:
                img_path = os.path.join(album_dict['album_directory'], img_name)
                if self.check_local_file_exists(img_path):
                    self.logger.info(f"Imagen de álbum descubierta: {img_path}")
                    return img_path
        
        return None

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
    """Endpoint para descargar álbum - VERSIÓN HÍBRIDA SSH + LOCAL"""
    
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
        
        # NUEVO: Verificar disponibilidad local
        local_availability = explorer.check_album_local_availability(album['name'], album['artist_name'])
        
        # Determinar método de descarga
        use_local_method = (
            explorer.preferred_download_method == 'local' and 
            local_availability['available'] and 
            local_availability['percentage'] >= 80  # Al menos 80% de archivos disponibles
        )
        
        # Logging para debug
        explorer.logger.info(f"=== INICIO DESCARGA ===")
        explorer.logger.info(f"Álbum: {album['name']}, Artista: {album['artist_name']}")
        explorer.logger.info(f"Ruta remota: {album_path}")
        explorer.logger.info(f"Download ID: {download_id}")
        explorer.logger.info(f"Método preferido: {explorer.preferred_download_method}")
        explorer.logger.info(f"Local disponible: {local_availability['available']} ({local_availability.get('percentage', 0):.1f}%)")
        explorer.logger.info(f"Método seleccionado: {'LOCAL' if use_local_method else 'SSH'}")
        
        # 🔔 NOTIFICAR INICIO DE DESCARGA
        user_info = request.headers.get('X-User-Info', 'Usuario Web')
        explorer.notifier.notify_download_started(
            album['name'], 
            album['artist_name'], 
            user_info,
            method='local' if use_local_method else 'ssh'
        )
        explorer.logger.info(f"📱 Notificación enviada: Descarga iniciada")
        
        # Inicializar estado de descarga
        download_status[download_id] = {
            'status': 'initializing',
            'progress': 0,
            'message': f'Iniciando descarga de "{album["name"]}" (método: {"local" if use_local_method else "SSH"})...',
            'album_name': album['name'],
            'artist_name': album['artist_name'],
            'method': 'local' if use_local_method else 'ssh',
            'local_availability': local_availability
        }
        
        # Iniciar descarga en hilo separado
        def perform_download():
            if use_local_method:
                # USAR DESCARGA LOCAL
                try:
                    explorer.perform_local_download(album['name'], album['artist_name'], download_id, local_availability)
                except Exception as e:
                    # Si falla local, intentar SSH como fallback
                    explorer.logger.warning(f"Descarga local falló, intentando SSH como fallback: {e}")
                    download_status[download_id]['message'] = 'Descarga local falló, intentando SSH...'
                    perform_ssh_download()
            else:
                # USAR DESCARGA SSH (TU CÓDIGO ORIGINAL)
                perform_ssh_download()
        
        def perform_ssh_download():
            # AQUÍ VA TODO TU CÓDIGO SSH ORIGINAL - NO LO MODIFICO
            try:
                download_status[download_id]['status'] = 'downloading'
                download_status[download_id]['message'] = f'Iniciando descarga SSH de "{album["name"]}"...'
                
                # DEBUG: Información del entorno actual
                explorer.logger.info(f"=== DEBUG ENTORNO ===")
                explorer.logger.info(f"Usuario actual (whoami): {os.getenv('USER', 'UNKNOWN')}")
                explorer.logger.info(f"UID del proceso: {os.getuid()}")
                
                # Configuración desde config.ini
                ssh_host = explorer.config.get('download', 'ssh_host', fallback='pepecono')
                ssh_user = explorer.config.get('download', 'ssh_user', fallback='pepe')
                
                explorer.logger.info(f"SSH Host: {ssh_host}")
                explorer.logger.info(f"SSH User: {ssh_user}")
                
                # OBTENER USUARIO DEL CONTENEDOR
                container_user = os.getenv('USER', 'musicapp')
                container_uid = os.getenv('CONTAINER_UID', '1000')
                
                explorer.logger.info(f"Usuario del contenedor (env): {container_user} (UID: {container_uid})")
                
                # Determinar el directorio home del usuario
                import pwd
                try:
                    user_info = pwd.getpwnam(container_user)
                    user_home = user_info.pw_dir
                    explorer.logger.info(f"Home del usuario {container_user}: {user_home}")
                except Exception as e:
                    user_home = f"/home/{container_user}"
                    explorer.logger.warning(f"No se pudo obtener info del usuario {container_user}: {e}, usando {user_home}")
                
                # Buscar clave SSH
                ssh_key_path = None
                possible_key_paths = [
                    f"{user_home}/.ssh/pepecono",
                    f"{user_home}/.ssh/id_rsa",
                    f"{user_home}/.ssh/id_ed25519"
                ]
                
                explorer.logger.info(f"Buscando claves SSH en:")
                for key_path in possible_key_paths:
                    exists = os.path.exists(key_path)
                    readable = os.access(key_path, os.R_OK) if exists else False
                    explorer.logger.info(f"  {key_path}: exists={exists}, readable={readable}")
                    if exists and readable:
                        ssh_key_path = key_path
                        break
                
                if not ssh_key_path:
                    error_msg = f"No se encontró clave SSH válida para usuario {container_user}"
                    explorer.logger.error(error_msg)
                    
                    # 🔔 NOTIFICAR ERROR
                    explorer.notifier.notify_download_error(
                        album['name'], 
                        album['artist_name'], 
                        f"Clave SSH no encontrada para usuario {container_user}"
                    )
                    
                    raise Exception(error_msg)
                
                explorer.logger.info(f"✅ Usando clave SSH: {ssh_key_path}")
                
                # Crear directorio de destino
                dest_path = Path(explorer.download_path) / album['artist_name'] / album['name']
                dest_path.mkdir(parents=True, exist_ok=True)
                explorer.logger.info(f"Directorio destino: {dest_path}")
                
                # Comando rsync
                rsync_cmd = [
                    'rsync',
                    '-avzh',
                    '--progress',
                    '-e', f'ssh -i {ssh_key_path} -o StrictHostKeyChecking=no -o ConnectTimeout=10',
                    f"{ssh_user}@{ssh_host}:{album_path}/",
                    str(dest_path) + "/"
                ]
                
                explorer.logger.info(f"=== COMANDO RSYNC ===")
                explorer.logger.info(f"Comando: {' '.join(rsync_cmd)}")
                
                # Probar primero test de conectividad SSH
                test_ssh_cmd = [
                    'ssh',
                    '-i', ssh_key_path,
                    '-o', 'StrictHostKeyChecking=no',
                    '-o', 'ConnectTimeout=10',
                    f"{ssh_user}@{ssh_host}",
                    'echo "SSH_TEST_OK"'
                ]
                
                # Ejecutar test SSH
                test_process = subprocess.Popen(
                    test_ssh_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env={
                        'HOME': user_home,
                        'USER': container_user,
                        'PATH': os.environ.get('PATH', '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin')
                    }
                )
                
                test_stdout, test_stderr = test_process.communicate(timeout=15)
                explorer.logger.info(f"Test SSH return code: {test_process.returncode}")
                
                if test_process.returncode != 0:
                    error_msg = f"Test SSH falló: {test_stderr}"
                    explorer.logger.error(error_msg)
                    
                    # 🔔 NOTIFICAR ERROR SSH
                    explorer.notifier.notify_download_error(
                        album['name'], 
                        album['artist_name'], 
                        f"Error de conexión SSH: {test_stderr[:100]}"
                    )
                    
                    raise Exception(error_msg)
                
                # Si el test SSH pasa, ejecutar rsync
                explorer.logger.info("✅ Test SSH exitoso, iniciando rsync...")
                
                # Ejecutar rsync
                process = subprocess.Popen(
                    rsync_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    env={
                        'HOME': user_home,
                        'USER': container_user,
                        'PATH': os.environ.get('PATH', '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin')
                    }
                )
                
                # Monitorear progreso
                stdout_lines = []
                stderr_lines = []
                
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    
                    if output:
                        line = output.strip()
                        stdout_lines.append(line)
                        download_status[download_id]['message'] = line
                        explorer.logger.info(f"rsync stdout: {line}")
                
                # Capturar stderr
                stderr_output = process.stderr.read()
                if stderr_output:
                    stderr_lines.append(stderr_output)
                    explorer.logger.info(f"rsync stderr: {stderr_output}")
                
                # Verificar resultado
                return_code = process.poll()
                explorer.logger.info(f"rsync return code: {return_code}")
                
                if return_code == 0:
                    # Verificar si realmente se descargó algo
                    downloaded_files = list(dest_path.rglob('*'))
                    file_count = len([f for f in downloaded_files if f.is_file()])
                    
                    explorer.logger.info(f"Archivos descargados: {file_count}")
                    
                    download_status[download_id] = {
                        'status': 'completed',
                        'progress': 100,
                        'message': f'Álbum "{album["name"]}" descargado exitosamente ({file_count} archivos)',
                        'album_name': album['name'],
                        'artist_name': album['artist_name'],
                        'download_path': str(dest_path),
                        'file_count': file_count,
                        'method': 'ssh'
                    }
                    
                    # 🔔 NOTIFICAR DESCARGA COMPLETADA
                    explorer.notifier.notify_download_completed(
                        album['name'], 
                        album['artist_name'], 
                        file_count, 
                        str(dest_path),
                        method='ssh'
                    )
                    
                    explorer.logger.info(f"✅ Descarga SSH completada: {download_id}")
                    explorer.logger.info(f"📱 Notificación enviada: Descarga completada")
                else:
                    all_stderr = '\n'.join(stderr_lines)
                    download_status[download_id] = {
                        'status': 'error',
                        'progress': 0,
                        'message': f'Error en descarga SSH (código {return_code}): {all_stderr}',
                        'album_name': album['name'],
                        'artist_name': album['artist_name'],
                        'method': 'ssh'
                    }
                    
                    # 🔔 NOTIFICAR ERROR EN DESCARGA
                    explorer.notifier.notify_download_error(
                        album['name'], 
                        album['artist_name'], 
                        f"Error rsync (código {return_code}): {all_stderr[:150]}"
                    )
                    
                    explorer.logger.error(f"❌ Error en descarga SSH {download_id} (código {return_code}): {all_stderr}")
                    
            except subprocess.TimeoutExpired as e:
                error_msg = f'Timeout en descarga SSH: {str(e)}'
                download_status[download_id] = {
                    'status': 'error',
                    'progress': 0,
                    'message': error_msg,
                    'album_name': album.get('name', 'Desconocido'),
                    'artist_name': album.get('artist_name', 'Desconocido'),
                    'method': 'ssh'
                }
                
                # 🔔 NOTIFICAR TIMEOUT
                explorer.notifier.notify_download_error(
                    album.get('name', 'Desconocido'), 
                    album.get('artist_name', 'Desconocido'), 
                    'Timeout en descarga SSH - conexión demasiado lenta'
                )
                
                explorer.logger.error(f"❌ Timeout en descarga SSH {download_id}: {e}")
            except Exception as e:
                error_msg = f'Error interno SSH: {str(e)}'
                download_status[download_id] = {
                    'status': 'error',
                    'progress': 0,
                    'message': error_msg,
                    'album_name': album.get('name', 'Desconocido'),
                    'artist_name': album.get('artist_name', 'Desconocido'),
                    'method': 'ssh'
                }
                
                # 🔔 NOTIFICAR ERROR GENERAL
                explorer.notifier.notify_download_error(
                    album.get('name', 'Desconocido'), 
                    album.get('artist_name', 'Desconocido'), 
                    str(e)[:150]
                )
                
                explorer.logger.error(f"❌ Excepción en descarga SSH {download_id}: {e}")
        
        # Iniciar descarga en hilo separado
        download_thread = threading.Thread(target=perform_download)
        download_thread.daemon = True
        download_thread.start()
        
        return jsonify({
            'success': True,
            'download_id': download_id,
            'message': 'Descarga iniciada',
            'album_name': album['name'],
            'artist_name': album['artist_name'],
            'album_path': str(album_path),
            'method': 'local' if use_local_method else 'ssh',
            'local_availability': local_availability
        })
        
    except Exception as e:
        explorer.logger.error(f"Error iniciando descarga del álbum {album_id}: {e}")
        if conn:
            conn.close()
        return jsonify({'error': str(e)}), 500

# NUEVO: Endpoint para verificar disponibilidad local
@app.route('/api/album/<int:album_id>/local-check')
def check_album_local_availability_endpoint(album_id):
    """API para verificar disponibilidad local de un álbum"""
    conn = explorer.get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de base de datos'}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT al.name, ar.name as artist_name
            FROM albums al
            JOIN artists ar ON al.artist_id = ar.id
            WHERE al.id = ? AND al.origen = 'local'
        """, (album_id,))
        
        album = cursor.fetchone()
        conn.close()
        
        if not album:
            return jsonify({'error': 'Álbum no encontrado'}), 404
        
        availability = explorer.check_album_local_availability(album['name'], album['artist_name'])
        return jsonify(availability)
        
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/album/<int:album_id>/files')
def get_album_files(album_id):
    """API para obtener información de archivos del álbum"""
    files_info = explorer.get_album_files_info(album_id)
    if files_info:
        return jsonify(files_info)
    else:
        return jsonify({'error': 'Álbum no encontrado'}), 404


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


# Añadir estas funciones a tu app.py

@app.route('/api/image/<path:image_path>')
def serve_image(image_path):
    """Servir imágenes desde las rutas montadas localmente"""
    try:
        import urllib.parse
        decoded_path = urllib.parse.unquote(image_path)
        
        explorer.logger.info(f"Solicitando imagen: {decoded_path}")
        
        if not explorer.local_access_enabled:
            return jsonify({'error': 'Acceso local deshabilitado'}), 404
        
        # Verificar si existe tal como está
        if os.path.exists(decoded_path) and os.access(decoded_path, os.R_OK):
            directory = os.path.dirname(decoded_path)
            filename = os.path.basename(decoded_path)
            explorer.logger.info(f"Imagen encontrada: {decoded_path}")
            return send_from_directory(directory, filename)
        
        # Si no existe, devolver error
        explorer.logger.warning(f"Imagen no encontrada: {decoded_path}")
        return jsonify({'error': 'Imagen no encontrada'}), 404
        
    except Exception as e:
        explorer.logger.error(f"Error sirviendo imagen: {e}")
        return jsonify({'error': str(e)}), 500




@app.route('/api/artist/<int:artist_id>/debug')
def debug_artist_images(artist_id):
    """Endpoint de debug para imágenes"""
    try:
        conn = explorer.get_db_connection()
        if not conn:
            return jsonify({'error': 'Error de conexión a BD'}), 500
        
        cursor = conn.cursor()
        
        # Obtener información del artista
        cursor.execute("""
            SELECT name, img, img_urls, img_paths FROM artists 
            WHERE id = ? AND origen = 'local'
        """, (artist_id,))
        
        artist = cursor.fetchone()
        if not artist:
            conn.close()
            return jsonify({'error': 'Artista no encontrado'}), 404
        
        # Obtener álbumes con imágenes
        cursor.execute("""
            SELECT al.name, al.album_art_path, MIN(s.album_art_path_denorm) as song_album_art,
                   MIN(s.file_path) as sample_path
            FROM albums al
            LEFT JOIN songs s ON (al.name = s.album AND s.artist = ? AND s.origen = 'local')
            WHERE al.artist_id = ? AND al.origen = 'local'
            GROUP BY al.id, al.name
        """, (artist['name'], artist_id))
        
        albums = cursor.fetchall()
        conn.close()
        
        debug_info = {
            'artist_id': artist_id,
            'artist_name': artist['name'],
            'artist_images': {
                'img': {
                    'value': artist.get('img'),
                    'exists': explorer.check_local_file_exists(artist.get('img')) if artist.get('img') else False
                },
                'img_urls': {
                    'value': artist.get('img_urls'),
                    'parsed': []
                },
                'img_paths': {
                    'value': artist.get('img_paths'),
                    'parsed': []
                }
            },
            'albums': []
        }
        
        # Procesar img_urls
        if artist.get('img_urls'):
            try:
                import json
                urls = json.loads(artist['img_urls'])
                if isinstance(urls, list):
                    for url in urls:
                        debug_info['artist_images']['img_urls']['parsed'].append({
                            'url': url,
                            'is_local': not url.startswith(('http://', 'https://')),
                            'exists': explorer.check_local_file_exists(url) if not url.startswith(('http://', 'https://')) else None
                        })
            except:
                # Intentar como CSV
                urls = [u.strip() for u in artist['img_urls'].split(',')]
                for url in urls:
                    if url:
                        debug_info['artist_images']['img_urls']['parsed'].append({
                            'url': url,
                            'is_local': not url.startswith(('http://', 'https://')),
                            'exists': explorer.check_local_file_exists(url) if not url.startswith(('http://', 'https://')) else None
                        })
        
        # Procesar img_paths
        if artist.get('img_paths'):
            try:
                import json
                paths = json.loads(artist['img_paths'])
                if isinstance(paths, list):
                    for path in paths:
                        debug_info['artist_images']['img_paths']['parsed'].append({
                            'path': path,
                            'exists': explorer.check_local_file_exists(path)
                        })
            except:
                # Intentar como CSV
                paths = [p.strip() for p in artist['img_paths'].split(',')]
                for path in paths:
                    if path:
                        debug_info['artist_images']['img_paths']['parsed'].append({
                            'path': path,
                            'exists': explorer.check_local_file_exists(path)
                        })
        
        # Procesar álbumes
        for album in albums:
            album_debug = {
                'name': album['name'],
                'album_art_path': {
                    'value': album.get('album_art_path'),
                    'exists': explorer.check_local_file_exists(album.get('album_art_path')) if album.get('album_art_path') else False
                },
                'song_album_art': {
                    'value': album.get('song_album_art'),
                    'exists': explorer.check_local_file_exists(album.get('song_album_art')) if album.get('song_album_art') else False
                },
                'sample_path': album.get('sample_path'),
                'directory_images': []
            }
            
            # Buscar imágenes en el directorio del álbum
            if album.get('sample_path'):
                album_dir = str(Path(album['sample_path']).parent)
                common_names = ['cover.jpg', 'folder.jpg', 'album.jpg', 'front.jpg', 'cover.png']
                for img_name in common_names:
                    img_path = os.path.join(album_dir, img_name)
                    if explorer.check_local_file_exists(img_path):
                        album_debug['directory_images'].append({
                            'name': img_name,
                            'path': img_path,
                            'exists': True
                        })
            
            debug_info['albums'].append(album_debug)
        
        return jsonify(debug_info)
        
    except Exception as e:
        explorer.logger.error(f"Error en debug de imágenes: {e}")
        return jsonify({'error': str(e)}), 500

# CANCIONES


@app.route('/api/album/<int:album_id>/details')
def get_album_details_with_tracks(album_id):
    """Obtener detalles completos del álbum con tracklist"""
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
        
        # Obtener imagen del álbum
        album_dict = dict(album)
        best_album_art = explorer.get_best_album_image(album_dict) if hasattr(explorer, 'get_best_album_image') else None
        album_dict['best_album_art'] = best_album_art
        
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

if __name__ == '__main__':
    # Configuración del servidor
    host = explorer.config.get('web', 'host', fallback='0.0.0.0')
    port = explorer.config.getint('web', 'port', fallback=5157)
    debug = explorer.config.getboolean('web', 'debug', fallback=False)
    
    explorer.logger.info(f"Iniciando servidor en {host}:{port}")
    app.run(host=host, port=port, debug=debug)