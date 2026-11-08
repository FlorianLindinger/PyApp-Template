# Finds or installs uv and the Python that runs the launcher, then records both in
# tmp\runtime.cmd for the batch fast path (ensure_runtime.bat).
# Called only when that cache is missing or stale. Windows PowerShell 5.1 compatible.
param([string]$Stamp = '', [string]$InstallNewerThan = '')

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'   # Invoke-WebRequest is very slow with its progress bar
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
# uv prints UTF-8; without this, Windows PowerShell 5.1 decodes it with the console code page and
# garbles non-ASCII project paths (e.g. a folder named with umlauts or CJK characters).
$originalOutputEncoding = [Console]::OutputEncoding   # restored at the end (it is shared with the calling console)
[Console]::OutputEncoding = New-Object Text.UTF8Encoding $false
$OutputEncoding = [Console]::OutputEncoding

$bootstrapDir = $PSScriptRoot
$dontChange = [IO.Path]::GetFullPath((Join-Path $bootstrapDir '..'))
$backendDir = [IO.Path]::GetFullPath((Join-Path $dontChange '..'))
$settingsPath = Join-Path $backendDir 'developer_settings.py'
$temporary = Join-Path $dontChange 'tmp'
$cachePath = Join-Path $temporary 'runtime.cmd'
$localUvDir = Join-Path $backendDir 'uv'
$localUvExe = Join-Path $localUvDir 'uv.exe'
# A per-user uv shared by projects, never on PATH: used when the usual uv is too old for a Python.
$userData = $(if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { Join-Path $env:USERPROFILE 'AppData\Local' })
$sharedUvDir = Join-Path $userData 'PyApp-Template\uv'
$sharedUvExe = Join-Path $sharedUvDir 'uv.exe'
$localPythons = Join-Path $backendDir 'pythons'
$localCache = Join-Path $backendDir 'uv-cache'
$environmentDir = Join-Path $backendDir 'environment'
$versionFile = Join-Path $environmentDir '.python-version'
$minimumPython = [version]'3.8'

function Fail([string]$message) { throw [System.Exception]::new($message) }

# Same look as the Python side (scripts/console_tools.py): a cyan step marker and an ERROR badge.
function Write-Step([string]$message) {
    Write-Host ([string][char]0xBB) -ForegroundColor Cyan -NoNewline
    Write-Host (' ' + $message)
}

function Show-Console {
    # Shortcuts start the launcher minimized; restore the window before long work or errors.
    try {
        if (-not ('PyApp.ConsoleWindow' -as [type])) {
            Add-Type -Namespace PyApp -Name ConsoleWindow -MemberDefinition @'
[DllImport("kernel32.dll")] public static extern IntPtr GetConsoleWindow();
[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
'@
        }
        $handle = [PyApp.ConsoleWindow]::GetConsoleWindow()
        if ($handle -ne [IntPtr]::Zero) {
            [PyApp.ConsoleWindow]::ShowWindow($handle, 9) | Out-Null
            [PyApp.ConsoleWindow]::SetForegroundWindow($handle) | Out-Null
        }
    } catch { }
}

function Invoke-Native([string]$exe, [string[]]$arguments) {
    # Captures stdout and stderr separately without PowerShell 5.1 turning stderr into exceptions.
    $saved = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = & $exe @arguments 2>&1
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $saved
    }
    $out = @($output | Where-Object { $_ -isnot [System.Management.Automation.ErrorRecord] } | ForEach-Object { "$_" })
    $err = @($output | Where-Object { $_ -is [System.Management.Automation.ErrorRecord] } | ForEach-Object { "$_" })
    return [pscustomobject]@{ Code = $code; Out = $out; Err = $err }
}

function Invoke-Live([string]$exe, [string[]]$arguments) {
    # Send progress to the console, leaving only the exit code in the success stream.
    $saved = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { & $exe @arguments | Out-Host; return $LASTEXITCODE } finally { $ErrorActionPreference = $saved }
}

# ---------------------------------------------------------------- settings

