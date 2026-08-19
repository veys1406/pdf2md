<#
.SYNOPSIS
    pdf2md'yi derler ve dagitima hazir paketi uretir.

.DESCRIPTION
    1) PyInstaller ile dist\pdf2md klasorunu uretir (onedir).
    2) 7-Zip varsa kendi kendine acilan pdf2md-kurulum.exe, yoksa pdf2md-windows.zip uretir.

    SFX icin 7-Zip gerekir:  winget install 7zip.7zip

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File packaging\build.ps1
    powershell -ExecutionPolicy Bypass -File packaging\build.ps1 -SkipBuild   # sadece paketle
#>

[CmdletBinding()]
param(
    [switch]$SkipBuild,
    [string]$Version = "0.1.0"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$dist = Join-Path $root "dist\pdf2md"
$out = Join-Path $root "dist"

function Write-Step($text) { Write-Host "`n== $text" -ForegroundColor Cyan }

# -- 1) derleme -----------------------------------------------------------

if (-not $SkipBuild) {
    Write-Step "PyInstaller derlemesi"
    Push-Location $root
    try {
        uv run pyinstaller packaging\pdf2md.spec --noconfirm --clean
        if ($LASTEXITCODE -ne 0) { throw "PyInstaller basarisiz (cikis kodu $LASTEXITCODE)" }
    }
    finally { Pop-Location }
}

if (-not (Test-Path $dist)) { throw "Derleme ciktisi yok: $dist" }

$sizeMb = [math]::Round(((Get-ChildItem $dist -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB), 0)
Write-Host "Derleme boyutu: $sizeMb MB"

# -- 2) hizli duman testi -------------------------------------------------

Write-Step "Duman testi: paketlenmis exe gercekten bir PDF ceviriyor mu"
$exe = Join-Path $dist "pdf2md.exe"
if (-not (Test-Path $exe)) { throw "pdf2md.exe uretilmemis" }

# Tek sayfalik test PDF'i uret (repoda ornek dosya tutulmuyor).
$testDir = Join-Path $env:TEMP "pdf2md-smoke"
if (Test-Path $testDir) { Remove-Item $testDir -Recurse -Force }
New-Item -ItemType Directory $testDir | Out-Null
$testPdf = Join-Path $testDir "test.pdf"

Push-Location $root
try {
    $py = @"
import pymupdf
doc = pymupdf.open()
page = doc.new_page()
page.insert_text((72, 96), 'pdf2md duman testi', fontsize=20)
page.insert_text((72, 140), 'Ikinci satir: paketleme dogrulamasi.', fontsize=12)
doc.save(r'$testPdf')
"@
    $py | uv run python -
    if ($LASTEXITCODE -ne 0) { throw "Test PDF'i uretilemedi" }
}
finally { Pop-Location }

$p = Start-Process -FilePath $exe -ArgumentList @("--cli", "`"$testPdf`"", "--cikti", "`"$testDir`"") -PassThru -Wait
$cliLog = Join-Path $env:LOCALAPPDATA "pdf2md\logs\cli.log"
$md = Join-Path $testDir "test.md"

if (-not (Test-Path $md)) {
    if (Test-Path $cliLog) { Get-Content $cliLog -Tail 20 | ForEach-Object { Write-Host "  $_" } }
    throw "Paketlenmis exe donusumu tamamlayamadi (cikis kodu $($p.ExitCode))"
}
Write-Host ("Donusum calisti: " + (Get-Item $md).Length + " bayt markdown uretildi.")

# Arayuz de aciliyor mu (pencere modunda hemen olmedigini dogrula)
$g = Start-Process -FilePath $exe -PassThru
Start-Sleep -Seconds 25
$g.Refresh()
if ($g.HasExited) { throw "Arayuz acilir acilmaz kapandi (cikis kodu $($g.ExitCode))" }
if ($g.MainWindowTitle -ne "pdf2md") {
    Stop-Process -Id $g.Id -Force
    throw "Beklenmeyen pencere basligi: '$($g.MainWindowTitle)' (muhtemelen hata penceresi)"
}
Stop-Process -Id $g.Id -Force
Write-Host "Arayuz acildi."

# -- 3) paketleme ---------------------------------------------------------

$sevenZip = @(
    "C:\Program Files\7-Zip\7z.exe",
    "C:\Program Files (x86)\7-Zip\7z.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $sevenZip) {
    $cmd = Get-Command 7z -ErrorAction SilentlyContinue
    if ($cmd) { $sevenZip = $cmd.Source }
}

if ($sevenZip) {
    Write-Step "7-Zip SFX paketi"
    # 7z.sfx = 7-Zip'in GUI cikaricisi: cift tiklaninca hedef klasoru sorar ve
    # icindeki pdf2md\ klasorunu oraya acar. LZMA SDK'daki 7zS/7zSD modulleri
    # bilerek kullanilmiyor: onlar arsivi TEMP'e acip programi calistiriyor,
    # 1 GB'lik bir pakette bu her acilista kabul edilemez.
    $archive = Join-Path $out "pdf2md.7z"
    $sfxModule = Join-Path (Split-Path $sevenZip) "7z.sfx"
    $target = Join-Path $out "pdf2md-$Version-windows.exe"

    if (-not (Test-Path $sfxModule)) { throw "7z.sfx bulunamadi: $sfxModule" }
    if (Test-Path $archive) { Remove-Item $archive -Force }

    # Arsivin kokunde 'pdf2md' klasoru olsun: kullanici nereye acarsa acsin
    # dosyalar dagilmasin.
    Push-Location (Split-Path $dist)
    try {
        & $sevenZip a -t7z -mx=5 -mmt=on $archive "pdf2md" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "7z arsivleme basarisiz" }
    }
    finally { Pop-Location }

    # SFX exe = sfx modulu + arsiv, akis olarak birlestirilir.
    # ReadAllBytes ile birlestirme denenmemeli: 280+ MB'lik arsivde PowerShell
    # "Dizi boyutlari desteklenen araligi asti" diye OutOfMemory veriyor.
    if (Test-Path $target) { Remove-Item $target -Force }
    $outStream = [System.IO.File]::Create($target)
    try {
        foreach ($part in @($sfxModule, $archive)) {
            $inStream = [System.IO.File]::OpenRead($part)
            try { $inStream.CopyTo($outStream) } finally { $inStream.Dispose() }
        }
    }
    finally { $outStream.Dispose() }
    Remove-Item $archive -Force

    $mb = [math]::Round((Get-Item $target).Length / 1MB, 0)
    Write-Host "Hazir: $target ($mb MB)"
}
else {
    Write-Step "ZIP paketi (7-Zip kurulu degil)"
    $target = Join-Path $out "pdf2md-windows-$Version.zip"
    if (Test-Path $target) { Remove-Item $target -Force }
    Compress-Archive -Path "$dist\*" -DestinationPath $target -CompressionLevel Optimal
    $mb = [math]::Round((Get-Item $target).Length / 1MB, 0)
    Write-Host "Hazir: $target ($mb MB)"
    Write-Host "Tek exe kurulum icin: winget install 7zip.7zip  sonra bu betigi tekrar calistir."
}
