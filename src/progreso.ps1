<#
  Barra de progreso para los pasos del .bat que corren antes de que exista
  el Python del portable: descarga, SHA-256 y extraccion.

  Dibuja la misma linea que src/progreso.py (la de la migracion): barra,
  porcentaje, GB hechos, tiempo que falta, velocidad, que se hace y con que
  archivo; en Windows Terminal tambien el anillo de la pestana. Al terminar
  deja una linea de resumen con el tiempo.

  Modos:
    prueba     sale con 0: el .bat comprueba asi que PowerShell puede correr
               este archivo; si no, usa curl y 7-Zip con su barra de siempre.
    descargar  curl.exe en silencio (mismos reintentos y reanudacion) y la
               barra segun el tamano del archivo que va escribiendo.
    hash       SHA-256 por bloques de 8 MB; sale con 0 si coincide.
    extraer    7-Zip "x" leyendo su porcentaje.
    probar     7-Zip "t" (prueba de integridad) leyendo su porcentaje.

  Archivo en ASCII a proposito: Windows PowerShell 5.1 lee un .ps1 sin BOM
  como ANSI, asi que los simbolos se arman con [char].
#>
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('prueba', 'descargar', 'hash', 'extraer', 'probar')]
    [string]$Modo,
    [string]$Url,
    [string]$Salida,
    [switch]$Reanudar,
    [string]$Archivo,
    [string]$Esperado,
    [string]$Destino,
    [string]$SieteZip,
    [string]$Nombre
)

if ($Modo -eq 'prueba') { exit 0 }
$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch { }

$E = [char]27
$LLENO = [string][char]0x2588
$VACIO = [string][char]0x2591
$SEP = ' ' + [char]0x00B7 + ' '
$WT = [bool]$env:WT_SESSION
$PUNTOS = if ($WT) { [string][char]0x2026 } else { '...' }
$MARCA_OK = if ($WT) { [string][char]0x2713 } else { 'OK' }
$MARCA_X = if ($WT) { [string][char]0x2717 } else { 'X' }
$VT = $false
try { $VT = [bool]$Host.UI.SupportsVirtualTerminal } catch { }
$VIVO = $true
try { $VIVO = -not [Console]::IsOutputRedirected } catch { }
if ($env:CINECONIA_PROGRESO -eq '0') { $VIVO = $false }
if (-not $VIVO) { $VT = $false }
# Ojo: PowerShell no distingue mayusculas; ninguna otra variable puede
# llamarse $a, $g, $v, $r, $x o $e.
$A = "$E[38;5;179m"; $G = "$E[38;5;245m"; $V = "$E[38;5;71m"; $R = "$E[38;5;203m"; $X = "$E[0m"
$SANGRIA = '   '
$INV = [Globalization.CultureInfo]::InvariantCulture

# -- textos: los mismos src/locales/*.json que usa Python --------------------
$TEXTOS = @{}
try {
    $lang = if ("$env:CINECONIA_LANG" -like 'es*') { 'es' } else { 'en' }
    $ruta = Join-Path (Join-Path $PSScriptRoot 'locales') "$lang.json"
    $json = Get-Content -Raw -Encoding UTF8 -LiteralPath $ruta | ConvertFrom-Json
    foreach ($p in $json.PSObject.Properties) { $TEXTOS[$p.Name] = [string]$p.Value }
} catch { }

function T([string]$clave, [hashtable]$datos = @{}) {
    $txt = $TEXTOS[$clave]
    if (-not $txt) { $txt = $clave }
    foreach ($k in $datos.Keys) { $txt = $txt.Replace('{' + $k + '}', [string]$datos[$k]) }
    return $txt
}

# -- formatos (copian los de progreso.py) -----------------------------------
function Num([double]$x, [string]$f) { return $x.ToString($f, $INV) }

function Unidad([double]$n) {
    if ($n -ge 1TB) { return @('TB', 1TB) }
    if ($n -ge 1GB) { return @('GB', 1GB) }
    if ($n -ge 1MB) { return @('MB', 1MB) }
    if ($n -ge 1KB) { return @('KB', 1KB) }
    return @('B', 1)
}

