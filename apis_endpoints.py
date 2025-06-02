#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import zipfile
import tempfile
import subprocess
from flask import jsonify, request, send_file, abort
from werkzeug.utils import secure_filename
import threading
import time

logger = logging.getLogger(__name__)

class APIEndpoints:
    """Maneja todos los endpoints de la API REST"""
    
    def __init__(self, app, db_manager, img_manager, telegram_notifier, config):
        self.app = app
        self.db_manager = db_manager
        self.img_manager = img_manager
        self.telegram_notifier = telegram_notifier
        self.config = config
        
        # Registro de descargas activas - MEJORADO
        self.active_downloads = {}
        self.download_cleanup_interval = 3600  # 1 hora
        
        # Configurar rutas de API
        self.setup_api_routes()
        
        # Programar limpieza de descargas antiguas
        self._schedule_cleanup()
    
    def _schedule_cleanup(self):
        """Programa la limpieza de descargas antiguas"""
        import threading
        
        def cleanup_worker():
            while True:
                try:
                    current_time = time.time()
                    expired_downloads = []
                    
                    for download_id, info in self.active_downloads.items():
                        # Limpiar descargas de más de 1 hora
                        if current_time - info.get('started_at', 0) > self.download_cleanup_interval:
                            expired_downloads.append(download_id)
                    
                    for download_id in expired_downloads:
                        self._cleanup_download(download_id)
                    
                    time.sleep(300)  # Verificar cada 5 minutos
                except Exception as e:
                    logger.error(f"Error en limpieza de descargas: {e}")
                    time.sleep(60)
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()

    def _cleanup_download(self, download_id):
        """Limpia una descarga específica"""
        try:
            if download_id in self.active_downloads:
                download_info = self.active_downloads[download_id]
                
                # Eliminar archivo si existe y la descarga está completada hace más de 1 hora
                if download_info.get('status') == 'completed':
                    file_path = download_info.get('file_path')
                    completed_at = download_info.get('completed_at', 0)
                    
                    if file_path and os.path.exists(file_path) and time.time() - completed_at > 3600:
                        os.remove(file_path)
                        logger.info(f"Archivo de descarga eliminado: {file_path}")
                
                # Eliminar del registro
                del self.active_downloads[download_id]
                logger.debug(f"Descarga {download_id} limpiada del registro")
                
        except Exception as e:
            logger.error(f"Error limpiando descarga {download_id}: {e}")


    
    def setup_api_routes(self):
        """Configura todas las rutas de la API"""
        
        # === BÚSQUEDAS ===
        @self.app.route('/api/search/artists')
        def api_search_artists():
            """Buscar artistas"""
            query = request.args.get('q', '').strip()
            limit = min(int(request.args.get('limit', 50)), 100)
            
            if len(query) < 2:
                return jsonify({'error': 'Consulta muy corta', 'results': []})
            
            try:
                results = self.db_manager.search_artists(query, limit)
                # Guardar búsqueda reciente
                self.db_manager.add_recent_search(query)
                return jsonify({'results': results, 'total': len(results)})
            except Exception as e:
                logger.error(f"Error en búsqueda de artistas: {e}")
                return jsonify({'error': str(e), 'results': []}), 500
        
        @self.app.route('/api/search/global')
        def api_search_global():
            """Búsqueda global en toda la base de datos"""
            query = request.args.get('q', '').strip()
            limit = min(int(request.args.get('limit', 25)), 50)
            
            if len(query) < 2:
                return jsonify({'error': 'Consulta muy corta', 'results': {}})
            
            try:
                results = self.db_manager.search_global(query, limit)
                self.db_manager.add_recent_search(query)
                return jsonify({'results': results})
            except Exception as e:
                logger.error(f"Error en búsqueda global: {e}")
                return jsonify({'error': str(e), 'results': {}}), 500
        
        # === ARTISTAS ===
        @self.app.route('/api/artists/<int:artist_id>')
        def api_get_artist(artist_id):
            """Obtener información de un artista"""
            try:
                artist = self.db_manager.get_artist_by_id(artist_id)
                if not artist:
                    return jsonify({'error': 'Artista no encontrado'}), 404
                
                return jsonify({'artist': artist})
            except Exception as e:
                logger.error(f"Error obteniendo artista {artist_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/artists/<int:artist_id>/albums')
        def api_get_artist_albums(artist_id):
            """Obtener álbumes de un artista"""
            try:
                artist = self.db_manager.get_artist_by_id(artist_id)
                if not artist:
                    return jsonify({'error': 'Artista no encontrado'}), 404
                
                albums = self.db_manager.get_artist_albums_by_id(artist_id)
                return jsonify({'albums': albums, 'total': len(albums)})
            except Exception as e:
                logger.error(f"Error obteniendo álbumes del artista {artist_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/artists/popular')
        def api_get_popular_artists():
            """Obtener artistas más populares"""
            limit = min(int(request.args.get('limit', 20)), 50)
            try:
                artists = self.db_manager.get_popular_artists(limit)
                return jsonify({'artists': artists, 'total': len(artists)})
            except Exception as e:
                logger.error(f"Error obteniendo artistas populares: {e}")
                return jsonify({'error': str(e)}), 500
        
        # === ÁLBUMES ===
        @self.app.route('/api/albums/<int:album_id>')
        def api_get_album(album_id):
            """Obtener información de un álbum"""
            try:
                album = self.db_manager.get_album_by_id(album_id)
                if not album:
                    return jsonify({'error': 'Álbum no encontrado'}), 404
                
                return jsonify({'album': album})
            except Exception as e:
                logger.error(f"Error obteniendo álbum {album_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/albums/<int:album_id>/tracks')
        def api_get_album_tracks(album_id):
            """Obtener canciones de un álbum"""
            try:
                tracks = self.db_manager.get_album_tracks_by_id(album_id)
                return jsonify({'tracks': tracks, 'total': len(tracks)})
            except Exception as e:
                logger.error(f"Error obteniendo canciones del álbum {album_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        # === CANCIONES ===
        @self.app.route('/api/songs/<int:song_id>')
        def api_get_song(song_id):
            """Obtener información de una canción"""
            try:
                song = self.db_manager.get_song_by_id(song_id)
                if not song:
                    return jsonify({'error': 'Canción no encontrada'}), 404
                
                return jsonify({'song': song})
            except Exception as e:
                logger.error(f"Error obteniendo canción {song_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/songs/<int:song_id>/lyrics')
        def api_get_song_lyrics(song_id):
            """Obtener letras de una canción"""
            try:
                lyrics = self.db_manager.get_song_lyrics_by_id(song_id)
                if not lyrics:
                    return jsonify({'error': 'Letras no encontradas'}), 404
                
                return jsonify({'lyrics': lyrics})
            except Exception as e:
                logger.error(f"Error obteniendo letras de la canción {song_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        # === DESCARGAS ===
        @self.app.route('/api/download/album/<int:album_id>', methods=['POST'])
        def api_download_album(album_id):
            """Iniciar descarga de álbum usando folder_path"""
            try:
                logger.info(f"Solicitud de descarga para álbum ID: {album_id}")
                
                # Obtener información del álbum incluyendo folder_path
                album = self.db_manager.get_album_by_id(album_id)
                if not album:
                    return jsonify({'error': 'Álbum no encontrado'}), 404
                
                logger.info(f"Álbum encontrado: {album['name']} - {album['artist_name']}")
                logger.info(f"Folder path: {album.get('folder_path', 'No especificado')}")
                
                # Información del usuario
                user_info = {
                    'ip': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', ''),
                    'timestamp': time.time()
                }
                
                # Crear ID único para la descarga
                download_id = f"album_{album_id}_{int(time.time())}_{hash(request.remote_addr) % 10000}"
                
                # Registrar descarga
                self.active_downloads[download_id] = {
                    'status': 'starting',
                    'album_id': album_id,
                    'album_name': album.get('name', ''),
                    'artist_name': album.get('artist_name', ''),
                    'folder_path': album.get('folder_path', ''),
                    'progress': 0,
                    'started_at': time.time(),
                    'user_ip': user_info['ip']
                }
                
                logger.info(f"Descarga registrada con ID: {download_id}")
                logger.info(f"Descargas activas: {list(self.active_downloads.keys())}")
                
                # Iniciar descarga en hilo separado
                thread = threading.Thread(
                    target=self._download_album_worker,
                    args=(download_id, album, user_info),
                    daemon=True
                )
                thread.start()
                
                return jsonify({
                    'download_id': download_id,
                    'status': 'started',
                    'message': 'Descarga iniciada',
                    'album_name': album.get('name'),
                    'artist_name': album.get('artist_name')
                })
                
            except Exception as e:
                logger.error(f"Error iniciando descarga del álbum {album_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/download/list')
        def api_list_downloads():
            """Listar todas las descargas activas (para debug)"""
            downloads_info = {}
            for download_id, info in self.active_downloads.items():
                downloads_info[download_id] = {
                    'status': info.get('status'),
                    'album_name': info.get('album_name'),
                    'artist_name': info.get('artist_name'),
                    'progress': info.get('progress', 0),
                    'started_at': info.get('started_at'),
                    'time_running': time.time() - info.get('started_at', time.time()),
                    'file_exists': os.path.exists(info.get('file_path', '')) if info.get('file_path') else False,
                    'file_size': os.path.getsize(info.get('file_path', '')) if info.get('file_path') and os.path.exists(info.get('file_path', '')) else 0
                }
            
            return jsonify({
                'active_downloads': downloads_info,
                'total': len(downloads_info),
                'debug_info': {
                    'downloads_dir': self.config.get('paths', {}).get('downloads', '/downloads'),
                    'active_keys': list(self.active_downloads.keys())
                }
            })



        
        @self.app.route('/api/download/file/<download_id>')
        def api_download_file(download_id):
            """Descargar archivo ZIP generado - VERSION ÚNICA Y CORREGIDA"""
            logger.info(f"Solicitud de descarga para ID: {download_id}")
            logger.debug(f"Descargas activas: {list(self.active_downloads.keys())}")
            
            # Verificar que la descarga existe
            if download_id not in self.active_downloads:
                logger.error(f"Download ID {download_id} no encontrado en active_downloads")
                available_downloads = list(self.active_downloads.keys())
                
                # Debug adicional
                logger.error(f"Descargas disponibles: {available_downloads}")
                for did, info in self.active_downloads.items():
                    logger.error(f"  - {did}: status={info.get('status')}, album={info.get('album_name')}")
                
                return jsonify({
                    'error': 'Descarga no encontrada',
                    'download_id': download_id,
                    'active_downloads': available_downloads,
                    'total_active': len(available_downloads)
                }), 404
            
            download_info = self.active_downloads[download_id]
            logger.info(f"Estado de descarga {download_id}: {download_info.get('status')}")
            
            # Verificar que la descarga está completada
            if download_info['status'] != 'completed':
                return jsonify({
                    'error': f'Descarga no completada. Estado: {download_info["status"]}',
                    'status': download_info['status'],
                    'progress': download_info.get('progress', 0),
                    'error_detail': download_info.get('error', ''),
                    'album_name': download_info.get('album_name', ''),
                    'artist_name': download_info.get('artist_name', '')
                }), 400
            
            # Obtener información del archivo
            file_path = download_info.get('file_path')
            zip_filename = download_info.get('zip_filename', 'album.zip')
            
            if not file_path:
                logger.error(f"No hay file_path en download_info: {download_info}")
                return jsonify({'error': 'Ruta del archivo no encontrada en la descarga'}), 404
            
            if not os.path.exists(file_path):
                logger.error(f"Archivo no existe en la ruta: {file_path}")
                return jsonify({'error': f'Archivo no existe: {file_path}'}), 404
            
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                logger.error(f"Archivo está vacío: {file_path}")
                return jsonify({'error': 'El archivo está vacío'}), 400
            
            logger.info(f"Enviando archivo: {file_path} ({file_size} bytes) como {zip_filename}")
            
            try:
                # Marcar descarga como entregada
                download_info['downloaded_at'] = time.time()
                download_info['download_count'] = download_info.get('download_count', 0) + 1
                
                return send_file(
                    file_path,
                    as_attachment=True,
                    download_name=zip_filename,
                    mimetype='application/zip'
                )
                
            except Exception as e:
                logger.error(f"Error enviando archivo: {e}")
                return jsonify({'error': f'Error enviando archivo: {str(e)}'}), 500

        
        # === HISTORIAL Y ESTADÍSTICAS ===
        @self.app.route('/api/recent/searches')
        def api_recent_searches():
            """Obtener búsquedas recientes"""
            limit = min(int(request.args.get('limit', 10)), 50)
            try:
                searches = self.db_manager.get_recent_searches(limit)
                return jsonify({'searches': searches})
            except Exception as e:
                logger.error(f"Error obteniendo búsquedas recientes: {e}")
                return jsonify({'error': str(e)}), 500
        
        # === IMÁGENES ===
        @self.app.route('/api/images/artist/<int:artist_id>')
        def api_get_artist_image(artist_id):
            """Obtener imagen de un artista"""
            try:
                image_path = self.img_manager.get_artist_image(artist_id)
                if image_path and os.path.exists(image_path):
                    return send_file(image_path)
                else:
                    # Devolver imagen por defecto
                    default_path = self.img_manager.get_default_artist_image()
                    return send_file(default_path)
            except Exception as e:
                logger.error(f"Error obteniendo imagen del artista {artist_id}: {e}")
                abort(404)
        
        @self.app.route('/api/images/album/<int:album_id>')
        def api_get_album_image(album_id):
            """Obtener carátula de un álbum"""
            try:
                image_path = self.img_manager.get_album_image(album_id)
                if image_path and os.path.exists(image_path):
                    return send_file(image_path)
                else:
                    # Devolver imagen por defecto
                    default_path = self.img_manager.get_default_album_image()
                    return send_file(default_path)
            except Exception as e:
                logger.error(f"Error obteniendo imagen del álbum {album_id}: {e}")
                abort(404)
        
        # === INFO DE SISTEMA ===
        @self.app.route('/api/system/info')
        def api_system_info():
            """Información del sistema y base de datos"""
            try:
                db_info = self.db_manager.get_database_info()
                return jsonify({
                    'database': db_info,
                    'config': {
                        'music_root': self.config.get('paths', {}).get('music_root'),
                        'downloads': self.config.get('paths', {}).get('downloads'),
                        'telegram_enabled': self.config.get('telegram', {}).get('enabled', False)
                    }
                })
            except Exception as e:
                logger.error(f"Error obteniendo info del sistema: {e}")
                return jsonify({'error': str(e)}), 500
        
        # === DIAGNÓSTICO ===
        @self.app.route('/api/debug/album/<int:album_id>')
        def api_debug_album(album_id):
            """Diagnóstico detallado usando folder_path"""
            try:
                album = self.db_manager.get_album_by_id(album_id)
                if not album:
                    return jsonify({'error': 'Álbum no encontrado'}), 404
                
                music_root = self.config.get('paths', {}).get('music_root', '/mnt/NFS/moode/moode')
                downloads_dir = self.config.get('paths', {}).get('downloads', '/downloads')
                folder_path = album.get('folder_path', '')
                
                debug_info = {
                    'album': album,
                    'music_root': music_root,
                    'music_root_exists': os.path.exists(music_root),
                    'downloads_dir': downloads_dir,
                    'downloads_dir_exists': os.path.exists(downloads_dir),
                    'downloads_dir_writable': os.access(downloads_dir, os.W_OK) if os.path.exists(downloads_dir) else False,
                    'folder_path_analysis': {}
                }
                
                # Analizar folder_path
                if folder_path:
                    # Determinar directorio del álbum
                    if folder_path.startswith('/'):
                        album_directory = folder_path
                    else:
                        album_directory = os.path.join(music_root, folder_path.lstrip('/'))
                    
                    debug_info['folder_path_analysis'] = {
                        'raw_folder_path': folder_path,
                        'computed_directory': album_directory,
                        'directory_exists': os.path.exists(album_directory),
                        'is_directory': os.path.isdir(album_directory) if os.path.exists(album_directory) else False,
                        'music_files': []
                    }
                    
                    # Buscar archivos de música
                    if os.path.exists(album_directory) and os.path.isdir(album_directory):
                        music_extensions = {'.mp3', '.flac', '.ogg', '.m4a', '.wav', '.wma', '.aac'}
                        music_files = []
                        
                        try:
                            for root, dirs, files in os.walk(album_directory):
                                for file in files:
                                    _, ext = os.path.splitext(file.lower())
                                    if ext in music_extensions:
                                        full_path = os.path.join(root, file)
                                        file_info = {
                                            'name': file,
                                            'path': full_path,
                                            'size': os.path.getsize(full_path),
                                            'relative_path': os.path.relpath(full_path, album_directory)
                                        }
                                        music_files.append(file_info)
                            
                            debug_info['folder_path_analysis']['music_files'] = music_files[:10]  # Primeros 10
                            debug_info['folder_path_analysis']['total_music_files'] = len(music_files)
                            debug_info['folder_path_analysis']['total_size'] = sum(f['size'] for f in music_files)
                            
                        except Exception as e:
                            debug_info['folder_path_analysis']['scan_error'] = str(e)
                    
                else:
                    # No hay folder_path, intentar construcción manual
                    artist_name = album.get('artist_name', '')
                    album_name = album.get('name', '')
                    
                    if artist_name and album_name:
                        possible_paths = [
                            os.path.join(music_root, artist_name, album_name),
                            os.path.join(music_root, artist_name.replace(' ', '_'), album_name),
                            os.path.join(music_root, artist_name, album_name.replace(' ', '_')),
                        ]
                        
                        debug_info['folder_path_analysis'] = {
                            'raw_folder_path': None,
                            'fallback_paths': []
                        }
                        
                        for path in possible_paths:
                            path_info = {
                                'path': path,
                                'exists': os.path.exists(path),
                                'is_directory': os.path.isdir(path) if os.path.exists(path) else False
                            }
                            
                            if path_info['is_directory']:
                                # Contar archivos de música
                                music_count = 0
                                try:
                                    music_extensions = {'.mp3', '.flac', '.ogg', '.m4a', '.wav', '.wma', '.aac'}
                                    for root, dirs, files in os.walk(path):
                                        for file in files:
                                            _, ext = os.path.splitext(file.lower())
                                            if ext in music_extensions:
                                                music_count += 1
                                    path_info['music_files_count'] = music_count
                                except:
                                    path_info['music_files_count'] = 0
                            
                            debug_info['folder_path_analysis']['fallback_paths'].append(path_info)
                
                return jsonify(debug_info)
                
            except Exception as e:
                logger.error(f"Error en diagnóstico del álbum {album_id}: {e}")
                return jsonify({'error': str(e)}), 500


        @self.app.route('/api/debug/downloads')
        def api_debug_downloads():
            """Debug de descargas activas - TEMPORAL"""
            downloads_debug = {}
            downloads_dir = self.config.get('paths', {}).get('downloads', '/downloads')
            
            # Información de directorio de descargas
            dir_info = {
                'path': downloads_dir,
                'exists': os.path.exists(downloads_dir),
                'writable': os.access(downloads_dir, os.W_OK) if os.path.exists(downloads_dir) else False,
                'files': []
            }
            
            if os.path.exists(downloads_dir):
                try:
                    files = os.listdir(downloads_dir)
                    for f in files:
                        file_path = os.path.join(downloads_dir, f)
                        if os.path.isfile(file_path):
                            dir_info['files'].append({
                                'name': f,
                                'size': os.path.getsize(file_path),
                                'modified': os.path.getmtime(file_path)
                            })
                except Exception as e:
                    dir_info['error'] = str(e)
            
            # Información de descargas activas
            for download_id, info in self.active_downloads.items():
                downloads_debug[download_id] = {
                    'status': info.get('status'),
                    'album_id': info.get('album_id'),
                    'album_name': info.get('album_name'),
                    'artist_name': info.get('artist_name'),
                    'progress': info.get('progress', 0),
                    'started_at': info.get('started_at'),
                    'file_path': info.get('file_path'),
                    'zip_filename': info.get('zip_filename'),
                    'file_exists': os.path.exists(info.get('file_path', '')) if info.get('file_path') else False,
                    'file_size': os.path.getsize(info.get('file_path', '')) if info.get('file_path') and os.path.exists(info.get('file_path', '')) else 0,
                    'error': info.get('error', ''),
                    'time_running': time.time() - info.get('started_at', time.time())
                }
            
            return jsonify({
                'downloads_directory': dir_info,
                'active_downloads': downloads_debug,
                'total_active': len(downloads_debug),
                'memory_usage': {
                    'active_downloads_keys': list(self.active_downloads.keys()),
                    'cleanup_interval': self.download_cleanup_interval
                }
            })
    
    def _download_album_worker(self, download_id, album, user_info):
        """Worker para descargar álbum usando folder_path - VERSION CORREGIDA"""
        try:
            download_info = self.active_downloads[download_id]
            download_info['status'] = 'processing'
            download_info['progress'] = 5
            
            album_name = album.get('name', '')
            artist_name = album.get('artist_name', '')
            album_id = album.get('id')
            folder_path = album.get('folder_path', '')
            
            logger.info(f"Iniciando descarga: {artist_name} - {album_name} (ID: {album_id})")
            logger.info(f"Folder path del álbum: {folder_path}")
            
            # Notificar inicio
            try:
                self.telegram_notifier.notify_download_started(
                    album_name, artist_name, user_info.get('ip', ''), 'local'
                )
            except Exception as e:
                logger.warning(f"Error notificando inicio: {e}")
            
            # Determinar directorio del álbum
            music_root = self.config.get('paths', {}).get('music_root', '/mnt/NFS/moode/moode')
            album_directory = None
            
            if folder_path:
                # Opción 1: Usar folder_path de la tabla albums
                if folder_path.startswith('/'):
                    album_directory = folder_path
                else:
                    album_directory = os.path.join(music_root, folder_path.lstrip('/'))
            else:
                # Opción 2: Construir ruta basada en artista/álbum
                safe_artist = artist_name.replace('/', '_').replace('\\', '_')
                safe_album = album_name.replace('/', '_').replace('\\', '_')
                album_directory = os.path.join(music_root, safe_artist, safe_album)
            
            logger.info(f"Directorio del álbum: {album_directory}")
            download_info['progress'] = 10
            
            # Verificar que el directorio existe
            if not album_directory or not os.path.exists(album_directory):
                raise Exception(f"Directorio del álbum no encontrado: {album_directory}")
            
            if not os.path.isdir(album_directory):
                raise Exception(f"La ruta no es un directorio: {album_directory}")
            
            download_info['progress'] = 15
            
            # Buscar archivos de música en el directorio
            music_extensions = {'.mp3', '.flac', '.ogg', '.m4a', '.wav', '.wma', '.aac'}
            music_files = []
            
            for root, dirs, files in os.walk(album_directory):
                for file in files:
                    _, ext = os.path.splitext(file.lower())
                    if ext in music_extensions:
                        full_path = os.path.join(root, file)
                        music_files.append({
                            'path': full_path,
                            'name': file,
                            'relative_path': os.path.relpath(full_path, album_directory)
                        })
            
            if not music_files:
                raise Exception(f"No se encontraron archivos de música en: {album_directory}")
            
            # Ordenar archivos por nombre para mantener orden de pistas
            music_files.sort(key=lambda x: x['name'])
            
            download_info['total_tracks'] = len(music_files)
            download_info['progress'] = 20
            logger.info(f"Encontrados {len(music_files)} archivos de música")
            
            # Crear directorio de descargas
            downloads_dir = self.config.get('paths', {}).get('downloads', '/downloads')
            os.makedirs(downloads_dir, exist_ok=True)
            
            if not os.access(downloads_dir, os.W_OK):
                raise Exception(f"Sin permisos de escritura en: {downloads_dir}")
            
            # Crear archivo ZIP
            safe_artist = "".join(c for c in artist_name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_album = "".join(c for c in album_name if c.isalnum() or c in (' ', '-', '_')).strip()
            timestamp = int(time.time())
            zip_filename = f"{safe_artist} - {safe_album} [{timestamp}].zip"
            zip_path = os.path.join(downloads_dir, zip_filename)
            
            logger.info(f"Creando ZIP: {zip_path}")
            download_info['progress'] = 25
            
            successful_files = 0
            failed_files = []
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as zipf:
                for i, music_file in enumerate(music_files):
                    try:
                        # Actualizar progreso (25% a 90%)
                        progress = 25 + int((i / len(music_files)) * 65)
                        download_info['progress'] = progress
                        download_info['processed_tracks'] = i + 1
                        download_info['current_track'] = music_file['name']
                        
                        file_path = music_file['path']
                        
                        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                            # Usar ruta relativa en el ZIP para mantener estructura
                            zip_name = music_file['relative_path']
                            zipf.write(file_path, zip_name)
                            successful_files += 1
                            logger.debug(f"Añadido: {zip_name}")
                        else:
                            failed_files.append(f"Archivo vacío o no existe: {music_file['name']}")
                            
                    except Exception as e:
                        error_msg = f"Error con {music_file['name']}: {str(e)}"
                        logger.warning(error_msg)
                        failed_files.append(error_msg)
                        continue
            
            download_info['progress'] = 95
            
            if successful_files == 0:
                if os.path.exists(zip_path):
                    os.remove(zip_path)
                raise Exception(f"No se pudieron procesar archivos de música. Errores: {failed_files[:3]}")
            
            # Verificar ZIP creado
            if not os.path.exists(zip_path) or os.path.getsize(zip_path) == 0:
                if os.path.exists(zip_path):
                    os.remove(zip_path)
                raise Exception("Error creando archivo ZIP")
            
            zip_size = os.path.getsize(zip_path)
            logger.info(f"ZIP completado: {zip_path} ({zip_size} bytes, {successful_files} archivos)")
            
            # Actualizar estado final
            download_info.update({
                'status': 'completed',
                'progress': 100,
                'file_path': zip_path,
                'zip_filename': zip_filename,
                'successful_files': successful_files,
                'failed_files': len(failed_files),
                'failed_list': failed_files[:10],
                'completed_at': time.time(),
                'file_size': zip_size
            })
            
            # Notificar finalización
            try:
                self.telegram_notifier.notify_download_completed(
                    album_name, artist_name, successful_files, zip_path, 'local'
                )
            except Exception as e:
                logger.warning(f"Error notificando finalización: {e}")
                
        except Exception as e:
            logger.error(f"Error en descarga {download_id}: {e}")
            
            # Actualizar estado de error
            if download_id in self.active_downloads:
                self.active_downloads[download_id].update({
                    'status': 'error',
                    'error': str(e),
                    'progress': 0
                })
            
            # Limpiar archivo parcial
            try:
                if 'zip_path' in locals() and os.path.exists(zip_path):
                    os.remove(zip_path)
                    logger.info(f"ZIP parcial eliminado: {zip_path}")
            except:
                pass
            
            # Notificar error
            try:
                self.telegram_notifier.notify_download_error(
                    album.get('name', ''), album.get('artist_name', ''), str(e)
                )
            except Exception as notify_error:
                logger.warning(f"Error notificando error: {notify_error}")

        # === ENDPOINT DE DESCARGA CORREGIDO ===


        @self.app.route('/api/download/status/<download_id>')
        def api_download_status(download_id):
            """Obtener estado de descarga con información detallada"""
            logger.debug(f"Consulta estado para: {download_id}")
            logger.debug(f"Descargas activas: {list(self.active_downloads.keys())}")
            
            if download_id not in self.active_downloads:
                return jsonify({
                    'error': 'Descarga no encontrada',
                    'download_id': download_id,
                    'active_downloads': list(self.active_downloads.keys())
                }), 404
            
            status = self.active_downloads[download_id].copy()
            
            # Añadir información adicional para debug
            status['debug_info'] = {
                'download_id': download_id,
                'time_running': time.time() - status.get('started_at', time.time())
            }
            
            return jsonify(status)


    def _find_track_file_improved(self, track, music_root):
            """Busca el archivo de una canción en el sistema de archivos - VERSION MEJORADA"""
            
            # Obtener la ruta principal del campo file_path
            file_path = track.get('file_path', '').strip()
            
            if not file_path:
                logger.debug(f"No hay file_path para: {track.get('title', 'Sin título')}")
                return None
            
            # Limpiar la ruta
            if file_path.startswith('file://'):
                file_path = file_path[7:]
            
            # Probar diferentes formas de construir la ruta
            search_paths = []
            
            # Ruta 1: Si es absoluta, usar directamente
            if file_path.startswith('/'):
                search_paths.append(file_path)
            
            # Ruta 2: Relativa desde music_root
            search_paths.append(os.path.join(music_root, file_path.lstrip('/')))
            
            # Ruta 3: Si la ruta contiene el music_root duplicado, limpiar
            if music_root in file_path and not file_path.startswith(music_root):
                clean_path = file_path.replace(music_root, '').lstrip('/')
                search_paths.append(os.path.join(music_root, clean_path))
            
            # Verificar cada ruta
            for search_path in search_paths:
                if os.path.exists(search_path) and os.path.isfile(search_path):
                    logger.debug(f"Archivo encontrado: {search_path}")
                    return search_path
                else:
                    logger.debug(f"Archivo no existe: {search_path}")
            
            # Si no se encuentra, intentar búsqueda por patrón como último recurso
            return self._search_track_by_pattern_improved(track, music_root)


    def _search_track_by_pattern_improved(self, track, music_root):
        """Búsqueda por patrón mejorada"""
        try:
            artist = track.get('artist', '').strip()
            album = track.get('album', '').strip()
            title = track.get('title', '').strip()
            
            if not all([artist, album, title]):
                return None
            
            # Buscar en directorio del artista/álbum
            possible_dirs = [
                os.path.join(music_root, artist, album),
                os.path.join(music_root, artist.replace(' ', '_'), album),
                os.path.join(music_root, artist, album.replace(' ', '_')),
            ]
            
            for base_dir in possible_dirs:
                if os.path.exists(base_dir) and os.path.isdir(base_dir):
                    # Buscar archivos que contengan el título
                    for filename in os.listdir(base_dir):
                        if any(ext in filename.lower() for ext in ['.mp3', '.flac', '.ogg', '.m4a', '.wav']):
                            if title.lower() in filename.lower():
                                full_path = os.path.join(base_dir, filename)
                                logger.debug(f"Encontrado por patrón: {full_path}")
                                return full_path
            
            return None
            
        except Exception as e:
            logger.debug(f"Error en búsqueda por patrón: {e}")
            return None



    def _find_track_file(self, track, music_root):
        """Busca el archivo de una canción en el sistema de archivos"""
        
        # Lista de posibles campos que contienen rutas
        path_fields = ['file_path', 'path', 'location', 'file', 'filename', 'url']
        
        for field in path_fields:
            if field in track and track[field]:
                file_path = track[field]
                
                # Normalizar la ruta
                if file_path.startswith('file://'):
                    file_path = file_path[7:]  # Quitar 'file://'
                
                # Si es ruta absoluta, usar directamente
                if file_path.startswith('/'):
                    full_path = file_path
                else:
                    # Si es ruta relativa, combinar con music_root
                    full_path = os.path.join(music_root, file_path.lstrip('/'))
                
                # Verificar si el archivo existe
                if os.path.exists(full_path):
                    logger.debug(f"Archivo encontrado en {field}: {full_path}")
                    return full_path
                else:
                    logger.debug(f"Archivo no existe en {field}: {full_path}")
        
        # Si no se encuentra por rutas directas, intentar búsqueda por patrones
        return self._search_track_by_pattern(track, music_root)
    
    def _search_track_by_pattern(self, track, music_root):
        """Busca un archivo de canción por patrones en el nombre"""
        
        try:
            artist = track.get('artist', '').strip()
            album = track.get('album', '').strip()
            title = track.get('title', '').strip()
            track_number = track.get('track_number')
            
            if not all([artist, album, title]):
                logger.debug("Información insuficiente para búsqueda por patrón")
                return None
            
            # Limpiar nombres para búsqueda
            clean_artist = "".join(c for c in artist if c.isalnum() or c in (' ', '-', '_')).strip()
            clean_album = "".join(c for c in album if c.isalnum() or c in (' ', '-', '_')).strip()
            clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
            
            # Patrones de búsqueda comunes
            search_patterns = [
                os.path.join(music_root, clean_artist, clean_album),
                os.path.join(music_root, artist, album),
                os.path.join(music_root, "**", clean_album),  # Búsqueda recursiva
            ]
            
            extensions = ['.mp3', '.flac', '.ogg', '.m4a', '.wav']
            
            for pattern_dir in search_patterns:
                if os.path.exists(pattern_dir):
                    # Buscar archivos en el directorio
                    for file in os.listdir(pattern_dir):
                        file_path = os.path.join(pattern_dir, file)
                        if os.path.isfile(file_path):
                            # Verificar extensión
                            _, ext = os.path.splitext(file.lower())
                            if ext in extensions:
                                # Verificar si el nombre coincide
                                if clean_title.lower() in file.lower():
                                    logger.debug(f"Archivo encontrado por patrón: {file_path}")
                                    return file_path
                                
                                # Verificar por número de pista
                                if track_number and str(track_number).zfill(2) in file:
                                    logger.debug(f"Archivo encontrado por número de pista: {file_path}")
                                    return file_path
            
            logger.debug(f"No se encontró archivo para: {artist} - {title}")
            return None
            
        except Exception as e:
            logger.warning(f"Error en búsqueda por patrón: {e}")
            return None