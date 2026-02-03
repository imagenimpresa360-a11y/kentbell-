# 🚀 GUÍA PRÁCTICA DE MIGRACIÓN A VPS PLANETAHOSTING
## Sistema Kent-Bell ERP - Deployment Manual

---

## 📋 PRE-REQUISITOS

### Información Necesaria
- [ ] Credenciales SSH del VPS (IP, usuario, contraseña)
- [ ] Dominio configurado: `erp.imagenyconcepto.cl`
- [ ] Backup de base de datos Railway (URL de conexión)
- [ ] Archivos del proyecto Kent-Bell

### Herramientas Locales
```bash
# En tu PC Windows
- PuTTY o Windows Terminal (SSH)
- WinSCP o FileZilla (transferencia de archivos)
- pgAdmin (gestión PostgreSQL)
```

---

## 🔧 FASE 1: CONFIGURACIÓN INICIAL DEL SERVIDOR

### 1.1 Conectar al VPS por SSH
```bash
# Desde PowerShell o PuTTY
ssh root@201.148.104.39
# Ingresa la contraseña proporcionada por PlanetaHosting
```

### 1.2 Actualizar Sistema Operativo
```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS (si aplica)
sudo yum update -y
```

### 1.3 Crear Usuario de Aplicación
```bash
# Crear usuario 'kentbell' (no usar root para la app)
sudo adduser kentbell
sudo usermod -aG sudo kentbell

# Cambiar a ese usuario
su - kentbell
```

---

## 🐍 FASE 2: INSTALACIÓN DE PYTHON Y DEPENDENCIAS

### 2.1 Instalar Python 3.10+
```bash
# Ubuntu 22.04
sudo apt install python3.10 python3.10-venv python3-pip -y

# Verificar instalación
python3 --version  # Debe mostrar 3.10 o superior
```

### 2.2 Instalar Herramientas de Desarrollo
```bash
sudo apt install build-essential libpq-dev python3-dev -y
```

---

## 🗄️ FASE 3: INSTALACIÓN Y CONFIGURACIÓN DE POSTGRESQL

### 3.1 Instalar PostgreSQL
```bash
sudo apt install postgresql postgresql-contrib -y

# Iniciar servicio
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Verificar estado
sudo systemctl status postgresql
```

### 3.2 Configurar Base de Datos
```bash
# Acceder a PostgreSQL
sudo -u postgres psql

# Dentro de psql, ejecutar:
CREATE DATABASE crossfit_control;
CREATE USER postgres WITH PASSWORD 'Imagen30';
ALTER USER postgres WITH SUPERUSER;
GRANT ALL PRIVILEGES ON DATABASE crossfit_control TO postgres;

# Salir
\q
```

### 3.3 Configurar Acceso Remoto (Opcional)
```bash
# Editar postgresql.conf
sudo nano /etc/postgresql/14/main/postgresql.conf

# Cambiar:
listen_addresses = 'localhost'  # Por:
listen_addresses = '*'

# Editar pg_hba.conf
sudo nano /etc/postgresql/14/main/pg_hba.conf

# Agregar al final:
host    all             all             0.0.0.0/0               md5

# Reiniciar PostgreSQL
sudo systemctl restart postgresql
```

---

## 📦 FASE 4: DESPLIEGUE DE LA APLICACIÓN

### 4.1 Crear Estructura de Directorios
```bash
# Como usuario kentbell
cd /home/kentbell
mkdir -p kent-bell/{logs,backups}
cd kent-bell
```

### 4.2 Transferir Archivos desde tu PC
```bash
# Opción A: Usando SCP desde tu PC Windows (PowerShell)
scp -r "C:\Users\DELL\Desktop\Agente kent-bell\*" kentbell@201.148.104.39:/home/kentbell/kent-bell/

# Opción B: Usando Git (si tienes repositorio)
git clone https://github.com/tu-usuario/kent-bell.git .
```

### 4.3 Crear Entorno Virtual
```bash
cd /home/kentbell/kent-bell
python3 -m venv venv
source venv/bin/activate

# Verificar que estás en el venv
which python  # Debe mostrar /home/kentbell/kent-bell/venv/bin/python
```

### 4.4 Instalar Dependencias
```bash
pip install --upgrade pip
pip install -r requirements.txt

# Verificar instalación
pip list
```

### 4.5 Configurar Variables de Entorno
```bash
nano .env
```