function Tamano([double]$n) {
    $u = Unidad $n
    $f = if ($u[0] -eq 'B' -or $u[0] -eq 'KB') { '0' } else { '0.0' }
    return (Num ($n / $u[1]) $f) + ' ' + $u[0]
}

function Tamano-Par([double]$hecho, [double]$total) {
    $u = Unidad $total
    $f = if ($u[0] -eq 'B' -or $u[0] -eq 'KB') { '0' } else { '0.0' }
    return (Num ($hecho / $u[1]) $f) + ' / ' + (Num ($total / $u[1]) $f) + ' ' + $u[0]
}

function Velocidad([double]$bps) {
    $u = Unidad ([Math]::Max($bps, 1MB))
    $valor = $bps / $u[1]
    if ($valor -ge 10) { return (Num $valor '0') + ' ' + $u[0] + '/s' }
    return (Num $valor '0.0') + ' ' + $u[0] + '/s'
}

function Tiempo-Restante([double]$seg) {
    $s = [int64][Math]::Floor([Math]::Max(0, $seg))
    if ($s -lt 60) { return "$([Math]::Max(5, [Math]::Floor(($s + 4) / 5) * 5)) s" }
    if ($s -lt 600) {
        $m = [Math]::Floor($s / 60); $decenas = [Math]::Floor(($s % 60) / 10) * 10
        return "$m min " + (Num $decenas '00') + ' s'
    }
    if ($s -lt 3600) { return "$([Math]::Floor(($s + 30) / 60)) min" }
    $h = [Math]::Floor($s / 3600); $m = [Math]::Floor(($s % 3600) / 60)
    return "$h h " + (Num $m '00') + ' min'
}

function Duracion([double]$seg) {
    $s = [int64][Math]::Floor([Math]::Max(0, $seg))
    if ($s -ge 60) { return "$([Math]::Floor($s / 60)) min " + (Num ($s % 60) '00') + ' s' }
    return "$s s"
}

function Recortar-Medio([string]$s, [int]$ancho) {
    if ($s.Length -le $ancho) { return $s }
    if ($ancho -le $PUNTOS.Length) { return $PUNTOS.Substring(0, [Math]::Max(0, $ancho)) }
    $resto = $ancho - $PUNTOS.Length
    $cabeza = [int][Math]::Floor($resto / 2)
    $cola = $resto - $cabeza
    return $s.Substring(0, $cabeza) + $PUNTOS + $s.Substring($s.Length - $cola)
}

function C([string]$texto, [string]$color) {
    if ($VT -and $texto -and $color) { return $color + $texto + $X }
    return $texto
}

function Ancho-Consola {
    try { $w = [Console]::WindowWidth; if ($w -gt 0) { return $w } } catch { }
    return 100
}

# -- estado de la linea ------------------------------------------------------
$reloj = [Diagnostics.Stopwatch]::StartNew()
$st = @{ vel = $null; mT = 0.0; mB = 0.0; ultimo = -1.0; visible = $false; pct = -1 }

function Medir([double]$hecho) {
    $ahora = $reloj.Elapsed.TotalSeconds
    $dt = $ahora - $st.mT
    if ($dt -lt 0.5) { return }
    $inst = [Math]::Max(0.0, ($hecho - $st.mB) / $dt)
    if ($null -eq $st.vel) { $st.vel = $inst } else { $st.vel = 0.3 * $inst + 0.7 * $st.vel }
    $st.mT = $ahora; $st.mB = $hecho
}

function Borrar {
    if (-not $st.visible) { return }
    if ($VT) { [Console]::Write("`r$E[2K") }
    else { [Console]::Write("`r" + (' ' * ((Ancho-Consola) - 1)) + "`r") }
    $st.visible = $false
}

function Escribir-Linea([string]$plano, [string]$color, [string]$extra) {
    $ancho = Ancho-Consola
    if ($VT) { [Console]::Write("`r" + $color + "$E[K" + $extra) }
    else { [Console]::Write("`r" + $plano + (' ' * [Math]::Max(0, $ancho - 1 - $plano.Length))) }
    $st.visible = $true
}

function Pestana([int]$estado, [int]$pct) {
    if ($WT -and $VT) { return "$E]9;4;$estado;$pct`a" }
    return ''
}

