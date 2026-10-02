# Windows PowerShell 5.1 entry point; ASCII source, UTF-8 translations.
param([switch]$LibraryOnly, [Parameter(ValueFromRemainingArguments=$true)][string[]]$CliArgs)
$script:Root = Split-Path $PSScriptRoot -Parent
$script:Texts = @{}
$script:ScanLimited = $false
$script:DriverNotice = $null
# Same folder name as 2.x; a taken name gets -2, -3...
$script:FolderName = 'ComfyUI'

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
# Numbered steps as in 2.x: 3 here and 11 in src\instalador.py (TITULOS). They
# reach its final summary through CIA_PASOS_BAT and CIA_PASO1..n.
$script:StepTotal = 14
$script:StepN = 0
$script:StepTitle = $null
function Start-Step([string]$Title) {
    $script:StepN++; $script:StepTitle = $Title
    Write-Host ("`n[{0}/{1}] {2}" -f $script:StepN,$script:StepTotal,$Title) -ForegroundColor DarkYellow
}
function Complete-Step([string]$Detail, [string]$State='ok') {
    $env:CIA_PASOS_BAT = [string]$script:StepN
    Set-Item -LiteralPath ("env:CIA_PASO$($script:StepN)") -Value ("{0}|{1}|{2}" -f $script:StepTitle,$Detail,$State)
    if ($State -ne 'ok') { return }
    $mark = if ($env:WT_SESSION) { [string][char]0x2713 } else { 'OK' }
    $line = ("[{0}/{1}] {2} " -f $script:StepN,$script:StepTotal,$script:StepTitle).PadRight(49,'.')
    Write-Host ("   $line $mark $Detail") -ForegroundColor Green
}
function Skip-Step([string]$Title, [string]$Detail) {
    $script:StepN++; $script:StepTitle = $Title
    Complete-Step $Detail 'omitido'
}
# Single seam for answers, so tests never wait for a keyboard.
function Read-Choice([string]$Prompt) { Read-Host $Prompt }
function Read-Option([string[]]$Valid) {
    while ($true) {
        $choice = ([string](Read-Choice ('   '+(T 'choose')))).Trim()
        if (-not $choice) { $choice = '1' }
        if ($choice -in $Valid) { return $choice }
    }
}
function Confirm-Change([string]$Text) {
    Write-Host $Text -ForegroundColor Yellow
    return ([string](Read-Choice (T 'confirm'))).Trim() -ceq (T 'confirm_word')
}
function Format-SetupError([string]$Message) {
    # Codes look like PATH_NOT_EMPTY or PATH_NOT_EMPTY: detail.
    if ($Message -match '^([A-Z0-9_]+)(?::\s*(.*))?$') {
        $code = $Matches[1]; $detail = [string]$Matches[2]
        if ($script:Texts.ContainsKey("setup.error.$code")) {
            return [pscustomobject]@{code=$code; text=$script:Texts["setup.error.$code"].Replace('{detail}',$detail)}
        }
    }
    return [pscustomobject]@{code=$null; text=$Message}
}
function Write-SetupError([string]$Message) {
    $e = Format-SetupError $Message
    Write-Host ("`n   [X] "+$e.text) -ForegroundColor Red
    # The code stays visible for support and in the log.
    if ($e.code) { Write-Host ('       '+(T 'error_code')+' '+$Message) -ForegroundColor DarkGray }
}
function Format-Argument([string]$Value) {
    # Windows command-line quoting, as parsed by Python and powershell.exe.
    if ($Value.Length -and $Value -notmatch '[\s"]') { return $Value }
    $escaped = [regex]::Replace($Value, '(\\*)"', { param($m) ($m.Groups[1].Value * 2) + '\"' })
    $escaped = [regex]::Replace($escaped, '(\\+)$', { param($m) $m.Groups[1].Value * 2 })
    return '"' + $escaped + '"'
}
function Invoke-Console([string]$FilePath, [string[]]$ArgumentList) {
    # Inherit this console. A pipe (| Out-Host) makes Python and progreso.ps1
    # believe output is redirected: live progress bars stop drawing and Python
    # buffers its messages for minutes.
    $info = New-Object Diagnostics.ProcessStartInfo
    $info.FileName = $FilePath
    $info.Arguments = (@($ArgumentList | ForEach-Object { Format-Argument $_ }) -join ' ')
    $info.UseShellExecute = $false
    $process = [Diagnostics.Process]::Start($info)
    try { $process.WaitForExit(); return $process.ExitCode } finally { $process.Dispose() }
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
function Test-LinkItem($Item) {
    # Junctions and symlinks can loop or point elsewhere. OneDrive folders are
    # also reparse points, but they are real folders: LinkType stays empty.
    return [bool]($Item.LinkType -in @('Junction','SymbolicLink'))
}
function Test-OneDrive([string]$Path) {
    foreach ($root in @($env:OneDrive,$env:OneDriveConsumer,$env:OneDriveCommercial)) {
        if ($root -and (Test-Within $Path $root)) { return $true }
    }
    return [bool]((Get-FullPath $Path) -match '\\OneDrive( - [^\\]+)?(\\|$)')
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
    # Accents and the letter n with tilde break some nodes and pip packages.
    if ($Path -match '[^\x20-\x7E]') { throw 'PATH_NON_ASCII' }
    $full = Get-FullPath $Path
    if ($full.Length -le 3) { throw 'PATH_DRIVE_ROOT' }
    # OneDrive would sync thousands of files and may leave them cloud-only.
    if (Test-OneDrive $full) { throw 'PATH_ONEDRIVE' }
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
    if ($drive.AvailableFreeSpace -lt $MinimumGB*1GB) { throw "DISK_SPACE: $MinimumGB" }
    # Probe inside the new folder, never a user's existing installation. Standard
    # users may create folders at C:\ but not files, so the parent is not probed.
    [IO.Directory]::CreateDirectory($full) | Out-Null
    $probe = Join-Path $full ('.cineconia-write-'+[guid]::NewGuid().ToString('N'))
    try { [IO.File]::WriteAllText($probe,'test') }
    finally {
        if (Test-Path -LiteralPath $probe) { Remove-Item -LiteralPath $probe -Force }
        # Remove only the empty folders this check created.
        $current = $full
        while ($current -and -not $current.TrimEnd('\').Equals($ancestor.TrimEnd('\'),[StringComparison]::OrdinalIgnoreCase)) {
            if (@(Get-ChildItem -LiteralPath $current -Force).Count) { break }
            Remove-Item -LiteralPath $current
            $current = Split-Path $current -Parent
        }
    }
    return $full
}
function Get-DriveMedia([string]$Root, [object[]]$Disks) {
    # SSD, HDD or empty when Windows does not report it. CIM directly: the
    # Get-PhysicalDisk cmdlet can take more than ten seconds.
    try {
        $letter = $Root.Substring(0,1)
        $partition = Get-CimInstance -Namespace root/Microsoft/Windows/Storage -ClassName MSFT_Partition -Filter "DriveLetter='$letter'" -ErrorAction Stop | Select-Object -First 1
        $disk = $Disks | Where-Object { [string]$_.DeviceId -eq [string]$partition.DiskNumber } | Select-Object -First 1
        if ($disk) {
            $media = [string]$disk.MediaType
            if ($media -in @('SSD','4')) { return 'SSD' }
            if ($media -in @('HDD','3')) { return 'HDD' }
        }
    } catch { }
    return ''
}
function Get-DefaultParent([double]$MinimumGB=20) {
    # Prefer an SSD with room; among equals, the disk with the most free space.
    $disks = @(try { Get-CimInstance -Namespace root/Microsoft/Windows/Storage -ClassName MSFT_PhysicalDisk -ErrorAction Stop } catch { })
    $drives = @([IO.DriveInfo]::GetDrives() | Where-Object { $_.DriveType -eq [IO.DriveType]::Fixed -and $_.IsReady } | ForEach-Object {
        $media = Get-DriveMedia $_.RootDirectory.FullName $disks
        [pscustomobject]@{root=$_.RootDirectory.FullName; free=$_.AvailableFreeSpace; media=$media;
            rank=$(if ($_.AvailableFreeSpace -lt $MinimumGB*1GB) {3} elseif ($media -eq 'SSD') {0} elseif ($media -eq 'HDD') {2} else {1})}
    } | Sort-Object rank, @{Expression='free';Descending=$true})
    if (-not $drives.Count) { return $null }
    return $drives[0]
}
function Get-FreeDestination([string]$Parent) {
    for ($n = 1; $n -le 99; $n++) {
        $name = if ($n -eq 1) { $script:FolderName } else { "$($script:FolderName)-$n" }
        $candidate = Join-Path $Parent $name
        if (-not (Test-Path -LiteralPath $candidate)) { return $candidate }
        if ((Test-Path -LiteralPath $candidate -PathType Container) -and -not @(Get-ChildItem -LiteralPath $candidate -Force).Count) { return $candidate }
    }
    throw "PATH_NOT_EMPTY: $(Join-Path $Parent $script:FolderName)"
}
function Select-Destination([object[]]$Existing, [double]$MinimumGB) {
    # Recommended: one proposal, Enter accepts. A rejected folder asks again
    # with the reason instead of closing the installer.
    $destination = $null
    $default = Get-DefaultParent $MinimumGB
    if ($default) {
        $destination = Get-FreeDestination $default.root
        $media = if ($default.media) { "$($default.media), " } else { '' }
        $info = '{0}{1} GB {2}' -f $media,[math]::Floor($default.free/1GB),(T 'free')
    }
    while ($true) {
        $answer = 'c'
        if ($destination) {
            Write-Host ("`n   "+(T 'destination_default')+' ') -NoNewline
            Write-Host $destination -ForegroundColor Green -NoNewline
            if ($info) { Write-Host "  ($info)" -ForegroundColor DarkGray } else { Write-Host '' }
            $answer = [string](Read-Choice ('   '+(T 'destination_accept')))
        }
        if ($answer.Trim() -match '^[cC]') {
            $parent = Select-Folder (T 'destination')
            if (-not $parent) { Write-Host ('   '+(T 'cancelled')); return $null }
            $info = $null
        } elseif ($answer.Trim()) { continue }
        try {
            if ($answer.Trim()) { $destination = Get-FreeDestination $parent }
            $direct = Get-Installation $destination
            $all = @($Existing) + @($direct | Where-Object { $_ })
            return (Assert-Destination $destination $all $MinimumGB)
        } catch {
            Write-SetupError $_.Exception.Message
            Write-Host ('   '+(T 'destination_retry')) -ForegroundColor Yellow
            $destination = $null
        }
    }
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
        $Roots = @([Environment]::GetFolderPath('MyDocuments'),[Environment]::GetFolderPath('Desktop'),(Join-Path $env:USERPROFILE 'Downloads'),$env:OneDrive)
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
        if (-not $item -or (Test-LinkItem $item)) { continue }
        $install=Get-Installation $path
        if ($install) { $found[$install.root.ToLowerInvariant()]=$install; continue }
        if ($depth -ge 6) { $script:ScanLimited=$true; continue }
        foreach ($child in @(Get-ChildItem -LiteralPath $path -Directory -Force -ErrorAction SilentlyContinue)) {
            if ($child.Name -match '^(\.|\$|Windows$|Program Files|ProgramData$|AppData$|Users$|node_modules$|models$|custom_nodes$|python_embeded$|venv$|site-packages$|System Volume Information$)') { continue }
            if (Test-LinkItem $child) { continue }
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
    $data=[ordered]@{os=$osInfo.Caption; cpu=([string]$cpuInfo.Name).Trim(); ram_gb=[math]::Round($systemInfo.TotalPhysicalMemory/1GB,1); gpu=$null; vendor=$null; vram_gb=$null; driver=$null; compute=$null; pcie_gen=$null; pcie_lanes=$null; memory_bus=$null; python=$null; git=$null}
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
function Show-Hardware($Hardware) {
    foreach ($p in $Hardware.PSObject.Properties) {
        $value = if ($null -ne $p.Value -and "$($p.Value)") { "$($p.Value)" } else { T 'unavailable' }
        if ($p.Name -in @('ram_gb','vram_gb') -and $null -ne $p.Value) { $value += ' GB' }
        Write-Host ('   {0,-18} {1}' -f (T "hw_$($p.Name)"),$value)
    }
}
function Select-Profile($Hardware, $Matrix, [string]$Cuda) {
    $script:DriverNotice = $null
    if (-not $Hardware.vendor) { throw 'GPU_UNKNOWN' }
    $variant=$Hardware.vendor
    if ($variant -eq 'nvidia') {
        if (-not $Hardware.compute -or -not $Hardware.driver) { throw 'GPU_CAPABILITY_UNKNOWN' }
        $cap=[double]::Parse([string]$Hardware.compute,[Globalization.CultureInfo]::InvariantCulture)
        if ($cap -lt 7.5) { $variant='nvidia_cu126' }
        elseif ($cap -lt 10 -and [version]$Hardware.driver -lt [version]'580.0') {
            # Works with CUDA 12.6 now; a driver update would allow CUDA 13.
            $variant='nvidia_cu126'
            if (-not $Cuda) { $script:DriverNotice=[string]$Hardware.driver }
        }
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
    $code=Invoke-Console (Join-Path $PSHOME 'powershell.exe') @('-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path $PSScriptRoot 'progreso.ps1'),'-Modo','descargar','-Url',$Spec.url,'-Salida',$part,'-Nombre',(Split-Path $Path -Leaf),'-Reanudar')
    if ($code -ne 0) { throw 'DOWNLOAD_FAILED' }
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
    $code=Invoke-Console (Join-Path $PSHOME 'powershell.exe') @('-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path $PSScriptRoot 'progreso.ps1'),'-Modo','extraer','-SieteZip',$Extractor,'-Archivo',$Archive,'-Destino',$stage)
    if ($code -ne 0) { throw "EXTRACTION_FAILED: $stage" }
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
function Remove-DownloadCache([string]$Cache, [string[]]$Files) {
    # The package is no longer needed after extraction: frees about 2 GB.
    foreach ($file in $Files) {
        if ($file -and (Test-Path -LiteralPath $file -PathType Leaf)) { Remove-Item -LiteralPath $file -Force -ErrorAction SilentlyContinue }
    }
    if ((Test-Path -LiteralPath $Cache) -and -not @(Get-ChildItem -LiteralPath $Cache -Force).Count) {
        Remove-Item -LiteralPath $Cache -ErrorAction SilentlyContinue
    }
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
    $env:CIA_INICIO=[string][DateTimeOffset]::Now.ToUnixTimeSeconds()
    $matrix=Read-Config 'compatibility_matrix'
    Show-Step ("CineConIA $($matrix.installer_version) - "+(T 'title'))
    if (-not [Environment]::Is64BitOperatingSystem -or $env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { throw 'WINDOWS_X64_REQUIRED' }
    Start-Step (T 'step_check')
    $hardware=Get-Hardware
    Show-Hardware $hardware
    Write-Host ("`n   "+(T 'search')) -ForegroundColor DarkGray
    $existing=@(Find-Installations)
    if ($script:ScanLimited) { Write-Host ('   '+(T 'scan_limited')) -ForegroundColor Yellow }
    if (-not $existing.Count) { Write-Host ('   '+(T 'none_found')) }
    foreach ($install in $existing) { Write-Host ('   '+$install.root) -ForegroundColor Green }
    Complete-Step $(if ($hardware.gpu) { [string]$hardware.gpu } else { T 'unavailable' })
    if ($diagnose) { Write-Host ("`n   "+(T 'diagnose_done')); return 0 }
    if (-not (Get-Command curl.exe -ErrorAction SilentlyContinue)) { throw 'CURL_REQUIRED' }
    $operation='new'
    if ($mode -eq 'advanced' -and -not $destination) {
        Write-Host ("`n   1) "+(T 'new_install'))
        Write-Host ('   2) '+(T 'manual'))
        if ((Read-Option @('1','2')) -eq '2') {
            $manual=Select-Folder (T 'manual')
            if (-not $manual) { Write-Host ('   '+(T 'cancelled')); return 2 }
            $selected=Get-Installation $manual
            if (-not $selected) { throw 'INSTALLATION_NOT_FOUND' }
            $existing=@($selected)
        }
    }
    if ($existing.Count -and -not $destination) {
        Write-Host ("`n   "+(T 'existing_menu'))
        $valid=@('1','2')
        if ($mode -eq 'advanced') { Write-Host (T 'maintenance_menu'); $valid+='3' }
        $choice=Read-Option $valid
        if ($choice -eq '1') { Write-Host ("`n   "+(T 'reuse_unchanged')) -ForegroundColor Green; return 0 }
        if ($choice -eq '3') {
            # Only maintenance needs to know which installation.
            for ($n=0;$n -lt $existing.Count;$n++) { Write-Host ("   $($n+1)) "+$existing[$n].root) }
            $index=[int](Read-Option @(1..$existing.Count | ForEach-Object { [string]$_ }))
            $selected=$existing[$index-1]
            if (-not $selected.portable) { throw 'MAINTENANCE_PORTABLE_ONLY' }
            if (-not (Confirm-Change ('   '+(T 'maintenance_confirm')+' '+$selected.root))) { Write-Host ('   '+(T 'cancelled')); return 2 }
            $destination=$selected.root; Assert-NoReparse $destination; $operation='maintenance'
        }
    }
    $variant=$null
    if ($operation -eq 'new') {
        # Hardware limits first: never ask for a folder an unsupported GPU cannot use.
        $variant=Select-Profile $hardware $matrix $cuda
        if ($script:DriverNotice) {
            Write-Host ("`n   "+(T 'driver_notice').Replace('{driver}',$script:DriverNotice)) -ForegroundColor Yellow
            if ($mode -eq 'advanced') {
                Write-Host ('   1) '+(T 'driver_continue'))
                Write-Host ('   2) '+(T 'driver_open'))
                if ((Read-Option @('1','2')) -eq '2') {
                    Start-Process 'https://www.nvidia.com/drivers'
                    Write-Host ('   '+(T 'driver_then_rerun')); return 0
                }
            }
        }
        if ($destination) {
            # Also inspect an explicitly selected destination outside the bounded search.
            $direct=Get-Installation $destination
            if ($direct) { $existing+=@($direct) }
            $destination=Assert-Destination $destination $existing $matrix.minimum_free_gb
        } else {
            $destination=Select-Destination $existing $matrix.minimum_free_gb
            if (-not $destination) { return 2 }
        }
        $profile=$matrix.profiles.$variant
        Write-Host ("`n   "+(T 'plan')+" $variant / ComfyUI $($profile.release) / $destination")
        # Same disk as the destination: its free space was checked, and it is never OneDrive.
        $cache=Join-Path (Split-Path $destination -Parent) '.cineconia-cache'
        Start-Step (T 'step_download')
        $archive=Get-VerifiedDownload $profile (Join-Path $cache "$($profile.release)-$variant.7z")
        $extractor=Get-VerifiedDownload $matrix.tools.'7zr' (Join-Path $cache '7zr.exe')
        Complete-Step ("ComfyUI $($profile.release) ($variant) - "+(T 'step_verified'))
        Start-Step (T 'step_extract')
        Expand-Portable $archive $extractor $destination
        Remove-DownloadCache $cache @($archive,$extractor)
        Complete-Step (T 'cleanup')
        Write-State $destination @{schema=1;status='base_ready';profile=$variant;release=$profile.release;installer=$matrix.installer_version;created_utc=[DateTime]::UtcNow.ToString('o');hardware=$hardware}
    } else {
        Skip-Step (T 'step_download') (T 'step_existing')
        Skip-Step (T 'step_extract') (T 'step_existing')
    }
    if ($mode -eq 'advanced' -and ([string](Read-Choice ('   '+(T 'outputs_question')))).Trim() -match '^(s|y)') {
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
    $arguments=@('-s',(Join-Path $PSScriptRoot 'instalador.py'),$destination)
    if ($hardware.vendor) { $arguments+=[string]$hardware.vendor; if ($variant) { $arguments+=$variant } }
    return (Invoke-Console (Join-Path $destination 'python_embeded\python.exe') $arguments)
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
        if (-not $script:Texts.Count) { try { Initialize-Language $null } catch { } }
        Write-SetupError $_.Exception.Message
        Write-Host ("`n   "+(T 'failure_help'))
        if ($log) { Write-Host ('   '+(T 'log')+' '+$log) -ForegroundColor DarkGray }
        exit 1
    } finally { if ($transcript) { Stop-Transcript | Out-Null } }
}
