# DWG -> DXF через AutoCAD Core Console (без интерфейса). X:\ только читаем: копия в OutDir, конвертация там.
# Запуск (PowerShell, не Git Bash — тот портит ключи /i /s):
#   powershell -File dwg2dxf.ps1 -Dwg "X:\...\план.dwg" -OutDir "C:\...\scratch"
param([Parameter(Mandatory)][string]$Dwg, [Parameter(Mandatory)][string]$OutDir)
$acc = "C:\Program Files\Autodesk\AutoCAD 2023\accoreconsole.exe"
New-Item -ItemType Directory -Force $OutDir | Out-Null
$md5 = [Security.Cryptography.MD5]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes($Dwg))
$name = 'dwg_' + (($md5[0..5] | ForEach-Object { $_.ToString('x2') }) -join '')  # только латиница: скрипт AutoCAD в ASCII
$copy = Join-Path $OutDir "$name.dwg"; $dxf = Join-Path $OutDir "$name.dxf"; $scr = Join-Path $OutDir "$name.scr"
Copy-Item -LiteralPath $Dwg -Destination $copy -Force
"FILEDIA 0`nDXFOUT`n`"$dxf`"`nV`n2018`n16`n" | Set-Content -Encoding ascii -NoNewline $scr
$p = Start-Process -FilePath $acc -ArgumentList @('/i', "`"$copy`"", '/s', "`"$scr`"", '/l', 'en-US') -NoNewWindow -PassThru -RedirectStandardOutput (Join-Path $OutDir "$name.log")
if (-not $p.WaitForExit(240000)) { $p.Kill(); Write-Error "AutoCAD завис (вопрос в консоли?): $Dwg"; exit 1 }
if (Test-Path $dxf) { Write-Output $dxf } else { Write-Error "DXF не создан: $Dwg" }