# Misma composicion que Progreso.linea() en progreso.py. $total 0 = sin total:
# el tramo ambar va y viene y en lugar del porcentaje va el tiempo.
function Dibujar([double]$hecho, [double]$total, [string]$tarea, [string]$nombre, [bool]$forzar = $false) {
    if (-not $VIVO) { return }
    $ahora = $reloj.Elapsed.TotalSeconds
    if (-not $forzar -and ($ahora - $st.ultimo) -lt 0.2) { return }
    $st.ultimo = $ahora
    Medir $hecho
    $util = [Math]::Max(20, (Ancho-Consola) - 1 - $SANGRIA.Length)
    $barra = if ($util -ge 90) { 20 } else { 12 }
    $segs = @()
    if ($total -gt 0) {
        $frac = [Math]::Min(1.0, $hecho / $total)
        $pct = [int][Math]::Floor($frac * 100)
        $pctTxt = ("$pct%").PadLeft(4)
        $segs += , @('gb', (Tamano-Par $hecho $total), $G)
        if ($ahora -ge 2 -and $st.vel -gt 0) { $eta = T 'progress.left' @{ time = (Tiempo-Restante (($total - $hecho) / $st.vel)) } }
        else { $eta = T 'progress.estimating' }
        $segs += , @('eta', $eta, $A)
        $llenos = [int][Math]::Round($frac * $barra)
        if ($frac -lt 1 -and $llenos -eq $barra) { $llenos = $barra - 1 }
        $bPlano = ($LLENO * $llenos) + ($VACIO * ($barra - $llenos))
        $bColor = (C ($LLENO * $llenos) $A) + (C ($VACIO * ($barra - $llenos)) $G)
    } else {
        $pct = -1
        $s = [int][Math]::Floor($ahora)
        $pctTxt = ("$([Math]::Floor($s / 60)):" + (Num ($s % 60) '00')).PadLeft(4)
        $segs += , @('gb', (Tamano $hecho), $G)
        $tramo = [Math]::Max(3, [int][Math]::Floor($barra / 4))
        $fase = ($ahora % 2.4) / 2.4
        $ida = if ($fase -lt 0.5) { $fase * 2 } else { 2 - $fase * 2 }
        $pos = [int][Math]::Round($ida * ($barra - $tramo))
        $bPlano = ($VACIO * $pos) + ($LLENO * $tramo) + ($VACIO * ($barra - $pos - $tramo))
        $bColor = (C ($VACIO * $pos) $G) + (C ($LLENO * $tramo) $A) + (C ($VACIO * ($barra - $pos - $tramo)) $G)
    }
    if ($st.vel) { $segs += , @('vel', (Velocidad $st.vel), $G) }
    if ($tarea) { $segs += , @('tarea', $tarea, '') }
    if ($nombre) { $segs += , @('nombre', $nombre, $G) }

    # Si no cabe se sacrifica, en orden: velocidad, GB, nombre, tarea, tiempo.
    $intentos = @(
        @(@(), 28), @(@('vel'), 28), @(@('vel', 'gb'), 20), @(@('vel', 'gb'), 12),
        @(@('vel', 'gb', 'nombre'), 0), @(@('vel', 'gb', 'nombre', 'tarea'), 0),
        @(@('vel', 'gb', 'nombre', 'tarea', 'eta'), 0))
    $partes = @()
    foreach ($it in $intentos) {
        $quitar = $it[0]; $minNombre = $it[1]
        $partes = @($segs | Where-Object { $quitar -notcontains $_[0] })
        $largo = $barra + 2 + $pctTxt.Length
        foreach ($p in $partes) { if ($p[0] -ne 'nombre') { $largo += $SEP.Length + $p[1].Length } }
        $conNombre = ($nombre -and ($quitar -notcontains 'nombre'))
        if ($conNombre) {
            $resto = $util - $largo - $SEP.Length
            if ($resto -ge [Math]::Min($nombre.Length, $minNombre)) {
                $partes = @($partes | ForEach-Object {
                    if ($_[0] -eq 'nombre') { , @('nombre', (Recortar-Medio $_[1] $resto), $_[2]) } else { , $_ }
                })
                break
            }
        } elseif ($largo -le $util) { break }
    }
    $plano = $SANGRIA + $bPlano + '  ' + $pctTxt
    $color = $SANGRIA + $bColor + '  ' + (C $pctTxt $A)
    foreach ($p in $partes) {
        $plano += $SEP + $p[1]
        $color += (C $SEP $G) + (C $p[1] $p[2])
    }
    $extra = ''
    if ($pct -ne $st.pct) {
        $st.pct = $pct
        if ($pct -ge 0) { $extra = Pestana 1 $pct } else { $extra = Pestana 3 0 }
    }
    Escribir-Linea $plano $color $extra
}