function Read-Settings {
    # Reads the [bootstrap] settings: top-level, one-line plain literals only. Like Python, the
    # last definition wins (the launcher reports settings that are defined more than once).
    $result = @{}
    foreach ($line in [IO.File]::ReadAllLines($settingsPath, [Text.Encoding]::UTF8)) {
        if ($line -notmatch '^([A-Za-z_][A-Za-z0-9_]*)\s*(?::[^=]*)?=\s*(.*)$') { continue }
        $name = $matches[1]
        $raw = $matches[2].Trim()
        if ($raw.Length -gt 0 -and ($raw[0] -eq '"' -or $raw[0] -eq "'")) {
            $end = $raw.IndexOf($raw[0], 1)
            if ($end -lt 0) { $result.Remove($name); continue }
            $result[$name] = $raw.Substring(1, $end - 1)
        } else {
            $token = ($raw -split '[\s#]', 2)[0]
            switch ($token) {
                'True' { $result[$name] = $true }
                'False' { $result[$name] = $false }
                'None' { $result[$name] = $null }
                default { $result.Remove($name) }   # not a plain literal: use the default
            }
        }
    }
    return $result
}

function Get-Setting($settings, [string]$name, $default) {
    if ($settings.ContainsKey($name)) { return $settings[$name] }
    return $default
}

function Assert-Choice([string]$name, $value, [string[]]$choices) {
    if ($choices -notcontains $value) {
        Fail ("developer_settings.py: $name = '$value' is not valid. Use one of: " + ($choices -join ', ') + ".")
    }
}

# ---------------------------------------------------------------- versions

function ConvertTo-Version([string]$text) {
    $clean = ($text -replace '[^0-9.].*$', '').Trim('.')
    if (-not $clean) { return $null }
    $parts = @($clean.Split('.') | Select-Object -First 4)
    while ($parts.Count -lt 2) { $parts += '0' }
    return [version]($parts -join '.')
}

function Test-VersionSpec([string]$version, [string]$spec) {
    # "" = any; "0.11.32" = exact; ">=0.9,<1" etc.; "~=0.11" = compatible release.
    if (-not $spec -or -not $spec.Trim()) { return $true }
    $actual = ConvertTo-Version $version
    if ($null -eq $actual) { return $false }
    foreach ($clause in $spec.Split(',')) {
        $clause = $clause.Trim()
        if (-not $clause) { continue }
        if ($clause -notmatch '^(>=|<=|==|!=|~=|>|<)?\s*([0-9][0-9.]*)$') { Fail "developer_settings.py: uv_version clause '$clause' is not understood." }
        $op = $matches[1]; $wanted = ConvertTo-Version $matches[2]
        $ok = switch ($op) {
            '>=' { $actual -ge $wanted }
            '<=' { $actual -le $wanted }
            '>' { $actual -gt $wanted }
            '<' { $actual -lt $wanted }
            '!=' { $actual -ne $wanted }
            '~=' {
                $prefix = $matches[2].Split('.'); $prefix = $prefix[0..($prefix.Count - 2)] -join '.'
                ($actual -ge $wanted) -and ("$actual.".StartsWith("$prefix."))
            }
            default { $actual -eq $wanted }
        }
        if (-not $ok) { return $false }
    }
    return $true
}

function Get-ExactVersion([string]$spec) {
    if ($spec -match '^\s*(==)?\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$') { return $matches[2] }
    return $null
}

# ---------------------------------------------------------------- uv

function Get-UvVersion([string]$exe) {
    $result = Invoke-Native $exe @('--version')
    if ($result.Code -ne 0 -or -not $result.Out) { return $null }
    return ($result.Out[0] -split '\s+')[1]
}

