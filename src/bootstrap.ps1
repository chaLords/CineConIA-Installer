# Windows PowerShell 5.1 entry point; ASCII source, UTF-8 translations.
param([switch]$LibraryOnly, [Parameter(ValueFromRemainingArguments=$true)][string[]]$CliArgs)
$script:Root = Split-Path $PSScriptRoot -Parent
$script:Texts = @{}
$script:ScanLimited = $false

function Read-Config([string]$Name) {
    Get-Content -LiteralPath (Join-Path $script:Root "config/$Name.json") -Raw -Encoding UTF8 | ConvertFrom-Json
}
function Initialize-Language([string]$Language) {
    if (-not $Language) { $Language = $env:CINECONIA_LANG }
    if (-not $Language) {
        $Language = if ((Get-UICulture).Name -like 'es*' -or (Get-Culture).Name -like 'es*') { 'es' } else { 'en' }
    }
    $env:CINECONIA_LANG = if ($Language -like 'es*') { 'es' } else { 'en' }
    $data = Get-Content -LiteralPath (Join-Path $PSScriptRoot "locales/$($env:CINECONIA_LANG).json") -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($p in $data.PSObject.Properties) { $script:Texts[$p.Name] = [string]$p.Value }
}
function T([string]$Key) {
    if ($script:Texts.ContainsKey("setup.$Key")) { return $script:Texts["setup.$Key"] }
    return $Key
}
function Show-Step([string]$Text) { Write-Host "`n   $Text" -ForegroundColor Cyan }
function Confirm-Change([string]$Text) {
    Write-Host $Text -ForegroundColor Yellow
    return (Read-Host (T 'confirm')) -ceq 'CONFIRMAR'
}
function Select-Folder([string]$Title) {
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = $Title
    $dialog.ShowNewFolderButton = $true
    try {
        if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { return $dialog.SelectedPath }
        return $null
    } finally { $dialog.Dispose() }
}
function Get-FullPath([string]$Path) {
    [IO.Path]::GetFullPath($Path).TrimEnd('\','/')
}
function Test-Within([string]$Path, [string]$Parent) {
    $a = Get-FullPath $Path; $b = Get-FullPath $Parent
    $a.Equals($b,[StringComparison]::OrdinalIgnoreCase) -or $a.StartsWith($b+'\',[StringComparison]::OrdinalIgnoreCase)
}
function Assert-NoReparse([string]$Path) {
    $current = [IO.Path]::GetFullPath($Path)
    while ($current) {
        if (Test-Path -LiteralPath $current) {
            $item = Get-Item -LiteralPath $current -Force
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "PATH_REPARSE: $current" }
        }
        $next = Split-Path $current -Parent
        if ($next -eq $current) { break }; $current = $next
    }
}
function Assert-Destination([string]$Path, [object[]]$Existing=@(), [double]$MinimumGB=20) {
    if ($Path -notmatch '^[A-Za-z]:[\\/]') { throw 'PATH_LOCAL_ABSOLUTE_REQUIRED' }
    # Percent expansion and cmd metacharacters are unsafe in generated BAT launchers.
    if ($Path -match '[%!?&|<>^"\r\n]') { throw 'PATH_UNSAFE_CHARACTERS' }
    $full = Get-FullPath $Path
    if ($full.Length -le 3) { throw 'PATH_DRIVE_ROOT' }
    Assert-NoReparse $full
    foreach ($protected in @($env:WINDIR,$env:ProgramFiles,${env:ProgramFiles(x86)},$env:ProgramData)) {
        if ($protected -and (Test-Within $full $protected)) { throw "PATH_PROTECTED: $protected" }
    }
    foreach ($install in $Existing) {
        if ((Test-Within $full $install.root) -or (Test-Within $install.root $full)) { throw "PATH_OVERLAP: $($install.root)" }
    }
    if (Test-Path -LiteralPath $full) {
        if (-not (Test-Path -LiteralPath $full -PathType Container)) { throw 'PATH_NOT_DIRECTORY' }
        if (@(Get-ChildItem -LiteralPath $full -Force).Count) { throw "PATH_NOT_EMPTY: $full" }
    }
    $ancestor = $full
    while (-not (Test-Path -LiteralPath $ancestor)) { $ancestor = Split-Path $ancestor -Parent }
    $drive = New-Object IO.DriveInfo ([IO.Path]::GetPathRoot($full))
    if ($drive.DriveType -ne [IO.DriveType]::Fixed) { throw 'PATH_FIXED_DISK_REQUIRED' }
    if ($drive.AvailableFreeSpace -lt $MinimumGB*1GB) { throw "DISK_SPACE: $MinimumGB GB" }
    # Probe the parent, never a user's existing installation.
    $probe = Join-Path $ancestor ('.cineconia-write-'+[guid]::NewGuid().ToString('N'))
    try { [IO.File]::WriteAllText($probe,'test') } finally { if (Test-Path -LiteralPath $probe) { Remove-Item -LiteralPath $probe } }
    return $full
}
function Get-Installation([string]$Path) {
    $root = Get-FullPath $Path
    $comfy = if (Test-Path -LiteralPath (Join-Path $root 'ComfyUI/main.py')) { Join-Path $root 'ComfyUI' } else { $root }
    if (-not (Test-Path -LiteralPath (Join-Path $comfy 'main.py')) -or -not (Test-Path -LiteralPath (Join-Path $comfy 'comfy'))) { return $null }
    $portable = Test-Path -LiteralPath (Join-Path $root 'python_embeded/python.exe')
    if (-not $portable -and (Split-Path $root -Leaf) -eq 'ComfyUI') {
        $parent = Split-Path $root -Parent
        if (Test-Path -LiteralPath (Join-Path $parent 'python_embeded/python.exe')) { $root=$parent; $portable=$true }
    }
    [pscustomobject]@{root=$root;comfy=$comfy;portable=$portable;models=(Join-Path $comfy 'models')}
}
function Find-Installations([string[]]$Roots, [int]$MaxDirectories=15000, [double]$MaxSeconds=15) {
    if (-not $Roots) {
        $Roots = @([Environment]::GetFolderPath('MyDocuments'),[Environment]::GetFolderPath('Desktop'),(Join-Path $env:USERPROFILE 'Downloads'))
        $Roots += @([IO.DriveInfo]::GetDrives() | Where-Object {$_.DriveType -eq 'Fixed' -and $_.IsReady} | ForEach-Object {$_.RootDirectory.FullName})
    }
    $queue = New-Object 'Collections.Generic.Queue[object]'
    foreach ($path in $Roots) { if ($path -and (Test-Path -LiteralPath $path -PathType Container)) { $queue.Enqueue(@($path,0)) } }
    $seen=@{}; $found=@{}; $clock=[Diagnostics.Stopwatch]::StartNew(); $count=0; $script:ScanLimited=$false
    while ($queue.Count) {
        if ($count -ge $MaxDirectories -or $clock.Elapsed.TotalSeconds -gt $MaxSeconds) { $script:ScanLimited=$true; break }
        $entry=$queue.Dequeue(); $path=[string]$entry[0]; $depth=[int]$entry[1]
        $key=(Get-FullPath $path).ToLowerInvariant()
        if ($seen.ContainsKey($key)) { continue }; $seen[$key]=$true; $count++
        $item=Get-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
        if (-not $item -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { continue }
        $install=Get-Installation $path
        if ($install) { $found[$install.root.ToLowerInvariant()]=$install; continue }
        if ($depth -ge 6) { $script:ScanLimited=$true; continue }
        foreach ($child in @(Get-ChildItem -LiteralPath $path -Directory -Force -ErrorAction SilentlyContinue)) {
            if ($child.Name -match '^(\.|\$|Windows$|Program Files|ProgramData$|AppData$|Users$|node_modules$|models$|custom_nodes$|python_embeded$|venv$|site-packages$|System Volume Information$)') { continue }
            if ($child.Attributes -band [IO.FileAttributes]::ReparsePoint) { continue }
            $queue.Enqueue(@($child.FullName,$depth+1))
        }
    }
    @($found.Values | Sort-Object root)
}
function Get-Hardware {
    $osInfo=Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue
    $cpuInfo=Get-CimInstance Win32_Processor -ErrorAction SilentlyContinue | Select-Object -First 1
    $systemInfo=Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
    $adapters=@(Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue)
    $data=[ordered]@{os=$osInfo.Caption; cpu=$cpuInfo.Name; ram_gb=[math]::Round($systemInfo.TotalPhysicalMemory/1GB,1); gpu=$null; vendor=$null; vram_gb=$null; driver=$null; compute=$null; pcie_gen=$null; pcie_lanes=$null; memory_bus=$null; python=$null; git=$null}
    $smi=Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue
    if ($smi) {
        $lines=@(& $smi.Source --query-gpu=name,memory.total,driver_version --format=csv,noheader,nounits 2>$null)
        if ($LASTEXITCODE -eq 0 -and $lines.Count) {
            $fields=$lines[0] -split ',\s*'
            if ($fields.Count -ge 3) {
                $data.gpu=$fields[0]; $data.vendor='nvidia'; $data.driver=$fields[2].Trim()
                $number=0.0
                if ([double]::TryParse($fields[1],[Globalization.NumberStyles]::Float,[Globalization.CultureInfo]::InvariantCulture,[ref]$number)) { $data.vram_gb=[math]::Round($number/1024,1) }
            }
        }
        foreach ($pair in @(@('compute','compute_cap'),@('pcie_gen','pcie.link.gen.max'),@('pcie_lanes','pcie.link.width.max'),@('memory_bus','memory.bus_width'))) {
            $value=@(& $smi.Source ("--query-gpu="+$pair[1]) --format=csv,noheader,nounits 2>$null)
            if ($LASTEXITCODE -eq 0 -and $value.Count -and $value[0] -match '^\d+(\.\d+)?$') { $data[$pair[0]]=$value[0] }
        }
    }
    if (-not $data.vendor) {
        foreach ($vendor in @('nvidia','amd','intel')) {
            $pattern=@{nvidia='NVIDIA';amd='AMD|Radeon';intel='Intel|Arc'}[$vendor]
            $adapter=$adapters | Where-Object {$_.Name -match $pattern} | Select-Object -First 1
            if ($adapter) { $data.vendor=$vendor; $data.gpu=$adapter.Name; $data.driver=$adapter.DriverVersion; break }
        }
    }
    # Detect only; never use or modify global Python/Conda.
    foreach ($name in @('python','git')) {
        $command=Get-Command "$name.exe" -ErrorAction SilentlyContinue
        if ($command) { $data[$name]=$command.Source }
    }
    [pscustomobject]$data
}
function Select-Profile($Hardware, $Matrix, [string]$Cuda) {
    if (-not $Hardware.vendor) { throw 'GPU_UNKNOWN' }
    $variant=$Hardware.vendor
    if ($variant -eq 'nvidia') {
        if (-not $Hardware.compute -or -not $Hardware.driver) { throw 'GPU_CAPABILITY_UNKNOWN' }
        $cap=[double]::Parse([string]$Hardware.compute,[Globalization.CultureInfo]::InvariantCulture)
        if ($cap -lt 7.5) { $variant='nvidia_cu126' }
        elseif ($cap -lt 10 -and [version]$Hardware.driver -lt [version]'580.0') { $variant='nvidia_cu126' }
        if ($Cuda -eq '13') { $variant='nvidia' }
        elseif ($Cuda -in @('12','126','12.6')) { $variant='nvidia_cu126' }
        elseif ($Cuda) { throw 'CUDA_ARGUMENT_INVALID' }
        $profile=$Matrix.profiles.$variant
        if ($cap -lt $profile.min_compute -or ($profile.max_compute_exclusive -and $cap -ge $profile.max_compute_exclusive)) { throw 'GPU_ARCHITECTURE_UNSUPPORTED' }
        if ([version]$Hardware.driver -lt [version]$profile.min_driver) { throw "DRIVER_TOO_OLD: $($profile.min_driver)" }
    } elseif ($Cuda) { throw 'CUDA_NVIDIA_ONLY' }
    if (-not $Matrix.profiles.$variant) { throw 'GPU_UNSUPPORTED' }
    return $variant
}
function Get-FileSHA256([string]$Path) {
    $stream=[IO.File]::OpenRead($Path)
    $sha=[Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToLowerInvariant() }
    finally { $stream.Dispose(); $sha.Dispose() }
}
function Get-VerifiedDownload($Spec, [string]$Path) {
    if ($Spec.url -notmatch '^https://' -or $Spec.sha256 -notmatch '^[a-fA-F0-9]{64}$') { throw 'DOWNLOAD_MANIFEST_INVALID' }
    $parent=Split-Path $Path -Parent
    [IO.Directory]::CreateDirectory($parent) | Out-Null
    Assert-NoReparse $Path
    Assert-NoReparse ($Path+'.part')
    if (Test-Path -LiteralPath $Path) {
        if ((Get-FileSHA256 $Path) -eq $Spec.sha256) { return $Path }
        # Preserve suspect cache entries for diagnostics.
        Move-Item -LiteralPath $Path -Destination ($Path+'.invalid-'+[guid]::NewGuid().ToString('N'))
    }
    $part=$Path+'.part'
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'progreso.ps1') -Modo descargar -Url $Spec.url -Salida $part -Nombre (Split-Path $Path -Leaf) -Reanudar | Out-Host
    if ($LASTEXITCODE -ne 0) { throw 'DOWNLOAD_FAILED: rerun to resume' }
    if ((Get-FileSHA256 $part) -ne $Spec.sha256) {
        Move-Item -LiteralPath $part -Destination ($part+'.invalid-'+[guid]::NewGuid().ToString('N'))
        throw 'DOWNLOAD_HASH_MISMATCH'
    }
    Move-Item -LiteralPath $part -Destination $Path
    return $Path
}
function Expand-Portable([string]$Archive, [string]$Extractor, [string]$Destination) {
    # Stage beside the destination: failed extraction never replaces an old installation.
    $parent=Split-Path $Destination -Parent
    [IO.Directory]::CreateDirectory($parent) | Out-Null
    $stage=Join-Path $parent ('.cineconia-stage-'+[guid]::NewGuid().ToString('N'))
    [IO.Directory]::CreateDirectory($stage) | Out-Null
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'progreso.ps1') -Modo extraer -SieteZip $Extractor -Archivo $Archive -Destino $stage | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "EXTRACTION_FAILED: $stage" }
    $candidates=@(Get-ChildItem -LiteralPath $stage -Directory | Where-Object {
        (Test-Path -LiteralPath (Join-Path $_.FullName 'python_embeded/python.exe')) -and (Test-Path -LiteralPath (Join-Path $_.FullName 'ComfyUI/main.py'))
    })
    if ($candidates.Count -ne 1) { throw "PORTABLE_LAYOUT_INVALID: $stage" }
    Assert-NoReparse $Destination
    if (Test-Path -LiteralPath $Destination) {
        if (@(Get-ChildItem -LiteralPath $Destination -Force).Count) { throw 'DESTINATION_CHANGED_DURING_DOWNLOAD' }
        # Only an empty, verified destination directory can be removed.
        Remove-Item -LiteralPath $Destination
    }
    Move-Item -LiteralPath $candidates[0].FullName -Destination $Destination
    if (-not @(Get-ChildItem -LiteralPath $stage -Force).Count) { Remove-Item -LiteralPath $stage }
}
function Write-State([string]$Destination, [hashtable]$State) {
    $dir=Join-Path $Destination '_cineconia'
    [IO.Directory]::CreateDirectory($dir) | Out-Null
    $file=Join-Path $dir 'install-state.json'
    $temp=$file+'.part'
    $State | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $temp -Encoding UTF8
    Move-Item -LiteralPath $temp -Destination $file -Force
}
function Invoke-Setup([string[]]$Arguments) {
    $ErrorActionPreference='Stop'
    [Console]::OutputEncoding=New-Object Text.UTF8Encoding $false
    $destination=$null; $cuda=$null; $lang=$null; $diagnose=$false; $mode='recommended'; $noShortcut=$false
    for ($i=0;$i -lt $Arguments.Count;$i++) {
        switch ($Arguments[$i]) {
            '--advanced' {$mode='advanced'}
            '--diagnose' {$diagnose=$true}
            '--no-shortcut' {$noShortcut=$true}
            '--destination' {if (++$i -ge $Arguments.Count) {throw 'ARGUMENT_MISSING'}; $destination=$Arguments[$i]}
            '--cuda' {if (++$i -ge $Arguments.Count) {throw 'ARGUMENT_MISSING'}; $cuda=$Arguments[$i]}
            '--lang' {if (++$i -ge $Arguments.Count) {throw 'ARGUMENT_MISSING'}; $lang=$Arguments[$i]}
            '--help' {Write-Host 'ComfyUI-Setup.bat [--advanced] [--destination PATH] [--cuda 13|12.6] [--lang es|en] [--diagnose] [--no-shortcut]'; return 0}
            default {throw "ARGUMENT_UNKNOWN: $($Arguments[$i])"}
        }
    }
    Initialize-Language $lang
    $matrix=Read-Config 'compatibility_matrix'
    Show-Step ("CineConIA $($matrix.installer_version) - "+(T 'title'))
    if (-not [Environment]::Is64BitOperatingSystem -or $env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { throw 'WINDOWS_X64_REQUIRED' }
    Show-Step (T 'hardware')
    $hardware=Get-Hardware
    foreach ($p in $hardware.PSObject.Properties) { Write-Host ('   {0,-16} {1}' -f $p.Name,$(if ($null -ne $p.Value -and "$($p.Value)") {$p.Value} else {T 'unavailable'})) }
    Show-Step (T 'search')
    $existing=@(Find-Installations)
    if ($script:ScanLimited) { Write-Host (T 'scan_limited') -ForegroundColor Yellow }
    foreach ($install in $existing) { Write-Host ('   '+$install.root) -ForegroundColor Green }
    if ($diagnose) { Write-Host (T 'diagnose_done'); return 0 }
    if (-not (Get-Command curl.exe -ErrorAction SilentlyContinue)) { throw 'CURL_REQUIRED' }
    $operation='new'
    if ($mode -eq 'advanced' -and -not $destination) {
        Write-Host ('1) '+(T 'destination'))
        Write-Host ('2) '+(T 'manual'))
        if ((Read-Host (T 'choose')) -eq '2') {
            $manual=Select-Folder (T 'manual')
            if (-not $manual) { return 2 }
            $selected=Get-Installation $manual
            if (-not $selected) { throw 'INSTALLATION_NOT_FOUND' }
            $existing=@($selected)
        }
    }
    if ($existing.Count) {
        Write-Host (T 'existing_menu')
        if ($mode -eq 'advanced') { Write-Host (T 'maintenance_menu') }
        $choice=Read-Host (T 'choose')
        if ($choice -eq '' -or $choice -eq '1' -or ($choice -eq '3' -and $mode -eq 'advanced')) {
            for ($n=0;$n -lt $existing.Count;$n++) { Write-Host ("   $($n+1)) "+$existing[$n].root) }
            $index=1
            if ($existing.Count -gt 1) {
                $answer=Read-Host (T 'choose')
                if ($answer -and (-not [int]::TryParse($answer,[ref]$index) -or $index -lt 1 -or $index -gt $existing.Count)) { throw 'SELECTION_INVALID' }
            }
            $selected=$existing[$index-1]
            if ($choice -ne '3') { Write-Host ((T 'reuse_unchanged')+' '+$selected.root); return 0 }
            if (-not $selected.portable) { throw 'MAINTENANCE_PORTABLE_ONLY' }
            if (-not (Confirm-Change ((T 'maintenance_confirm')+' '+$selected.root))) { return 2 }
            $destination=$selected.root; Assert-NoReparse $destination; $operation='maintenance'
        } elseif ($choice -ne '2') { return 2 }
    }
    if ($operation -eq 'new') {
        if (-not $destination) {
            $parent=Select-Folder (T 'destination')
            if (-not $parent) { return 2 }
            $destination=Join-Path $parent 'ComfyUI-CineConIA-V2'
        }
        # Also inspect an explicitly selected destination outside the bounded search.
        $direct=Get-Installation $destination
        if ($direct) { $existing+=@($direct) }
        $destination=Assert-Destination $destination $existing $matrix.minimum_free_gb
        $variant=Select-Profile $hardware $matrix $cuda
        $profile=$matrix.profiles.$variant
        Write-Host ((T 'plan')+" $variant / ComfyUI $($profile.release) / $destination")
        $cache=Join-Path $script:Root '.cache'
        Show-Step (T 'download')
        $archive=Get-VerifiedDownload $profile (Join-Path $cache "$($profile.release)-$variant.7z")
        $extractor=Get-VerifiedDownload $matrix.tools.'7zr' (Join-Path $cache '7zr.exe')
        Show-Step (T 'extract')
        Expand-Portable $archive $extractor $destination
        Write-State $destination @{schema=1;status='base_ready';profile=$variant;release=$profile.release;installer=$matrix.installer_version;created_utc=[DateTime]::UtcNow.ToString('o');hardware=$hardware}
    } else { $variant=$null }
    if ($mode -eq 'advanced' -and (Read-Host (T 'outputs_question')) -match '^(s|y)$') {
        $outputPath=Select-Folder (T 'outputs')
        if ($outputPath) {
            Assert-NoReparse $outputPath
            if ($outputPath -match '[%!&|<>^"\r\n]') { throw 'OUTPUT_PATH_UNSAFE' }
            $statePath=Join-Path $destination '_cineconia/install-state.json'
            $state=@{}
            if (Test-Path -LiteralPath $statePath) {
                $old=Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
                foreach ($property in $old.PSObject.Properties) { $state[$property.Name]=$property.Value }
            }
            $state.output_directory=$outputPath
            Write-State $destination $state
        }
    }
    $env:CINECONIA_MODE=$mode
    $env:CIA_AUTHORIZED_DESTINATION=Get-FullPath $destination
    $env:CIA_OPERATION=$operation
    $env:CIA_NO_SHORTCUT=if ($noShortcut) {'1'} else {'0'}
    $env:CIA_PROFILE=$variant
    $env:CIA_BOOTSTRAP_HARDWARE=$hardware | ConvertTo-Json -Compress -Depth 4
    Show-Step (T 'configure')
    & (Join-Path $destination 'python_embeded/python.exe') -s (Join-Path $PSScriptRoot 'instalador.py') $destination $hardware.vendor $variant | Out-Host
    return $LASTEXITCODE
}

if (-not $LibraryOnly) {
    $log=$null; $transcript=$false
    try {
        $logDir=Join-Path $script:Root 'logs'
        [IO.Directory]::CreateDirectory($logDir) | Out-Null
        $log=Join-Path $logDir ('install-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.log')
        Start-Transcript -LiteralPath $log -ErrorAction Stop | Out-Null; $transcript=$true
        $result=Invoke-Setup $CliArgs
        exit $result
    } catch {
        Write-Host ("`n[X] "+$_.Exception.Message) -ForegroundColor Red
        Write-Host (T 'failure_help')
        if ($log) { Write-Host ("Log: "+$log) }
        exit 1
    } finally { if ($transcript) { Stop-Transcript | Out-Null } }
}
