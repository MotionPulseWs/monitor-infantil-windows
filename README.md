# Monitor de actividad PC — Control Parental (Windows 10/11)

Herramienta de **supervisión parental** para uso propio sobre un dispositivo familiar. Corre en segundo plano en la cuenta estándar de un menor (instalada desde una cuenta de administrador), registra la actividad del día y envía **un correo diario** con un informe legible: qué apps usó y por cuánto tiempo, qué páginas visitó (marcando juegos/contenido adulto), qué archivos descargó y qué borró o si vació la papelera.

> Repositorio **privado**. Es una herramienta de supervisión parental legítima sobre una PC propia/familiar. No contiene ni debe contener credenciales reales ni datos capturados del menor (ver [`.gitignore`](.gitignore) y `docs/monitor_pc_spec.md` §9).

## Estado

En construcción. La especificación completa y las decisiones tomadas están en [`docs/monitor_pc_spec.md`](docs/monitor_pc_spec.md) — es la fuente de verdad. La estructura de módulos ya está montada como esqueleto en [`src/`](src/); la implementación de cada módulo está pendiente (marcada con `TODO` referenciando la sección del spec).

## Estructura

```
monitor-infantil-windows/
├── docs/monitor_pc_spec.md   Especificación técnica y decisiones (fuente de verdad)
├── config.example.ini        Plantilla de configuración (copiar a config.ini, sin subir)
├── requirements.txt          Dependencias de terceros (psutil, watchdog, openpyxl)
├── src/
│   ├── monitor_pc.py         Punto de entrada: bucle en segundo plano
│   ├── config.py             Carga de config.ini
│   ├── state.py              Estado local (SQLite) para sobrevivir reinicios
│   ├── mailer.py             Envío SMTP + consolidación de días pendientes
│   ├── collectors/           Módulos de recolección (procesos, historial, descargas, papelera)
│   ├── report/               Generación de reporte HTML y Excel
│   └── utils/                Utilidades (manejo de tiempo UTC → America/Lima)
└── install/install_task.ps1  Instalador: registra la Tarea Programada (ejecuta como SYSTEM)
```

## Uso (desarrollo)

```powershell
# 1. Crear entorno e instalar dependencias
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Configurar
Copy-Item config.example.ini config.ini   # luego editar config.ini con tus datos SMTP

# 3. Ejecutar en primer plano para probar (con ventana de consola)
python src\monitor_pc.py

# En produccion se ejecuta headless con pythonw.exe via Tarea Programada (ver install/)
```

## Instalación en la PC del menor

Ver [`docs/monitor_pc_spec.md`](docs/monitor_pc_spec.md) §8 y el script [`install/install_task.ps1`](install/install_task.ps1) (ejecutar como administrador). El instalador lista las cuentas locales para elegir la del menor y registra una Tarea Programada que se dispara al iniciar sesión ese usuario pero se ejecuta como `SYSTEM`.
