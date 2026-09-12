# Especificación técnica: Monitor de actividad PC (Control Parental)

Este documento amplía el diseño que ya habíamos definido antes (informe diario por correo, chequeo cada 30 min, SMTP genérico) para cubrir los nuevos requisitos: categorización de sitios visitados, historial de descargas, y seguimiento de la papelera de reciclaje. Está pensado para pegarlo directamente en Claude Code (sección 11 trae la versión resumida en forma de prompt).

## 1. Objetivo

Script en Python que corre en segundo plano en la PC del menor (Windows 10 y 11), registra su actividad a lo largo del día, y envía **un correo diario** con un informe legible (tabla HTML y/o adjunto Excel) que permita verificar: qué apps usó, qué páginas visitó (marcando juegos/contenido para adultos), qué archivos descargó, y qué archivos borró o si vació la papelera.

## 2. Alcance y compatibilidad

- Windows 10 y Windows 11 (misma base de código; las rutas de `$Recycle.Bin` y las bases de datos de historial de navegador son compatibles en ambas versiones).
- Se instala desde la cuenta de administrador, pero la actividad que registra es la de la cuenta estándar del menor (leer el historial/papelera de ese perfil no requiere privilegios especiales una vez identificado el usuario correcto).
- Un solo script (o un paquete pequeño de módulos) que se ejecuta continuamente mientras hay sesión iniciada.

## 3. Módulos de recolección de datos

### 3.1 Procesos (ya definido)
- Poll periódico con `psutil` para detectar procesos que se abren/cierran, con marca de tiempo.

**3.1.1 Tiempo total por aplicación (nuevo).** Con el par apertura/cierre de cada proceso, calcular y mostrar en el reporte diario el **tiempo acumulado por aplicación** (ej. "Word: 1h 40min", "Chrome/YouTube: 2h 15min", "Roblox: 3h 05min"). Esto responde directamente a la necesidad de saber cuánto tiempo se usó cada cosa en el día, no solo la lista cruda de eventos.

### 3.2 Navegación web y categorización de dominios
- Leer el historial de los navegadores basados en Chromium (Chrome, Edge — ambos usan el mismo esquema SQLite en `%LOCALAPPDATA%\...\User Data\Default\History`) y, si aplica, Firefox (`places.sqlite`).
- **Importante:** el archivo de historial suele estar bloqueado mientras el navegador está abierto → copiar a un archivo temporal antes de abrir con `sqlite3` (patrón estándar para este problema).
- Extraer: URL, título, fecha/hora de visita.
- Categorizar cada dominio en: `juegos`, `adulto/pornografía`, `dudoso/otros`, `normal`. **Decisión: no se va a curar una lista propia de dominios.** Claude Code debe usar listas públicas de referencia ya existentes (por ejemplo hostlists de categorización de contenido tipo StevenBlack/OISD para adultos, y listas de dominios de juegos conocidos) e implementar la heurística de palabras clave como respaldo para lo que no esté en la lista.
- En el reporte, cada visita marcada debe mostrarse con un **badge/etiqueta tipo "pill"** (una insignia redondeada, como las de estado en apps modernas) indicando por ejemplo "⚠️ dominio de juegos" o "🔞 dominio para adultos", en vez de solo resaltar la fila. El resto del historial se muestra normal, sin badge.

### 3.3 Descargas de archivos (nuevo)
- Los navegadores Chromium guardan una tabla `downloads` dentro del mismo archivo `History` (no es un archivo aparte), con: nombre de archivo, ruta destino, URL de origen, tamaño, hora de inicio/fin, y estado (completo/cancelado/interrumpido). Esto es clave para el caso del PDF: permite comprobar objetivamente si una descarga ocurrió o no, sin depender de lo que diga el navegador "a simple vista".
- Firefox guarda algo equivalente en `places.sqlite` (tabla `moz_annos` / `downloads`, según versión).
- Como respaldo adicional (para capturar archivos que lleguen por otra vía, no solo navegador), monitorear en tiempo real con `watchdog` las carpetas típicas: `Descargas`, `Escritorio`, `Documentos`.
- Marcar con una alerta visual en el reporte cualquier archivo con extensión `.apk`, `.exe` o `.zip` que no sea de un dominio conocido/confiable, ya que puede ser un intento de instalar algo que vulnere los filtros ya puestos.

