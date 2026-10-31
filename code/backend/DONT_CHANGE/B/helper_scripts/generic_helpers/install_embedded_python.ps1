param([Parameter(Mandatory=$true)][string]$Version, [Parameter(Mandatory=$true)][string]$InstallDir)
$ErrorActionPreference = 'Stop'
try {
    if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw 'Use an exact stable Python version.' }
    $destination = [IO.Path]::GetFullPath($InstallDir)
    # This helper never deletes or overwrites an existing directory.
    if (Test-Path -LiteralPath $destination) { throw "Destination already exists: $destination" }
    $architecture = $env:PROCESSOR_ARCHITECTURE
    if ($env:PROCESSOR_ARCHITEW6432) { $architecture = $env:PROCESSOR_ARCHITEW6432 }
    if ($architecture -ne 'AMD64') { throw "Managed installation supports Windows x64 only; detected $architecture." }
    [IO.Directory]::CreateDirectory($destination) | Out-Null
    $zip = Join-Path $destination 'python.zip.download'
    $url = "https://www.python.org/ftp/python/$Version/python-$Version-embed-amd64.zip"
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $zip -TimeoutSec 120
    # Expand-Archive requires the .zip suffix; all path values are literal arguments.
    $archive = Join-Path $destination 'python.zip'
    Move-Item -LiteralPath $zip -Destination $archive
    Expand-Archive -LiteralPath $archive -DestinationPath $destination
    $python = Join-Path $destination 'python.exe'
    $signature = Get-AuthenticodeSignature -LiteralPath $python
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Python Software Foundation') {
        throw 'Downloaded Python does not have a trusted Python Software Foundation signature.'
    }
    foreach ($binary in Get-ChildItem -LiteralPath $destination -File | Where-Object { $_.Extension -in @('.dll', '.pyd', '.exe') }) {
        $signature = Get-AuthenticodeSignature -LiteralPath $binary.FullName
        if ($signature.Status -ne 'Valid') { throw "Invalid signature on $($binary.Name)" }
    }
    @{url=$url;sha256=(Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash;python=$Version;architecture='amd64'} |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $destination 'download-manifest.json') -Encoding UTF8
    Remove-Item -LiteralPath $archive
    $global:LASTEXITCODE = 0
} catch {
    Write-Host ('[Error] ' + $_.Exception.Message)
    throw
}
