# Local unsigned Windows acceptance rehearsal only. No release, installer, upload or deployment.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Run-Checked([string]$Tool, [string[]]$ArgsList) {
  & $Tool @ArgsList
  if ($LASTEXITCODE -ne 0) { throw "$Tool failed: exit $LASTEXITCODE" }
}
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or
    -not [Environment]::Is64BitOperatingSystem) {
  throw 'Windows x64 is required to build the rehearsal executable.'
}
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location $Root
try {
  foreach ($tool in @('git','node','npm','cargo','rustc')) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
      throw "Missing build tool: $tool"
    }
  }
  $nodeVersion = (& node --version).Trim()
  if ($LASTEXITCODE -ne 0 -or $nodeVersion -notmatch '^v(\d+)\.') {
    throw 'Could not determine the Node.js version.'
  }
  if ([int]$Matches[1] -lt 20) { throw 'Node.js 20+ required.' }
  $rustInfo = (& rustc -vV) -join ' '
  if ($LASTEXITCODE -ne 0 -or $rustInfo -notmatch 'host:\s*x86_64-pc-windows-msvc') {
    throw 'Rust x86_64-pc-windows-msvc and Microsoft C++ Build Tools required.'
  }
  $sha = (& git rev-parse --verify HEAD).Trim()
  if ($LASTEXITCODE -ne 0 -or $sha -notmatch '^[a-f0-9]{40}$') {
    throw 'Exact source commit could not be verified.'
  }
  & git diff --quiet HEAD --
  if ($LASTEXITCODE -ne 0) { throw 'Tracked source changes present. Refusing mislabeled build.' }
  $config = Get-Content 'src-tauri/tauri.conf.json' -Raw | ConvertFrom-Json
  if ($config.bundle.active -ne $false) { throw 'Tauri installer must remain disabled.' }

  Run-Checked 'npm' @('run','build:desktop')
  foreach ($image in @('welcome.png','background-clean.png')) {
    $original = (Get-FileHash "assets/$image" -Algorithm SHA256).Hash
    $staged = (Get-FileHash "dist/desktop/assets/$image" -Algorithm SHA256).Hash
    if ($original -ne $staged) { throw "Original Canva asset changed: $image" }
  }
  Run-Checked 'cargo' @('build','--release','--manifest-path','src-tauri/Cargo.toml','--bin','ubf-koeln-timer')
  $exe = 'src-tauri/target/release/ubf-koeln-timer.exe'
  if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw 'Windows EXE missing.' }

  $out = 'dist/windows-rehearsal'
  if (Test-Path -LiteralPath $out) {
    if ((Get-Item $out).Attributes -band [IO.FileAttributes]::ReparsePoint) {
      throw 'Refusing to overwrite a linked output directory.'
    }
    Remove-Item -LiteralPath $out -Recurse -Force
  }
  New-Item -ItemType Directory -Path $out | Out-Null
  Copy-Item -LiteralPath $exe -Destination "$out/UBF-Koeln-Timer-PROBE.exe"
  Copy-Item -LiteralPath 'assets/welcome.png' -Destination $out
  foreach ($doc in @('HANDOFF_OPERATOR_CARD_DE.md','PHYSICAL_ACCEPTANCE_WINDOWS11.md')) {
    Copy-Item -LiteralPath $doc -Destination $out
  }
  $exeHash = (Get-FileHash "$out/UBF-Koeln-Timer-PROBE.exe" -Algorithm SHA256).Hash
  $pngHash = (Get-FileHash "$out/welcome.png" -Algorithm SHA256).Hash
  [ordered]@{
    source_commit = $sha
    executable_sha256 = $exeHash
    welcome_png_sha256 = $pngHash
    created_utc = [DateTime]::UtcNow.ToString('o')
    purpose = 'unsigned-local-physical-acceptance'
    physical_tests = 'NOT_TESTED'
    live_service = 'NO_GO'
  } | ConvertTo-Json | Set-Content -Encoding UTF8 "$out/BUILD_MANIFEST.json"
  @'
LOKALE PROBE — KEIN RELEASE / KEINE LIVE-FREIGABE
Nur auf genehmigtem Windows-11-x64-Testgeraet entpacken.
BUILD_MANIFEST.json-Quell-SHA und EXE-Pruefsumme pruefen:
  Get-FileHash .\UBF-Koeln-Timer-PROBE.exe -Algorithm SHA256
WebView2 muss installiert sein; Node/Rust sind zum Ausfuehren nicht noetig.
Die EXE ist unsigniert; Sicherheitswarnungen nicht blind umgehen.
Win+P -> Erweitern; Laptop als HAUPTANZEIGE waehlen.
Bedienkarte und W01-W08-Protokoll fuer den echten Beamer verwenden.
Nur beobachtete Ergebnisse als PASS eintragen. Live-Einsatz: NO_GO.
welcome.png ist der unveraenderte statische Notfall-Fallback.
'@ | Set-Content -Encoding UTF8 "$out/BITTE_LESEN.txt"

  $zip = 'dist/UBF-Koeln-Timer-LOKALE-PROBE.zip'
  if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force }
  Compress-Archive -Path "$out/*" -DestinationPath $zip
  $zipHash = (Get-FileHash $zip -Algorithm SHA256).Hash
  Write-Host "LOCAL ONLY ZIP: $zip"
  Write-Host "SOURCE_SHA: $sha"
  Write-Host "EXE_SHA256: $exeHash"
  Write-Host "ZIP_SHA256: $zipHash"
  Write-Host 'No upload/release/deployment. Church projector NOT_TESTED. Live NO_GO.'
} finally {
  Pop-Location
}
