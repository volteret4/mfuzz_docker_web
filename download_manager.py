#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import subprocess
import time
import zipfile
import shlex  # NUEVO: Para escapar rutas correctamente
from typing import Dict, Optional, List

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
        """Ejecuta rsync para copiar archivos al servidor remoto - VERSION CORREGIDA PARA ESPACIOS"""
        try:
            # Construir ruta relativa para el servidor remoto
            relative_path = os.path.relpath(source_path, self.local_music_root)
            remote_target_path = os.path.join(self.remote_music_path, relative_path)
            
            logger.info(f"Rutas para rsync:")
            logger.info(f"  - Origen local: {source_path}")
            logger.info(f"  - Destino remoto: {remote_target_path}")
            logger.info(f"  - Ruta relativa: {relative_path}")
            
            # CORREGIDO: Crear directorio remoto con escapado correcto
            remote_dir = os.path.dirname(remote_target_path)
            
            # Usar shlex.quote para escapar correctamente la ruta
            escaped_remote_dir = shlex.quote(remote_dir)
            mkdir_cmd = ['ssh']
            
            if self.ssh_key_path and os.path.exists(self.ssh_key_path):
                mkdir_cmd.extend(['-i', self.ssh_key_path])
            
            mkdir_cmd.extend([self.ssh_host, f'mkdir -p {escaped_remote_dir}'])
            
            logger.info(f"Comando mkdir: {' '.join(mkdir_cmd)}")
            result = subprocess.run(mkdir_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.warning(f"Error creando directorio remoto: {result.stderr}")
                # No es crítico, continuar con rsync
            
            # CORREGIDO: Construir comando rsync con escapado correcto
            rsync_cmd = ['rsync'] + self.rsync_options
            
            if self.ssh_key_path and os.path.exists(self.ssh_key_path):
                rsync_cmd.extend(['-e', f'ssh -i {shlex.quote(self.ssh_key_path)}'])
            
            # IMPORTANTE: Añadir trailing slash para copiar contenido del directorio
            source_with_slash = source_path.rstrip('/') + '/'
            
            # CORREGIDO: Escapar rutas con espacios correctamente
            # Para rsync, necesitamos escapar tanto la ruta local como la remota
            escaped_source = shlex.quote(source_with_slash)
            escaped_remote_target = f'{self.ssh_host}:{shlex.quote(remote_target_path + "/")}'
            
            rsync_cmd.extend([escaped_source, escaped_remote_target])
            
            logger.info(f"Comando rsync: {' '.join(rsync_cmd)}")
            logger.info(f"Ejecutando rsync desde {escaped_source} hacia {escaped_remote_target}")
            
            # Ejecutar rsync con captura de progreso
            process = subprocess.Popen(
                rsync_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Monitorear progreso
            stdout_lines = []
            stderr_lines = []
            
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    stdout_lines.append(output.strip())
                    logger.debug(f"rsync output: {output.strip()}")
                    if progress_callback:
                        progress_callback(output.strip())
            
            # Capturar stderr
            stderr = process.stderr.read()
            if stderr:
                stderr_lines.extend(stderr.strip().split('\n'))
                logger.warning(f"rsync stderr: {stderr}")
            
            return_code = process.wait()
            
            if return_code == 0:
                logger.info(f"Rsync completado exitosamente para {download_id}")
                logger.info(f"Archivos transferidos: {len(stdout_lines)}")
                return {
                    'status': 'ssh_complete',
                    'success': True,
                    'remote_path': remote_target_path,
                    'files_copied': len(stdout_lines),
                    'next_action': 'compress_remote'
                }
            else:
                error_msg = '\n'.join(stderr_lines) if stderr_lines else f'Error rsync con código {return_code}'
                logger.error(f"Rsync falló para {download_id}: {error_msg}")
                return {
                    'status': 'error',
                    'success': False,
                    'error': error_msg,
                    'return_code': return_code
                }
                
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout en rsync para {download_id}")
            return {
                'status': 'error',
                'success': False,
                'error': f'Timeout después de {self.timeout} segundos'
            }
        except Exception as e:
            logger.error(f"Error ejecutando rsync para {download_id}: {e}")
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