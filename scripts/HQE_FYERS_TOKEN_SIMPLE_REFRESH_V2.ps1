param(
  [string]$RepoRoot = "D:\Hunter_Quant_Engine_PC_TRANSFER",
  [string]$Workspace = "D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722",
  [string]$Symbol = "NSE:NIFTY50-INDEX"
)

$ErrorActionPreference = "Stop"

function Read-PlainSecret([string]$PromptText) {
  $sec = Read-Host $PromptText -AsSecureString
  $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
  try {
    return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr).Trim()
  } finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
  }
}

function Get-TrimmedFile([string]$Path) {
  if (-not (Test-Path $Path)) { return "" }
  $v = Get-Content $Path -Raw -ErrorAction SilentlyContinue
  if ($null -eq $v) { return "" }
  return $v.Trim()
}

Write-Host ""
Write-Host "HQE FYERS SIMPLE TOKEN REFRESH V2"
Write-Host "Safety: DATA ONLY / NO ORDERS / NO BROKER EXECUTION / NO AUTO TRADING"
Write-Host ""

Set-Location $RepoRoot
$Py = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { throw "Python venv not found: $Py" }

$SecretDir = "D:\HQE_BACKTEST_RUNS\HQE_LOCAL_FYERS_TOKEN_REFRESH"
New-Item -ItemType Directory -Force $SecretDir | Out-Null

$ClientFile = Join-Path $SecretDir "fyers_client_id.txt"
$RedirectUriFile = Join-Path $SecretDir "fyers_redirect_uri.txt"
$SecretFile = Join-Path $SecretDir "fyers_secret_key.txt"
$RedirectUrlFile = Join-Path $SecretDir "fyers_redirect_url.txt"
$TokenFile = Join-Path $SecretDir "fyers_access_token.txt"
$TokenResponseFile = Join-Path $SecretDir "fyers_token_response.json"
$LogFile = Join-Path $SecretDir "token_refresh_run.log"

$cid = Get-TrimmedFile $ClientFile
if ([string]::IsNullOrWhiteSpace($cid) -or $cid -like "PASTE_*") {
  $cid = Read-Host "Paste FYERS API ID / Client ID from API dashboard"
  $cid = $cid.Trim()
  Set-Content $ClientFile $cid -NoNewline
}

$redirectUri = Get-TrimmedFile $RedirectUriFile
if ([string]::IsNullOrWhiteSpace($redirectUri) -or $redirectUri -like "PASTE_*") {
  $redirectUri = Read-Host "Paste FYERS Redirect URI exactly as app dashboard shows (press Enter for https://127.0.0.1)"
  if ([string]::IsNullOrWhiteSpace($redirectUri)) { $redirectUri = "https://127.0.0.1" }
  $redirectUri = $redirectUri.Trim()
  Set-Content $RedirectUriFile $redirectUri -NoNewline
}

$secret = Get-TrimmedFile $SecretFile
if ([string]::IsNullOrWhiteSpace($secret) -or $secret -like "PASTE_*") {
  $secret = Read-PlainSecret "Paste FYERS Secret Key"
  Set-Content $SecretFile $secret -NoNewline
}

Write-Host ""
Write-Host "Opening FYERS login URL..."
& $Py scripts\refresh_fyers_token.py --open-browser-only --client-id-file $ClientFile --redirect-uri-file $RedirectUriFile --secret-key-file $SecretFile --redirect-url-file $RedirectUrlFile

Write-Host ""
Write-Host "After browser login:"
Write-Host "1) Browser may show 127.0.0.1 cannot be reached. That is OK."
Write-Host "2) Copy the FULL address-bar URL after login."
Write-Host "3) It must contain auth_code= or code=."
Write-Host "4) Paste it into Notepad, save, and close Notepad."
Write-Host ""

Set-Content $RedirectUrlFile "PASTE_FULL_FYERS_REDIRECT_URL_HERE_WITH_AUTH_CODE_OR_CODE" -NoNewline
Start-Process notepad.exe -ArgumentList "`"$RedirectUrlFile`"" -Wait

$redirectUrl = Get-TrimmedFile $RedirectUrlFile
if ($redirectUrl -notmatch "auth_code=|code=") {
  Write-Host ""
  Write-Host "ERROR: Redirect URL does not contain auth_code= or code=."
  Write-Host "Tip: do NOT paste the original FYERS login URL. Paste the URL after successful login/redirect."
  exit 1
}

Write-Host ""
Write-Host "Generating FYERS access token..."
if (Test-Path $TokenFile) { Remove-Item $TokenFile -Force -ErrorAction SilentlyContinue }
if (Test-Path $TokenResponseFile) { Remove-Item $TokenResponseFile -Force -ErrorAction SilentlyContinue }
if (Test-Path $LogFile) { Remove-Item $LogFile -Force -ErrorAction SilentlyContinue }

& $Py scripts\refresh_fyers_token.py --from-redirect-file --client-id-file $ClientFile --redirect-uri-file $RedirectUriFile --secret-key-file $SecretFile --redirect-url-file $RedirectUrlFile --access-token-output $TokenFile --token-response-output $TokenResponseFile *> $LogFile

if (-not (Test-Path $TokenFile)) {
  Write-Host ""
  Write-Host "TOKEN FILE NOT CREATED. Token generation failed."
  Write-Host "Local log file:"
  Write-Host $LogFile
  Get-Content $LogFile -Tail 20 -ErrorAction SilentlyContinue
  exit 1
}

$tok = Get-TrimmedFile $TokenFile
$cid = Get-TrimmedFile $ClientFile

[Environment]::SetEnvironmentVariable("FYERS_ACCESS_TOKEN", $tok, "User")
[Environment]::SetEnvironmentVariable("FYERS_CLIENT_ID", $cid, "User")
$env:FYERS_ACCESS_TOKEN = $tok
$env:FYERS_CLIENT_ID = $cid

Write-Host ""
Write-Host "FYERS token saved to user environment."
Write-Host "Token length:" $tok.Length
Write-Host "Client ID length:" $cid.Length

Write-Host ""
Write-Host "Running HQE data-only historical test..."
& $Py scripts\hqe_fyers_historical_5m_data_only_fetcher.py --workspace $Workspace --symbol $Symbol --execute-live-data-only --write

Write-Host ""
Write-Host "Cleaning temporary sensitive files..."
Remove-Item $TokenFile -Force -ErrorAction SilentlyContinue
Remove-Item $TokenResponseFile -Force -ErrorAction SilentlyContinue
Remove-Item $RedirectUrlFile -Force -ErrorAction SilentlyContinue
Remove-Item $SecretFile -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "DONE. Safety remained DATA ONLY / NO ORDERS / NO BROKER EXECUTION."
Read-Host "Press Enter to close"
