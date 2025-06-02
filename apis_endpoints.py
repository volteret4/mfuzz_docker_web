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
            """Descargar un álbum completo"""
            try:
                album = self.db_manager.get_album_by_id(album_id)
                if not album:
                    return jsonify({'error': 'Álbum no encontrado'}), 404
                
                # Obtener información del usuario (IP, user-agent, etc.)
                user_info = {
                    'ip': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', ''),
                    'timestamp': time.time()
                }
                
                # Iniciar descarga en hilo separado
                download_id = f"album_{album_id}_{int(time.time())}"
                self.active_downloads[download_id] = {
                    'status': 'starting',
                    'album_id': album_id,
                    'album_name': album.get('name', ''),
                    'artist_name': album.get('artist_name', ''),
                    'progress': 0,
                    'started_at': time.time()
                }
                
                thread = threading.Thread(
                    target=self._download_album_worker,
                    args=(download_id, album, user_info)
                )
                thread.daemon = True
                thread.start()
                
                return jsonify({
                    'download_id': download_id,
                    'status': 'started',
                    'message': 'Descarga iniciada'
                })
                
            except Exception as e:
                logger.error(f"Error iniciando descarga del álbum {album_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/download/status/<download_id>')
        def api_download_status(download_id):
            """Obtener estado de una descarga"""
            if download_id not in self.active_downloads:
                return jsonify({'error': 'Descarga no encontrada'}), 404
            
            return jsonify(self.active_downloads[download_id])
        
        @self.app.route('/api/download/file/<download_id>')
        def api_download_file(download_id):
            """Descargar archivo generado - VERSION CORREGIDA"""
            if download_id not in self.active_downloads:
                return jsonify({'error': 'Descarga no encontrada'}), 404
            
            download_info = self.active_downloads[download_id]
            if download_info['status'] != 'completed':
                return jsonify({
                    'error': f'Descarga no completada. Estado actual: {download_info["status"]}',
                    'status': download_info['status']
                }), 400
            
            try:
                file_path = download_info.get('file_path')
                zip_filename = download_info.get('zip_filename', 'album.zip')
                
                if not file_path:
                    return jsonify({'error': 'Ruta del archivo no encontrada'}), 404
                
                if not os.path.exists(file_path):
                    return jsonify({'error': f'Archivo no encontrado en: {file_path}'}), 404
                
                # Verificar que el archivo tiene contenido
                file_size = os.path.getsize(file_path)
                if file_size == 0:
                    return jsonify({'error': 'El archivo está vacío'}), 400
                
                logger.info(f"Enviando archivo: {file_path} ({file_size} bytes)")
                
                return send_file(
                    file_path,
                    as_attachment=True,
                    download_name=zip_filename,
                    mimetype='application/zip'
                )
                
            except Exception as e:
                logger.error(f"Error enviando archivo de descarga {download_id}: {e}")
                return jsonify({'error': f'Error interno: {str(e)}'}), 500
        
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
            """Diagnóstico detallado de un álbum - VERSION MEJORADA"""
            try:
                # Información básica del álbum
                album = self.db_manager.get_album_by_id(album_id)
                if not album:
                    return jsonify({'error': 'Álbum no encontrado'}), 404
                
                # Obtener canciones con información de rutas
                tracks = self.db_manager.get_album_tracks_with_paths(album_id)
                
                # Verificar sistema de archivos
                music_root = self.config.get('paths', {}).get('music_root', '/mnt/NFS/moode/moode')
                downloads_dir = self.config.get('paths', {}).get('downloads', '/downloads')
                
                debug_info = {
                    'album': album,
                    'tracks_count': len(tracks),
                    'music_root': music_root,
                    'music_root_exists': os.path.exists(music_root),
                    'downloads_dir': downloads_dir,
                    'downloads_dir_exists': os.path.exists(downloads_dir),
                    'downloads_dir_writable': os.access(downloads_dir, os.W_OK) if os.path.exists(downloads_dir) else False,
                    'tracks_analysis': []
                }
                
                # Contar tipos de errores
                path_stats = {
                    'with_paths': 0,
                    'without_paths': 0,
                    'files_exist': 0,
                    'files_missing': 0,
                    'path_types': {}
                }
                
                for i, track in enumerate(tracks):
                    track_info = {
                        'id': track.get('id'),
                        'title': track.get('title'),
                        'artist': track.get('artist'),
                        'track_number': track.get('track_number'),
                        'available_paths': track.get('available_paths', {}),
                        'best_path': track.get('best_path'),
                        'file_exists': False,
                        'full_path': None,
                        'search_attempts': []
                    }
                    
                    # Estadísticas de rutas
                    if track.get('available_paths'):
                        path_stats['with_paths'] += 1
                        for path_type in track['available_paths'].keys():
                            path_stats['path_types'][path_type] = path_stats['path_types'].get(path_type, 0) + 1
                    else:
                        path_stats['without_paths'] += 1
                    
                    # Verificar archivos
                    if track.get('best_path'):
                        # Intentar diferentes formas de construir la ruta
                        search_paths = []
                        
                        best_path = track['best_path']
                        
                        # Ruta absoluta
                        if best_path.startswith('/'):
                            search_paths.append(best_path)
                        
                        # Ruta relativa desde music_root
                        search_paths.append(os.path.join(music_root, best_path.lstrip('/')))
                        
                        # Quitar file:// si existe
                        if best_path.startswith('file://'):
                            clean_path = best_path[7:]
                            search_paths.append(clean_path)
                            if not clean_path.startswith('/'):
                                search_paths.append(os.path.join(music_root, clean_path))
                        
                        # Verificar cada ruta
                        for search_path in search_paths:
                            exists = os.path.exists(search_path)
                            track_info['search_attempts'].append({
                                'path': search_path,
                                'exists': exists
                            })
                            
                            if exists:
                                track_info['file_exists'] = True
                                track_info['full_path'] = search_path
                                path_stats['files_exist'] += 1
                                break
                        
                        if not track_info['file_exists']:
                            path_stats['files_missing'] += 1
                    
                    # Solo incluir las primeras 10 canciones en el análisis detallado
                    if i < 10:
                        debug_info['tracks_analysis'].append(track_info)
                
                debug_info['path_statistics'] = path_stats
                
                # Verificar algunos directorios comunes
                common_dirs = [
                    music_root,
                    os.path.join(music_root, album.get('artist_name', '')),
                    os.path.join(music_root, album.get('artist_name', ''), album.get('name', ''))
                ]
                
                debug_info['directory_check'] = []
                for dir_path in common_dirs:
                    if dir_path.strip():
                        debug_info['directory_check'].append({
                            'path': dir_path,
                            'exists': os.path.exists(dir_path),
                            'is_dir': os.path.isdir(dir_path) if os.path.exists(dir_path) else False,
                            'files_count': len(os.listdir(dir_path)) if os.path.exists(dir_path) and os.path.isdir(dir_path) else 0
                        })
                
                return jsonify(debug_info)
                
            except Exception as e:
                logger.error(f"Error en diagnóstico del álbum {album_id}: {e}")
                return jsonify({'error': str(e)}), 500
    
    def _download_album_worker(self, download_id, album, user_info):
        """Worker para descargar álbum en hilo separado - VERSION FINAL CORREGIDA"""
        try:
            download_info = self.active_downloads[download_id]
            download_info['status'] = 'processing'
            
            album_name = album.get('name', '')
            artist_name = album.get('artist_name', '')
            album_id = album.get('id')
            
            logger.info(f"Iniciando descarga: {artist_name} - {album_name} (ID: {album_id})")
            
            # Notificar inicio de descarga
            try:
                self.telegram_notifier.notify_download_started(
                    album_name, artist_name, 
                    user_info.get('ip', ''), 
                    'local'
                )
            except Exception as e:
                logger.warning(f"Error notificando inicio: {e}")
            
            # Obtener canciones del álbum con información de rutas
            tracks = self.db_manager.get_album_tracks_with_paths(album_id)
            if not tracks:
                raise Exception("No se encontraron canciones en el álbum")
            
            download_info['total_tracks'] = len(tracks)
            download_info['processed_tracks'] = 0
            logger.info(f"Encontradas {len(tracks)} canciones para descargar")
            
            # Crear directorio de descargas si no existe
            downloads_dir = self.config.get('paths', {}).get('downloads', '/downloads')
            os.makedirs(downloads_dir, exist_ok=True)
            
            # Verificar permisos de escritura
            if not os.access(downloads_dir, os.W_OK):
                raise Exception(f"Sin permisos de escritura en directorio de descargas: {downloads_dir}")
            
            # Crear nombre seguro para el archivo ZIP
            safe_artist = "".join(c for c in artist_name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_album = "".join(c for c in album_name if c.isalnum() or c in (' ', '-', '_')).strip()
            timestamp = int(time.time())
            zip_filename = f"{safe_artist} - {safe_album} [{timestamp}].zip"
            zip_path = os.path.join(downloads_dir, zip_filename)
            
            music_root = self.config.get('paths', {}).get('music_root', '/mnt/NFS/moode/moode')
            successful_files = 0
            failed_files = []
            
            logger.info(f"Directorio raíz de música: {music_root}")
            logger.info(f"Creando ZIP en: {zip_path}")
            
            # Verificar que el directorio de música existe
            if not os.path.exists(music_root):
                raise Exception(f"Directorio de música no encontrado: {music_root}")
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as zipf:
                for i, track in enumerate(tracks):
                    try:
                        # Actualizar progreso ANTES de procesar
                        download_info['processed_tracks'] = i
                        progress = int((i / len(tracks)) * 90)  # Máximo 90% durante procesamiento
                        download_info['progress'] = progress
                        
                        track_title = track.get('title', f'Track {i+1}')
                        track_number = track.get('track_number', i+1)
                        download_info['current_track'] = track_title
                        
                        logger.debug(f"Procesando canción {i+1}/{len(tracks)}: {track_title}")
                        
                        # Buscar archivo de música
                        file_path = self._find_track_file_improved(track, music_root)
                        
                        if file_path and os.path.exists(file_path):
                            # Crear nombre limpio para el archivo en el ZIP
                            safe_title = "".join(c for c in track_title if c.isalnum() or c in (' ', '-', '_', '.')).strip()
                            _, ext = os.path.splitext(file_path)
                            
                            # Nombre del archivo en el ZIP
                            if track_number and str(track_number).isdigit():
                                zip_filename_track = f"{int(track_number):02d} - {safe_title}{ext}"
                            else:
                                zip_filename_track = f"{safe_title}{ext}"
                            
                            # Verificar que el archivo no está vacío
                            file_size = os.path.getsize(file_path)
                            if file_size > 0:
                                # Añadir archivo al ZIP
                                zipf.write(file_path, zip_filename_track)
                                successful_files += 1
                                logger.debug(f"Añadido al ZIP: {zip_filename_track} ({file_size} bytes)")
                            else:
                                failed_files.append(f"{track_title} - Archivo vacío")
                            
                        else:
                            error_msg = f"Archivo no encontrado para: {track_title}"
                            if file_path:
                                error_msg += f" (ruta: {file_path})"
                            logger.warning(error_msg)
                            failed_files.append(error_msg)
                        
                    except Exception as e:
                        error_msg = f"Error procesando {track_title}: {str(e)}"
                        logger.warning(error_msg)
                        failed_files.append(error_msg)
                        continue
                
                # Actualizar progreso final del procesamiento
                download_info['processed_tracks'] = len(tracks)
                download_info['progress'] = 95
            
            if successful_files == 0:
                # Limpiar archivo ZIP vacío
                if os.path.exists(zip_path):
                    os.remove(zip_path)
                error_msg = f"No se encontraron archivos de música. Errores: {failed_files[:3]}"
                raise Exception(error_msg)
            
            # Verificar que el ZIP se creó correctamente y tiene contenido
            if not os.path.exists(zip_path):
                raise Exception("Error: El archivo ZIP no se creó")
                
            zip_size = os.path.getsize(zip_path)
            if zip_size == 0:
                os.remove(zip_path)
                raise Exception("Error: El archivo ZIP está vacío")
            
            logger.info(f"ZIP creado exitosamente: {zip_path} ({zip_size} bytes, {successful_files} archivos)")
            
            # Actualizar estado final
            download_info['status'] = 'completed'
            download_info['progress'] = 100
            download_info['file_path'] = zip_path
            download_info['zip_filename'] = zip_filename
            download_info['successful_files'] = successful_files
            download_info['failed_files'] = len(failed_files)
            download_info['failed_list'] = failed_files[:10]
            download_info['completed_at'] = time.time()
            download_info['file_size'] = zip_size
            
            # Notificar finalización
            try:
                self.telegram_notifier.notify_download_completed(
                    album_name, artist_name, 
                    successful_files, zip_path, 
                    'local'
                )
            except Exception as e:
                logger.warning(f"Error notificando finalización: {e}")
            
        except Exception as e:
            logger.error(f"Error en descarga {download_id}: {e}")
            download_info['status'] = 'error'
            download_info['error'] = str(e)
            download_info['progress'] = 0
            
            # Limpiar archivo parcial si existe
            try:
                if 'zip_path' in locals() and os.path.exists(zip_path):
                    os.remove(zip_path)
                    logger.info(f"Archivo ZIP parcial eliminado: {zip_path}")
            except:
                pass
            
            # Notificar error
            try:
                self.telegram_notifier.notify_download_error(
                    album.get('name', ''), 
                    album.get('artist_name', ''), 
                    str(e)
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