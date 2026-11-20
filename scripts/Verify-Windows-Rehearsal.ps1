# Offline verification; -Launch requires explicit human confirmation.
# Manifest hashes detect accidental/tampered copies, NOT publisher authenticity.
param(
  [string]$Folder = $PSScriptRoot,
  [string]$ExpectedSourceSha = '',
  [switch]$Launch
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$dir = (Resolve-Path -LiteralPath $Folder).Path
$manifestPath = Join-Path $dir 'BUILD_MANIFEST.json'
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
  throw 'BUILD_MANIFEST.json fehlt. Bitte die ganze Probe-ZIP entpacken.'
}
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ([string]$manifest.source_commit -notmatch '^[a-f0-9]{40}$') {
  throw 'Unbekannte Quellversion im Manifest.'
}
if ($ExpectedSourceSha -and $manifest.source_commit -ne $ExpectedSourceSha) {
  throw 'Quell-SHA stimmt NICHT mit der erwarteten Version überein.'
}
if ($manifest.purpose -ne 'unsigned-local-physical-acceptance' -or
    $manifest.live_service -ne 'NO_GO' -or $manifest.physical_tests -ne 'NOT_TESTED') {
  throw 'Unerwartetes oder fehlerhaftes Probe-Manifest.'
}
$exe = Join-Path $dir 'UBF-Koeln-Timer-PROBE.exe'
$png = Join-Path $dir 'welcome.png'
foreach ($p in @($exe, $png)) {
  if (-not (Test-Path -LiteralPath $p -PathType Leaf)) {
    throw "Datei fehlt: $p"
  }
  if ((Get-Item -LiteralPath $p).Attributes -band [IO.FileAttributes]::ReparsePoint) {
    throw 'Verknüpfungen statt regulärer Dateien sind nicht erlaubt.'
  }
}
$actualExe = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
$actualPng = (Get-FileHash -LiteralPath $png -Algorithm SHA256).Hash
if ($actualExe -ne [string]$manifest.executable_sha256) {
  throw 'FEHLER: Die EXE-Prüfsumme ist falsch. Nicht ausführen.'
}
if ($actualPng -ne [string]$manifest.welcome_png_sha256) {
  throw 'FEHLER: welcome.png wurde verändert. Nicht ausführen.'
}
$sheet = Join-Path $dir 'ABNAHME_W01-W08.html'
if (-not (Test-Path -LiteralPath $sheet -PathType Leaf)) {
  throw 'Das Offline-Abnahmeprotokoll fehlt.'
}
if ((Get-FileHash -LiteralPath $sheet -Algorithm SHA256).Hash -ne
    [string]$manifest.acceptance_html_sha256) {
  throw 'FEHLER: Das Offline-Protokoll wurde verändert.'
}
Write-Host "PR-Quell-SHA: $($manifest.source_commit)"
Write-Host "EXE SHA256: $actualExe"
Write-Host "welcome.png SHA256: $actualPng"
Write-Host 'DATEIEN KONSISTENT — Manifest ist KEINE digitale Signatur.'
Write-Host 'Die Quell-SHA unabhängig mit dem genehmigten GitHub-Commit vergleichen.'
Write-Host 'Alle realen Windows-11-/Projektor-/PowerPoint-/Canva-Tests: NOT_TESTED.'
Write-Host 'Live-Sonntagsgottesdienst: NO_GO.'

if (-not $Launch) { return }
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or
    -not [Environment]::Is64BitOperatingSystem -or
    [Environment]::OSVersion.Version.Build -lt 22000) {
  throw 'Start nur für eine autorisierte Windows-11-x64-Probe erlaubt.'
}
Write-Host 'Unsignierter Entwicklungs-Build. Windows-Sicherheitsmeldungen nicht blind umgehen.'
Write-Host 'Win + P -> Erweitern; Laptop als Hauptbildschirm konfigurieren.'
$answer = Read-Host 'Nur auf autorisiertem Testgerät: PROBE eingeben, um die EXE zu öffnen'
if ($answer -cne 'PROBE') {
  throw 'Probe nicht bestätigt; Programm bleibt geschlossen.'
}
Start-Process -FilePath $exe -WorkingDirectory $dir
