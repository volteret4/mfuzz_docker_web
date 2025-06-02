#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import subprocess
import time
import zipfile
import shlex  # NUEVO: Para escapar rutas correctamente
from typing import Dict, Optional, List
import re

logger = logging.getLogger(__name__)

class DownloadManager:
    """Gestor de descargas que soporta modo local y SSH"""
    
    def __init__(self, config):
        self.config = config
        self.download_config = config.get('downloads', {})
        self.mode = self.download_config.get('mode', 'local')
        
        # Configuración SSH
        self.ssh_config = self.download_config.get('ssh', {})
        self.ssh_enabled = self.ssh_config.get('enabled', False)
        self.ssh_host = self.ssh_config.get('host', '')
        self.remote_music_path = self.ssh_config.get('remote_music_path', '')
        self.rsync_options = self.ssh_config.get('rsync_options', ['-avz', '--progress'])
        self.ssh_key_path = self.ssh_config.get('ssh_key_path', '')
        self.timeout = self.ssh_config.get('timeout', 300)
        
        # Rutas locales
        self.local_music_root = config.get('paths', {}).get('music_root', '/mnt/NFS/moode/moode')
        self.downloads_dir = config.get('paths', {}).get('downloads', '/downloads')
        
        logger.info(f"DownloadManager inicializado - Modo: {self.mode}")
        
        if self.mode == 'ssh' and not self.ssh_enabled:
            logger.warning("Modo SSH seleccionado pero no está habilitado en la configuración")
    
    def get_download_mode(self) -> str:
        """Obtiene el modo de descarga actual"""
        return self.mode
    
    def is_ssh_mode(self) -> bool:
        """Verifica si está en modo SSH"""
        return self.mode == 'ssh' and self.ssh_enabled
    
    def get_album_source_path(self, album_info: Dict) -> Optional[str]:
        """Obtiene la ruta de origen del álbum - CORREGIDO PARA SSH"""
        folder_path = album_info.get('folder_path', '')
        
        if folder_path:
            if folder_path.startswith('/'):
                # En modo SSH, devolver la ruta tal como está (será usada en el servidor remoto)
                return folder_path
            else:
                return os.path.join(self.local_music_root, folder_path.lstrip('/'))
        
        # Fallback: construir desde artista/álbum
        artist_name = album_info.get('artist_name', '')
        album_name = album_info.get('name', '')
        
        if artist_name and album_name:
            return os.path.join(self.local_music_root, artist_name, album_name)
        
        return None



    def prepare_album_download(self, album_info: Dict, download_id: str) -> Dict:
        """Prepara la descarga de un álbum según el modo configurado"""
        try:
            if self.is_ssh_mode():
                return self._prepare_ssh_download(album_info, download_id)
            else:
                return self._prepare_local_download(album_info, download_id)
                
        except Exception as e:
            logger.error(f"Error preparando descarga {download_id}: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'mode': self.mode
            }
    
    def _prepare_local_download(self, album_info: Dict, download_id: str) -> Dict:
        """Prepara descarga en modo local (método actual)"""
        return {
            'status': 'ready_local',
            'mode': 'local',
            'source_path': self._get_album_source_path(album_info),
            'can_proceed': True,
            'next_action': 'compress_local'
        }
    
    def _prepare_ssh_download(self, album_info: Dict, download_id: str) -> Dict:
        """Prepara descarga en modo SSH"""
        if not self.ssh_host or not self.remote_music_path:
            return {
                'status': 'error',
                'error': 'Configuración SSH incompleta (host o remote_music_path)',
                'mode': 'ssh'
            }
        
        source_path = self._get_album_source_path(album_info)
        if not source_path or not os.path.exists(source_path):
            return {
                'status': 'error',
                'error': f'Directorio de álbum no encontrado: {source_path}',
                'mode': 'ssh'
            }
        
        # Construir ruta relativa para el servidor remoto
        relative_path = os.path.relpath(source_path, self.local_music_root)
        remote_target_path = os.path.join(self.remote_music_path, relative_path)
        
        return {
            'status': 'ready_ssh',
            'mode': 'ssh',
            'source_path': source_path,
            'remote_target_path': remote_target_path,
            'can_proceed': True,
            'next_action': 'rsync_to_remote'
        }
    
    def execute_rsync(self, source_path: str, album_info: Dict, download_id: str, progress_callback=None) -> Dict:
        """Ejecuta rsync para copiar archivos al servidor remoto - VERSIÓN CORREGIDA PARA SSH"""
        try:
            # CORREGIDO: En modo SSH, source_path es la ruta en el servidor remoto
            # No necesitamos calcular ruta relativa, usamos directamente la ruta remota
            
            # Construir ruta remota de destino
            # Para SSH, copiamos desde la ruta remota original a una ruta temporal remota
            album_name = album_info.get('name', 'Unknown')
            artist_name = album_info.get('artist_name', 'Unknown')
            
            # Crear un directorio temporal único en el servidor remoto
            safe_name = f"{artist_name}_{album_name}_{int(time.time())}"
            safe_name = "".join(c for c in safe_name if c.isalnum() or c in ('_', '-'))
            
            remote_temp_path = f"/tmp/music_transfer_{safe_name}"
            
            logger.info(f"Rutas para rsync SSH:")
            logger.info(f"  - Origen remoto: {source_path}")
            logger.info(f"  - Destino temporal remoto: {remote_temp_path}")
            
            # PASO 1: Crear directorio temporal en servidor remoto y copiar archivos
            commands = [
                f'rm -rf {shlex.quote(remote_temp_path)}',  # Limpiar si existe
                f'mkdir -p {shlex.quote(remote_temp_path)}',  # Crear directorio
                f'cp -r {shlex.quote(source_path)}/* {shlex.quote(remote_temp_path)}/ 2>/dev/null || cp -r {shlex.quote(source_path)} {shlex.quote(remote_temp_path)}/'  # Copiar contenido
            ]
            
            for cmd in commands:
                ssh_cmd = ['ssh']
                if self.ssh_key_path and os.path.exists(self.ssh_key_path):
                    ssh_cmd.extend(['-i', self.ssh_key_path])
                ssh_cmd.extend([self.ssh_host, cmd])
                
                logger.info(f"Ejecutando comando SSH: {' '.join(ssh_cmd)}")
                result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode != 0 and 'mkdir' not in cmd:  # mkdir puede fallar si ya existe
                    logger.warning(f"Comando SSH falló: {result.stderr}")
                    if 'rm -rf' not in cmd:  # rm puede fallar si no existe, no es crítico
                        return {
                            'status': 'error',
                            'success': False,
                            'error': f'Error en comando SSH: {result.stderr}'
                        }
            
            # PASO 2: Verificar que se copiaron archivos
            verify_cmd = ['ssh']
            if self.ssh_key_path and os.path.exists(self.ssh_key_path):
                verify_cmd.extend(['-i', self.ssh_key_path])
            verify_cmd.extend([self.ssh_host, f'ls -la {shlex.quote(remote_temp_path)}'])
            
            verify_result = subprocess.run(verify_cmd, capture_output=True, text=True, timeout=30)
            
            if verify_result.returncode != 0:
                return {
                    'status': 'error',
                    'success': False,
                    'error': f'No se pudieron copiar archivos al directorio temporal: {verify_result.stderr}'
                }
            
            # Contar archivos copiados
            files_copied = len(verify_result.stdout.strip().split('\n')) - 2  # Restar . y ..
            
            logger.info(f"SSH copy completado exitosamente para {download_id}")
            logger.info(f"Archivos en directorio temporal: {files_copied}")
            
            return {
                'status': 'ssh_complete',
                'success': True,
                'remote_path': remote_temp_path,
                'files_copied': max(files_copied, 1),  # Al menos 1 para evitar errores
                'next_action': 'compress_remote'
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout en operación SSH para {download_id}")
            return {
                'status': 'error',
                'success': False,
                'error': f'Timeout después de {self.timeout} segundos'
            }
        except Exception as e:
            logger.error(f"Error ejecutando operación SSH para {download_id}: {e}")
            return {
                'status': 'error',
                'success': False,
                'error': str(e)
            }
    
    def compress_remote_album(self, remote_path: str, album_info: Dict, download_id: str) -> Dict:
        """Comprime un álbum desde el servidor remoto y lo transfiere - VERSION CORREGIDA"""
        try:
            # Generar nombre de archivo ZIP
            artist_name = album_info.get('artist_name', 'Unknown')
            album_name = album_info.get('name', 'Unknown')
            
            safe_artist = "".join(c for c in artist_name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_album = "".join(c for c in album_name if c.isalnum() or c in (' ', '-', '_')).strip()
            timestamp = int(time.time())
            zip_filename = f"{safe_artist} - {safe_album} [SSH-{timestamp}].tar.gz"  # Cambiado a .tar.gz
            
            # Ruta local para el archivo comprimido
            local_zip_path = os.path.join(self.downloads_dir, zip_filename)
            
            logger.info(f"Comprimiendo álbum remoto:")
            logger.info(f"  - Ruta remota: {remote_path}")
            logger.info(f"  - Archivo destino: {local_zip_path}")
            
            # CORREGIDO: Crear comando para comprimir en el servidor remoto y transferir
            # Escapar correctamente las rutas con espacios
            escaped_remote_path = shlex.quote(remote_path)
            remote_dir = shlex.quote(os.path.dirname(remote_path))
            remote_basename = shlex.quote(os.path.basename(remote_path))
            
            # Comando SSH que comprime y envía por stdout
            ssh_cmd = ['ssh']
            
            if self.ssh_key_path and os.path.exists(self.ssh_key_path):
                ssh_cmd.extend(['-i', self.ssh_key_path])
            
            # CORREGIDO: Comando que maneja espacios correctamente
            compress_command = f'cd {remote_dir} && tar -czf - {remote_basename}'
            ssh_cmd.extend([self.ssh_host, compress_command])
            
            logger.info(f"Comando de compresión SSH: {' '.join(ssh_cmd)}")
            
            # Ejecutar compresión y transferencia
            with open(local_zip_path, 'wb') as zip_file:
                process = subprocess.run(
                    ssh_cmd,
                    stdout=zip_file,
                    stderr=subprocess.PIPE,
                    timeout=self.timeout
                )
            
            if process.returncode == 0 and os.path.exists(local_zip_path):
                file_size = os.path.getsize(local_zip_path)
                logger.info(f"Compresión remota completada: {local_zip_path} ({file_size} bytes)")
                
                return {
                    'status': 'completed',
                    'success': True,
                    'file_path': local_zip_path,
                    'zip_filename': zip_filename,
                    'file_size': file_size,
                    'mode': 'ssh'
                }
            else:
                error_msg = process.stderr.decode() if process.stderr else 'Error en compresión remota'
                logger.error(f"Error en compresión remota: {error_msg}")
                return {
                    'status': 'error',
                    'success': False,
                    'error': error_msg
                }
                
        except Exception as e:
            logger.error(f"Error comprimiendo álbum remoto {download_id}: {e}")
            return {
                'status': 'error',
                'success': False,
                'error': str(e)
            }
    
    def _get_album_source_path(self, album_info: Dict) -> Optional[str]:
        """Obtiene la ruta de origen del álbum"""
        folder_path = album_info.get('folder_path', '')
        
        if folder_path:
            if folder_path.startswith('/'):
                return folder_path
            else:
                return os.path.join(self.local_music_root, folder_path.lstrip('/'))
        
        # Fallback: construir desde artista/álbum
        artist_name = album_info.get('artist_name', '')
        album_name = album_info.get('name', '')
        
        if artist_name and album_name:
            return os.path.join(self.local_music_root, artist_name, album_name)
        
        return None

    def cleanup_remote_files(self, remote_path: str) -> bool:
        """Limpia archivos temporales en el servidor remoto - VERSION CORREGIDA"""
        try:
            # CORREGIDO: Escapar ruta correctamente
            escaped_remote_path = shlex.quote(remote_path)
            cleanup_cmd = ['ssh']
            
            if self.ssh_key_path and os.path.exists(self.ssh_key_path):
                cleanup_cmd.extend(['-i', self.ssh_key_path])
            
            cleanup_cmd.extend([self.ssh_host, f'rm -rf {escaped_remote_path}'])
            
            logger.info(f"Comando de limpieza: {' '.join(cleanup_cmd)}")
            result = subprocess.run(cleanup_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"Archivos remotos limpiados: {remote_path}")
                return True
            else:
                logger.warning(f"Error limpiando archivos remotos: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error en limpieza remota: {e}")
            return False


    def execute_ssh_transfer(self, source_path: str, album_info: Dict, download_id: str, progress_callback=None) -> Dict:
        """Ejecuta transferencia SSH - copia archivos dentro del servidor remoto"""
        try:
            album_name = album_info.get('name', 'Unknown')
            artist_name = album_info.get('artist_name', 'Unknown')
            
            # Crear un directorio temporal único en el servidor remoto
            safe_name = f"{artist_name}_{album_name}_{int(time.time())}"
            safe_name = "".join(c for c in safe_name if c.isalnum() or c in ('_', '-'))
            
            remote_temp_path = f"/tmp/music_transfer_{safe_name}"
            
            logger.info(f"Transferencia SSH:")
            logger.info(f"  - Origen remoto: {source_path}")
            logger.info(f"  - Destino temporal remoto: {remote_temp_path}")
            
            # PASO 1: Verificar que el directorio origen existe en el servidor remoto
            verify_cmd = ['ssh']
            if self.ssh_key_path and os.path.exists(self.ssh_key_path):
                verify_cmd.extend(['-i', self.ssh_key_path])
            verify_cmd.extend([self.ssh_host, f'test -d {shlex.quote(source_path)}'])
            
            logger.info(f"Verificando directorio remoto: {' '.join(verify_cmd)}")
            verify_result = subprocess.run(verify_cmd, capture_output=True, text=True, timeout=30)
            
            if verify_result.returncode != 0:
                return {
                    'status': 'error',
                    'success': False,
                    'error': f'Directorio no encontrado en servidor remoto: {source_path}'
                }
            
            # PASO 2: Crear directorio temporal y copiar archivos
            commands = [
                f'rm -rf {shlex.quote(remote_temp_path)}',  # Limpiar si existe
                f'mkdir -p {shlex.quote(remote_temp_path)}',  # Crear directorio
                f'cp -r {shlex.quote(source_path)}/* {shlex.quote(remote_temp_path)}/ 2>/dev/null || cp -r {shlex.quote(source_path)} {shlex.quote(remote_temp_path + "/album")}',  # Copiar contenido
            ]
            
            for i, cmd in enumerate(commands):
                ssh_cmd = ['ssh']
                if self.ssh_key_path and os.path.exists(self.ssh_key_path):
                    ssh_cmd.extend(['-i', self.ssh_key_path])
                ssh_cmd.extend([self.ssh_host, cmd])
                
                logger.info(f"Ejecutando comando SSH {i+1}/{len(commands)}: {cmd}")
                result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode != 0:
                    if 'rm -rf' in cmd:
                        # rm puede fallar si no existe, no es crítico
                        logger.debug(f"rm falló (normal): {result.stderr}")
                        continue
                    elif 'mkdir' in cmd:
                        # mkdir puede fallar si ya existe
                        logger.debug(f"mkdir falló: {result.stderr}")
                        continue
                    else:
                        logger.error(f"Comando SSH falló: {result.stderr}")
                        return {
                            'status': 'error',
                            'success': False,
                            'error': f'Error en comando SSH: {result.stderr}'
                        }
                
                if progress_callback:
                    progress_callback(f"Paso {i+1}/{len(commands)} completado")
            
            # PASO 3: Verificar que se copiaron archivos
            list_cmd = ['ssh']
            if self.ssh_key_path and os.path.exists(self.ssh_key_path):
                list_cmd.extend(['-i', self.ssh_key_path])
            list_cmd.extend([self.ssh_host, f'find {shlex.quote(remote_temp_path)} -type f | head -20'])
            
            list_result = subprocess.run(list_cmd, capture_output=True, text=True, timeout=30)
            
            if list_result.returncode != 0:
                return {
                    'status': 'error',
                    'success': False,
                    'error': f'No se pudieron listar archivos en directorio temporal: {list_result.stderr}'
                }
            
            # Contar archivos copiados
            files_list = list_result.stdout.strip().split('\n') if list_result.stdout.strip() else []
            files_copied = len([f for f in files_list if f.strip()])
            
            if files_copied == 0:
                return {
                    'status': 'error',
                    'success': False,
                    'error': 'No se encontraron archivos en el directorio temporal después de la copia'
                }
            
            logger.info(f"Transferencia SSH completada exitosamente para {download_id}")
            logger.info(f"Archivos encontrados: {files_copied}")
            logger.info(f"Primeros archivos: {files_list[:5]}")
            
            return {
                'status': 'ssh_complete',
                'success': True,
                'remote_path': remote_temp_path,
                'files_copied': files_copied,
                'next_action': 'compress_remote'
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout en transferencia SSH para {download_id}")
            return {
                'status': 'error',
                'success': False,
                'error': f'Timeout después de {self.timeout} segundos'
            }
        except Exception as e:
            logger.error(f"Error ejecutando transferencia SSH para {download_id}: {e}")
            return {
                'status': 'error',
                'success': False,
                'error': str(e)
            }