function Find-GlobalUv {
    $candidates = @()
    foreach ($command in @(Get-Command uv.exe -All -ErrorAction SilentlyContinue)) { $candidates += $command.Source }
    $installDirs = @($env:UV_INSTALL_DIR, $env:XDG_BIN_HOME, (Join-Path $env:USERPROFILE '.local\bin'), (Join-Path $env:USERPROFILE '.cargo\bin'))
    foreach ($dir in $installDirs) { if ($dir) { $candidates += (Join-Path $dir 'uv.exe') } }
    foreach ($candidate in $candidates) {
        if (-not $candidate -or -not (Test-Path -LiteralPath $candidate)) { continue }
        $full = [IO.Path]::GetFullPath($candidate)
        if ($full.StartsWith($localUvDir + '\', [StringComparison]::OrdinalIgnoreCase)) { continue }
        return $full
    }
    return $null
}

function Get-UvTarget {
    $architecture = $env:PROCESSOR_ARCHITECTURE
    if ($env:PROCESSOR_ARCHITEW6432) { $architecture = $env:PROCESSOR_ARCHITEW6432 }
    switch ($architecture) {
        'AMD64' { return 'x86_64-pc-windows-msvc' }
        'ARM64' { return 'aarch64-pc-windows-msvc' }
        'x86' { return 'i686-pc-windows-msvc' }
        default { Fail "Unsupported Windows architecture '$architecture' for uv." }
    }
}

function Install-Uv([string]$spec, [string]$destination) {
    $target = Get-UvTarget
    $exact = Get-ExactVersion $spec
    $file = "uv-$target.zip"
    if ($exact) { $base = "https://github.com/astral-sh/uv/releases/download/$exact" }
    else { $base = 'https://github.com/astral-sh/uv/releases/latest/download' }
    Show-Console
    Write-Step "Downloading uv $(if ($exact) { $exact } else { '(latest)' }) to $destination..."
    # Next to the destination: Move-Item cannot move a folder to another drive.
    $parent = Split-Path -Parent $destination
    [IO.Directory]::CreateDirectory($parent) | Out-Null
    $stage = Join-Path $parent ('uv-download-' + [Guid]::NewGuid().ToString('N'))
    [IO.Directory]::CreateDirectory($stage) | Out-Null
    try {
        $zip = Join-Path $stage $file
        Invoke-WebRequest -UseBasicParsing -Uri "$base/$file" -OutFile $zip -TimeoutSec 300
        # Saved to a file: Invoke-WebRequest returns this octet-stream as bytes, not text.
        $checksumFile = Join-Path $stage "$file.sha256"
        Invoke-WebRequest -UseBasicParsing -Uri "$base/$file.sha256" -OutFile $checksumFile -TimeoutSec 60
        $expected = ([IO.File]::ReadAllText($checksumFile).Trim() -split '\s+')[0].ToUpperInvariant()
        $actual = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash
        if ($expected -ne $actual) { Fail "The downloaded uv archive does not match its published SHA-256 checksum." }
        $extracted = Join-Path $stage 'extracted'
        Expand-Archive -LiteralPath $zip -DestinationPath $extracted
        $exe = Get-ChildItem -LiteralPath $extracted -Recurse -Filter 'uv.exe' | Select-Object -First 1
        if (-not $exe) { Fail 'The uv archive did not contain uv.exe.' }
        $version = Get-UvVersion $exe.FullName
        if (-not (Test-VersionSpec $version $spec)) { Fail "The latest uv ($version) does not satisfy uv_version '$spec'. Use an exact version in uv_version." }
        $previous = $destination + '.previous'
        if (Test-Path -LiteralPath $previous) { Remove-Item -LiteralPath $previous -Recurse -Force }
        if (Test-Path -LiteralPath $destination) { Move-Item -LiteralPath $destination -Destination $previous }
        Move-Item -LiteralPath $exe.Directory.FullName -Destination $destination
        if (Test-Path -LiteralPath $previous) { Remove-Item -LiteralPath $previous -Recurse -Force -ErrorAction SilentlyContinue }
        Write-Step "uv $version installed in $destination"
        return (Join-Path $destination 'uv.exe')
    } finally {
        Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function Install-GlobalUv([string]$spec) {
    $exact = Get-ExactVersion $spec
    if ($exact) { $url = "https://astral.sh/uv/$exact/install.ps1" } else { $url = 'https://astral.sh/uv/install.ps1' }
    Show-Console
    Write-Step "Installing uv $(if ($exact) { $exact } else { '(latest)' }) for your Windows user with Astral's installer ($url)..."
    $code = Invoke-Live 'powershell.exe' @('-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', "irm '$url' | iex")
    if ($code -ne 0) { Fail "Astral's uv installer failed (exit code $code)." }
    $uv = Find-GlobalUv
    if (-not $uv) { Fail "uv was installed but could not be found. Open a new window and try again." }
    $version = Get-UvVersion $uv
    if (-not (Test-VersionSpec $version $spec)) { Fail "The installed global uv ($version) does not satisfy uv_version '$spec'." }
    return $uv
}

function Resolve-Uv($settings) {
    $prefer = Get-Setting $settings 'uv_prefer' 'global'
    $install = Get-Setting $settings 'uv_install_if_missing' 'global'
    $spec = [string](Get-Setting $settings 'uv_version' '')
    Assert-Choice 'uv_prefer' $prefer @('global', 'local')
    Assert-Choice 'uv_install_if_missing' $install @('global', 'local', 'never')

    $global = Find-GlobalUv
    $local = $null
    if (Test-Path -LiteralPath $localUvExe) { $local = $localUvExe }
    $order = @($global, $local)
    if ($prefer -eq 'local') { $order = @($local, $global) }
    $outdatedGlobal = $null
    foreach ($candidate in $order) {
        if (-not $candidate) { continue }
        $version = Get-UvVersion $candidate
        if ($version -and (Test-VersionSpec $version $spec)) { return $candidate }
        if ($candidate -eq $global) { $outdatedGlobal = "$candidate ($version)" }
    }
    if ($install -eq 'never') {
        Fail ("No usable uv found" + $(if ($outdatedGlobal) { " (global uv $outdatedGlobal does not satisfy uv_version '$spec')" } else { '' }) + " and uv_install_if_missing = 'never'. Install uv or change the uv settings in developer_settings.py.")
    }
    if ($outdatedGlobal) {
        Write-Step "The global uv $outdatedGlobal does not satisfy uv_version '$spec'; it is left unchanged and a local uv is installed instead."
        return Install-Uv $spec $localUvDir
    }
    if ($install -eq 'global') { return Install-GlobalUv $spec }
    return Install-Uv $spec $localUvDir
}

function Test-SharedUvAllowed($settings) {
    # An exact uv_version is a deliberate pin, and "never" means the launcher must not fetch uv.
    if ((Get-Setting $settings 'uv_install_if_missing' 'global') -eq 'never') { return $false }
    return -not (Get-ExactVersion ([string](Get-Setting $settings 'uv_version' '')))
}

function Select-NewestUv($settings, [string]$uv) {
    # The shared uv exists because an older one could not provide a Python: keep using it.
    if (-not (Test-SharedUvAllowed $settings) -or -not (Test-Path -LiteralPath $sharedUvExe)) { return $uv }
    $sharedVersion = Get-UvVersion $sharedUvExe
    if (-not $sharedVersion -or -not (Test-VersionSpec $sharedVersion ([string](Get-Setting $settings 'uv_version' '')))) { return $uv }
    if ((ConvertTo-Version $sharedVersion) -gt (ConvertTo-Version (Get-UvVersion $uv))) { return $sharedUvExe }
    return $uv
}

function Install-NewerSharedUv($settings, [string]$currentUv) {
    # Returns the shared uv when it is newer than $currentUv, otherwise $null; never fails the launch.
    if (-not (Test-SharedUvAllowed $settings)) { return $null }
    $current = ConvertTo-Version (Get-UvVersion $currentUv)
    Write-Step "uv $current cannot provide this Python. Getting the newest uv; the uv on PATH stays as it is."
    try {
        $new = Install-Uv ([string](Get-Setting $settings 'uv_version' '')) $sharedUvDir
    } catch {
        Write-Step "Could not get a newer uv: $($_.Exception.Message)"
        return $null
    }
    if ((ConvertTo-Version (Get-UvVersion $new)) -le $current) { return $null }
    return $new
}

# ---------------------------------------------------------------- Python

function Set-UvEnvironment($settings, [string]$source) {
    foreach ($name in @('UV_PYTHON', 'UV_PYTHON_INSTALL_DIR', 'UV_MANAGED_PYTHON', 'UV_NO_MANAGED_PYTHON', 'UV_PYTHON_PREFERENCE', 'UV_PYTHON_INSTALL_BIN', 'UV_PYTHON_INSTALL_REGISTRY', 'UV_PROJECT_ENVIRONMENT', 'UV_PROJECT', 'UV_WORKING_DIR', 'VIRTUAL_ENV')) {
        Remove-Item "Env:$name" -ErrorAction SilentlyContinue
    }
    $visible = [bool](Get-Setting $settings 'uv_user_python_visible_globally' $true)
    switch ($source) {
        'uv_user' {
            $env:UV_MANAGED_PYTHON = '1'
            $env:UV_PYTHON_INSTALL_BIN = $(if ($visible) { '1' } else { '0' })
            $env:UV_PYTHON_INSTALL_REGISTRY = $(if ($visible) { '1' } else { '0' })
        }
        'local' {
            $env:UV_PYTHON_INSTALL_DIR = $localPythons
            $env:UV_MANAGED_PYTHON = '1'
            $env:UV_PYTHON_INSTALL_BIN = '0'
            $env:UV_PYTHON_INSTALL_REGISTRY = '0'
        }
    }
    if ((Get-Setting $settings 'uv_cache' 'global') -eq 'local') { $env:UV_CACHE_DIR = $localCache }
    if ([bool](Get-Setting $settings 'use_system_certificates' $false)) { $env:UV_SYSTEM_CERTS = '1' }
    $env:UV_PYTHON_DOWNLOADS = 'automatic'
}

function Remove-BrokenPythonLinks {
    # uv links minor versions (e.g. cpython-3.14-...) to the newest patch with junctions,
    # which keep absolute targets. After moving the project they point nowhere.
    if (-not (Test-Path -LiteralPath $localPythons)) { return }
    foreach ($item in Get-ChildItem -LiteralPath $localPythons -Directory -Force -ErrorAction SilentlyContinue) {
        if (-not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { continue }
        $target = @($item.Target) | Select-Object -First 1
        if (-not $target -or -not (Test-Path -LiteralPath $target)) {
            [IO.Directory]::Delete($item.FullName, $false)   # removes only the link
        }
    }
}

function Get-PythonDownloads([string]$uv, [switch]$All) {
    $arguments = @('python', 'list', '--only-downloads', '--output-format', 'json')
    if ($All) { $arguments += '--all-versions' }
    $result = Invoke-Native $uv $arguments
    if ($result.Code -ne 0) { return @() }
    return @(($result.Out -join "`n") | ConvertFrom-Json | Where-Object { $_.implementation -eq 'cpython' -and $_.variant -eq 'default' })
}

function Get-NewestStablePython([string]$uv) {
    $stable = @(Get-PythonDownloads $uv | Where-Object { $_.version -match '^\d+\.\d+\.\d+$' } | Sort-Object { [version]$_.version } -Descending)
    if (-not $stable) { Fail 'uv could not list downloadable Python versions (no internet?). Set python_version, e.g. "3.14".' }
    $v = [version]$stable[0].version
    return "$($v.Major).$($v.Minor)"
}

function Get-AvailableSummary([string]$uv) {
    $versions = @(Get-PythonDownloads $uv -All | ForEach-Object { $_.version } | Sort-Object { ConvertTo-Version $_ } -Unique)
    if (-not $versions) { return 'uv could not list the downloadable versions (no internet?).' }
    $minors = @($versions | ForEach-Object { $v = ConvertTo-Version $_; "$($v.Major).$($v.Minor)" } | Select-Object -Unique)
    return "uv offers $($versions[0]) to $($versions[-1]) for this PC (minor versions: $($minors -join ', '))."
}

function Get-PythonVersion([string]$python) {
    $result = Invoke-Native $python @('-I', '-S', '-c', "import sys; print('%d.%d.%d' % sys.version_info[:3])")
    if ($result.Code -ne 0 -or -not $result.Out) { return $null }
    return $result.Out[0].Trim()
}

function Find-Python([string]$uv, [string]$request) {
    $arguments = @('python', 'find', '--no-project')
    if ($request) { $arguments += $request }
    $result = Invoke-Native $uv $arguments
    if ($result.Code -ne 0 -or -not $result.Out) { return $null }
    return $result.Out[-1].Trim()
}

function Resolve-Python($settings, [string]$uv) {
    $source = Get-Setting $settings 'python_source' 'uv_user'
    Assert-Choice 'python_source' $source @('local', 'uv_user')
    Set-UvEnvironment $settings $source
    Remove-BrokenPythonLinks

    # The project's current Python (backend\environment\.python-version) runs the launcher; the launcher
    # itself offers the migration when python_version in the settings differs from it.
    $request = ''
    if (Test-Path -LiteralPath $versionFile) {
        $request = @([IO.File]::ReadAllLines($versionFile) | ForEach-Object { $_.Trim() } | Where-Object { $_ -and -not $_.StartsWith('#') }) | Select-Object -First 1
    }
    if (-not $request) { $request = [string](Get-Setting $settings 'python_version' '3.14') }

    # Outside the project: uv would otherwise discover backend\environment\.venv as "the" Python.
    Push-Location ([IO.Path]::GetTempPath())
    try {
        if (-not $request) {
            $request = Get-NewestStablePython $uv
            Write-Step "python_version is empty: using the newest stable Python, $request."
        }
        $python = Find-Python $uv $request
        if (-not $python) {
            Show-Console
            Write-Step "Installing Python $request with uv..."
            $code = Invoke-Live $uv @('python', 'install', $request)
            if ($code -ne 0) {
                $newer = Install-NewerSharedUv $settings $uv
                if ($newer) {
                    $uv = $newer
                    $script:currentUv = $newer
                    $code = Invoke-Live $uv @('python', 'install', $request)
                }
            }
            if ($code -ne 0) {
                Fail ("uv could not install Python '$request'. " + (Get-AvailableSummary $uv) + " The launcher needs Python 3.8 or newer. Check python_version in developer_settings.py.")
            }
            $python = Find-Python $uv $request
            if (-not $python) { Fail "Python $request was installed but uv cannot find it." }
        }
    } finally {
        Pop-Location
    }

    $version = Get-PythonVersion $python
    if (-not $version) { Fail "The Python at '$python' does not start." }
    if ((ConvertTo-Version $version) -lt $minimumPython) {
        Fail "Python $version at '$python' is older than 3.8, which the launcher needs. Choose python_version 3.8 or newer in developer_settings.py."
    }
    return $python
}

# ---------------------------------------------------------------- project folder

function Move-ProjectFilesIntoEnvironment {
    # Creates code\backend\environment and moves files from where older versions kept them.
    [IO.Directory]::CreateDirectory($environmentDir) | Out-Null
    foreach ($name in @('pyproject.toml', 'uv.lock', '.python-version', '.venv')) {
        $old = Join-Path $backendDir $name
        $new = Join-Path $environmentDir $name
        if ((Test-Path -LiteralPath $old) -and -not (Test-Path -LiteralPath $new)) {
            try { Move-Item -LiteralPath $old -Destination $new }
            catch { Fail "Could not move '$name' into $environmentDir. Close the running app and programs using it, then start again. ($($_.Exception.Message))" }
        }
    }
}

# ---------------------------------------------------------------- main

$lock = $null
try {
    [IO.Directory]::CreateDirectory($temporary) | Out-Null
    $deadline = [DateTime]::UtcNow.AddMinutes(10)
    while ($null -eq $lock) {
        try { $lock = [IO.File]::Open((Join-Path $temporary 'bootstrap.lock'), 'OpenOrCreate', 'ReadWrite', 'None') }
        catch [IO.IOException] {
            if ([DateTime]::UtcNow -gt $deadline) { Fail 'Another launcher is still preparing uv/Python.' }
            Start-Sleep -Milliseconds 100
        }
    }
    $settings = Read-Settings
    if ($InstallNewerThan) {
        # Called by the launcher (scripts/env/uv.py) when changing the project's Python.
        if (Install-NewerSharedUv $settings $InstallNewerThan) { exit 0 }
        exit 1
    }
    Move-ProjectFilesIntoEnvironment
    $script:currentUv = Select-NewestUv $settings (Resolve-Uv $settings)
    $python = Resolve-Python $settings $script:currentUv
    $uv = $script:currentUv

    # ensure_runtime.bat skips its code page switch for caches whose first line is "rem ascii".
    $ascii = (($uv + $python + $Stamp) -cmatch '^[\x20-\x7E]*$')
    $lines = @(
        $(if ($ascii) { 'rem ascii' } else { 'rem utf-8' }),
        'rem Generated by resolve_runtime.ps1. Delete this file to force a new uv/Python lookup.',
        ('set "PYAPP_UV=' + $uv.Replace('%', '%%') + '"'),
        ('set "PYAPP_PYTHON=' + $python.Replace('%', '%%') + '"'),
        ('set "PYAPP_CACHED_STAMP=' + $Stamp.Replace('%', '%%') + '"')
    )
    [IO.File]::WriteAllText($cachePath, (($lines -join "`r`n") + "`r`n"), (New-Object Text.UTF8Encoding $false))
    exit 0
} catch {
    Show-Console
    Write-Host ''
    Write-Host ' ERROR ' -ForegroundColor White -BackgroundColor DarkRed -NoNewline
    Write-Host (' ' + $_.Exception.Message)
    Write-Host ''
    exit 1
} finally {
    if ($lock) { $lock.Dispose() }
    try { [Console]::OutputEncoding = $originalOutputEncoding } catch { }
}
