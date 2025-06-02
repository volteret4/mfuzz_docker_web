#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import time

def test_album_download():
    """Prueba la descarga de un álbum"""
    base_url = "http://localhost:8447"
    album_id = 9  # El álbum que estás probando
    
    print(f"=== PRUEBA DE DESCARGA ÁLBUM {album_id} ===")
    
    # 1. Verificar que el álbum existe
    print("1. Verificando álbum...")
    response = requests.get(f"{base_url}/api/albums/{album_id}")
    if response.status_code != 200:
        print(f"❌ Álbum no encontrado: {response.status_code}")
        return
    
    album = response.json()['album']
    print(f"✓ Álbum encontrado: {album['name']} - {album['artist_name']}")
    
    # 2. Verificar canciones del álbum
    print("2. Verificando canciones...")
    response = requests.get(f"{base_url}/api/albums/{album_id}/tracks")
    if response.status_code != 200:
        print(f"❌ Error obteniendo canciones: {response.status_code}")
        return
    
    tracks_data = response.json()
    tracks = tracks_data['tracks']
    print(f"✓ {len(tracks)} canciones encontradas")
    
    if tracks:
        print("Primeras 3 canciones:")
        for i, track in enumerate(tracks[:3]):
            print(f"  {i+1}. {track.get('title', 'Sin título')} (ID: {track.get('id')})")
    
    # 3. Usar endpoint de diagnóstico
    print("3. Diagnóstico detallado...")
    response = requests.get(f"{base_url}/api/debug/album/{album_id}")
    if response.status_code == 200:
        debug_info = response.json()
        print(f"✓ Music root: {debug_info['music_root']}")
        print(f"✓ Music root existe: {debug_info['music_root_exists']}")
        
        if debug_info['tracks_analysis']:
            files_found = sum(1 for t in debug_info['tracks_analysis'] if t['file_exists'])
            total_files = len(debug_info['tracks_analysis'])
            print(f"✓ Archivos encontrados: {files_found}/{total_files}")
            
            if files_found == 0:
                print("❌ PROBLEMA: No se encontraron archivos de música")
                print("Análisis de las primeras 3 canciones:")
                for track in debug_info['tracks_analysis'][:3]:
                    print(f"  - {track['title']}")
                    print(f"    Rutas disponibles: {track['available_paths']}")
                    print(f"    Mejor ruta: {track['best_path']}")
                    print(f"    Ruta completa: {track['full_path']}")
                    print(f"    Archivo existe: {track['file_exists']}")
                    print()
                return
        else:
            print("❌ No hay análisis de canciones")
            return
    else:
        print(f"❌ Error en diagnóstico: {response.status_code}")
        # Continuar con la prueba de descarga
    
    # 4. Iniciar descarga
    print("4. Iniciando descarga...")
    response = requests.post(f"{base_url}/api/download/album/{album_id}")
    if response.status_code != 200:
        print(f"❌ Error iniciando descarga: {response.status_code}")
        print(f"Respuesta: {response.text}")
        return
    
    download_data = response.json()
    download_id = download_data['download_id']
    print(f"✓ Descarga iniciada: {download_id}")
    
    # 5. Monitorear progreso
    print("5. Monitoreando progreso...")
    max_attempts = 30  # 30 segundos máximo
    
    for attempt in range(max_attempts):
        response = requests.get(f"{base_url}/api/download/status/{download_id}")
        if response.status_code != 200:
            print(f"❌ Error obteniendo estado: {response.status_code}")
            break
        
        status = response.json()
        print(f"Estado: {status['status']} - Progreso: {status.get('progress', 0)}%")
        
        if status['status'] == 'completed':
            print(f"✅ Descarga completada!")
            print(f"Archivos exitosos: {status.get('successful_files', 0)}")
            print(f"Archivos fallidos: {status.get('failed_files', 0)}")
            if status.get('failed_list'):
                print("Errores:")
                for error in status['failed_list'][:5]:
                    print(f"  - {error}")
            break
        elif status['status'] == 'error':
            print(f"❌ Error en descarga: {status.get('error', 'Error desconocido')}")
            break
        
        time.sleep(1)
    else:
        print("❌ Timeout esperando descarga")

if __name__ == "__main__":
    test_album_download()