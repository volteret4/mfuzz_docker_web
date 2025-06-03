#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Notificador de Telegram básico (stub)"""
    
    def __init__(self, bot_token=None, chat_id=None, enabled=False):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled
        
        if not self.enabled:
            logger.info("Notificador de Telegram deshabilitado")
        else:
            logger.info("Notificador de Telegram habilitado")
    
    def send_message(self, message, parse_mode=None):
        """Envía un mensaje por Telegram (stub)"""
        if not self.enabled:
            logger.debug(f"Telegram deshabilitado - Mensaje no enviado: {message}")
            return True
        
        try:
            # Aquí iría la lógica real de envío
            logger.info(f"[TELEGRAM STUB] Mensaje: {message}")
            return True
        except Exception as e:
            logger.error(f"Error enviando mensaje de Telegram: {e}")
            return False
    
    def notify_download_started(self, album_name, artist_name, user_info=None, method='ssh'):
        """Notifica inicio de descarga"""
        method_emoji = "📁" if method == 'local' else "🌐"
        msg = f"{method_emoji} Descarga iniciada ({method.upper()}):\n"
        msg += f"🎵 {artist_name} - {album_name}"
        if user_info:
            msg += f"\n👤 Usuario: {user_info}"
        return self.send_message(msg)
    
    def notify_download_completed(self, album_name, artist_name, file_count, download_path, method='ssh'):
        """Notifica descarga completada"""
        method_emoji = "📁" if method == 'local' else "🌐"
        msg = f"✅ Descarga completada ({method.upper()}):\n"
        msg += f"🎵 {artist_name} - {album_name}\n"
        msg += f"📊 {file_count} archivos\n"
        msg += f"📂 {download_path}"
        return self.send_message(msg)
    
    def notify_download_error(self, album_name, artist_name, error_message):
        """Notifica error en descarga"""
        msg = f"❌ Error en descarga:\n"
        msg += f"🎵 {artist_name} - {album_name}\n"
        msg += f"🚨 {error_message}"
        return self.send_message(msg)
    
    def send_download_notification(self, album_name, artist_name, status, message=None):
        """Envía notificación de descarga (compatibilidad)"""
        if status == 'started':
            return self.notify_download_started(album_name, artist_name)
        elif status == 'completed':
            return self.notify_download_completed(album_name, artist_name, 0, "")
        elif status == 'error':
            return self.notify_download_error(album_name, artist_name, message or '')
        else:
            msg = f"📋 Descarga {status}:\n{artist_name} - {album_name}\n{message or ''}"
            return self.send_message(msg)

    def notify_album_extracted(self, album_name, artist_name, extract_path, file_count):
        """Notifica que un álbum ha sido extraído"""
        if not self.enabled:
            return
        
        try:
            message = f"📁 *Álbum Extraído*\n\n"
            message += f"🎵 *{artist_name}* - *{album_name}*\n"
            message += f"📂 Ubicación: `{extract_path}`\n"
            message += f"📊 Archivos: {file_count}\n"
            message += f"🗑️ ZIP eliminado automáticamente"
            
            self._send_message(message)
            
        except Exception as e:
            logger.error(f"Error enviando notificación de extracción: {e}")

    def notify_file_auto_deleted(self, album_name, artist_name, file_path):
        """Notifica que un archivo ZIP ha sido borrado automáticamente"""
        if not self.enabled:
            return
        
        try:
            message = f"🗑️ *Borrado Automático*\n\n"
            message += f"🎵 *{artist_name}* - *{album_name}*\n"
            message += f"📁 Archivo: `{os.path.basename(file_path)}`\n"
            message += f"⏰ Borrado tras 180 segundos desde la descarga"
            
            self._send_message(message)
            
        except Exception as e:
            logger.error(f"Error enviando notificación de borrado automático: {e}")

    def notify_extraction_error(self, album_name, artist_name, error_msg):
        """Notifica error en extracción"""
        if not self.enabled:
            return
        
        try:
            message = f"❌ *Error en Extracción*\n\n"
            message += f"🎵 *{artist_name}* - *{album_name}*\n"
            message += f"💥 Error: `{error_msg}`"
            
            self._send_message(message)
            
        except Exception as e:
            logger.error(f"Error enviando notificación de error de extracción: {e}")


def create_notifier(config=None):
    """Crea una instancia del notificador"""
    if config is None:
        # Configuración por defecto (deshabilitado)
        return TelegramNotifier(enabled=False)
    
    try:
        # Intentar leer configuración
        bot_token = config.get('telegram', 'bot_token', fallback=None)
        chat_id = config.get('telegram', 'chat_id', fallback=None)
        enabled = config.getboolean('telegram', 'enabled', fallback=False)
        
        return TelegramNotifier(
            bot_token=bot_token,
            chat_id=chat_id,
            enabled=enabled
        )
    except Exception as e:
        logger.error(f"Error creando notificador de Telegram: {e}")
        return TelegramNotifier(enabled=False)