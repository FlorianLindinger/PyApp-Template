# Prints the longest paths below PYAPP_LP_ROOT; started by tools\show_longest_paths.bat.
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath($env:PYAPP_LP_ROOT).TrimEnd('\')
$count = [int]$env:PYAPP_LP_COUNT
# MAX_PATH = 260 including the terminating NUL: a file path may have at most 259 characters.
# Creating a folder leaves room for an 8.3 file name: a folder path may have at most 247 characters.
$fileLimit = 259
$folderLimit = 247
if (-not [IO.Directory]::Exists($root)) { Write-Host "[Error] Folder not found: $root" -ForegroundColor Red; return }

$results = New-Object System.Collections.Generic.List[object]
$unreadable = New-Object System.Collections.Generic.List[string]
$pythonFiles = New-Object System.Collections.Generic.List[string]
$stack = New-Object System.Collections.Generic.Stack[string]
$stack.Push($root)
while ($stack.Count -gt 0) {
    $dir = $stack.Pop()
    try {
        # The \\?\ prefix lets .NET read paths beyond MAX_PATH even when long paths are disabled.
        $items = @((New-Object IO.DirectoryInfo ('\\?\' + $dir)).EnumerateFileSystemInfos())
    } catch {
        $unreadable.Add($dir)
        continue
    }
    foreach ($item in $items) {
        $path = $item.FullName
        if ($path.StartsWith('\\?\')) { $path = $path.Substring(4) }
        $isDir = [bool]($item.Attributes -band [IO.FileAttributes]::Directory)
        $isLink = [bool]($item.Attributes -band [IO.FileAttributes]::ReparsePoint)
        $limit = if ($isDir) { $folderLimit } else { $fileLimit }
        $results.Add([pscustomobject]@{ Length = $path.Length; IsDir = $isDir; Limit = $limit; Path = $path; WouldAppear = $false })
        if (-not $isDir -and $item.Extension -eq '.py') { $pythonFiles.Add($path) }
        if ($isDir -and -not $isLink -and $item.Name -ne '.git') { $stack.Push($path) }
    }
}

# Compiled files Python would write next to each module, without creating them. The file name
# contains the Python version, so this uses the project's own .venv Python to get it.
$scanned = $results.Count
$cacheTag = $null
$projectPython = Join-Path $root 'code\backend\generated\.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $projectPython) {
    try { $cacheTag = & $projectPython -I -S -c 'import sys; print(sys.implementation.cache_tag)' | Select-Object -First 1 } catch { }
}
if ($cacheTag) {
    $known = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
    foreach ($r in $results) { [void]$known.Add($r.Path) }
    foreach ($module in $pythonFiles) {
        # String operations: System.IO.Path refuses paths beyond MAX_PATH on Windows PowerShell 5.1.
        $slash = $module.LastIndexOf('\')
        $cacheFolder = $module.Substring(0, $slash) + '\__pycache__'
        $stem = $module.Substring($slash + 1, $module.Length - $slash - 4)
        foreach ($candidate in @(@($cacheFolder, $true, $folderLimit), @("$cacheFolder\$stem.$cacheTag.pyc", $false, $fileLimit))) {
            if ($known.Add($candidate[0])) {
                $results.Add([pscustomobject]@{ Length = $candidate[0].Length; IsDir = $candidate[1]; Limit = $candidate[2]; Path = $candidate[0]; WouldAppear = $true })
            }
        }
    }
}

$longPathsEnabled = $false
try { $longPathsEnabled = [int](Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled).LongPathsEnabled -eq 1 } catch { }

Write-Host "Longest paths in $root"
Write-Host ("{0} files and folders scanned. Windows path limit: files {1} characters, folders {2}." -f $scanned, $fileLimit, $folderLimit)
if ($cacheTag) {
    Write-Host ("Also counted: {0} __pycache__ paths for {1} that do not exist yet, marked (would appear)." -f ($results.Count - $scanned), $cacheTag)
} else {
    Write-Host "__pycache__ paths that do not exist yet are not counted: this project has no .venv Python to ask for the file names." -ForegroundColor Yellow
}
Write-Host ""
Write-Host ("{0,6}  {1,-6}  {2,-8}  {3}" -f 'Length', 'Type', 'Status', 'Path')
foreach ($r in ($results | Sort-Object Length -Descending | Select-Object -First $count)) {
    $type = if ($r.IsDir) { 'folder' } else { 'file' }
    if ($r.Length -gt $r.Limit) { $status = 'TOO LONG'; $color = 'Red' }
    elseif ($r.Length -gt $r.Limit - 20) { $status = 'close'; $color = 'Yellow' }
    else { $status = 'ok'; $color = 'Gray' }
    $shown = if ($r.WouldAppear) { $r.Path + '  (would appear)' } else { $r.Path }
    Write-Host ("{0,6}  {1,-6}  {2,-8}  {3}" -f $r.Length, $type, $status, $shown) -ForegroundColor $color
}

Write-Host ""
$over = @($results | Where-Object { $_.Length -gt $_.Limit })
if ($over.Count -gt 0) {
    Write-Host ("{0} path(s) exceed the Windows path limit (by up to {1} characters)." -f $over.Count, (($over | ForEach-Object { $_.Length - $_.Limit } | Measure-Object -Maximum).Maximum)) -ForegroundColor Red
} elseif ($results.Count -gt 0) {
    $headroom = ($results | ForEach-Object { $_.Limit - $_.Length } | Measure-Object -Minimum).Minimum
    Write-Host ("No path exceeds the Windows path limit. The project folder path can grow by {0} more characters (e.g. a deeper or longer folder) before one does." -f $headroom) -ForegroundColor Green
}
if ($longPathsEnabled) {
    Write-Host "Long paths are enabled on this PC (LongPathsEnabled = 1), but Explorer, cmd and many programs still fail beyond the limit."
} else {
    Write-Host "Long paths are disabled on this PC (LongPathsEnabled = 0): most programs fail on paths beyond the limit."
}
if ($unreadable.Count -gt 0) {
    Write-Host ("{0} folder(s) could not be read and were skipped, e.g. {1}" -f $unreadable.Count, $unreadable[0]) -ForegroundColor Yellow
}