### 3.4 Papelera de reciclaje — archivos eliminados (nuevo)
- En Windows, cada archivo enviado a la papelera genera un par de archivos ocultos dentro de `C:\$Recycle.Bin\<SID-del-usuario>\`: uno `$I......` (metadatos: ruta original, tamaño, fecha/hora de eliminación en formato FILETIME de Windows) y otro `$R......` (el contenido real).
- El script debe monitorear esa carpeta (con `watchdog`, o poll cada pocos minutos) y, al detectar un nuevo `$I*`, parsear su cabecera binaria para extraer: nombre y ruta original, tamaño, y fecha/hora exacta de eliminación. El formato de estos archivos es público y bien documentado; hay parsers de referencia disponibles que Claude Code puede adaptar.
- Registrar cada eliminación como una fila del reporte.

### 3.5 Papelera de reciclaje — evento de vaciado (nuevo)
- Detectar cuándo se vació la papelera es distinto a detectar eliminaciones individuales: ocurre cuando varios pares `$I`/`$R` desaparecen juntos.
- Enfoque recomendado: mantener en memoria (o en un pequeño estado persistente en disco) el conjunto de archivos `$I*` conocidos en cada carpeta de papelera vigilada. Si en una misma ventana corta de tiempo desaparecen varios de golpe (por ejemplo, ≥2 en menos de 2 segundos, o el conteo total pasa de N>0 a 0 sin haber un evento de "restaurar" individual previo), se registra como **"papelera vaciada"** con la fecha/hora en que se detectó el vaciado.
- Con `watchdog` esto se puede detectar casi en tiempo real (evento `on_deleted` disparado para varios archivos casi simultáneamente); con poll periódico, la precisión queda limitada al intervalo de chequeo (por eso se recomienda watchdog para este módulo en particular).

## 4. Zona horaria

- Internamente, guardar todas las marcas de tiempo en **UTC** (evita ambigüedades si la PC cambia de reloj o de zona).
- Al generar el reporte, convertir a **America/Lima (UTC-5, sin horario de verano, fijo todo el año)** para que las horas mostradas sean las reales de Lima. Usar `zoneinfo` (Python 3.9+, incluido en Windows sin dependencias extra) con `ZoneInfo("America/Lima")`.

## 5. Formato y contenido del reporte

- Reporte en **HTML con tablas** (una tabla por módulo: procesos, navegación categorizada, descargas, papelera-eliminados, papelera-vaciado), enviado como cuerpo del correo (fácil de leer desde el celular, sin depender de abrir un adjunto).
- Opcionalmente, adjuntar también un **Excel (.xlsx)** generado con `openpyxl` (una hoja por módulo) como respaldo/archivo histórico descargable.
- Resaltar visualmente (por ejemplo fondo rojo/naranja) las filas de: contenido para adultos, dominios de juegos no permitidos, archivos `.apk`/`.exe` sospechosos, y el evento de "papelera vaciada".

## 6. Lógica de envío de correo

- Un correo al día (resumen del día), no por hora. **Por ahora no hay alertas inmediatas** (ni por descargas sospechosas ni por contenido para adultos): todo va en el resumen diario. Se puede agregar una alerta inmediata más adelante si aparece un caso que lo amerite — dejar el código organizado para que sea fácil añadir ese modo después sin rediseñar todo.
- SMTP genérico que el usuario configura manualmente (host, puerto, usuario, contraseña/app-password) en un archivo de configuración aparte (no hardcodeado en el script).
- Si la PC estuvo apagada varios días y quedaron reportes pendientes, combinarlos en **un solo correo** con secciones por fecha, no uno por día.

## 7. Frecuencia de ejecución / arquitectura del script

- Mientras la PC está encendida y con sesión iniciada: el proceso corre en segundo plano, revisando procesos y actividad continuamente (o cada pocos minutos para lo liviano), y cada **30 minutos** revisa si ya toca enviar/consolidar el reporte del día.
- Guardar el estado del día (eventos capturados) en un archivo local (SQLite o JSON) para poder reconstruir el correo si el script se reinicia a medias.

## 8. Instalación en Windows (Task Scheduler) — Windows 10 y 11

El mecanismo de Programador de Tareas es idéntico en Windows 10 y 11, así que un solo procedimiento sirve para ambos. Contexto confirmado: la cuenta del menor ya es una **cuenta estándar** (no administrador), y la instalación se hace desde la cuenta de administrador.

1. Empaquetar el script para que corra sin ventana de consola visible, usando `pythonw.exe` en vez de `python.exe` (o compilarlo con PyInstaller si se quiere evitar depender de que Python esté instalado en esa PC).
2. **Detección del usuario del menor durante la instalación:** el instalador (script `.ps1`, ejecutado como administrador) debe listar los perfiles locales disponibles y dejar que el admin elija cuál es el del menor, por ejemplo:

```powershell
Get-LocalUser | Where-Object { $_.Enabled -eq $true } | Select-Object Name, SID
```

   El nombre elegido se usa para dos cosas: (a) armar el *trigger* "al iniciar sesión de ese usuario específico", y (b) construir las rutas de `%LOCALAPPDATA%` / `$Recycle.Bin\<SID>` de ese usuario, ya que el proceso puede terminar corriendo con otro contexto de ejecución (ver punto 3).

3. **Crear la tarea para que sea difícil de detener desde la cuenta del menor:** en vez de que la tarea corra con los privilegios del propio usuario que inicia sesión, conviene que el *trigger* sea "al iniciar sesión del menor" pero la *ejecución* corra como `SYSTEM` (con privilegios más altos que la cuenta estándar del menor, que no puede ni ver el detalle ni deshabilitar tareas que corren como SYSTEM):

```powershell
$action = New-ScheduledTaskAction -Execute "pythonw.exe" -Argument '"C:\Ruta\monitor_pc.py"'
$trigger = New-ScheduledTaskTrigger -AtLogOn -User "NOMBRE-PC\usuario_menor"
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -Hidden
Register-ScheduledTask -TaskName "WindowsSystemHelper" -Action $action -Trigger $trigger -Principal $principal -Settings $settings
```

   Nota: usar un nombre de tarea neutro (no "MonitorPC") reduce que llame la atención si el menor llega a abrir el Programador de Tareas.

4. Alternativa por interfaz gráfica (si se prefiere no usar PowerShell): Programador de tareas → Crear tarea → "Ejecutar tanto si el usuario inició sesión como si no" + "Ejecutar con los privilegios más altos" → pestaña "Desencadenadores" → "Al iniciar sesión" → "Usuario específico" (elegir la cuenta del menor) → pestaña "Acciones" → ejecutar `pythonw.exe` con el script como argumento → en "Configuración" marcar "Ejecutar la tarea tan pronto como sea posible después de una hora de inicio programada perdida" (por si la PC estuvo apagada).

## 9. Documentación en repositorio Git privado

Quieres dejar registro del proyecto en Git, pero como es una herramienta que técnicamente podría usarse mal fuera de este contexto (control parental legítimo sobre una PC propia), conviene manejarlo con cuidado:

- Repositorio **privado** desde el inicio (GitHub/GitLab privado, en tu cuenta), nunca público.
- Estructura sugerida: `README.md` (qué hace el proyecto, para qué se instaló, en qué PC/perfil), `docs/` (esta especificación y decisiones tomadas), `src/` (código), `config.example.ini` (plantilla de configuración SIN credenciales reales).
- **Nunca subir al repo:** credenciales SMTP reales, el archivo de configuración real (`config.ini`), ni los datos capturados (logs, historial, reportes generados) — eso son datos del menor y de la PC, no código. Usa un `.gitignore` que excluya `config.ini`, `*.log`, la carpeta de reportes y cualquier base de datos local (`.db`/`.sqlite`) que use el script para su estado.
- El README puede incluir una nota breve dejando explícito que es una herramienta de supervisión parental para uso propio sobre un dispositivo familiar, como referencia para ti mismo si en algún momento necesitas explicar el propósito del repositorio.

## 10. Librerías Python sugeridas

| Función | Librería |
|---|---|
| Procesos | `psutil` |
| Historial navegador | `sqlite3` (stdlib) |
| Monitoreo de archivos en tiempo real | `watchdog` |
| Excel | `openpyxl` |
| Envío de correo | `smtplib` + `email` (stdlib) |
| Zona horaria | `zoneinfo` (stdlib, Python 3.9+) |
| Parseo de `$I` de la papelera | script propio (formato documentado, sin librería especial) |

## 11. Prompt listo para pegar en Claude Code

```
Necesito construir/ampliar un script en Python llamado monitor_pc.py para Windows 10 y 11 que sirva como herramienta de control parental sobre una cuenta de usuario estándar (no administrador) de un menor de edad, instalada desde una cuenta de administrador. Debe:

