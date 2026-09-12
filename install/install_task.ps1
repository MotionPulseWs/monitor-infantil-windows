<#
    install_task.ps1  —  Instalador de la Tarea Programada del monitor (spec §8).

    Ejecutar COMO ADMINISTRADOR. Funciona igual en Windows 10 y 11.

    Que hace:
      1. Lista las cuentas locales habilitadas para que el admin elija la del menor.
      2. Registra una Tarea Programada cuyo TRIGGER es "al iniciar sesion de ese
         usuario especifico", pero cuya EJECUCION corre como SYSTEM (RunLevel Highest),
         para que la cuenta estandar del menor no pueda verla ni detenerla facilmente.
      3. Usa un nombre de tarea NEUTRO (no "MonitorPC") para no llamar la atencion.

    Nota: se ejecuta pythonw.exe (sin ventana de consola). Si se empaqueto con
    PyInstaller, reemplazar $Execute por la ruta del .exe y quitar el argumento.
#>

#Requires -RunAsAdministrator

param(
    [string]$TaskName = "WindowsSystemHelper",
    [string]$ScriptPath = "C:\ProgramData\WindowsSystemHelper\monitor_pc.py",
    [string]$PythonwPath = "C:\Windows\pyw.exe"  # o la ruta a pythonw.exe
)

Write-Host "== Instalador de tarea de monitoreo (control parental) ==" -ForegroundColor Cyan
Write-Host ""

# 1) Listar cuentas locales habilitadas (spec §8, punto 2)
$users = Get-LocalUser | Where-Object { $_.Enabled -eq $true } | Select-Object Name, SID
if (-not $users) { Write-Error "No se encontraron cuentas locales habilitadas."; exit 1 }

Write-Host "Cuentas locales disponibles:" -ForegroundColor Yellow
$i = 0
foreach ($u in $users) { Write-Host ("  [{0}] {1}  (SID: {2})" -f $i, $u.Name, $u.SID); $i++ }

$sel = Read-Host "`nNumero de la cuenta del MENOR a monitorear"
$target = $users[[int]$sel]
if (-not $target) { Write-Error "Seleccion invalida."; exit 1 }

$computer = $env:COMPUTERNAME
$targetPrincipal = "$computer\$($target.Name)"
Write-Host ("Cuenta elegida: {0}  (SID: {1})" -f $targetPrincipal, $target.SID) -ForegroundColor Green

# 2) Definir la tarea: trigger al logon del menor, ejecucion como SYSTEM (spec §8, punto 3)
$action = New-ScheduledTaskAction -Execute $PythonwPath -Argument ('"{0}"' -f $ScriptPath)
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $targetPrincipal
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -Hidden

# StartWhenAvailable cubre "ejecutar cuanto antes si se perdio el inicio programado"
# (por si la PC estuvo apagada, spec §8 punto 4).

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings -Force | Out-Null

Write-Host ""
Write-Host ("Tarea '{0}' registrada correctamente." -f $TaskName) -ForegroundColor Green
Write-Host "Recuerda: coloca config.ini junto al script y NO lo subas al repositorio." -ForegroundColor Yellow

# TODO (post-instalacion): guardar el SID elegido en config.ini ([monitoring].target_sid)
#       para que el script resuelva %LOCALAPPDATA% y $Recycle.Bin del menor.
