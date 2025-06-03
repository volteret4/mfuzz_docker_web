#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import yaml
import logging
from flask import Flask, render_template, request, jsonify, send_file, redirect
from werkzeug.exceptions import NotFound
import configparser


# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Importar módulos locales
try:
    from db_manager import DatabaseManager
    from apis_endpoints import APIEndpoints
    from img_manager import ImageManager
    from telegram_notifier import create_notifier
    from template_routes import TemplateRoutes
    from album_analysis_endpoint import AlbumAnalysisEndpoints
    from scrobbles_analysis_endpoint import ScrobblesAnalysisEndpoints
except ImportError as e:
    logger.error(f"Error importando módulos: {e}")
    raise



class MusicWebExplorer:
    """Aplicación principal de Music Web Explorer"""
    
    def __init__(self, config_path='config.yml'):
        self.app = Flask(__name__)
        self.config = self.load_config(config_path)
        self.setup_logging()
        
        # Inicializar componentes
        self.db_manager = DatabaseManager(self.config)
        self.img_manager = ImageManager(self.config)
        self.telegram_notifier = self.create_telegram_notifier()
        self.template_routes = TemplateRoutes(self.app, self.config)
        self.album_analysis_endpoints = AlbumAnalysisEndpoints(
            self.app, 
            self.db_manager, 
            self.config
        )
        self.scrobbles_endpoints = ScrobblesAnalysisEndpoints(self.app, self.db_manager, self.config)

        # Configurar rutas
        self.setup_routes()
        
        # Inicializar API endpoints
        self.api_endpoints = APIEndpoints(
            self.app, 
            self.db_manager, 
            self.img_manager,
            self.telegram_notifier,
            self.config
        )
        
        logger.info("Music Web Explorer inicializado correctamente")
    
    def load_config(self, config_path):
        """Carga la configuración desde archivo YAML"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            # Sobrescribir con variables de entorno si existen
            telegram_config = config.get('telegram', {})
            telegram_config['enabled'] = os.getenv('TELEGRAM_ENABLED', 'false').lower() == 'true'
            telegram_config['bot_token'] = os.getenv('TELEGRAM_BOT_TOKEN', telegram_config.get('bot_token', ''))
            telegram_config['chat_id'] = os.getenv('TELEGRAM_CHAT_ID', telegram_config.get('chat_id', ''))
            
            logger.info(f"Configuración cargada desde {config_path}")
            return config
            
        except Exception as e:
            logger.error(f"Error cargando configuración: {e}")
            # Configuración por defecto
            return {
                'app': {'host': '0.0.0.0', 'port': 5157, 'debug': False},
                'database': {'path': '/app/data/musica.sqlite'},
                'paths': {
                    'music_root': '/mnt/NFS/moode/moode',
                    'downloads': '/downloads',
                    'images': '/app/images'
                },
                'telegram': {'enabled': False}
            }
    
    def setup_logging(self):
        """Configura el sistema de logging"""
        log_config = self.config.get('logging', {})
        log_level = getattr(logging, log_config.get('level', 'INFO'))
        
        # Configurar handler para archivo si está especificado
        log_file = log_config.get('file')
        if log_file:
            try:
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                file_handler.setLevel(log_level)
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                file_handler.setFormatter(formatter)
                logging.getLogger().addHandler(file_handler)
            except Exception as e:
                logger.warning(f"No se pudo configurar logging a archivo: {e}")
    
    def create_telegram_notifier(self):
        """Crea el notificador de Telegram"""
        try:
            # Crear un objeto config-like para compatibilidad
            class ConfigLike:
                def __init__(self, config_dict):
                    self.config = config_dict
                
                def get(self, section, key, fallback=None):
                    return self.config.get(section, {}).get(key, fallback)
                
                def getboolean(self, section, key, fallback=False):
                    value = self.get(section, key, fallback)
                    if isinstance(value, bool):
                        return value
                    return str(value).lower() in ('true', '1', 'yes', 'on')
            
            config_obj = ConfigLike(self.config)
            return create_notifier(config_obj)
            
        except Exception as e:
            logger.error(f"Error creando notificador de Telegram: {e}")
            return create_notifier(None)  # Notificador deshabilitado
    
    def setup_routes(self):
        """Configura las rutas principales de la aplicación"""
        
        @self.app.route('/')
        def index():
            """Página principal"""
            return render_template('index.html', config=self.config)
        
        @self.app.route('/health')
        @self.app.route('/health.html')
        def health():
            """Endpoint de salud para healthcheck"""
            try:
                # Verificar componentes críticos
                db_status = self.db_manager.test_connection()
                
                # Información del modo de descarga (si API endpoints está disponible)
                download_info = {}
                try:
                    if hasattr(self, 'api_endpoints') and hasattr(self.api_endpoints, 'download_manager'):
                        download_manager = self.api_endpoints.download_manager
                        download_info = {
                            'mode': download_manager.get_download_mode(),
                            'ssh_enabled': download_manager.is_ssh_mode(),
                            'ssh_host': download_manager.ssh_host if download_manager.is_ssh_mode() else None
                        }
                except:
                    download_info = {'mode': 'unknown', 'error': 'DownloadManager not available'}
                
                return jsonify({
                    'status': 'healthy',
                    'database': 'connected' if db_status else 'disconnected',
                    'version': self.config.get('app', {}).get('version', '1.0.0'),
                    'download_manager': download_info
                })
            except Exception as e:
                logger.error(f"Error en healthcheck: {e}")
                return jsonify({'status': 'unhealthy', 'error': str(e)}), 500
        
        @self.app.route('/static/health.html')
        def static_health():
            """Healthcheck estático para nginx"""
            return '<html><body>OK</body></html>'
        
        @self.app.errorhandler(404)
        def not_found(error):
            """Manejador de errores 404"""
            return render_template('error.html', 
                                 error_code=404, 
                                 error_message="Página no encontrada"), 404
        
        @self.app.errorhandler(500)
        def internal_error(error):
            """Manejador de errores 500"""
            logger.error(f"Error interno del servidor: {error}")
            return render_template('error.html', 
                                 error_code=500, 
                                 error_message="Error interno del servidor"), 500
    
    def run(self):
        """Ejecuta la aplicación"""
        app_config = self.config.get('app', {})
        host = app_config.get('host', '0.0.0.0')
        port = app_config.get('port', 5157)
        debug = app_config.get('debug', False)
        
        logger.info(f"Iniciando servidor en {host}:{port} (debug={debug})")
        
        self.app.run(
            host=host,
            port=port,
            debug=debug,
            threaded=True
        )

def create_app():
    """Factory function para crear la aplicación"""
    return MusicWebExplorer().app

if __name__ == '__main__':
    try:
        app_instance = MusicWebExplorer()
        app_instance.run()
    except KeyboardInterrupt:
        logger.info("Aplicación terminada por el usuario")
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        raise