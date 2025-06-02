class ImageManager:
    def __init__(self):
        self.project_root = Path.cwd()
        self.images_dir = self.project_root / 'container_images'
        self.docker_compose_file = self.project_root / 'docker-compose.yml'
        
    def check_dependencies(self):
        """Verificar dependencias necesarias"""
        print("🔍 Verificando dependencias...")
        
        # Verificar archivos necesarios
        required_files = [
            'extract_images.py',
            'config.ini',
            'app.py',
            'docker-compose.yml'
        ]
        
        missing_files = []
        for file in required_files:
            if not (self.project_root / file).exists():
                missing_files.append(file)
        
        if missing_files:
            print(f"❌ Archivos faltantes: {', '.join(missing_files)}")
            return False
        
        # Verificar docker y docker-compose
        try:
            subprocess.run(['docker', '--version'], capture_output=True, check=True)
            subprocess.run(['docker-compose', '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Docker o docker-compose no están disponibles")
            return False
        
        print("✅ Todas las dependencias están disponibles")
        return True
    
    def extract_images(self, force=False):
        """Extraer imágenes de la base de datos usando el extractor real"""
        print("📷 Extrayendo imágenes...")
        
        if self.images_dir.exists() and not force:
            print(f"⚠️  El directorio {self.images_dir} ya existe")
            response = input("¿Quieres sobrescribirlo? (y/N): ")
            if response.lower() != 'y':
                print("❌ Extracción cancelada")
                return False
            
            shutil.rmtree(self.images_dir)
        
        try:
            # Importar el extractor real
            from extract_images import ImageExtractor
            
            # Leer configuración para obtener rutas
            config = configparser.ConfigParser()
            config.read('config.ini')
            
            db_path = config.get('database', 'path')
            mounted_paths_str = config.get('music', 'mounted_paths', fallback='')
            mounted_paths = [path.strip() for path in mounted_paths_str.split(',') if path.strip()]
            
            # Crear extractor y ejecutar
            extractor = ImageExtractor(db_path, mounted_paths)
            success = extractor.extract_all_images(str(self.images_dir))
            
            if not success:
                print("❌ Error en el proceso de extracción")
                return False
            
            # Verificar resultados
            if not self.images_dir.exists():
                print("❌ No se creó el directorio de imágenes")
                return False
            
            # Contar archivos
            image_files = list(self.images_dir.rglob('*.jpg')) + \
                        list(self.images_dir.rglob('*.jpeg')) + \
                        list(self.images_dir.rglob('*.png'))
            
            total_size = sum(f.stat().st_size for f in self.images_dir.rglob('*') if f.is_file())
            size_mb = total_size / (1024 * 1024)
            
            print(f"✅ Extracción completada:")
            print(f"   📊 {len(image_files)} imágenes extraídas")
            print(f"   💾 Tamaño total: {size_mb:.1f} MB")
            
            return True
            
        except Exception as e:
            print(f"❌ Error durante extracción: {e}")
            return False
    
    def build_container(self):
        """Construir contenedor Docker"""
        print("🐳 Construyendo contenedor...")
        
        try:
            # Parar contenedor si está corriendo
            subprocess.run(['docker-compose', 'down'], capture_output=True)
            
            # Build
            result = subprocess.run(
                ['docker-compose', 'build', '--no-cache'], 
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                print(f"❌ Error en build: {result.stderr}")
                return False
            
            print("✅ Contenedor construido exitosamente")
            return True
            
        except Exception as e:
            print(f"❌ Error durante build: {e}")
            return False
    
    def deploy_container(self):
        """Desplegar contenedor"""
        print("🚀 Desplegando contenedor...")
        
        try:
            # Crear directorios persistentes
            persistent_dirs = [
                Path.home() / 'contenedores' / 'mfuzz' / 'logs',
                Path.home() / 'contenedores' / 'mfuzz' / 'images'
            ]
            
            for dir_path in persistent_dirs:
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"📁 Directorio creado: {dir_path}")
            
            # Iniciar contenedor
            result = subprocess.run(
                ['docker-compose', 'up', '-d'], 
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                print(f"❌ Error en deploy: {result.stderr}")
                return False
            
            # Esperar a que esté listo
            print("⏳ Esperando a que el contenedor esté listo...")
            time.sleep(15)
            
            # Verificar estado
            result = subprocess.run(
                ['docker-compose', 'ps'], 
                capture_output=True, text=True
            )
            
            if 'Up' in result.stdout:
                print("✅ Contenedor desplegado exitosamente")
                print("🌐 Acceso web: http://localhost:8447")
                print("🔌 API directa: http://localhost:5157")
                return True
            else:
                print("❌ El contenedor no está corriendo correctamente")
                print("📋 Logs:")
                subprocess.run(['docker-compose', 'logs', '--tail=20'])
                return False
                
        except Exception as e:
            print(f"❌ Error durante deploy: {e}")
            return False
    
    def show_status(self):
        """Mostrar estado actual con información detallada"""
        print("📊 Estado actual:")
        print("=" * 40)
        
        # Verificar extracción de imágenes
        if self.images_dir.exists():
            # Contar archivos por tipo
            artists_dir = self.images_dir / 'artists'
            albums_dir = self.images_dir / 'albums'
            
            artist_images = list(artists_dir.glob('*')) if artists_dir.exists() else []
            album_images = list(albums_dir.glob('*')) if albums_dir.exists() else []
            
            total_size = sum(f.stat().st_size for f in self.images_dir.rglob('*') if f.is_file())
            size_mb = total_size / (1024 * 1024)
            
            print(f"📷 Imágenes extraídas:")
            print(f"   🎤 Artistas: {len([f for f in artist_images if f.is_file()])} imágenes")
            print(f"   💿 Álbumes: {len([f for f in album_images if f.is_file()])} imágenes")
            print(f"   💾 Tamaño total: {size_mb:.1f} MB")
            
            # Verificar índice maestro
            master_index = self.images_dir / 'master_index.json'
            if master_index.exists():
                try:
                    with open(master_index) as f:
                        index_data = json.load(f)
                    artists_count = len(index_data.get('artists', {}))
                    albums_count = len(index_data.get('albums', {}))
                    print(f"📋 Índice maestro: ✅ {artists_count} artistas, {albums_count} álbumes indexados")
                except Exception:
                    print("📋 Índice maestro: ⚠️ Existe pero no se puede leer")
            else:
                print("📋 Índice maestro: ❌ No encontrado")
        else:
            print("📷 Imágenes: ❌ No extraídas")
            print("   💡 Ejecuta: python manage_images.py extract")
        
        # Verificar contenedor
        try:
            result = subprocess.run(
                ['docker-compose', 'ps'], 
                capture_output=True, text=True
            )
            
            if 'Up' in result.stdout:
                print("🐳 Contenedor: ✅ Corriendo")
                print("   🌐 Web UI: http://localhost:8447")
                print("   🔌 API directa: http://localhost:5157")
            else:
                print("🐳 Contenedor: ❌ No está corriendo")
                print("   💡 Ejecuta: python manage_images.py deploy")
                
        except Exception:
            print("🐳 Contenedor: ❌ Error verificando estado")
            print("   💡 Verifica que Docker esté instalado y funcionando")
    
    def clean(self, full=False):
        """Limpiar archivos temporales"""
        print("🧹 Limpiando...")
        
        # Limpiar imágenes extraídas
        if self.images_dir.exists():
            shutil.rmtree(self.images_dir)
            print(f"🗑️  Eliminado: {self.images_dir}")
        
        if full:
            # Parar y eliminar contenedor
            subprocess.run(['docker-compose', 'down'], capture_output=True)
            
            # Eliminar imagen Docker
            subprocess.run(['docker', 'rmi', 'mfuzz_docker_web_music-web-explorer'], 
                          capture_output=True)
            
            print("🗑️  Contenedor y imagen Docker eliminados")
        
        print("✅ Limpieza completada")