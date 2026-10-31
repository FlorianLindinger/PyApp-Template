$ErrorActionPreference = 'Stop'
$backend = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$temporary = Join-Path $backend 'temporary'
[IO.Directory]::CreateDirectory($temporary) | Out-Null
$lock = $null
$stage = $null
try {
    $deadline = [DateTime]::UtcNow.AddMinutes(10)
    while ($null -eq $lock) {
        try { $lock = [IO.File]::Open((Join-Path $temporary 'backend-install.lock'), 'OpenOrCreate', 'ReadWrite', 'None') }
        catch [IO.IOException] {
            if ([DateTime]::UtcNow -gt $deadline) { throw 'Another backend installation is still running.' }
            Start-Sleep -Milliseconds 100
        }
    }
    $values = @{}
    Get-Content -LiteralPath (Join-Path $backend 'settings\backend_settings.ini') | ForEach-Object {
        if ($_ -match '^\s*([^;#=]+?)\s*=\s*(.*?)\s*$') { $values[$matches[1]] = $matches[2] }
    }
    $version = $values['backend_python_version']
    if ($version -notmatch '^\d+\.\d+\.\d+$') { throw 'Invalid backend Python version.' }
    $settingsDir = Join-Path $backend 'settings'
    $runtime = Join-Path $backend 'backend_python'
    $packages = Join-Path $backend 'backend_packages'
    $finish = Join-Path $backend 'scripts\setup\finish_backend_installation.py'
    if ([IO.Path]::GetFullPath((Join-Path $settingsDir $values['backend_python_install_dir_relative_path'])) -ne $runtime -or
        [IO.Path]::GetFullPath((Join-Path $settingsDir $values['backend_python_finish_installation_relative_path'])) -ne $finish) {
        throw 'Backend configuration points outside the supported runtime/finalization locations.'
    }
    $requirements = Join-Path $settingsDir 'backend_packages.txt'
    $fingerprint = ((Get-FileHash -LiteralPath $requirements -Algorithm SHA256).Hash +
        (Get-FileHash -LiteralPath (Join-Path $settingsDir 'backend_build_tools.txt') -Algorithm SHA256).Hash + $version)
    $health = Join-Path $backend 'scripts\setup\check_backend.py'
    $python = Join-Path $runtime 'python.exe'
    $marker = Join-Path $runtime 'installation-complete.txt'
    if (Test-Path -LiteralPath $python) {
        $savedPreference = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        & $python $health $version $requirements 2>$null
        $healthy = $LASTEXITCODE -eq 0
        $ErrorActionPreference = $savedPreference
        if ($healthy) {
            # Adopt older installations only after validating actual imports and exact versions.
            [IO.File]::WriteAllText($marker, $fingerprint)
            exit 0
        }
    }
    $architecture = $env:PROCESSOR_ARCHITECTURE
    if ($env:PROCESSOR_ARCHITEW6432) { $architecture = $env:PROCESSOR_ARCHITEW6432 }
    if ($architecture -ne 'AMD64') { throw "Managed installation supports Windows x64 only; detected $architecture. Native ARM64/x86 packages are not provided by this template." }
    $stage = Join-Path $temporary ('backend-install-' + [Guid]::NewGuid().ToString('N'))
    [IO.Directory]::CreateDirectory($stage) | Out-Null
    $stagedRuntime = Join-Path $stage 'backend_python'
    $stagedPackages = Join-Path $stage 'backend_packages'
    & (Join-Path $PSScriptRoot 'generic_helpers\install_embedded_python.ps1') -Version $version -InstallDir $stagedRuntime
    if ($LASTEXITCODE -ne 0) { throw 'Embedded Python download/extraction failed.' }
    $env:PYAPP_BACKEND_STAGING = $stagedRuntime
    $env:PYAPP_PACKAGES_STAGING = $stagedPackages
    $env:PYTHONDONTWRITEBYTECODE = '1'
    & (Join-Path $stagedRuntime 'python.exe') $finish
    if ($LASTEXITCODE -ne 0) { throw 'Backend dependency finalization failed; existing runtime retained.' }
    & (Join-Path $stagedRuntime 'python.exe') $health $version $requirements
    if ($LASTEXITCODE -ne 0) { throw 'Staged backend failed its health check.' }
    [IO.File]::WriteAllText((Join-Path $stagedRuntime 'installation-complete.txt'), $fingerprint)
    $movedOld = @()
    $movedNew = @()
    try {
        foreach ($target in @($runtime, $packages)) {
            if (Test-Path -LiteralPath ($target + '.previous')) { throw "Inspect the retained backup before reinstalling: $target.previous" }
        }
        foreach ($target in @($runtime, $packages)) {
            if (Test-Path -LiteralPath $target) {
                Move-Item -LiteralPath $target -Destination ($target + '.previous')
                $movedOld += $target
            }
        }
        Move-Item -LiteralPath $stagedRuntime -Destination $runtime
        $movedNew += $runtime
        Move-Item -LiteralPath $stagedPackages -Destination $packages
        $movedNew += $packages
    } catch {
        foreach ($target in $movedNew) {
            # All targets are fixed children of this backend, never user-supplied paths.
            if ([IO.Path]::GetDirectoryName($target) -ne $backend) { throw 'Unexpected replacement target.' }
            Remove-Item -LiteralPath $target -Recurse -Force
        }
        foreach ($target in $movedOld) { Move-Item -LiteralPath ($target + '.previous') -Destination $target }
        throw
    }
    foreach ($target in $movedOld) {
        if ([IO.Path]::GetDirectoryName($target) -ne $backend) { throw 'Unexpected backup target.' }
        try { Remove-Item -LiteralPath ($target + '.previous') -Recurse -Force }
        catch { Write-Warning "Previous backend retained at $target.previous; the new installation is healthy." }
    }
    exit 0
} catch {
    Write-Host ('[Error] ' + $_.Exception.Message)
    if ($stage) { Write-Host "Installation diagnostics retained in $stage" }
    exit 1
} finally {
    Remove-Item Env:PYAPP_BACKEND_STAGING -ErrorAction SilentlyContinue
    Remove-Item Env:PYAPP_PACKAGES_STAGING -ErrorAction SilentlyContinue
    if ($lock) { $lock.Dispose() }
}