**Contenido del archivo `.env`:**
```env
# Base de Datos (LOCAL)
DB_NAME=crossfit_control
DB_USER=postgres
DB_PASS=Imagen30
DB_HOST=localhost
DB_PORT=5432

# BoxMagic
BOXMAGIC_URL=https://auth.boxmagic.cl/
BOXMAGIC_USER=contactoboosbox@gmail.com
BOXMAGIC_PASS="#Campa2024"

# VirtualPOS
VIRTUALPOS_URL=https://www.virtualpos.cl
VIRTUALPOS_USER=contactoboosbox@gmail.com
VIRTUALPOS_PASS=Imagen12

# Gmail
GMAIL_USER=contactoboosbox@gmail.com
GMAIL_PASS=nfqv qhhg cajm tttj

# Lioren
LIOREN_URL=https://lioren.io/
LIOREN_USER=contactoboosbox@gmail.com
LIOREN_PASS=#Imagen2022

# Aplicación
APP_USER=admin
APP_PASS=Imagen2026
```

---

## 🔄 FASE 5: MIGRACIÓN DE DATOS DESDE RAILWAY

### 5.1 Exportar Base de Datos de Railway
```bash
# Desde tu PC Windows (PowerShell)
# Reemplaza con tu URL real de Railway
$RAILWAY_URL = "postgresql://usuario:password@host.railway.app:5432/railway"

# Exportar datos
pg_dump $RAILWAY_URL > backup_railway.sql

# Transferir al VPS
scp backup_railway.sql kentbell@201.148.104.39:/home/kentbell/kent-bell/backups/
```

### 5.2 Importar Datos al VPS
```bash
# En el VPS
cd /home/kentbell/kent-bell/backups
psql -U postgres -d crossfit_control -f backup_railway.sql

# Verificar importación
psql -U postgres -d crossfit_control -c "SELECT COUNT(*) FROM raw_boxmagic;"
```

---

## 🌐 FASE 6: CONFIGURACIÓN DE NGINX (REVERSE PROXY)

### 6.1 Instalar Nginx
```bash
sudo apt install nginx -y
sudo systemctl start nginx
sudo systemctl enable nginx
```

### 6.2 Configurar Sitio
```bash
sudo nano /etc/nginx/sites-available/kentbell
```

**Contenido del archivo:**
```nginx
server {
    listen 80;
    server_name erp.imagenyconcepto.cl;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_read_timeout 86400;
    }
}
```

### 6.3 Activar Sitio
```bash
sudo ln -s /etc/nginx/sites-available/kentbell /etc/nginx/sites-enabled/
sudo nginx -t  # Verificar configuración
sudo systemctl reload nginx
```

---

## 🔒 FASE 7: CONFIGURACIÓN DE SSL (HTTPS)

### 7.1 Instalar Certbot
```bash
sudo apt install certbot python3-certbot-nginx -y
```

### 7.2 Obtener Certificado SSL
```bash
sudo certbot --nginx -d erp.imagenyconcepto.cl

# Seguir las instrucciones:
# - Ingresar email: contactoboosbox@gmail.com
# - Aceptar términos: Yes
# - Redirigir HTTP a HTTPS: Yes (opción 2)
```

### 7.3 Renovación Automática
```bash
# Certbot ya configura auto-renovación, verificar:
sudo systemctl status certbot.timer

# Probar renovación manual
sudo certbot renew --dry-run
```

---

## ⚙️ FASE 8: CONFIGURACIÓN DE SYSTEMD (AUTO-INICIO)

### 8.1 Crear Servicio Systemd
```bash
sudo nano /etc/systemd/system/kentbell.service
```

**Contenido del archivo:**
```ini
[Unit]
Description=Kent Bell ERP - Streamlit Application
After=network.target postgresql.service

[Service]
Type=simple
User=kentbell
WorkingDirectory=/home/kentbell/kent-bell
Environment="PATH=/home/kentbell/kent-bell/venv/bin"
ExecStart=/home/kentbell/kent-bell/venv/bin/streamlit run app.py --server.port=8501 --server.address=localhost --server.headless=true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 8.2 Activar y Arrancar Servicio
```bash
sudo systemctl daemon-reload
sudo systemctl enable kentbell.service
sudo systemctl start kentbell.service

# Verificar estado
sudo systemctl status kentbell.service

# Ver logs en tiempo real
sudo journalctl -u kentbell.service -f
```

---

## 🔥 FASE 9: CONFIGURACIÓN DE FIREWALL

### 9.1 Configurar UFW
```bash
# Instalar UFW (si no está)
sudo apt install ufw -y

# Configurar reglas
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS

# Activar firewall
sudo ufw enable

# Verificar estado
sudo ufw status verbose
```

---

## 📊 FASE 10: VERIFICACIÓN Y PRUEBAS

### 10.1 Verificar Servicios
```bash
# PostgreSQL
sudo systemctl status postgresql

# Nginx
sudo systemctl status nginx

# Kent Bell App
sudo systemctl status kentbell

