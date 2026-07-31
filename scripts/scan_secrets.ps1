$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$patterns = @(
    'ghp_[A-Za-z0-9]{20,}',
    'github_pat_[A-Za-z0-9_]{20,}',
    'AKIA[0-9A-Z]{16}',
    'AIza[0-9A-Za-z\-_]{35}',
    '-----BEGIN (RSA|EC|OPENSSH|DSA) PRIVATE KEY-----',
    '(?i)api[_-]?key\s*[:=]\s*["''][^"'']{8,}["'']',
    '(?i)secret[_-]?key\s*[:=]\s*["''][^"'']{8,}["'']'
)
$files = Get-ChildItem -Path $root -Recurse -File | Where-Object {
    $_.FullName -notmatch '\\.venv\\|\\runtime-output\\|\\.git\\|\\__pycache__\\'
}
foreach ($pattern in $patterns) {
    $matches = $files | Select-String -Pattern $pattern
    if ($matches) {
        $matches | ForEach-Object { Write-Host $_.Path ':' $_.LineNumber ':' $_.Line }
        throw "Potential secret detected for pattern: $pattern"
    }
}
Write-Host 'Secret scan passed.'
