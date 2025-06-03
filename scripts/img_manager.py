#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import sqlite3
from typing import Optional, Dict, List
from PIL import Image, ImageOps
import hashlib
import json
import requests
from urllib.parse import urlparse

logger = logging.getLogger(__name__)



class ImageManager:
    """Gestor de imágenes para artistas y álbumes - VERSIÓN MEJORADA CON SOPORTE JSON"""
    
    def __init__(self, config):
        self.config = config
        self.db_path = config.get('database', {}).get('path', '/app/data/musica.sqlite')
        self.images_dir = config.get('paths', {}).get('images', '/app/images')
        self.cache_enabled = config.get('images', {}).get('cache_enabled', True)
        self.max_size = config.get('images', {}).get('max_size', 1024)
        self.supported_formats = config.get('images', {}).get('supported_formats', ['jpg', 'jpeg', 'png', 'webp'])
        
        # NUEVO: Configuración para usar archivos JSON locales
        self.use_json_metadata = config.get('images', {}).get('use_json_metadata', False)
        self.json_artists_file = os.path.join(self.images_dir, 'artists', 'artists.json')
        self.json_albums_file = os.path.join(self.images_dir, 'albums', 'albums.json')
        
        # Cache para evitar leer JSON repetidamente
        self._artists_json_cache = None
        self._albums_json_cache = None
        self._json_cache_loaded = False
        
        # Crear directorios necesarios
        self.setup_directories()
        
        # Cargar metadatos JSON si está habilitado
        if self.use_json_metadata:
            self._load_json_metadata()
        
        logger.info(f"ImageManager inicializado - Cache: {self.cache_enabled}, JSON metadata: {self.use_json_metadata}, Dir: {self.images_dir}")
    
    def _load_json_metadata(self):
        """Carga los metadatos JSON de artistas y álbumes"""
        try:
            # Cargar artistas
            if os.path.exists(self.json_artists_file):
                with open(self.json_artists_file, 'r', encoding='utf-8') as f:
                    self._artists_json_cache = json.load(f)
                logger.info(f"Cargado JSON de artistas: {len(self._artists_json_cache)} entradas")
            else:
                logger.warning(f"Archivo JSON de artistas no encontrado: {self.json_artists_file}")
                self._artists_json_cache = {}
            
            # Cargar álbumes
            if os.path.exists(self.json_albums_file):
                with open(self.json_albums_file, 'r', encoding='utf-8') as f:
                    self._albums_json_cache = json.load(f)
                logger.info(f"Cargado JSON de álbumes: {len(self._albums_json_cache)} entradas")
            else:
                logger.warning(f"Archivo JSON de álbumes no encontrado: {self.json_albums_file}")
                self._albums_json_cache = {}
            
            self._json_cache_loaded = True
            
        except Exception as e:
            logger.error(f"Error cargando metadatos JSON: {e}")
            self._artists_json_cache = {}
            self._albums_json_cache = {}
            self._json_cache_loaded = False
    
    def setup_directories(self):
        """Crea la estructura de directorios para imágenes"""
        try:
            dirs_to_create = [
                self.images_dir,
                os.path.join(self.images_dir, 'artists'),
                os.path.join(self.images_dir, 'albums'),
                os.path.join(self.images_dir, 'cache'),
                os.path.join(self.images_dir, 'defaults')
            ]
            
            for directory in dirs_to_create:
                os.makedirs(directory, exist_ok=True)
                
            # Crear imágenes por defecto si no existen
            self.create_default_images()
            
        except Exception as e:
            logger.error(f"Error creando directorios de imágenes: {e}")
    
    def create_default_images(self):
        """Crea imágenes por defecto si no existen"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            defaults_dir = os.path.join(self.images_dir, 'defaults')
            
            # Imagen por defecto para artistas
            artist_default = os.path.join(defaults_dir, 'artist_default.jpg')
            if not os.path.exists(artist_default):
                img = Image.new('RGB', (300, 300), color='#4A5568')
                draw = ImageDraw.Draw(img)
                
                # Dibujar un círculo simple
                draw.ellipse([50, 50, 250, 250], fill='#718096', outline='#2D3748', width=3)
                
                # Añadir texto si es posible
                try:
                    draw.text((150, 150), "🎤", anchor="mm", fill='white')
                except:
                    draw.text((140, 140), "Artist", fill='white')
                
                img.save(artist_default, 'JPEG', quality=85)
            
            # Imagen por defecto para álbumes
            album_default = os.path.join(defaults_dir, 'album_default.jpg')
            if not os.path.exists(album_default):
                img = Image.new('RGB', (300, 300), color='#2D3748')
                draw = ImageDraw.Draw(img)
                
                # Dibujar un cuadrado con borde
                draw.rectangle([25, 25, 275, 275], fill='#4A5568', outline='#718096', width=3)
                
                # Añadir texto
                try:
                    draw.text((150, 150), "🎵", anchor="mm", fill='white')
                except:
                    draw.text((140, 140), "Album", fill='white')
                
                img.save(album_default, 'JPEG', quality=85)
                
            logger.info("Imágenes por defecto creadas")
            
        except Exception as e:
            logger.warning(f"Error creando imágenes por defecto: {e}")
    
    def get_db_connection(self):
        """Obtiene conexión a la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.error(f"Error conectando a la base de datos: {e}")
            raise
    
    def get_artist_image(self, artist_id: int) -> Optional[str]:
        """Obtiene la imagen de un artista - VERSIÓN MEJORADA"""
        try:
            # NUEVO: Intentar desde JSON local primero si está habilitado
            if self.use_json_metadata and self._json_cache_loaded:
                json_image = self._get_artist_image_from_json(artist_id)
                if json_image:
                    return json_image
            
            # Verificar cache local
            cache_path = os.path.join(self.images_dir, 'artists', f'{artist_id}.jpg')
            if os.path.exists(cache_path):
                return cache_path
            
            # Buscar información de imagen en la base de datos (método original)
            with self.get_db_connection() as conn:
                cursor = conn.execute("""
                    SELECT img, img_urls, img_paths 
                    FROM artists 
                    WHERE id = ?
                """, (artist_id,))
                result = cursor.fetchone()
                
                if not result:
                    return self.get_default_artist_image()
                
                # Intentar obtener imagen de diferentes fuentes
                image_path = self._process_artist_image_data(artist_id, result)
                return image_path or self.get_default_artist_image()
                
        except Exception as e:
            logger.error(f"Error obteniendo imagen del artista {artist_id}: {e}")
            return self.get_default_artist_image()
    
    def get_album_image(self, album_id: int) -> Optional[str]:
        """Obtiene la carátula de un álbum - VERSIÓN MEJORADA"""
        try:
            # NUEVO: Intentar desde JSON local primero si está habilitado
            if self.use_json_metadata and self._json_cache_loaded:
                json_image = self._get_album_image_from_json(album_id)
                if json_image:
                    return json_image
            
            # Verificar cache local
            cache_path = os.path.join(self.images_dir, 'albums', f'{album_id}.jpg')
            if os.path.exists(cache_path):
                return cache_path
            
            # Buscar información de imagen en la base de datos (método original)
            with self.get_db_connection() as conn:
                cursor = conn.execute("""
                    SELECT album_art_path, album_art_urls 
                    FROM albums 
                    WHERE id = ?
                """, (album_id,))
                result = cursor.fetchone()
                
                if not result:
                    return self.get_default_album_image()
                
                # Intentar obtener imagen de diferentes fuentes
                image_path = self._process_album_image_data(album_id, result)
                return image_path or self.get_default_album_image()
                
        except Exception as e:
            logger.error(f"Error obteniendo imagen del álbum {album_id}: {e}")
            return self.get_default_album_image()
    
    def _get_artist_image_from_json(self, artist_id: int) -> Optional[str]:
        """Obtiene imagen de artista desde JSON local"""
        try:
            artist_id_str = str(artist_id)
            
            if artist_id_str in self._artists_json_cache:
                metadata = self._artists_json_cache[artist_id_str]
                filename = metadata.get('filename')
                
                if filename:
                    image_path = os.path.join(self.images_dir, 'artists', filename)
                    
                    if os.path.exists(image_path):
                        logger.debug(f"Imagen de artista encontrada en JSON: {image_path}")
                        return image_path
                    else:
                        logger.warning(f"Archivo de imagen de artista no existe: {image_path}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo imagen de artista desde JSON {artist_id}: {e}")
            return None
    
    def _get_album_image_from_json(self, album_id: int) -> Optional[str]:
        """Obtiene imagen de álbum desde JSON local"""
        try:
            album_id_str = str(album_id)
            
            if album_id_str in self._albums_json_cache:
                metadata = self._albums_json_cache[album_id_str]
                filename = metadata.get('filename')
                
                if filename:
                    image_path = os.path.join(self.images_dir, 'albums', filename)
                    
                    if os.path.exists(image_path):
                        logger.debug(f"Imagen de álbum encontrada en JSON: {image_path}")
                        return image_path
                    else:
                        logger.warning(f"Archivo de imagen de álbum no existe: {image_path}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo imagen de álbum desde JSON {album_id}: {e}")
            return None
    
    def reload_json_metadata(self):
        """Recarga los metadatos JSON (útil para recargar sin reiniciar)"""
        if self.use_json_metadata:
            logger.info("Recargando metadatos JSON...")
            self._load_json_metadata()
            return True
        return False
    
    def get_json_stats(self) -> Dict:
        """Obtiene estadísticas de los metadatos JSON"""
        if not self.use_json_metadata or not self._json_cache_loaded:
            return {
                'enabled': self.use_json_metadata,
                'loaded': self._json_cache_loaded,
                'artists': 0,
                'albums': 0
            }
        
        return {
            'enabled': self.use_json_metadata,
            'loaded': self._json_cache_loaded,
            'artists': len(self._artists_json_cache),
            'albums': len(self._albums_json_cache),
            'artists_file': self.json_artists_file,
            'albums_file': self.json_albums_file,
            'artists_file_exists': os.path.exists(self.json_artists_file),
            'albums_file_exists': os.path.exists(self.json_albums_file)
        }
    
    def get_album_image(self, album_id: int) -> Optional[str]:
        """Obtiene la carátula de un álbum"""
        try:
            # Verificar cache local primero
            cache_path = os.path.join(self.images_dir, 'albums', f'{album_id}.jpg')
            if os.path.exists(cache_path):
                return cache_path
            
            # Buscar información de imagen en la base de datos
            with self.get_db_connection() as conn:
                cursor = conn.execute("""
                    SELECT album_art_path, album_art_urls 
                    FROM albums 
                    WHERE id = ?
                """, (album_id,))
                result = cursor.fetchone()
                
                if not result:
                    return self.get_default_album_image()
                
                # Intentar obtener imagen de diferentes fuentes
                image_path = self._process_album_image_data(album_id, result)
                return image_path or self.get_default_album_image()
                
        except Exception as e:
            logger.error(f"Error obteniendo imagen del álbum {album_id}: {e}")
            return self.get_default_album_image()
    
    def _process_artist_image_data(self, artist_id: int, db_data: sqlite3.Row) -> Optional[str]:
        """Procesa los datos de imagen de artista desde la BD"""
        try:
            # Verificar rutas locales primero
            if db_data['img_paths']:
                try:
                    paths = json.loads(db_data['img_paths'])
                    for path in paths:
                        if os.path.exists(path):
                            return self._cache_local_image(path, 'artists', artist_id)
                except (json.JSONDecodeError, TypeError):
                    # Si no es JSON, intentar como ruta simple
                    if os.path.exists(db_data['img_paths']):
                        return self._cache_local_image(db_data['img_paths'], 'artists', artist_id)
            
            # Verificar campo img
            if db_data['img'] and os.path.exists(db_data['img']):
                return self._cache_local_image(db_data['img'], 'artists', artist_id)
            
            # Intentar descargar desde URLs
            if db_data['img_urls']:
                try:
                    urls = json.loads(db_data['img_urls'])
                    for url in urls:
                        image_path = self._download_and_cache_image(url, 'artists', artist_id)
                        if image_path:
                            return image_path
                except (json.JSONDecodeError, TypeError):
                    # Si no es JSON, intentar como URL simple
                    return self._download_and_cache_image(db_data['img_urls'], 'artists', artist_id)
            
            return None
            
        except Exception as e:
            logger.error(f"Error procesando imagen del artista {artist_id}: {e}")
            return None
    
    def _process_album_image_data(self, album_id: int, db_data: sqlite3.Row) -> Optional[str]:
        """Procesa los datos de imagen de álbum desde la BD"""
        try:
            # Verificar ruta local primero
            if db_data['album_art_path'] and os.path.exists(db_data['album_art_path']):
                return self._cache_local_image(db_data['album_art_path'], 'albums', album_id)
            
            # Intentar descargar desde URLs
            if db_data['album_art_urls']:
                try:
                    urls = json.loads(db_data['album_art_urls'])
                    for url in urls:
                        image_path = self._download_and_cache_image(url, 'albums', album_id)
                        if image_path:
                            return image_path
                except (json.JSONDecodeError, TypeError):
                    # Si no es JSON, intentar como URL simple
                    return self._download_and_cache_image(db_data['album_art_urls'], 'albums', album_id)
            
            return None
            
        except Exception as e:
            logger.error(f"Error procesando imagen del álbum {album_id}: {e}")
            return None
    
    def _cache_local_image(self, source_path: str, category: str, entity_id: int) -> Optional[str]:
        """Copia y redimensiona una imagen local al cache"""
        try:
            cache_path = os.path.join(self.images_dir, category, f'{entity_id}.jpg')
            
            if os.path.exists(cache_path) and self.cache_enabled:
                return cache_path
            
            # Copiar y procesar imagen
            with Image.open(source_path) as img:
                # Convertir a RGB si es necesario
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Redimensionar manteniendo aspecto
                img = ImageOps.fit(img, (self.max_size, self.max_size), Image.Resampling.LANCZOS)
                
                # Guardar en cache
                os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                img.save(cache_path, 'JPEG', quality=85, optimize=True)
                
                logger.debug(f"Imagen cacheada: {cache_path}")
                return cache_path
                
        except Exception as e:
            logger.error(f"Error cacheando imagen local {source_path}: {e}")
            return None
    
    def _download_and_cache_image(self, url: str, category: str, entity_id: int) -> Optional[str]:
        """Descarga una imagen desde URL y la cachea"""
        try:
            if not url or not url.startswith(('http://', 'https://')):
                return None
            
            cache_path = os.path.join(self.images_dir, category, f'{entity_id}.jpg')
            
            if os.path.exists(cache_path) and self.cache_enabled:
                return cache_path
            
            # Descargar imagen
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; MusicWebExplorer/1.0)'
            }
            
            response = requests.get(url, headers=headers, timeout=30, stream=True)
            response.raise_for_status()
            
            # Verificar tipo de contenido
            content_type = response.headers.get('content-type', '').lower()
            if not any(fmt in content_type for fmt in ['image/jpeg', 'image/png', 'image/webp']):
                logger.warning(f"Tipo de contenido no soportado: {content_type}")
                return None
            
            # Procesar imagen
            with Image.open(response.raw) as img:
                # Convertir a RGB si es necesario
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Redimensionar manteniendo aspecto
                img = ImageOps.fit(img, (self.max_size, self.max_size), Image.Resampling.LANCZOS)
                
                # Guardar en cache
                os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                img.save(cache_path, 'JPEG', quality=85, optimize=True)
                
                logger.debug(f"Imagen descargada y cacheada: {cache_path}")
                return cache_path
                
        except Exception as e:
            logger.error(f"Error descargando imagen {url}: {e}")
            return None
    
    def get_default_artist_image(self) -> str:
        """Obtiene la imagen por defecto para artistas"""
        default_path = os.path.join(self.images_dir, 'defaults', 'artist_default.jpg')
        if os.path.exists(default_path):
            return default_path
        
        # Fallback: crear imagen simple en memoria
        return self._create_fallback_image('artist')
    
    def get_default_album_image(self) -> str:
        """Obtiene la imagen por defecto para álbumes"""
        default_path = os.path.join(self.images_dir, 'defaults', 'album_default.jpg')
        if os.path.exists(default_path):
            return default_path
        
        # Fallback: crear imagen simple en memoria
        return self._create_fallback_image('album')
    
    def _create_fallback_image(self, image_type: str) -> str:
        """Crea una imagen de fallback simple"""
        try:
            fallback_path = os.path.join(self.images_dir, 'defaults', f'{image_type}_fallback.jpg')
            
            if os.path.exists(fallback_path):
                return fallback_path
            
            # Crear imagen simple
            color = '#4A5568' if image_type == 'artist' else '#2D3748'
            img = Image.new('RGB', (300, 300), color=color)
            
            os.makedirs(os.path.dirname(fallback_path), exist_ok=True)
            img.save(fallback_path, 'JPEG', quality=85)
            
            return fallback_path
            
        except Exception as e:
            logger.error(f"Error creando imagen de fallback: {e}")
            # Retornar ruta que al menos no cause error 500
            return os.path.join(self.images_dir, 'defaults', 'fallback.jpg')
    
    def clear_cache(self, category: str = None) -> bool:
        """Limpia el cache de imágenes"""
        try:
            if category:
                cache_dir = os.path.join(self.images_dir, category)
            else:
                cache_dir = self.images_dir
            
            import shutil
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir)
                self.setup_directories()
                logger.info(f"Cache de imágenes limpiado: {cache_dir}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error limpiando cache de imágenes: {e}")
            return False
    
    def get_cache_stats(self) -> Dict:
        """Obtiene estadísticas del cache de imágenes - VERSIÓN MEJORADA"""
        try:
            stats = {
                'artists': 0,
                'albums': 0,
                'total_size': 0
            }
            
            for category in ['artists', 'albums']:
                cache_dir = os.path.join(self.images_dir, category)
                if os.path.exists(cache_dir):
                    files = [f for f in os.listdir(cache_dir) if f.endswith(('.jpg', '.png', '.webp')) and not f.endswith('.json')]
                    stats[category] = len(files)
                    
                    for file in files:
                        file_path = os.path.join(cache_dir, file)
                        try:
                            stats['total_size'] += os.path.getsize(file_path)
                        except:
                            pass
            
            # Convertir a MB
            stats['total_size_mb'] = round(stats['total_size'] / (1024 * 1024), 2)
            
            # Añadir estadísticas JSON
            stats['json_metadata'] = self.get_json_stats()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas del cache: {e}")
            return {'error': str(e)}