1. Registrar procesos que se abren/cierran (con hora, usando psutil) y calcular el tiempo total acumulado por aplicación en el día (ej. cuánto tiempo estuvo en Word vs. YouTube vs. un juego).
2. Leer el historial de navegación de Chrome/Edge (y si es fácil, Firefox) copiando el archivo de historial bloqueado antes de leerlo con sqlite3. Categorizar cada URL visitada en: juegos, contenido para adultos, dudoso, normal — usando listas públicas de referencia existentes (no una lista curada a mano) más una heurística de palabras clave como respaldo.
3. Leer la tabla "downloads" del mismo historial de Chrome/Edge para obtener un registro objetivo de archivos descargados (nombre, ruta, URL origen, tamaño, hora, estado), y marcar como sospechosos los .apk/.exe/.zip de dominios no confiables. Además monitorear con watchdog las carpetas Descargas/Escritorio/Documentos como respaldo. Por ahora esto NO genera alerta inmediata, solo entra al resumen diario.
4. Monitorear la carpeta $Recycle.Bin del usuario (con watchdog) para detectar archivos movidos a la papelera, parseando los archivos $I para extraer ruta original, tamaño y hora de eliminación.
5. Detectar cuándo se vacía la papelera completa (varios pares $I/$R desaparecen juntos en una ventana corta de tiempo) y registrar la hora de ese evento por separado.
6. Guardar todas las marcas de tiempo en UTC internamente, y convertirlas a America/Lima (UTC-5 fijo) al generar el reporte, usando zoneinfo.
7. Generar un reporte HTML con una tabla por módulo (tiempo por app, navegación categorizada, descargas, papelera-eliminados, papelera-vaciada). Cada visita/archivo marcado debe llevar un badge tipo "pill" (insignia redondeada) indicando por ejemplo "⚠️ dominio de juegos" o "🔞 dominio para adultos", no solo resaltar la fila. Opcionalmente generar también un adjunto .xlsx con openpyxl.
8. Enviar un correo diario (no por hora) vía SMTP genérico configurado en un archivo de configuración aparte (host, puerto, usuario, contraseña — nunca hardcodeado). Si hay varios días pendientes (PC apagada), combinarlos en un solo correo con secciones por fecha.
9. Correr en segundo plano revisando actividad continuamente, y cada 30 minutos evaluar si toca enviar el reporte del día.
10. Darme un script .ps1 de instalación que: liste los perfiles de usuario locales para elegir cuál es el del menor, y registre una Tarea Programada cuyo trigger sea "al iniciar sesión de ese usuario específico" pero que se ejecute con el principal SYSTEM (para que la cuenta estándar del menor no pueda detenerla fácilmente), con un nombre de tarea neutro. Debe funcionar igual en Windows 10 y 11.
11. Organiza el proyecto para subirlo a un repositorio Git privado: README explicando el propósito, docs/, src/, config.example.ini sin credenciales reales, y un .gitignore que excluya config.ini real, logs, reportes generados y cualquier base de datos local de estado — nada de eso debe llegar al repo.

Por favor primero muéstrame la estructura de archivos y módulos que propones antes de escribir todo el código.
```

## 12. Puntos ya resueltos y checklist final

- Categorización de dominios: sin lista curada, listas públicas + badges tipo pill. ✔
- Alertas inmediatas: no por ahora, solo reporte diario. ✔
- Cuenta del menor: estándar, ya configurada; instalación desde cuenta de administrador. ✔
- Resistencia a que el menor detenga el monitor: trigger al iniciar sesión del menor, ejecución como SYSTEM, nombre de tarea neutro. ✔
- Registro del proyecto: repositorio Git privado, sin credenciales ni datos capturados en el repo. ✔

Único punto que sigue abierto porque depende de una decisión tuya al momento de instalar, no de diseño: confirmar en la PC específica cuál es exactamente el nombre de la cuenta de Windows del menor (el script de instalación te lo va a listar para elegir, pero es bueno que lo tengas a mano antes de correr el instalador).
