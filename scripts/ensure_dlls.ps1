param(
  [Parameter(Mandatory = $true)]
  [string]$SourceRoot,

  [Parameter(Mandatory = $true)]
  [string]$DestRoot,

  [string]$Pattern = "*.dll"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $SourceRoot)) {
  throw "SourceRoot not found: $SourceRoot"
}

if (-not (Test-Path -LiteralPath $DestRoot)) {
  New-Item -ItemType Directory -Force -Path $DestRoot | Out-Null
}

$source = (Resolve-Path -LiteralPath $SourceRoot).Path
$dest = (Resolve-Path -LiteralPath $DestRoot).Path

if (-not $source.EndsWith("\")) {
  $source += "\"
}

$files = Get-ChildItem -LiteralPath $source -Recurse -File -Filter $Pattern

$copied = 0
$updated = 0
$skipped = 0

foreach ($file in $files) {
  if (-not $file.FullName.StartsWith($source, [System.StringComparison]::OrdinalIgnoreCase)) {
    continue
  }

  $relative = $file.FullName.Substring($source.Length)
  $target = Join-Path $dest $relative
  $targetDir = Split-Path -Parent $target

  if (-not (Test-Path -LiteralPath $targetDir)) {
    New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
  }

  if (-not (Test-Path -LiteralPath $target)) {
    Copy-Item -LiteralPath $file.FullName -Destination $target
    $copied++
    continue
  }

  $targetInfo = Get-Item -LiteralPath $target
  if ($targetInfo.Length -ne $file.Length) {
    Copy-Item -LiteralPath $file.FullName -Destination $target -Force
    $updated++
  } else {
    $skipped++
  }
}

Write-Host ("DLL sync complete ({0}): copied={1} updated={2} skipped={3}" -f $files.Count, $copied, $updated, $skipped)

