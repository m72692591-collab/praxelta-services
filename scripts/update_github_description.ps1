[CmdletBinding()]
param(
    [string]$Repository = "m72692591-collab/praxelta-services",
    [string]$Description = "Публичная витрина и рабочие материалы ПРАКСЕЛЬТЫ",
    [string]$Homepage = "https://m72692591-collab.github.io/praxelta-services/",
    [string]$ReceiptPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-GhJson {
    param([string[]]$Arguments)
    $raw = & gh @Arguments 2>&1
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        throw "gh завершился с кодом $code: $($raw -join [Environment]::NewLine)"
    }
    return (($raw -join [Environment]::NewLine) | ConvertFrom-Json)
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI (gh) не найден. Установите его или запустите из среды, где gh уже доступен."
}

& gh auth status --hostname github.com 1>$null 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "Нет действующей локальной авторизации GitHub CLI. Выполните: gh auth login"
}

$before = Invoke-GhJson -Arguments @(
    "api", "repos/$Repository",
    "--method", "GET"
)

$patched = Invoke-GhJson -Arguments @(
    "api", "repos/$Repository",
    "--method", "PATCH",
    "-f", "description=$Description",
    "-f", "homepage=$Homepage"
)

$after = Invoke-GhJson -Arguments @(
    "api", "repos/$Repository",
    "--method", "GET"
)

if ([string]$after.description -ne $Description) {
    throw "Свежий API GET не подтвердил точный description. Фактически: $($after.description)"
}
if ([string]$after.homepage -ne $Homepage) {
    throw "Свежий API GET не подтвердил homepage. Фактически: $($after.homepage)"
}
if ([string]$after.default_branch -ne "main") {
    throw "Default branch неожиданно изменён: $($after.default_branch)"
}

$receipt = [ordered]@{
    schema_version = 1
    repository = $Repository
    status = "VERIFIED"
    verified_at_utc = [DateTime]::UtcNow.ToString("o")
    before_description = [string]$before.description
    expected_description = $Description
    actual_description = [string]$after.description
    homepage = [string]$after.homepage
    default_branch = [string]$after.default_branch
    repository_id = [int64]$after.id
    secrets_recorded = $false
    token_recorded = $false
    private_url_recorded = $false
}

if ([string]::IsNullOrWhiteSpace($ReceiptPath)) {
    $ReceiptPath = Join-Path $env:TEMP "PRAXELTA_REPOSITORY_METADATA_RECEIPT.json"
}
$directory = Split-Path -Parent $ReceiptPath
if ($directory) {
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
}
$receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $ReceiptPath -Encoding UTF8

Write-Host "PRAXELTA_REPOSITORY_METADATA=VERIFIED"
Write-Host "DESCRIPTION=$($after.description)"
Write-Host "HOMEPAGE=$($after.homepage)"
Write-Host "DEFAULT_BRANCH=$($after.default_branch)"
Write-Host "SANITIZED_RECEIPT=$ReceiptPath"
