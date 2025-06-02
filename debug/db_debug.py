#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os
import logging

def debug_database_structure(db_path='/app/data/musica.sqlite'):
    """Diagnostica la estructura de la base de datos y rutas de archivos"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        print("=== ESTRUCTURA DE LA TABLA SONGS ===")
        cursor = conn.execute("PRAGMA table_info(songs)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"- {col[1]} ({col[2]})")
        
        print("\n=== MUESTRA DE DATOS DE SONGS ===")
        cursor = conn.execute("SELECT * FROM songs LIMIT 3")
        songs = cursor.fetchall()
        
        for song in songs:
            print(f"\nCanción ID {song['id']}:")
            for key in song.keys():
                value = song[key]
                if key in ['file_path', 'path', 'location', 'file', 'filename']:
                    print(f"  {key}: {value}")
                elif len(str(value)) < 100:  # Solo campos cortos
                    print(f"  {key}: {value}")
        
        print("\n=== VERIFICACIÓN DE RUTAS DE ARCHIVOS ===")
        # Buscar columnas que puedan contener rutas
        path_columns = []
        for col in columns:
            col_name = col[1].lower()
            if any(keyword in col_name for keyword in ['path', 'file', 'location', 'url']):
                path_columns.append(col[1])
        
        print(f"Columnas que pueden contener rutas: {path_columns}")
        
        if path_columns:
            for col in path_columns:
                cursor = conn.execute(f"SELECT DISTINCT {col} FROM songs WHERE {col} IS NOT NULL LIMIT 5")
                values = cursor.fetchall()
                print(f"\nEjemplos de {col}:")
                for val in values:
                    print(f"  {val[0]}")
        
        print("\n=== VERIFICACIÓN DE ÁLBUM ESPECÍFICO ===")
        cursor = conn.execute("""
            SELECT s.*, a.name as album_name, ar.name as artist_name
            FROM songs s
            JOIN albums a ON s.album = a.name OR s.album_id = a.id
            JOIN artists ar ON a.artist_id = ar.id
            WHERE a.id = 9
            LIMIT 3
        """)
        album_songs = cursor.fetchall()
        
        if album_songs:
            print(f"Canciones del álbum ID 9:")
            for song in album_songs:
                print(f"  - {song['title']} (ID: {song['id']})")
                # Buscar campos de ruta
                for key in song.keys():
                    if 'path' in key.lower() or 'file' in key.lower():
                        print(f"    {key}: {song[key]}")
        else:
            print("No se encontraron canciones para el álbum ID 9")
            
            # Verificar si existe el álbum
            cursor = conn.execute("SELECT * FROM albums WHERE id = 9")
            album = cursor.fetchone()
            if album:
                print(f"Álbum encontrado: {album['name']} - {album.get('artist_name', 'Unknown')}")
            else:
                print("Álbum ID 9 no existe")
        
        conn.close()
        
    except Exception as e:
        print(f"Error en diagnóstico: {e}")
        import traceback
        traceback.print_exc()

def check_file_system_access(music_root='/mnt/NFS/moode/moode'):
    """Verifica el acceso al sistema de archivos de música"""
    print(f"\n=== VERIFICACIÓN DEL SISTEMA DE ARCHIVOS ===")
    print(f"Directorio raíz de música: {music_root}")
    
    if os.path.exists(music_root):
        print(f"✓ Directorio existe")
        
        if os.access(music_root, os.R_OK):
            print(f"✓ Directorio legible")
            
            try:
                files = os.listdir(music_root)
                print(f"✓ Contenido accesible - {len(files)} elementos")
                
                # Mostrar algunos ejemplos
                print("Primeros 5 elementos:")
                for item in files[:5]:
                    item_path = os.path.join(music_root, item)
                    if os.path.isdir(item_path):
                        print(f"  📁 {item}/")
                    else:
                        print(f"  📄 {item}")
                        
            except PermissionError:
                print("❌ Sin permisos para listar contenido")
            except Exception as e:
                print(f"❌ Error accediendo al contenido: {e}")
        else:
            print(f"❌ Directorio no legible")
    else:
        print(f"❌ Directorio no existe")

if __name__ == "__main__":
    debug_database_structure()
    check_file_system_access()