# KB Score 3.0 / Step 13: LOCAL Windows launcher. No private key upload.
param([string]$ArchiveZip="",[string]$PrivateKey="",[switch]$SkipTests)
$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

function Fail-Safe([string]$msg) {
    Write-Host ("STOP: "+$msg) -ForegroundColor Red
    exit 3
}
function Choose-File([string]$title,[string]$filter,[string]$dir) {
    Add-Type -AssemblyName System.Windows.Forms
    $picker=New-Object System.Windows.Forms.OpenFileDialog
    $picker.Title=$title
    $picker.Filter=$filter
    $picker.Multiselect=$false
    $picker.CheckFileExists=$true
    if(Test-Path -LiteralPath $dir -PathType Container){$picker.InitialDirectory=$dir}
    if($picker.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK){
        Fail-Safe "Nie wybrano pliku; bez zmian."
    }
    return $picker.FileName
}
function Ensure-Command([string]$what){
    if($LASTEXITCODE -ne 0){Fail-Safe ("Nieudane: "+$what+". Nie udostepniaj zawartosci klucza.")}
}

$root=[System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$private=Join-Path $env:LOCALAPPDATA "KB3-Private"
[System.IO.Directory]::CreateDirectory($private) | Out-Null
if(-not $ArchiveZip){
    $ArchiveZip=Choose-File "Wybierz oryginalny archiwalny PitchAPI ZIP 2023-2026" "ZIP (*.zip)|*.zip" (Join-Path $env:USERPROFILE "Downloads")
}
if(-not $PrivateKey){
    $PrivateKey=Choose-File "Wybierz PRYWATNY klucz RSA (bez wysylania)" "RSA PEM/KEY (*.pem;*.key)|*.pem;*.key|Wszystkie (*.*)|*.*" $private
}
if(-not (Test-Path -LiteralPath $ArchiveZip -PathType Leaf)){Fail-Safe "Nie znaleziono ZIP."}
if(-not (Test-Path -LiteralPath $PrivateKey -PathType Leaf)){Fail-Safe "Nie znaleziono pliku PEM/KEY."}
$archive=(Resolve-Path -LiteralPath $ArchiveZip).Path
$key=(Resolve-Path -LiteralPath $PrivateKey).Path
if($key.StartsWith($root.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)){
    Fail-Safe "Klucz nie moze lezec w repozytorium GitHub."
}
if($env:OneDrive -and $key.StartsWith($env:OneDrive.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)){
    Fail-Safe "Klucz znajduje sie w folderze OneDrive. Przenies do %LOCALAPPDATA%\KB3-Private."
}
$firstLine=[System.IO.File]::ReadLines($key) | Select-Object -First 1
if($firstLine -eq "-----BEGIN ENCRYPTED PRIVATE KEY-----"){
    Fail-Safe "Klucz szyfrowany haslem wymaga osobnego przygotowania lokalnie; nie udostepniaj go."
}
if($firstLine -ne "-----BEGIN PRIVATE KEY-----" -and $firstLine -ne "-----BEGIN RSA PRIVATE KEY-----"){
    Fail-Safe "Nieprawidlowy naglowek klucza prywatnego PEM."
}
$expected="301bae69251d19a0192e12c2c033636b3f2822a15dcea2c4beaca28f4b45de2e"
if((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected){
    Fail-Safe "ZIP nie jest oryginalnym archiwum kroku 13. SHA256 rozny."
}
foreach($required in @("src\kb3_step13_archive_preflight.py","scripts\step13_pitch_retrospective_local.py","data\splits\STEP12_SAFE_MODEL_VIEW_2026-10-26.json")){
    if(-not (Test-Path -LiteralPath (Join-Path $root $required) -PathType Leaf)){
        Fail-Safe "Niepelny katalog kb-score-3. Pobierz i rozpakuj cale repozytorium."
    }
}
Write-Host "OK: oryginalny ZIP, klucz lokalny poza repozytorium." -ForegroundColor Green

$venv=Join-Path $private "step13-venv"
$python=Join-Path $venv "Scripts\python.exe"
if(-not (Test-Path -LiteralPath $python -PathType Leaf)){
    if(Get-Command "py" -ErrorAction SilentlyContinue){
        & py -3 -m venv $venv
        Ensure-Command "tworzenie venv przez py"
    } elseif(Get-Command "python" -ErrorAction SilentlyContinue){
        & python -m venv $venv
        Ensure-Command "tworzenie venv przez python"
    } else {
        Fail-Safe "Brak Python 3. Zainstaluj Python z python.org (z obsluga venv)."
    }
}
if(-not (Test-Path -LiteralPath $python -PathType Leaf)){Fail-Safe "Nie mozna uruchomic prywatnego srodowiska Python."}
& $python -c "import cryptography" 2>$null
if($LASTEXITCODE -ne 0){
    Write-Host "Instalacja cryptography do prywatnego srodowiska Python (tylko biblioteka)."
    & $python -m pip install --disable-pip-version-check "cryptography>=42,<47"
    Ensure-Command "instalacja cryptography"
}
$preflight=Join-Path $private "STEP13_ORIGINAL_ZIP_PREFLIGHT.json"
$report=Join-Path $private "STEP13_RETROSPECTIVE_RESEARCH_RESULT.json"
Push-Location $root
try{
    if(-not $SkipTests){
        Write-Host "Uruchamiam syntetyczne testy bezpieczenstwa..."
        & $python -m unittest discover -s tests -p "test_step13*.py" -q
        Ensure-Command "testy offline"
    }
    Write-Host "Sprawdzam archiwum ZIP..."
    & $python -m src.kb3_step13_archive_preflight --archive-zip $archive --output $preflight
    Ensure-Command "kontrola zaszyfrowanego ZIP"
    Write-Host "Uruchamiam lokalne odszyfrowanie i retrospektywne badanie."
    $argsResearch=@("-m","scripts.step13_pitch_retrospective_local","--archive-zip",$archive,"--private-key",$key,"--research-policy","RECONSTRUCTED_EVENT_TIME_RESEARCH_NOT_VERIFIED_PIT","--output",$report)
    & $python @argsResearch
    Ensure-Command "prawdziwe badanie retrospektywne"
} finally {
    Pop-Location
}
$r=Get-Content -LiteralPath $report -Raw -Encoding UTF8 | ConvertFrom-Json
if($r.train_partition_rows -ne 760 -or $r.validation_partition_rows -ne 380 -or $r.test_rows_processed -ne 0 -or $r.training_allowed -ne $false -or $r.gate13_pass -ne $false){
    Fail-Safe "Raport narusza ograniczenia danych kroku 13."
}
Write-Host ""
Write-Host "GOTOWE: rzeczywisty retrospektywny eksperyment ELO+Poisson." -ForegroundColor Green
Write-Host "TRAIN 760; VALIDATION 380; TEST 0. Wynik NIE jest certyfikowany PIT."
foreach($method in @("EXPANDING","ROLLING_24_CALENDAR_MONTHS")){
    $m=$r.overall.$method
    Write-Host ("{0}: n={1}; logloss={2:N4}; Brier sum3={3:N4}; ECE fold-weighted={4:N4}" -f $method,$m.validation_n,$m.multiclass_logloss_fold_weighted,$m.multiclass_brier_sum3_fold_weighted,$m.top_class_ece_5bin_fold_weighted)
}
Write-Host "Raport zapisany poza GitHubem: %LOCALAPPDATA%\KB3-Private\STEP13_RETROSPECTIVE_RESEARCH_RESULT.json"
Write-Host "Nie wysylaj klucza ani prywatnego surowego archiwum. Udostepnic mozna tylko zbiorcze metryki."