# Ver logs de la aplicación
tail -f /home/kentbell/kent-bell/logs/app.log
```

### 10.2 Probar Conectividad
```bash
# Desde el servidor
curl http://localhost:8501

# Desde tu PC (navegador)
https://erp.imagenyconcepto.cl
```

### 10.3 Verificar Base de Datos
```bash
psql -U postgres -d crossfit_control

# Dentro de psql:
\dt  # Listar tablas
SELECT COUNT(*) FROM raw_boxmagic;
SELECT COUNT(*) FROM expense_ledger;
\q
```

---

## 🔄 FASE 11: CONFIGURACIÓN DE BACKUPS AUTOMÁTICOS

### 11.1 Crear Script de Backup
```bash
nano /home/kentbell/kent-bell/scripts/backup_db.sh
```

**Contenido:**
```bash
#!/bin/bash
BACKUP_DIR="/home/kentbell/kent-bell/backups"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="crossfit_backup_$DATE.sql"

# Crear backup
pg_dump -U postgres crossfit_control > "$BACKUP_DIR/$FILENAME"

# Comprimir
gzip "$BACKUP_DIR/$FILENAME"

# Eliminar backups antiguos (más de 30 días)
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup completado: $FILENAME.gz"
```

### 11.2 Dar Permisos de Ejecución
```bash
chmod +x /home/kentbell/kent-bell/scripts/backup_db.sh
```

### 11.3 Configurar Cron (Backup Diario a las 2 AM)
```bash
crontab -e

# Agregar línea:
0 2 * * * /home/kentbell/kent-bell/scripts/backup_db.sh >> /home/kentbell/kent-bell/logs/backup.log 2>&1
```

---

## 🎯 COMANDOS ÚTILES DE ADMINISTRACIÓN

### Reiniciar Aplicación
```bash
sudo systemctl restart kentbell
```

### Ver Logs en Tiempo Real
```bash
sudo journalctl -u kentbell -f
```

### Actualizar Código
```bash
cd /home/kentbell/kent-bell
source venv/bin/activate
git pull origin main  # Si usas Git
sudo systemctl restart kentbell
```

### Restaurar Backup
```bash
cd /home/kentbell/kent-bell/backups
gunzip crossfit_backup_YYYYMMDD_HHMMSS.sql.gz
psql -U postgres -d crossfit_control < crossfit_backup_YYYYMMDD_HHMMSS.sql
```

### Monitorear Recursos
```bash
# CPU y RAM
htop

# Espacio en disco
df -h

# Conexiones PostgreSQL
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"
```

---

## 🚨 TROUBLESHOOTING

### Problema: Aplicación no inicia
```bash
# Ver logs detallados
sudo journalctl -u kentbell -n 100 --no-pager

# Verificar puerto 8501
sudo netstat -tulpn | grep 8501

# Probar manualmente
cd /home/kentbell/kent-bell
source venv/bin/activate
streamlit run app.py
```

### Problema: Error de conexión a PostgreSQL
```bash
# Verificar servicio
sudo systemctl status postgresql

# Probar conexión
psql -U postgres -d crossfit_control -h localhost

# Revisar logs de PostgreSQL
sudo tail -f /var/log/postgresql/postgresql-14-main.log
```

### Problema: SSL no funciona
```bash
# Renovar certificado
sudo certbot renew --force-renewal

# Verificar configuración Nginx
sudo nginx -t
sudo systemctl restart nginx
```

---

## 📞 CONTACTOS DE SOPORTE

- **PlanetaHosting:** https://planetahosting.cl/soporte
- **Teléfono:** +56 2 XXXX XXXX (verificar en panel de cliente)
- **Email:** soporte@planetahosting.cl

---

## ✅ CHECKLIST FINAL

- [ ] VPS contratado y accesible por SSH
- [ ] Python 3.10+ instalado
- [ ] PostgreSQL configurado y funcionando
- [ ] Base de datos migrada desde Railway
- [ ] Aplicación corriendo en puerto 8501
- [ ] Nginx configurado como reverse proxy
- [ ] SSL/HTTPS funcionando
- [ ] Servicio systemd activo y habilitado
- [ ] Firewall configurado
- [ ] Backups automáticos programados
- [ ] Dominio apuntando al VPS
- [ ] Pruebas de todos los módulos exitosas

---

**¡MIGRACIÓN COMPLETA!** 🎉

Tu sistema Kent-Bell ahora está corriendo en infraestructura local chilena con control total.

**Próximos pasos:**
1. Monitorear logs durante 48 horas
2. Validar performance con usuarios reales
3. Documentar credenciales en lugar seguro
4. Cancelar Railway (después de 1 mes de prueba)

---

**Elaborado por:** Antigravity AI  
**Fecha:** 2 de Febrero de 2026  
**Versión:** 1.0