function Cerrar([string]$resumen, [bool]$ok = $true) {
    Borrar
    if ($VIVO) { [Console]::Write((Pestana 0 0)) }
    if ($resumen) {
        if ($ok) { $m = C $MARCA_OK $V } else { $m = C $MARCA_X $R }
        [Console]::WriteLine($SANGRIA + $m + ' ' + $resumen)
    }
}

function Iniciar-Proceso([string]$exe, [string[]]$argumentos, [bool]$leerSalida) {
    $psi = New-Object Diagnostics.ProcessStartInfo
    $psi.FileName = $exe
    $psi.Arguments = ($argumentos | ForEach-Object { '"' + $_ + '"' }) -join ' '
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $leerSalida
    return [Diagnostics.Process]::Start($psi)
}

function Tamano-Abierto([string]$ruta) {
    # Con el archivo abierto por curl, el tamano del directorio puede ir
    # atrasado en NTFS: se pregunta al propio archivo.
    try {
        $fs = [IO.File]::Open($ruta, 'Open', 'Read', 'ReadWrite, Delete')
        try { return $fs.Length } finally { $fs.Close() }
    } catch {
        try { return (Get-Item -LiteralPath $ruta).Length } catch { return 0 }
    }
}

# -- modos ---------------------------------------------------------------------
$codigo = 1
try {
    switch ($Modo) {
        'descargar' {
            $curl = (Get-Command curl.exe -ErrorAction SilentlyContinue)
            if (-not $curl) { $curl = Get-Command curl -CommandType Application }
            $curl = @($curl)[0].Path
            $Salida = [IO.Path]::GetFullPath($Salida)
            if (-not $Nombre) { $Nombre = [IO.Path]::GetFileName($Url) }
            $total = 0
            try {
                foreach ($l in (& $curl -sIL --max-time 25 $Url 2>$null)) {
                    if ($l -match '^content-length:\s*(\d+)') { $largo = [int64]$Matches[1]; if ($largo -gt 0) { $total = $largo } }
                }
            } catch { }
            $argumentos = @('--fail', '--location', '--retry', '5', '--retry-delay', '2', '--silent', '--show-error')
            if ($Reanudar) { $argumentos += @('-C', '-') }
            $argumentos += @('-o', $Salida, $Url)
            $st.mB = [double](Tamano-Abierto $Salida)
            $p = Iniciar-Proceso $curl $argumentos $false
            Dibujar $st.mB $total (T 'progress.downloading') $Nombre $true
            while (-not $p.WaitForExit(200)) {
                Dibujar ([double](Tamano-Abierto $Salida)) $total (T 'progress.downloading') $Nombre
            }
            $p.WaitForExit()
            $codigo = $p.ExitCode
            if ($codigo -eq 0) {
                Cerrar (T 'progress.download_done' @{ name = $Nombre; size = (Tamano (Tamano-Abierto $Salida)); time = (Duracion $reloj.Elapsed.TotalSeconds) })
            } else { Cerrar '' }
        }
        'hash' {
            $Archivo = [IO.Path]::GetFullPath($Archivo)
            if (-not $Nombre) { $Nombre = [IO.Path]::GetFileName($Archivo) }
            $sha = $null
            try { $sha = New-Object Security.Cryptography.SHA256Cng } catch { $sha = [Security.Cryptography.SHA256]::Create() }
            $fs = [IO.File]::OpenRead($Archivo)
            try {
                $total = [double]$fs.Length
                $buf = New-Object byte[] (8MB)
                $hecho = 0.0
                Dibujar 0 $total (T 'progress.verifying') $Nombre $true
                while (($n = $fs.Read($buf, 0, $buf.Length)) -gt 0) {
                    [void]$sha.TransformBlock($buf, 0, $n, $null, 0)
                    $hecho += $n
                    Dibujar $hecho $total (T 'progress.verifying') $Nombre
                }
                [void]$sha.TransformFinalBlock($buf, 0, 0)
            } finally { $fs.Close() }
            $real = -join ($sha.Hash | ForEach-Object { $_.ToString('x2') })
            if ($real -eq "$Esperado".Trim().ToLower()) {
                $codigo = 0
                Cerrar (T 'progress.hash_done' @{ size = (Tamano $total); time = (Duracion $reloj.Elapsed.TotalSeconds) })
            } else { $codigo = 1; Cerrar '' }
        }
        { $_ -eq 'extraer' -or $_ -eq 'probar' } {
            $SieteZip = (Resolve-Path -LiteralPath $SieteZip).Path
            $Archivo = [IO.Path]::GetFullPath($Archivo)
            # Tamano descomprimido y cantidad de archivos, de la lista del paquete.
            # El contador del progreso de 7-Zip incluye las carpetas.
            $total = 0.0; $cuantos = 0; $elementos = 0
            try {
                foreach ($l in (& $SieteZip l $Archivo 2>$null)) {
                    if ($l -match '(\d+)\s+(\d+)\s+(\d+)\s+files(?:,\s+(\d+)\s+folders)?') {
                        $total = [double]$Matches[1]; $cuantos = [int]$Matches[3]; $elementos = $cuantos
                        if ($Matches[4]) { $elementos += [int]$Matches[4] }
                    }
                }
            } catch { }
            if ($Modo -eq 'extraer') {
                $tarea = T 'progress.extracting'
                $argumentos = @('x', $Archivo, "-o$([IO.Path]::GetFullPath($Destino))", '-y', '-bso0', '-bsp1')
            } else {
                $tarea = T 'progress.checking'
                $argumentos = @('t', $Archivo, '-bso0', '-bsp1')
            }
            $p = Iniciar-Proceso $SieteZip $argumentos $true
            $lector = $p.StandardOutput
            $buf = New-Object char[] 4096
            $pendiente = ''
            $pct = 0.0; $n7 = 0; $actual = [IO.Path]::GetFileName($Archivo)
            $escala = if ($total -gt 0) { $total } else { 100.0 }
            Dibujar 0 $escala $tarea $actual $true
            # 7-Zip reescribe su porcentaje con retrocesos: " 31% 2 - carpeta\archivo".
            while (($n = $lector.Read($buf, 0, $buf.Length)) -gt 0) {
                $pendiente += [string]::new($buf, 0, $n)
                $trozos = $pendiente -split "[`b`r`n]"
                $pendiente = $trozos[-1]
                # El ultimo trozo puede estar a medio escribir: queda para la proxima vuelta.
                $completos = if ($trozos.Length -gt 1) { $trozos[0..($trozos.Length - 2)] } else { @() }
                foreach ($tz in $completos) {
                    if ($tz -match '^\s*(\d+)%(?:\s+(\d+))?(?:\s+-\s+(.*\S))?') {
                        $pct = [double]$Matches[1]
                        if ($Matches[2]) { $n7 = [int]$Matches[2] }
                        if ($Matches[3]) { $actual = [IO.Path]::GetFileName($Matches[3].Trim()) }
                    }
                }
                $t2 = if ($elementos -gt 0 -and $n7 -gt 0) { "$tarea $([Math]::Min($n7, $elementos))/$elementos" } else { $tarea }
                Dibujar ($escala * $pct / 100) $escala $t2 $actual
            }
            $p.WaitForExit()
            $codigo = $p.ExitCode
            if ($codigo -eq 0) {
                $clave = if ($Modo -eq 'extraer') { 'progress.extract_done' } else { 'progress.test_done' }
                Cerrar (T $clave @{ files = $cuantos; size = (Tamano $total); time = (Duracion $reloj.Elapsed.TotalSeconds) })
            } else { Cerrar '' }
        }
    }
} catch {
    Cerrar ''
    [Console]::Error.WriteLine($SANGRIA + '[X] ' + $_.Exception.Message)
    $codigo = 1
}
exit $codigo
