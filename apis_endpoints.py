#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import zipfile
import tempfile
import subprocess
from flask import jsonify, request, send_file, abort, render_template
from werkzeug.utils import secure_filename
import threading
import time


logger = logging.getLogger(__name__)

try:
    from download_manager import DownloadManager
except ImportError as e:
    logger.error(f"Error importando módulos: {e}")
    raise


class APIEndpoints:
    """Maneja todos los endpoints de la API REST"""
    
    def __init__(self, app, db_manager, img_manager, telegram_notifier, config):
        self.app = app
        self.db_manager = db_manager
        self.img_manager = img_manager
        self.telegram_notifier = telegram_notifier
        self.config = config
        self.download_manager = DownloadManager(config)
        
        # Registro de descargas activas
        self.active_downloads = {}
        self.download_cleanup_interval = 3600  # 1 hora
        self.scheduled_deletions = {}
        
        # Configurar rutas de API
        self.setup_api_routes()
        
        # Programar limpieza de descargas antiguas
        self._schedule_cleanup()
        self._schedule_auto_deletion()
    
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

    def _schedule_auto_deletion(self):
        """Programa borrados automáticos de archivos ZIP"""
        import threading
        
        def deletion_worker():
            while True:
                try:
                    current_time = time.time()
                    files_to_delete = []
                    
                    # Verificar archivos programados para borrado
                    for download_id, deletion_info in list(self.scheduled_deletions.items()):
                        if current_time >= deletion_info['delete_at']:
                            files_to_delete.append(download_id)
                    
                    # Ejecutar borrados
                    for download_id in files_to_delete:
                        self._execute_scheduled_deletion(download_id)
                    
                    time.sleep(10)  # Verificar cada 10 segundos
                    
                except Exception as e:
                    logger.error(f"Error en worker de borrado automático: {e}")
                    time.sleep(30)
        
        deletion_thread = threading.Thread(target=deletion_worker, daemon=True)
        deletion_thread.start()

    def _execute_scheduled_deletion(self, download_id):
        """Ejecuta un borrado programado"""
        try:
            if download_id not in self.scheduled_deletions:
                return
            
            deletion_info = self.scheduled_deletions[download_id]
            file_path = deletion_info['file_path']
            
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Archivo ZIP borrado automáticamente: {file_path}")
                
                # Notificar borrado
                try:
                    album_name = deletion_info.get('album_name', 'Desconocido')
                    artist_name = deletion_info.get('artist_name', 'Desconocido')
                    self.telegram_notifier.notify_file_auto_deleted(album_name, artist_name, file_path)
                except Exception as e:
                    logger.warning(f"Error notificando borrado automático: {e}")
            
            # Actualizar estado en active_downloads si existe
            if download_id in self.active_downloads:
                self.active_downloads[download_id]['zip_auto_deleted'] = True
                self.active_downloads[download_id]['auto_deleted_at'] = time.time()
            
            # Remover de programación
            del self.scheduled_deletions[download_id]
            
        except Exception as e:
            logger.error(f"Error ejecutando borrado programado para {download_id}: {e}")

    def _schedule_zip_deletion(self, download_id, delay_seconds=180):
        """Programa el borrado de un ZIP después de un delay"""
        try:
            if download_id not in self.active_downloads:
                logger.warning(f"No se puede programar borrado para descarga inexistente: {download_id}")
                return
            
            download_info = self.active_downloads[download_id]
            file_path = download_info.get('file_path')
            
            if not file_path or not os.path.exists(file_path):
                logger.warning(f"No se puede programar borrado, archivo no existe: {file_path}")
                return
            
            delete_at = time.time() + delay_seconds
            
            self.scheduled_deletions[download_id] = {
                'file_path': file_path,
                'delete_at': delete_at,
                'album_name': download_info.get('album_name'),
                'artist_name': download_info.get('artist_name'),
                'scheduled_at': time.time(),
                'delay_seconds': delay_seconds
            }
            
            # Actualizar info de descarga
            download_info['auto_delete_scheduled'] = True
            download_info['auto_delete_at'] = delete_at
            
            logger.info(f"Programado borrado automático de {file_path} en {delay_seconds} segundos")
            
        except Exception as e:
            logger.error(f"Error programando borrado de ZIP: {e}")
    
    def setup_api_routes(self):
        """Configura todas las rutas de la API"""
        

        
        @self.app.route('/sistema.html')
        def sistema():
            """Página de estadísticas completas"""
            try:
                return render_template('sistema.html', config=self.config)
            except Exception as e:
                logger.error(f"Error renderizando sistema.html: {e}")
                # Template embebido básico en caso de error
                return '''
                <!DOCTYPE html>
                <html lang="es">
                <head>
                    <meta charset="UTF-8">
                    <title>Sistema - Music Web Explorer</title>
                    <style>body { font-family: Arial, sans-serif; margin: 20px; }</style>
                </head>
                <body>
                    <h1>Sistema - Music Web Explorer</h1>
                    <p>Error cargando template sistema.html: ''' + str(e) + '''</p>
                    <p><a href="/">← Volver al inicio</a></p>
                </body>
                </html>
                ''', 500



        # === BÚSQUEDAS ===
        @self.app.route('/api/search/artists')
        def api_search_artists():
            """Buscar artistas"""
            query = request.args.get('q', '').strip()
            limit = min(int(request.args.get('limit', 50)), 100)
            
            if len(query) < 2:
                return jsonify({'error': 'Consulta muy corta', 'results': []})
            
            try:
                if not self.db_manager:
                    return jsonify({'error': 'Base de datos no disponible', 'results': []}), 500
                    
                results = self.db_manager.search_artists(query, limit)
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
                if not self.db_manager:
                    return jsonify({'error': 'Base de datos no disponible', 'results': {}}), 500
                    
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
                if not self.db_manager:
                    return jsonify({'error': 'Base de datos no disponible'}), 500
                    
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
                if not self.db_manager:
                    return jsonify({'error': 'Base de datos no disponible'}), 500
                    
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
                if not self.db_manager:
                    return jsonify({'error': 'Base de datos no disponible'}), 500
                    
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
                if not self.db_manager:
                    return jsonify({'error': 'Base de datos no disponible'}), 500
                    
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
                if not self.db_manager:
                    return jsonify({'error': 'Base de datos no disponible'}), 500
                    
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
                if not self.db_manager:
                    return jsonify({'error': 'Base de datos no disponible'}), 500
                    
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
                if not self.db_manager:
                    return jsonify({'error': 'Base de datos no disponible'}), 500
                    
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
            """Iniciar descarga de álbum - VERSIÓN DUAL (local/SSH)"""
            try:
                logger.info(f"Solicitud de descarga para álbum ID: {album_id}")
                
                # Obtener información del álbum incluyendo folder_path
                album = self.db_manager.get_album_by_id(album_id)
                if not album:
                    return jsonify({'error': 'Álbum no encontrado'}), 404
                
                logger.info(f"Álbum encontrado: {album['name']} - {album['artist_name']}")
                logger.info(f"Folder path: {album.get('folder_path', 'No especificado')}")
                logger.info(f"Modo de descarga: {self.download_manager.get_download_mode()}")
                
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
                    'user_ip': user_info['ip'],
                    'download_mode': self.download_manager.get_download_mode()
                }
                
                logger.info(f"Descarga registrada con ID: {download_id}")
                logger.info(f"Descargas activas: {list(self.active_downloads.keys())}")
                
                # Iniciar descarga en hilo separado según el modo
                if self.download_manager.is_ssh_mode():
                    thread = threading.Thread(
                        target=self._download_album_worker_ssh,
                        args=(download_id, album, user_info),
                        daemon=True
                    )
                else:
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
                    'artist_name': album.get('artist_name'),
                    'download_mode': self.download_manager.get_download_mode()
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
            """Descargar archivo ZIP y programar borrado automático"""
            logger.info(f"Solicitud de descarga para ID: {download_id}")
            
            if download_id not in self.active_downloads:
                return jsonify({
                    'error': 'Descarga no encontrada',
                    'download_id': download_id
                }), 404
            
            download_info = self.active_downloads[download_id]
            
            if download_info['status'] != 'completed':
                return jsonify({
                    'error': f'Descarga no completada. Estado: {download_info["status"]}',
                    'status': download_info['status']
                }), 400
            
            file_path = download_info.get('file_path')
            zip_filename = download_info.get('zip_filename', 'album.zip')
            
            if not file_path or not os.path.exists(file_path):
                return jsonify({'error': 'Archivo no encontrado'}), 404
            
            try:
                # Marcar como descargado
                download_info['downloaded_at'] = time.time()
                download_info['download_count'] = download_info.get('download_count', 0) + 1
                
                # NUEVO: Programar borrado automático en 180 segundos
                if not download_info.get('auto_delete_scheduled', False):
                    self._schedule_zip_deletion(download_id, delay_seconds=180)
                    logger.info(f"Programado borrado automático en 180 segundos para {download_id}")
                
                logger.info(f"Enviando archivo: {file_path} (borrado programado)")
                
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
                if not self.db_manager:
                    return jsonify({'error': 'Base de datos no disponible'}), 500
                    
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
                if not self.img_manager:
                    abort(404)
                    
                image_path = self.img_manager.get_artist_image(artist_id)
                if image_path and os.path.exists(image_path):
                    return send_file(image_path)
                else:
                    default_path = self.img_manager.get_default_artist_image()
                    return send_file(default_path)
            except Exception as e:
                logger.error(f"Error obteniendo imagen del artista {artist_id}: {e}")
                abort(404)
        
        @self.app.route('/api/images/album/<int:album_id>')
        def api_get_album_image(album_id):
            """Obtener carátula de un álbum"""
            try:
                if not self.img_manager:
                    abort(404)
                    
                image_path = self.img_manager.get_album_image(album_id)
                if image_path and os.path.exists(image_path):
                    return send_file(image_path)
                else:
                    default_path = self.img_manager.get_default_album_image()
                    return send_file(default_path)
            except Exception as e:
                logger.error(f"Error obteniendo imagen del álbum {album_id}: {e}")
                abort(404)
        

        
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




        @self.app.route('/api/download/extract/<download_id>', methods=['POST'])
        def api_extract_album(download_id):
            """Extraer álbum y borrar ZIP inmediatamente - VERSIÓN MÁS ROBUSTA"""
            logger.info(f"Solicitud de extracción para ID: {download_id}")
            
            # DEBUG: Verificar qué descargas tenemos
            logger.info(f"Descargas activas disponibles: {list(self.active_downloads.keys())}")
            
            # MEJORADA: Búsqueda más flexible
            actual_download_id = None
            
            if download_id in self.active_downloads:
                actual_download_id = download_id
                logger.info(f"Encontrado download_id exacto: {download_id}")
            else:
                # Buscar por patrones similares
                possible_matches = []
                for active_id in self.active_downloads.keys():
                    if download_id in active_id or active_id in download_id:
                        possible_matches.append(active_id)
                
                if possible_matches:
                    logger.info(f"Encontrados posibles matches: {possible_matches}")
                    actual_download_id = possible_matches[0]  # Usar el primero
                    logger.info(f"Usando download_id: {actual_download_id}")
                else:
                    # NUEVA: Búsqueda por timestamp (últimos 10 minutos) y estado completed
                    current_time = time.time()
                    recent_completed_downloads = []
                    
                    for active_id, info in self.active_downloads.items():
                        started_at = info.get('started_at', 0)
                        status = info.get('status', '')
                        
                        # Buscar descargas completadas en los últimos 10 minutos
                        if (current_time - started_at < 600 and status == 'completed'):
                            recent_completed_downloads.append({
                                'id': active_id,
                                'album_name': info.get('album_name', ''),
                                'artist_name': info.get('artist_name', ''),
                                'status': status,
                                'age_seconds': current_time - started_at,
                                'completed_at': info.get('completed_at', 0)
                            })
                    
                    # Ordenar por más reciente
                    recent_completed_downloads.sort(key=lambda x: x['completed_at'], reverse=True)
                    
                    return jsonify({
                        'error': 'Descarga no encontrada',
                        'download_id': download_id,
                        'available_downloads': list(self.active_downloads.keys()),
                        'recent_completed_downloads': recent_completed_downloads,
                        'suggestion': 'Verifica que la descarga haya terminado correctamente',
                        'help': 'Si hay descargas completadas recientes, intenta usar uno de esos IDs',
                        'debug': {
                            'requested_id': download_id,
                            'total_active': len(self.active_downloads),
                            'completed_count': len([d for d in self.active_downloads.values() if d.get('status') == 'completed'])
                        }
                    }), 404
            
            download_info = self.active_downloads[actual_download_id]
            
            # Verificar estado - MEJORADO
            if download_info['status'] != 'completed':
                return jsonify({
                    'error': f'Descarga no completada. Estado: {download_info["status"]}',
                    'status': download_info['status'],
                    'progress': download_info.get('progress', 0),
                    'download_id': actual_download_id,
                    'current_track': download_info.get('current_track'),
                    'suggestions': {
                        'processing': 'La descarga aún está en proceso, espera un momento',
                        'error': 'La descarga falló, revisa los logs',
                        'starting': 'La descarga acaba de empezar, espera un momento'
                    }.get(download_info['status'], 'Estado desconocido'),
                    'time_since_start': time.time() - download_info.get('started_at', time.time())
                }), 400
            
            try:
                file_path = download_info.get('file_path')
                if not file_path or not os.path.exists(file_path):
                    return jsonify({
                        'error': 'Archivo ZIP no encontrado',
                        'file_path': file_path,
                        'file_exists': os.path.exists(file_path) if file_path else False,
                        'download_id': actual_download_id,
                        'download_info': {
                            'status': download_info.get('status'),
                            'completed_at': download_info.get('completed_at'),
                            'file_size': download_info.get('file_size', 0)
                        }
                    }), 404
                
                # Verificar que es un ZIP válido antes de extraer
                try:
                    with zipfile.ZipFile(file_path, 'r') as test_zip:
                        test_result = test_zip.testzip()  # Verificar integridad
                        if test_result:
                            return jsonify({
                                'error': f'Archivo ZIP corrupto: {test_result}',
                                'file_path': file_path
                            }), 400
                except zipfile.BadZipFile as e:
                    return jsonify({
                        'error': f'Archivo ZIP corrupto o inválido: {str(e)}',
                        'file_path': file_path
                    }), 400
                except Exception as e:
                    return jsonify({
                        'error': f'Error verificando ZIP: {str(e)}',
                        'file_path': file_path
                    }), 400
                
                # Directorio de extracción
                downloads_dir = self.config.get('paths', {}).get('downloads', '/downloads')
                
                # Crear nombre del directorio de extracción más seguro
                artist_name = download_info.get('artist_name', 'Unknown')
                album_name = download_info.get('album_name', 'Unknown')
                
                # Limpiar nombres para sistema de archivos
                safe_artist = "".join(c for c in artist_name if c.isalnum() or c in (' ', '-', '_', '.')).strip()
                safe_album = "".join(c for c in album_name if c.isalnum() or c in (' ', '-', '_', '.')).strip()
                
                extract_dir_name = f"{safe_artist} - {safe_album}"
                extract_path = os.path.join(downloads_dir, extract_dir_name)
                
                # Si el directorio ya existe, añadir sufijo numérico
                counter = 1
                original_extract_path = extract_path
                while os.path.exists(extract_path):
                    extract_path = f"{original_extract_path} ({counter})"
                    counter += 1
                
                # Crear directorio si no existe
                try:
                    os.makedirs(extract_path, exist_ok=True)
                    logger.info(f"Directorio de extracción creado: {extract_path}")
                except Exception as e:
                    return jsonify({
                        'error': f'Error creando directorio de extracción: {str(e)}',
                        'extract_path': extract_path
                    }), 403
                
                # Extraer ZIP
                extracted_files = []
                extraction_errors = []
                
                try:
                    with zipfile.ZipFile(file_path, 'r') as zip_ref:
                        for member in zip_ref.namelist():
                            try:
                                # Evitar problemas de seguridad con rutas
                                if member.startswith('/') or '..' in member:
                                    logger.warning(f"Saltando archivo con ruta insegura: {member}")
                                    continue
                                
                                # Verificar que el nombre del archivo es válido
                                if not member or member.endswith('/'):
                                    continue  # Saltear directorios vacíos
                                
                                zip_ref.extract(member, extract_path)
                                extracted_files.append(member)
                                logger.debug(f"Extraído: {member}")
                                
                            except Exception as e:
                                error_msg = f"Error extrayendo {member}: {str(e)}"
                                logger.warning(error_msg)
                                extraction_errors.append(error_msg)
                                continue
                
                except Exception as e:
                    return jsonify({
                        'error': f'Error durante extracción: {str(e)}',
                        'extract_path': extract_path
                    }), 500
                
                if not extracted_files:
                    # Limpiar directorio vacío
                    try:
                        os.rmdir(extract_path)
                    except:
                        pass
                    return jsonify({
                        'error': 'No se pudieron extraer archivos del ZIP',
                        'extraction_errors': extraction_errors
                    }), 400
                
                logger.info(f"Extraídos {len(extracted_files)} archivos a {extract_path}")
                
                # Verificar que se extrajeron archivos realmente
                actual_files = []
                total_size = 0
                try:
                    for root, dirs, files in os.walk(extract_path):
                        for file in files:
                            file_path_check = os.path.join(root, file)
                            actual_files.append(file_path_check)
                            try:
                                total_size += os.path.getsize(file_path_check)
                            except:
                                pass
                except Exception as e:
                    logger.warning(f"Error verificando archivos extraídos: {e}")
                
                logger.info(f"Archivos verificados en disco: {len(actual_files)}")
                
                # Borrar ZIP inmediatamente
                zip_deleted = False
                zip_delete_error = None
                try:
                    os.remove(file_path)
                    logger.info(f"ZIP borrado tras extracción: {file_path}")
                    zip_deleted = True
                except Exception as e:
                    error_msg = f"Error borrando ZIP: {str(e)}"
                    logger.warning(error_msg)
                    zip_delete_error = error_msg
                    zip_deleted = False
                
                # Cancelar borrado programado si existe
                if actual_download_id in self.scheduled_deletions:
                    del self.scheduled_deletions[actual_download_id]
                    logger.info(f"Cancelado borrado automático programado para {actual_download_id}")
                
                # Actualizar estado de forma robusta
                try:
                    if actual_download_id in self.active_downloads:
                        self.active_downloads[actual_download_id].update({
                            'extracted': True,
                            'extracted_at': time.time(),
                            'extract_path': extract_path,
                            'extracted_files': len(extracted_files),
                            'actual_files_count': len(actual_files),
                            'extraction_errors': extraction_errors,
                            'zip_deleted': zip_deleted,
                            'zip_deleted_at': time.time() if zip_deleted else None,
                            'zip_delete_error': zip_delete_error,
                            'total_extracted_size': total_size
                        })
                    else:
                        logger.warning(f"Download ID {actual_download_id} no encontrado para actualizar estado de extracción")
                except Exception as e:
                    logger.error(f"Error actualizando estado de extracción: {e}")
                
                # Notificar extracción
                try:
                    self.telegram_notifier.notify_album_extracted(
                        album_name,
                        artist_name,
                        extract_path,
                        len(actual_files)
                    )
                except Exception as e:
                    logger.warning(f"Error notificando extracción: {e}")
                
                return jsonify({
                    'success': True,
                    'message': 'Álbum extraído correctamente',
                    'extract_path': extract_path,
                    'extracted_files': len(extracted_files),
                    'actual_files_count': len(actual_files),
                    'total_size': total_size,
                    'zip_deleted': zip_deleted,
                    'zip_delete_error': zip_delete_error if not zip_deleted else None,
                    'extraction_errors': extraction_errors if extraction_errors else None,
                    'download_id': actual_download_id,
                    'summary': {
                        'artist': artist_name,
                        'album': album_name,
                        'success_files': len(extracted_files),
                        'error_files': len(extraction_errors),
                        'total_size_mb': round(total_size / (1024*1024), 2) if total_size > 0 else 0
                    }
                })
                
            except zipfile.BadZipFile:
                return jsonify({
                    'error': 'Archivo ZIP corrupto',
                    'file_path': file_path
                }), 400
            except PermissionError:
                return jsonify({
                    'error': 'Sin permisos para extraer archivos',
                    'extract_path': extract_path if 'extract_path' in locals() else 'N/A'
                }), 403
            except Exception as e:
                logger.error(f"Error extrayendo álbum {actual_download_id}: {e}")
                return jsonify({
                    'error': f'Error interno: {str(e)}',
                    'download_id': actual_download_id,
                    'file_path': file_path if 'file_path' in locals() else 'N/A'
                }), 500

        @self.app.route('/api/download/cancel-auto-delete/<download_id>', methods=['POST'])
        def api_cancel_auto_delete(download_id):
            """Cancelar borrado automático programado"""
            if download_id in self.scheduled_deletions:
                deletion_info = self.scheduled_deletions[download_id]
                del self.scheduled_deletions[download_id]
                
                # Actualizar info de descarga
                if download_id in self.active_downloads:
                    self.active_downloads[download_id]['auto_delete_scheduled'] = False
                    self.active_downloads[download_id]['auto_delete_cancelled_at'] = time.time()
                
                logger.info(f"Cancelado borrado automático para {download_id}")
                
                return jsonify({
                    'success': True,
                    'message': 'Borrado automático cancelado',
                    'was_scheduled_for': deletion_info.get('delete_at'),
                    'time_remaining': deletion_info.get('delete_at', 0) - time.time()
                })
            else:
                return jsonify({
                    'error': 'No hay borrado programado para esta descarga',
                    'download_id': download_id
                }), 404

        @self.app.route('/api/download/scheduled-deletions')
        def api_list_scheduled_deletions():
            """Listar borrados programados (debug)"""
            deletions_info = {}
            current_time = time.time()
            
            for download_id, deletion_info in self.scheduled_deletions.items():
                deletions_info[download_id] = {
                    'file_path': deletion_info['file_path'],
                    'delete_at': deletion_info['delete_at'],
                    'album_name': deletion_info.get('album_name'),
                    'artist_name': deletion_info.get('artist_name'),
                    'time_remaining': deletion_info['delete_at'] - current_time,
                    'delay_seconds': deletion_info.get('delay_seconds'),
                    'file_exists': os.path.exists(deletion_info['file_path'])
                }
            
            return jsonify({
                'scheduled_deletions': deletions_info,
                'total': len(deletions_info),
                'current_time': current_time
            })
    

        @self.app.route('/api/debug/download/<download_id>')
        def api_debug_download(download_id):
            """Debug detallado de una descarga específica"""
            debug_info = {
                'download_id': download_id,
                'exists_in_active': download_id in self.active_downloads,
                'exists_in_scheduled': download_id in self.scheduled_deletions,
                'current_time': time.time()
            }
            
            if download_id in self.active_downloads:
                download_info = self.active_downloads[download_id].copy()
                
                # Añadir información de archivo
                file_path = download_info.get('file_path')
                if file_path:
                    debug_info['file_info'] = {
                        'path': file_path,
                        'exists': os.path.exists(file_path),
                        'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                        'readable': os.access(file_path, os.R_OK) if os.path.exists(file_path) else False
                    }
                
                debug_info['download_info'] = download_info
            
            if download_id in self.scheduled_deletions:
                debug_info['scheduled_deletion'] = self.scheduled_deletions[download_id].copy()
                debug_info['scheduled_deletion']['time_remaining'] = self.scheduled_deletions[download_id]['delete_at'] - time.time()
            
            return jsonify(debug_info)



        @self.app.route('/api/download/status/<download_id>')
        def api_download_status(download_id):
            """Obtener estado de descarga con información detallada - VERSION MEJORADA"""
            logger.debug(f"Consulta estado para: {download_id}")
            logger.debug(f"Descargas activas: {list(self.active_downloads.keys())}")
            
            # NUEVO: Búsqueda más flexible para manejar race conditions
            actual_download_id = None
            
            # Búsqueda exacta primero
            if download_id in self.active_downloads:
                actual_download_id = download_id
            else:
                # Búsqueda por patrón (en caso de que haya alguna diferencia menor)
                for active_id in self.active_downloads.keys():
                    if download_id in active_id or active_id in download_id:
                        actual_download_id = active_id
                        logger.info(f"Encontrado match alternativo: {download_id} -> {actual_download_id}")
                        break
            
            if not actual_download_id:
                # MEJORADO: Respuesta más informativa
                return jsonify({
                    'error': 'Descarga no encontrada',
                    'download_id': download_id,
                    'active_downloads': list(self.active_downloads.keys()),
                    'suggestion': 'La descarga puede haber terminado o expirado',
                    'debug': {
                        'requested_id': download_id,
                        'available_ids': list(self.active_downloads.keys()),
                        'total_active': len(self.active_downloads)
                    }
                }), 404
            
            # Usar el ID encontrado
            status = self.active_downloads[actual_download_id].copy()
            
            # Añadir información de borrado automático si existe
            if actual_download_id in self.scheduled_deletions:
                deletion_info = self.scheduled_deletions[actual_download_id]
                status['auto_delete_scheduled'] = True
                status['auto_delete_at'] = deletion_info['delete_at']
                status['auto_delete_time_remaining'] = max(0, deletion_info['delete_at'] - time.time())
            else:
                status['auto_delete_scheduled'] = False
            
            # NUEVO: Añadir validación de archivo para estados completados
            if status.get('status') == 'completed':
                file_path = status.get('file_path')
                if file_path:
                    status['file_exists'] = os.path.exists(file_path)
                    if os.path.exists(file_path):
                        status['file_size_current'] = os.path.getsize(file_path)
                    else:
                        logger.warning(f"Archivo completado no existe: {file_path}")
                else:
                    status['file_exists'] = False
            
            # Añadir información adicional para debug
            status['debug_info'] = {
                'requested_download_id': download_id,
                'actual_download_id': actual_download_id,
                'time_running': time.time() - status.get('started_at', time.time()),
                'keys_in_status': list(status.keys())
            }
            
            logger.debug(f"Enviando estado: {status.get('status')} - {status.get('progress')}%")
            
            return jsonify(status)

        @self.app.route('/api/test/endpoints')
        def api_test_endpoints():
            """Verificar que endpoints están registrados"""
            routes = []
            for rule in self.app.url_map.iter_rules():
                if '/api/' in rule.rule:
                    routes.append({
                        'endpoint': rule.endpoint,
                        'methods': list(rule.methods),
                        'rule': rule.rule
                    })
            return jsonify({'routes': sorted(routes, key=lambda x: x['rule'])})


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
        
        # === ESTADÍSTICAS ===

        # === ESTADÍSTICAS CORREGIDAS ===
        @self.app.route('/api/stats/overview')
        def api_stats_overview():
            """Resumen general de estadísticas"""
            try:
                from stats_manager import StatsManager
                stats_manager = StatsManager(self.db_manager.db_path, self.config)
                overview = stats_manager.get_system_overview()
                return jsonify(overview)
            except ImportError as e:
                logger.warning(f"StatsManager no disponible: {e}")
                # Fallback básico si stats_manager no está disponible
                if not self.db_manager:
                    return jsonify({'error': 'Base de datos no disponible'}), 500
                
                try:
                    db_info = self.db_manager.get_database_info()
                    overview = {
                        'database': {
                            'size_mb': 0,  # Placeholder
                            'total_tables': len(db_info.get('tables', {})),
                            'last_updated': 'N/A'
                        },
                        'content': {
                            'total_artists': db_info.get('tables', {}).get('artists', {}).get('count', 0),
                            'total_albums': db_info.get('tables', {}).get('albums', {}).get('count', 0),
                            'total_songs': db_info.get('tables', {}).get('songs', {}).get('count', 0),
                            'total_duration_hours': 0  # Placeholder
                        },
                        'completeness': 75  # Placeholder
                    }
                    return jsonify(overview)
                except Exception as fallback_error:
                    logger.error(f"Error en fallback de estadísticas: {fallback_error}")
                    return jsonify({'error': 'Error obteniendo estadísticas'}), 500
            except Exception as e:
                logger.error(f"Error obteniendo resumen de estadísticas: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/stats/database')
        def api_stats_database():
            """Información detallada de la base de datos"""
            try:
                from stats_manager import StatsManager
                stats_manager = StatsManager(self.db_manager.db_path, self.config)
                db_info = stats_manager.get_database_info()
                return jsonify(db_info)
            except Exception as e:
                logger.error(f"Error obteniendo info de base de datos: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/stats/artists')
        def api_stats_artists():
            """Estadísticas de artistas"""
            try:
                from stats_manager import StatsManager
                stats_manager = StatsManager(self.db_manager.db_path, self.config)
                artists_stats = stats_manager.get_artists_stats()
                return jsonify(artists_stats)
            except Exception as e:
                logger.error(f"Error obteniendo estadísticas de artistas: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/stats/albums')
        def api_stats_albums():
            """Estadísticas de álbumes"""
            try:
                from stats_manager import StatsManager
                stats_manager = StatsManager(self.db_manager.db_path, self.config)
                albums_stats = stats_manager.get_albums_stats()
                return jsonify(albums_stats)
            except Exception as e:
                logger.error(f"Error obteniendo estadísticas de álbumes: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/stats/songs')
        def api_stats_songs():
            """Estadísticas de canciones"""
            try:
                from stats_manager import StatsManager
                stats_manager = StatsManager(self.db_manager.db_path, self.config)
                songs_stats = stats_manager.get_songs_stats()
                return jsonify(songs_stats)
            except Exception as e:
                logger.error(f"Error obteniendo estadísticas de canciones: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/stats/missing-data')
        def api_stats_missing_data():
            """Análisis de datos faltantes"""
            try:
                from stats_manager import StatsManager
                stats_manager = StatsManager(self.db_manager.db_path, self.config)
                missing_stats = stats_manager.get_missing_data_stats()
                return jsonify(missing_stats)
            except Exception as e:
                logger.error(f"Error analizando datos faltantes: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/stats/charts/<category>/<chart_type>')
        def api_stats_charts(category, chart_type):
            """Gráficos estadísticos específicos"""
            try:
                from stats_manager import StatsManager
                stats_manager = StatsManager(self.db_manager.db_path, self.config)
                chart_data = stats_manager.get_chart_data_for_frontend(chart_type, category)
                return jsonify(chart_data)
            except Exception as e:
                logger.error(f"Error generando gráfico {category}/{chart_type}: {e}")
                return jsonify({'error': str(e)}), 500


        


        @self.app.route('/api/images/reload-json', methods=['POST'])
        def api_reload_json_metadata():
            """Recarga los metadatos JSON de imágenes"""
            try:
                if not self.img_manager:
                    return jsonify({'error': 'ImageManager no disponible'}), 500
                
                success = self.img_manager.reload_json_metadata()
                
                if success:
                    stats = self.img_manager.get_json_stats()
                    return jsonify({
                        'success': True,
                        'message': 'Metadatos JSON recargados correctamente',
                        'stats': stats
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Metadatos JSON no están habilitados en la configuración'
                    })
                    
            except Exception as e:
                logger.error(f"Error recargando metadatos JSON: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/images/json-stats')
        def api_get_json_stats():
            """Obtiene estadísticas de los metadatos JSON"""
            try:
                if not self.img_manager:
                    return jsonify({'error': 'ImageManager no disponible'}), 500
                
                stats = self.img_manager.get_json_stats()
                return jsonify(stats)
                
            except Exception as e:
                logger.error(f"Error obteniendo estadísticas JSON: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/images/cache-stats')
        def api_get_cache_stats():
            """Obtiene estadísticas del cache de imágenes - VERSIÓN MEJORADA"""
            try:
                if not self.img_manager:
                    return jsonify({'error': 'ImageManager no disponible'}), 500
                
                stats = self.img_manager.get_cache_stats()
                return jsonify(stats)
                
            except Exception as e:
                logger.error(f"Error obteniendo estadísticas del cache: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/images/clear-cache', methods=['POST'])
        def api_clear_image_cache():
            """Limpia el cache de imágenes"""
            try:
                if not self.img_manager:
                    return jsonify({'error': 'ImageManager no disponible'}), 500
                
                category = request.json.get('category') if request.is_json else None
                success = self.img_manager.clear_cache(category)
                
                if success:
                    return jsonify({
                        'success': True,
                        'message': f'Cache de imágenes limpiado{"" if not category else f" (categoría: {category})"}',
                        'stats': self.img_manager.get_cache_stats()
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': 'No se pudo limpiar el cache'
                    })
                    
            except Exception as e:
                logger.error(f"Error limpiando cache de imágenes: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/download/compress/<download_id>', methods=['POST'])
        def api_compress_and_download(download_id):
            """Comprimir álbum transferido por SSH y preparar descarga - NUEVO ENDPOINT"""
            logger.info(f"Solicitud de compresión para ID: {download_id}")
            
            if download_id not in self.active_downloads:
                return jsonify({
                    'error': 'Descarga no encontrada',
                    'download_id': download_id
                }), 404
            
            download_info = self.active_downloads[download_id]
            
            # Verificar que la transferencia SSH esté completa
            if download_info.get('status') != 'ssh_ready_download':
                return jsonify({
                    'error': f'Transferencia SSH no completada. Estado: {download_info.get("status")}',
                    'status': download_info.get('status'),
                    'download_id': download_id
                }), 400
            
            # El archivo ya está listo, solo marcar como completado para descarga
            try:
                download_info.update({
                    'status': 'completed',
                    'ready_for_download': True,
                    'compressed_at': time.time()
                })
                
                logger.info(f"Álbum SSH {download_id} listo para descarga")
                
                return jsonify({
                    'success': True,
                    'message': 'Álbum listo para descarga',
                    'download_id': download_id,
                    'file_path': download_info.get('file_path'),
                    'zip_filename': download_info.get('zip_filename'),
                    'file_size': download_info.get('file_size'),
                    'album_name': download_info.get('album_name'),
                    'artist_name': download_info.get('artist_name')
                })
                
            except Exception as e:
                logger.error(f"Error preparando descarga para {download_id}: {e}")
                return jsonify({'error': str(e)}), 500


        @self.app.route('/api/download/mode')
        def api_get_download_mode():
            """Obtener información del modo de descarga actual"""
            try:
                return jsonify({
                    'mode': self.download_manager.get_download_mode(),
                    'is_ssh_mode': self.download_manager.is_ssh_mode(),
                    'ssh_config': {
                        'enabled': self.download_manager.ssh_enabled,
                        'host': self.download_manager.ssh_host,
                        'remote_path': self.download_manager.remote_music_path
                    } if self.download_manager.is_ssh_mode() else {}
                })
            except Exception as e:
                logger.error(f"Error obteniendo modo de descarga: {e}")
                return jsonify({'error': str(e)}), 500


# Otras funciones

    def _download_album_worker(self, download_id, album, user_info):
        """Worker para descargar álbum usando folder_path - VERSION CORREGIDA CON PROGRESO"""
        try:
            # Verificar que la descarga existe al inicio
            if download_id not in self.active_downloads:
                logger.error(f"Download ID {download_id} no encontrado al iniciar worker")
                return
                
            download_info = self.active_downloads[download_id]
            download_info['status'] = 'processing'
            download_info['progress'] = 5
            download_info['current_track'] = 'Inicializando...'
            
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
            
            # Verificar que la descarga sigue existiendo
            if download_id not in self.active_downloads:
                logger.error(f"Download ID {download_id} desapareció durante inicialización")
                return
                
            self.active_downloads[download_id]['current_track'] = 'Localizando directorio del álbum...'
            self.active_downloads[download_id]['progress'] = 10
            
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
            
            # Verificar que el directorio existe
            if not album_directory or not os.path.exists(album_directory):
                raise Exception(f"Directorio del álbum no encontrado: {album_directory}")
            
            if not os.path.isdir(album_directory):
                raise Exception(f"La ruta no es un directorio: {album_directory}")
            
            # Verificar que la descarga sigue existiendo
            if download_id not in self.active_downloads:
                logger.error(f"Download ID {download_id} desapareció durante verificación de directorio")
                return
                
            self.active_downloads[download_id]['current_track'] = 'Escaneando archivos de música...'
            self.active_downloads[download_id]['progress'] = 15
            
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
            
            # Verificar que la descarga sigue existiendo
            if download_id not in self.active_downloads:
                logger.error(f"Download ID {download_id} desapareció durante escaneo de archivos")
                return
                
            self.active_downloads[download_id]['total_tracks'] = len(music_files)
            self.active_downloads[download_id]['progress'] = 20
            self.active_downloads[download_id]['current_track'] = f'Encontrados {len(music_files)} archivos'
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
            
            # Verificar que la descarga sigue existiendo
            if download_id not in self.active_downloads:
                logger.error(f"Download ID {download_id} desapareció antes de crear ZIP")
                return
                
            self.active_downloads[download_id]['current_track'] = 'Iniciando creación del ZIP...'
            self.active_downloads[download_id]['progress'] = 25
            
            successful_files = 0
            failed_files = []
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as zipf:
                for i, music_file in enumerate(music_files):
                    try:
                        # Verificar que la descarga sigue existiendo cada 5 archivos
                        if i % 5 == 0 and download_id not in self.active_downloads:
                            logger.error(f"Download ID {download_id} desapareció durante creación de ZIP en archivo {i}")
                            # Limpiar ZIP parcial
                            if os.path.exists(zip_path):
                                os.remove(zip_path)
                            return
                        
                        # Actualizar progreso (25% a 90%) - MÁS GRANULAR
                        progress = 25 + int((i / len(music_files)) * 65)
                        self.active_downloads[download_id]['progress'] = progress
                        self.active_downloads[download_id]['processed_tracks'] = i + 1
                        self.active_downloads[download_id]['current_track'] = music_file['name']
                        
                        # LOG PARA DEBUG
                        if i % 5 == 0 or i == len(music_files) - 1:  # Log cada 5 archivos
                            logger.info(f"Procesando {i+1}/{len(music_files)}: {music_file['name']} ({progress}%)")
                        
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
            
            # Verificar que la descarga sigue existiendo
            if download_id not in self.active_downloads:
                logger.error(f"Download ID {download_id} desapareció al finalizar ZIP")
                # Limpiar ZIP si se creó
                if os.path.exists(zip_path):
                    os.remove(zip_path)
                return
                
            self.active_downloads[download_id]['current_track'] = 'Finalizando ZIP...'
            self.active_downloads[download_id]['progress'] = 95
            
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
            
            # SECCIÓN MEJORADA: Actualizar estado final de forma más robusta
            try:
                # Asegurar que el download_id existe en active_downloads antes de actualizar
                if download_id in self.active_downloads:
                    self.active_downloads[download_id].update({
                        'status': 'completed',
                        'progress': 100,
                        'current_track': None,
                        'file_path': zip_path,
                        'zip_filename': zip_filename,
                        'successful_files': successful_files,
                        'failed_files': len(failed_files),
                        'failed_list': failed_files[:10],
                        'completed_at': time.time(),
                        'file_size': zip_size,
                        'album_name': album_name,
                        'artist_name': artist_name,
                        'download_id': download_id,  # AÑADIDO: Asegurar que el ID esté presente
                        'album_id': album_id  # AÑADIDO: Mantener referencia al álbum
                    })
                    logger.info(f"Estado actualizado correctamente para descarga {download_id}")
                else:
                    logger.error(f"Download ID {download_id} no encontrado en active_downloads al completar")
                    # Recrear entrada si no existe
                    self.active_downloads[download_id] = {
                        'status': 'completed',
                        'progress': 100,
                        'current_track': None,
                        'file_path': zip_path,
                        'zip_filename': zip_filename,
                        'successful_files': successful_files,
                        'failed_files': len(failed_files),
                        'failed_list': failed_files[:10],
                        'completed_at': time.time(),
                        'file_size': zip_size,
                        'album_name': album_name,
                        'artist_name': artist_name,
                        'download_id': download_id,
                        'album_id': album_id,
                        'started_at': time.time() - 60  # Estimación
                    }
                    logger.info(f"Recreada entrada para descarga {download_id}")
            except Exception as e:
                logger.error(f"Error actualizando estado final de descarga {download_id}: {e}")
            
            logger.info(f"Descarga {download_id} completada exitosamente")
            
            # Notificar finalización
            try:
                self.telegram_notifier.notify_download_completed(
                    album_name, artist_name, successful_files, zip_path, 'local'
                )
            except Exception as e:
                logger.warning(f"Error notificando finalización: {e}")
                
        except Exception as e:
            logger.error(f"Error en descarga {download_id}: {e}")
            
            # SECCIÓN MEJORADA: Actualizar estado de error de forma más robusta
            try:
                if download_id in self.active_downloads:
                    self.active_downloads[download_id].update({
                        'status': 'error',
                        'error': str(e),
                        'progress': 0,
                        'current_track': None,
                        'download_id': download_id,  # AÑADIDO: Asegurar que el ID esté presente
                        'error_at': time.time()
                    })
                else:
                    # Recrear entrada de error si no existe
                    self.active_downloads[download_id] = {
                        'status': 'error',
                        'error': str(e),
                        'progress': 0,
                        'current_track': None,
                        'download_id': download_id,
                        'album_id': album.get('id'),
                        'album_name': album.get('name', ''),
                        'artist_name': album.get('artist_name', ''),
                        'started_at': time.time(),
                        'error_at': time.time()
                    }
            except Exception as update_error:
                logger.error(f"Error actualizando estado de error para {download_id}: {update_error}")
            
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


    def _download_album_worker_ssh(self, download_id, album, user_info):
        """Worker para descargar álbum en modo SSH - CORREGIDO PARA NO VERIFICAR LOCALMENTE"""
        try:
            # Verificar que la descarga existe al inicio
            if download_id not in self.active_downloads:
                logger.error(f"Download ID {download_id} no encontrado al iniciar worker SSH")
                return
                
            download_info = self.active_downloads[download_id]
            download_info['status'] = 'ssh_preparing'
            download_info['progress'] = 5
            download_info['current_track'] = 'Preparando transferencia SSH...'
            
            album_name = album.get('name', '')
            artist_name = album.get('artist_name', '')
            album_id = album.get('id')
            
            logger.info(f"Iniciando descarga SSH: {artist_name} - {album_name} (ID: {album_id})")
            
            # Notificar inicio
            try:
                self.telegram_notifier.notify_download_started(
                    album_name, artist_name, user_info.get('ip', ''), 'ssh'
                )
            except Exception as e:
                logger.warning(f"Error notificando inicio SSH: {e}")
            
            # CORREGIDO: Obtener ruta sin verificar existencia local
            source_path = self.download_manager.get_album_source_path(album)
            if not source_path:
                raise Exception("No se pudo determinar la ruta del álbum")
            
            # NUEVO: Detectar si es un subdirectorio de disco y usar el padre
            import re
            if re.search(r'/Disc \d+$', source_path):
                parent_path = os.path.dirname(source_path)
                logger.info(f"Detectado subdirectorio de disco '{os.path.basename(source_path)}', usando directorio padre: {parent_path}")
                source_path = parent_path
            
            logger.info(f"Ruta de origen SSH: {source_path}")
            
            # Verificar que la descarga sigue existiendo
            if download_id not in self.active_downloads:
                logger.error(f"Download ID {download_id} desapareció durante preparación SSH")
                return
            
            # FASE 1: Transferencia SSH con rsync
            self.active_downloads[download_id]['status'] = 'ssh_transferring'
            self.active_downloads[download_id]['progress'] = 10
            self.active_downloads[download_id]['current_track'] = 'Verificando archivos remotos...'
            
            def progress_callback(line):
                """Callback para monitorear progreso de operaciones SSH"""
                if download_id in self.active_downloads:
                    if line and not line.startswith('total'):
                        filename = line.strip()
                        if filename:
                            self.active_downloads[download_id]['current_track'] = f'Procesando: {filename}'
            
            # Ejecutar operación SSH
            ssh_result = self.download_manager.execute_ssh_transfer(
                source_path, album, download_id, progress_callback
            )
            
            # Verificar que la descarga sigue existiendo
            if download_id not in self.active_downloads:
                logger.error(f"Download ID {download_id} desapareció durante transferencia SSH")
                return
            
            if not ssh_result['success']:
                raise Exception(f"Error en transferencia SSH: {ssh_result['error']}")
            
            remote_path = ssh_result['remote_path']
            logger.info(f"Transferencia SSH completada para {download_id}, archivos en: {remote_path}")
            
            # FASE 2: Compresión remota y descarga
            self.active_downloads[download_id]['status'] = 'ssh_compressing'
            self.active_downloads[download_id]['progress'] = 65
            self.active_downloads[download_id]['current_track'] = 'Comprimiendo álbum en servidor remoto...'
            self.active_downloads[download_id]['remote_path'] = remote_path
            
            # Comprimir y transferir
            compression_result = self.download_manager.compress_remote_album(
                remote_path, album, download_id
            )
            
            # Verificar que la descarga sigue existiendo
            if download_id not in self.active_downloads:
                logger.error(f"Download ID {download_id} desapareció durante compresión")
                return
            
            if not compression_result['success']:
                # Limpiar archivos remotos en caso de error
                try:
                    self.download_manager.cleanup_remote_files(remote_path)
                except:
                    pass
                raise Exception(f"Error en compresión remota: {compression_result['error']}")
            
            # FASE 3: Finalización
            self.active_downloads[download_id]['status'] = 'ssh_cleaning'
            self.active_downloads[download_id]['progress'] = 90
            self.active_downloads[download_id]['current_track'] = 'Limpiando archivos temporales...'
            
            # Limpiar archivos remotos
            cleanup_success = self.download_manager.cleanup_remote_files(remote_path)
            if not cleanup_success:
                logger.warning(f"No se pudieron limpiar archivos remotos para {download_id}")
            
            # Verificar que la descarga sigue existiendo
            if download_id not in self.active_downloads:
                logger.error(f"Download ID {download_id} desapareció durante limpieza")
                return
            
            # Actualizar estado final
            self.active_downloads[download_id].update({
                'status': 'ssh_ready_download',  # NUEVO ESTADO: listo para descargar
                'progress': 100,
                'current_track': None,
                'file_path': compression_result['file_path'],
                'zip_filename': compression_result['zip_filename'],
                'file_size': compression_result['file_size'],
                'completed_at': time.time(),
                'album_name': album_name,
                'artist_name': artist_name,
                'download_id': download_id,
                'album_id': album_id,
                'remote_cleanup': cleanup_success,
                'ssh_transfer_complete': True
            })
            
            logger.info(f"Descarga SSH {download_id} completada - Lista para descarga")
            
            # Notificar finalización de transferencia SSH
            try:
                self.telegram_notifier.notify_download_completed(
                    album_name, artist_name, ssh_result['files_copied'], 
                    compression_result['file_path'], 'ssh'
                )
            except Exception as e:
                logger.warning(f"Error notificando finalización SSH: {e}")
                
        except Exception as e:
            logger.error(f"Error en descarga SSH {download_id}: {e}")
            
            # Actualizar estado de error
            try:
                if download_id in self.active_downloads:
                    self.active_downloads[download_id].update({
                        'status': 'error',
                        'error': str(e),
                        'progress': 0,
                        'current_track': None,
                        'download_id': download_id,
                        'error_at': time.time(),
                        'ssh_error': True
                    })
                else:
                    # Recrear entrada de error si no existe
                    self.active_downloads[download_id] = {
                        'status': 'error',
                        'error': str(e),
                        'progress': 0,
                        'current_track': None,
                        'download_id': download_id,
                        'album_id': album.get('id'),
                        'album_name': album.get('name', ''),
                        'artist_name': album.get('artist_name', ''),
                        'started_at': time.time(),
                        'error_at': time.time(),
                        'ssh_error': True,
                        'download_mode': 'ssh'
                    }
            except Exception as update_error:
                logger.error(f"Error actualizando estado de error SSH para {download_id}: {update_error}")
            
            # Intentar limpiar archivos remotos si existen
            try:
                if 'remote_path' in locals():
                    self.download_manager.cleanup_remote_files(remote_path)
            except:
                pass
            
            # Notificar error
            try:
                self.telegram_notifier.notify_download_error(
                    album.get('name', ''), album.get('artist_name', ''), str(e)
                )
            except Exception as notify_error:
                logger.warning(f"Error notificando error SSH: {notify_error}")