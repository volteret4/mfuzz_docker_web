#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
extract_images.py - Extractor real de imágenes desde base de datos SQLite
"""

import sqlite3
import os
import shutil
import json
import argparse
import configparser
from pathlib import Path
from collections import defaultdict
from datetime import datetime

class ImageExtractor:
    def __init__(self, db_path, mounted_paths=None):
        self.db_path = db_path
        
        # Rutas montadas donde buscar las imágenes originales
        if mounted_paths:
            self.mounted_paths = mounted_paths if isinstance(mounted_paths, list) else [mounted_paths]
        else:
            # Rutas por defecto si no se especifican
            self.mounted_paths = [
                '/mnt/NFS/moode/moode',
                '/home/huan/gits/pollo/music-fuzzy/.content'
            ]
        
        print(f"Base de datos: {self.db_path}")
        print(f"Rutas montadas: {self.mounted_paths}")
    
    def get_db_connection(self):
        """Obtener conexión a la base de datos"""
        return sqlite3.connect(self.db_path)
    
    def find_image_file(self, image_path):
        """Buscar archivo de imagen en las rutas montadas"""
        if not image_path:
            return None
        
        # 1. Verificar ruta completa tal como está
        if os.path.exists(image_path) and os.access(image_path, os.R_OK):
            return image_path
        
        # 2. Verificar en rutas montadas
        for mounted_path in self.mounted_paths:
            # Si el image_path ya contiene el mounted_path, no duplicar
            if image_path.startswith(mounted_path):
                if os.path.exists(image_path) and os.access(image_path, os.R_OK):
                    return image_path
            else:
                # Intentar construir la ruta completa
                full_path = os.path.join(mounted_path, image_path.lstrip('/'))
                if os.path.exists(full_path) and os.access(full_path, os.R_OK):
                    return full_path
        
        return None
    
    def extract_artist_images(self):
        """Extraer imágenes de artistas desde la base de datos"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        print("Extrayendo imágenes de artistas...")
        
        cursor.execute("""
            SELECT id, name, img, img_urls, img_paths 
            FROM artists 
            WHERE origen = 'local' 
            AND (img IS NOT NULL OR img_urls IS NOT NULL OR img_paths IS NOT NULL)
        """)
        
        artist_images = {}
        processed = 0
        found = 0
        
        for row in cursor.fetchall():
            artist_id, name, img, img_urls, img_paths = row
            processed += 1
            
            if processed % 100 == 0:
                print(f"  Procesados {processed} artistas...")
            
            # Lista de posibles rutas de imagen
            image_candidates = []
            
            # 1. Campo img
            if img:
                image_candidates.append(img)
            
            # 2. Campo img_paths (JSON)
            if img_paths:
                try:
                    paths = json.loads(img_paths)
                    if isinstance(paths, list):
                        image_candidates.extend(paths)
                except (json.JSONDecodeError, TypeError):
                    # Si no es JSON, intentar como CSV
                    paths = [p.strip() for p in str(img_paths).split(',') if p.strip()]
                    image_candidates.extend(paths)
            
            # 3. Campo img_urls (solo rutas locales)
            if img_urls:
                try:
                    urls = json.loads(img_urls)
                    if isinstance(urls, list):
                        for item in urls:
                            # Puede ser string o dict con 'path'
                            path = item.get('path') if isinstance(item, dict) else item
                            if path and not str(path).startswith(('http://', 'https://')):
                                image_candidates.append(path)
                except (json.JSONDecodeError, TypeError):
                    # Si no es JSON, intentar como CSV
                    urls = [u.strip() for u in str(img_urls).split(',') if u.strip()]
                    for url in urls:
                        if not url.startswith(('http://', 'https://')):
                            image_candidates.append(url)
            
            # Buscar la primera imagen que exista
            for candidate in image_candidates:
                actual_path = self.find_image_file(candidate)
                if actual_path:
                    artist_images[artist_id] = {
                        'name': name,
                        'source_path': actual_path,
                        'original_path': candidate
                    }
                    found += 1
                    break
        
        conn.close()
        print(f"  Artistas procesados: {processed}")
        print(f"  Imágenes de artistas encontradas: {found}")
        
        return artist_images
    
    def extract_album_images(self):
        """Extraer imágenes de álbumes desde la base de datos"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        print("Extrayendo imágenes de álbumes...")
        
        cursor.execute("""
            SELECT al.id, al.name, ar.name as artist_name, al.album_art_path,
                   MIN(s.album_art_path_denorm) as song_album_art,
                   MIN(s.file_path) as sample_path
            FROM albums al
            LEFT JOIN artists ar ON al.artist_id = ar.id
            LEFT JOIN songs s ON (al.name = s.album AND ar.name = s.artist AND s.origen = 'local')
            WHERE al.origen = 'local'
            GROUP BY al.id, al.name, ar.name, al.album_art_path
        """)
        
        album_images = {}
        processed = 0
        found = 0
        
        for row in cursor.fetchall():
            album_id, album_name, artist_name, album_art_path, song_album_art, sample_path = row
            processed += 1
            
            if processed % 100 == 0:
                print(f"  Procesados {processed} álbumes...")
            
            # Lista de posibles rutas de imagen
            image_candidates = []
            
            # 1. album_art_path del álbum
            if album_art_path:
                image_candidates.append(album_art_path)
            
            # 2. album_art_path_denorm de canciones
            if song_album_art:
                image_candidates.append(song_album_art)
            
            # 3. Buscar en el directorio del álbum usando sample_path
            if sample_path:
                album_dir = str(Path(sample_path).parent)
                common_names = [
                    'cover.jpg', 'cover.png', 'folder.jpg', 'folder.png',
                    'album.jpg', 'album.png', 'front.jpg', 'front.png',
                    'albumart.jpg', 'albumartsmall.jpg', 'thumb.jpg'
                ]
                
                for img_name in common_names:
                    img_path = os.path.join(album_dir, img_name)
                    image_candidates.append(img_path)
            
            # Buscar la primera imagen que exista
            for candidate in image_candidates:
                actual_path = self.find_image_file(candidate)
                if actual_path:
                    album_images[album_id] = {
                        'name': album_name,
                        'artist_name': artist_name,
                        'source_path': actual_path,
                        'original_path': candidate
                    }
                    found += 1
                    break
        
        conn.close()
        print(f"  Álbumes procesados: {processed}")
        print(f"  Imágenes de álbumes encontradas: {found}")
        
        return album_images
    
    def copy_images_to_directory(self, output_dir, artist_images, album_images):
        """Copiar las imágenes encontradas al directorio de salida"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Crear subdirectorios
        artists_dir = output_path / 'artists'
        albums_dir = output_path / 'albums'
        artists_dir.mkdir(exist_ok=True)
        albums_dir.mkdir(exist_ok=True)
        
        print(f"Copiando imágenes a {output_dir}...")
        
        # Copiar imágenes de artistas
        artist_index = {}
        copied_artists = 0
        
        for artist_id, info in artist_images.items():
            try:
                source_path = Path(info['source_path'])
                # Usar ID y nombre para evitar conflictos
                safe_name = "".join(c for c in info['name'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
                dest_filename = f"{artist_id}_{safe_name}{source_path.suffix}"
                dest_path = artists_dir / dest_filename
                
                shutil.copy2(source_path, dest_path)
                
                artist_index[artist_id] = {
                    'name': info['name'],
                    'filename': dest_filename,
                    'original_path': info['original_path'],
                    'size': dest_path.stat().st_size
                }
                
                copied_artists += 1
                
            except Exception as e:
                print(f"Error copiando imagen de artista {info['name']}: {e}")
        
        # Copiar imágenes de álbumes
        album_index = {}
        copied_albums = 0
        
        for album_id, info in album_images.items():
            try:
                source_path = Path(info['source_path'])
                # Usar ID, artista y álbum para evitar conflictos
                safe_artist = "".join(c for c in info['artist_name'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
                safe_album = "".join(c for c in info['name'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
                dest_filename = f"{album_id}_{safe_artist}_{safe_album}{source_path.suffix}"
                dest_path = albums_dir / dest_filename
                
                shutil.copy2(source_path, dest_path)
                
                album_index[album_id] = {
                    'name': info['name'],
                    'artist_name': info['artist_name'],
                    'filename': dest_filename,
                    'original_path': info['original_path'],
                    'size': dest_path.stat().st_size
                }
                
                copied_albums += 1
                
            except Exception as e:
                print(f"Error copiando imagen de álbum {info['artist_name']} - {info['name']}: {e}")
        
        print(f"  Imágenes de artistas copiadas: {copied_artists}")
        print(f"  Imágenes de álbumes copiadas: {copied_albums}")
        
        return artist_index, album_index
    
    def create_master_index(self, output_dir, artist_index, album_index):
        """Crear índice maestro de todas las imágenes"""
        master_index = {
            'metadata': {
                'extraction_date': datetime.now().isoformat(),
                'total_artists': len(artist_index),
                'total_albums': len(album_index),
                'total_images': len(artist_index) + len(album_index)
            },
            'artists': artist_index,
            'albums': album_index
        }
        
        index_file = Path(output_dir) / 'master_index.json'
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(master_index, f, indent=2, ensure_ascii=False)
        
        print(f"Índice maestro creado: {index_file}")
        
        # Crear también índices separados para fácil acceso
        artists_index_file = Path(output_dir) / 'artists' / 'index.json'
        albums_index_file = Path(output_dir) / 'albums' / 'index.json'
        
        with open(artists_index_file, 'w', encoding='utf-8') as f:
            json.dump(artist_index, f, indent=2, ensure_ascii=False)
        
        with open(albums_index_file, 'w', encoding='utf-8') as f:
            json.dump(album_index, f, indent=2, ensure_ascii=False)
        
        print(f"Índices específicos creados en artists/ y albums/")
    
    def extract_all_images(self, output_dir):
        """Función principal para extraer todas las imágenes"""
        print("=== EXTRACTOR DE IMÁGENES ===")
        print(f"Directorio de salida: {output_dir}")
        
        # Verificar que la base de datos existe
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Base de datos no encontrada: {self.db_path}")
        
        # Extraer información de imágenes
        artist_images = self.extract_artist_images()
        album_images = self.extract_album_images()
        
        # Copiar imágenes al directorio de salida
        artist_index, album_index = self.copy_images_to_directory(
            output_dir, artist_images, album_images
        )
        
        # Crear índices
        self.create_master_index(output_dir, artist_index, album_index)
        
        # Estadísticas finales
        total_size = 0
        for info in artist_index.values():
            total_size += info['size']
        for info in album_index.values():
            total_size += info['size']
        
        size_mb = total_size / (1024 * 1024)
        
        print("\n=== RESUMEN ===")
        print(f"✅ Imágenes de artistas: {len(artist_index)}")
        print(f"✅ Imágenes de álbumes: {len(album_index)}")
        print(f"✅ Total imágenes: {len(artist_index) + len(album_index)}")
        print(f"✅ Tamaño total: {size_mb:.1f} MB")
        print(f"✅ Directorio: {output_dir}")
        
        return True


def main():
    parser = argparse.ArgumentParser(description='Extraer imágenes de la base de datos musical')
    parser.add_argument('--output', '-o', default='./container_images',
                       help='Directorio de salida para las imágenes (default: ./container_images)')
    parser.add_argument('--database', '-d', required=True,
                       help='Ruta a la base de datos SQLite')
    parser.add_argument('--mounted-paths', '-m', nargs='+',
                       default=['/mnt/NFS/moode/moode', '/home/huan/gits/pollo/music-fuzzy/.content'],
                       help='Rutas montadas donde buscar las imágenes (default: rutas NFS y content)')
    parser.add_argument('--force', action='store_true',
                       help='Sobrescribir directorio de salida si existe')
    
    args = parser.parse_args()
    
    # Verificar que la base de datos existe
    if not os.path.exists(args.database):
        print(f"❌ Base de datos no encontrada: {args.database}")
        return 1
    
    # Verificar si el directorio de salida existe
    if os.path.exists(args.output) and not args.force:
        response = input(f"El directorio {args.output} ya existe. ¿Sobrescribir? (y/N): ")
        if response.lower() != 'y':
            print("Operación cancelada")
            return 1
        
        shutil.rmtree(args.output)
    
    try:
        extractor = ImageExtractor(args.database, args.mounted_paths)
        success = extractor.extract_all_images(args.output)
        
        if success:
            print("\n🎉 Extracción completada exitosamente")
            return 0
        else:
            print("\n❌ Error durante la extracción")
            return 1
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == '__main__':
    exit(main())