[CmdletBinding()]
param(
    [ValidateSet('Repair','FollowUp','SelfTest')]
    [string]$Mode = 'Repair',
    [string]$InstallRoot = '',
    [string]$Desktop = '',
    [switch]$NoUi
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
    $base = if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        $env:LOCALAPPDATA
    } else {
        $env:TEMP
    }
    $InstallRoot = Join-Path $base 'MAESTRO\AutopilotV4'
}
if ([string]::IsNullOrWhiteSpace($Desktop)) {
    $Desktop = [Environment]::GetFolderPath([Environment+SpecialFolder]::Desktop)
    if ([string]::IsNullOrWhiteSpace($Desktop)) {
        $Desktop = Join-Path $env:USERPROFILE 'Desktop'
    }
}

$InstalledPs1 = Join-Path $InstallRoot 'MAESTRO_AUTOPILOT_V4.ps1'
$StatePath = Join-Path $InstallRoot 'autopilot-state.json'
$RepairCopy = Join-Path $InstallRoot 'MAESTRO_AUTOPILOT_V4_SELFHEAL_V4_1.ps1'
$ReceiptPath = Join-Path $InstallRoot 'MAESTRO_AUTOPILOT_V4_SELFHEAL_V4_1_RECEIPT.json'
$MarkerPath = Join-Path $InstallRoot 'MAESTRO_AUTOPILOT_V4_SELFHEAL_V4_1.marker'
$NoticePath = Join-Path $Desktop 'MAESTRO_НУЖНО_ОДНО_ДЕЙСТВИЕ.txt'
$PatchMarker = '# MAESTRO_AUTOPILOT_NOTICE_ARRAY_PATCH_V4_1'

function Ensure-Directory {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Write-Utf8Bom {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][AllowEmptyString()][string]$Content
    )
    Ensure-Directory -Path (Split-Path -Parent $Path)
    [IO.File]::WriteAllText($Path, $Content, (New-Object Text.UTF8Encoding($true)))
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][AllowEmptyString()][string]$Content
    )
    Ensure-Directory -Path (Split-Path -Parent $Path)
    [IO.File]::WriteAllText($Path, $Content, (New-Object Text.UTF8Encoding($false)))
}

function Read-JsonSafe {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $null
    }
    try {
        return (Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json)
    } catch {
        return $null
    }
}

function Write-JsonAtomic {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)]$Value
    )
    Ensure-Directory -Path (Split-Path -Parent $Path)
    $temporary = "$Path.$([Guid]::NewGuid().ToString('N')).tmp"
    try {
        Write-Utf8NoBom -Path $temporary -Content ($Value | ConvertTo-Json -Depth 30)
        Move-Item -LiteralPath $temporary -Destination $Path -Force
    } finally {
        Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
    }
}

function Get-PropertyValue {
    param($Object, [string]$Name, $Default = $null)
    if ($null -eq $Object) { return $Default }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) { return $Default }
    return $property.Value
}

function Set-PropertyValue {
    param($Object, [string]$Name, $Value)
    if ($null -eq $Object.PSObject.Properties[$Name]) {
        $Object | Add-Member -NotePropertyName $Name -NotePropertyValue $Value
    } else {
        $Object.$Name = $Value
    }
}

function Get-Sha256 {
    param([Parameter(Mandatory = $true)][string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Test-PowerShellFile {
    param([Parameter(Mandatory = $true)][string]$Path)
    $tokens = $null
    $errors = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile(
        $Path,
        [ref]$tokens,
        [ref]$errors
    )
    if (@($errors).Count -gt 0) {
        $rendered = @($errors | ForEach-Object {
            '{0}:{1} {2}' -f $_.Extent.StartLineNumber, $_.Extent.StartColumnNumber, $_.Message
        }) -join "`n"
        throw "PATCHED_AUTOPILOT_PARSE_FAILED:`n$rendered"
    }
}

function Patch-InstalledAutopilot {
    if (-not (Test-Path -LiteralPath $InstalledPs1 -PathType Leaf)) {
        return [pscustomobject][ordered]@{
            status = 'AUTOPILOT_NOT_INSTALLED'
            changed = $false
            replacements = 0
            before_sha256 = $null
            after_sha256 = $null
            backup = $null
        }
    }

    $beforeHash = Get-Sha256 -Path $InstalledPs1
    $text = [IO.File]::ReadAllText($InstalledPs1, [Text.Encoding]::UTF8)
    $replacements = 0

    $oldBlockerLine = @'
            ($blockerList | ForEach-Object { '- ' + [string]$_ }),
'@.TrimEnd("`r","`n")
    $newBlockerLine = @'
            (($blockerList | ForEach-Object { '- ' + [string]$_ }) -join "`r`n"),
'@.TrimEnd("`r","`n")
    $oldErrorLine = @'
            $errorLines,
'@.TrimEnd("`r","`n")
    $newErrorLine = @'
            ($errorLines -join "`r`n"),
'@.TrimEnd("`r","`n")

    if ($text.Contains($oldBlockerLine)) {
        $text = $text.Replace($oldBlockerLine, $newBlockerLine)
        $replacements++
    } elseif (-not $text.Contains($newBlockerLine)) {
        throw 'AUTOPILOT_BLOCKER_RENDER_LINE_NOT_FOUND'
    }

    if ($text.Contains($oldErrorLine)) {
        $text = $text.Replace($oldErrorLine, $newErrorLine)
        $replacements++
    } elseif (-not $text.Contains($newErrorLine)) {
        throw 'AUTOPILOT_ERROR_RENDER_LINE_NOT_FOUND'
    }

    if (-not $text.Contains($PatchMarker)) {
        $text += "`r`n$PatchMarker`r`n"
    }

    $changed = ($replacements -gt 0)
    $backup = $null
    if ($changed) {
        $stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
        $backup = Join-Path $InstallRoot ("MAESTRO_AUTOPILOT_V4.before-notice-v4-1.$stamp.ps1")
        Copy-Item -LiteralPath $InstalledPs1 -Destination $backup
        $temporary = "$InstalledPs1.$([Guid]::NewGuid().ToString('N')).tmp"
        try {
            Write-Utf8Bom -Path $temporary -Content $text
            Test-PowerShellFile -Path $temporary
            Move-Item -LiteralPath $temporary -Destination $InstalledPs1 -Force
        } finally {
            Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
        }
    } else {
        Test-PowerShellFile -Path $InstalledPs1
    }

    return [pscustomobject][ordered]@{
        status = if ($changed) { 'PATCHED' } else { 'ALREADY_PATCHED' }
        changed = $changed
        replacements = $replacements
        before_sha256 = $beforeHash
        after_sha256 = Get-Sha256 -Path $InstalledPs1
        backup = $backup
    }
}

function Reset-AutopilotNotificationState {
    $state = Read-JsonSafe -Path $StatePath
    if ($null -eq $state) { return $null }
    Set-PropertyValue -Object $state -Name 'owner_notification_signature' -Value ''
    Set-PropertyValue -Object $state -Name 'consecutive_same_signature' -Value 0
    Set-PropertyValue -Object $state -Name 'last_signature' -Value ''
    Write-JsonAtomic -Path $StatePath -Value $state
    return $state
}

function Write-ExactNoticeFromState {
    $state = Read-JsonSafe -Path $StatePath
    $summaryPath = [string](Get-PropertyValue -Object $state -Name 'last_json' -Default '')
    $humanPath = [string](Get-PropertyValue -Object $state -Name 'last_report' -Default '')
    $summary = Read-JsonSafe -Path $summaryPath

    $blockers = @()
    if ($null -eq $summary) {
        $blockers = @('RUNNER_FATAL_NO_SUMMARY')
    } else {
        $blockers = @((Get-PropertyValue -Object $summary -Name 'blockers' -Default @()))
    }
    if (@($blockers).Count -eq 0) {
        $blockers = @('NO_EXPLICIT_BLOCKERS_IN_SUMMARY')
    }

    $errors = @()
    if ($null -ne $summary) {
        $errors = @((Get-PropertyValue -Object $summary -Name 'runner_errors' -Default @()))
    }

    $lines = New-Object System.Collections.Generic.List[string]
    foreach ($line in @(
        'MAESTRO AUTOPILOT V4 продолжает работать сам. Повторно запускать файлы не нужно.',
        '',
        'Сейчас осталось действие владельца либо устойчивый внешний блокер:'
    )) {
        [void]$lines.Add([string]$line)
    }
    foreach ($item in @($blockers)) {
        [void]$lines.Add('- ' + [string]$item)
    }
    [void]$lines.Add('')
    [void]$lines.Add('Точные runner errors:')
    if (@($errors).Count -eq 0) {
        [void]$lines.Add('- runner exceptions отсутствуют либо summary недоступен.')
    } else {
        foreach ($errorItem in @($errors)) {
            $stage = [string](Get-PropertyValue -Object $errorItem -Name 'stage' -Default 'UNKNOWN_STAGE')
            $type = [string](Get-PropertyValue -Object $errorItem -Name 'type' -Default 'UNKNOWN_TYPE')
            $lineNumber = [string](Get-PropertyValue -Object $errorItem -Name 'script_line' -Default '')
            $message = ([string](Get-PropertyValue -Object $errorItem -Name 'message' -Default '')).Replace("`r", ' ').Replace("`n", ' ')
            [void]$lines.Add(('- stage={0}; type={1}; line={2}; message={3}' -f $stage,$type,$lineNumber,$message))
        }
    }
    [void]$lines.Add('')
    [void]$lines.Add("Последний отчёт: $humanPath")
    [void]$lines.Add("Последний JSON: $summaryPath")
    [void]$lines.Add('')
    [void]$lines.Add('После выполнения действительно необходимого действия автопилот сам повторит проверку.')

    $content = $lines.ToArray() -join "`r`n"
    if ($content -match 'System\.Object\[\]') {
        throw 'NOTICE_RENDER_STILL_CONTAINS_SYSTEM_OBJECT_ARRAY'
    }
    Write-Utf8Bom -Path $NoticePath -Content $content
    return [pscustomobject][ordered]@{
        path = $NoticePath
        summary_path = $summaryPath
        human_path = $humanPath
        blocker_count = @($blockers).Count
        error_count = @($errors).Count
        contains_system_object_array = $false
    }
}

function Start-FollowUpHidden {
    Ensure-Directory -Path $InstallRoot
    Copy-Item -LiteralPath $PSCommandPath -Destination $RepairCopy -Force
    $arguments = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "{0}" -Mode FollowUp -InstallRoot "{1}" -Desktop "{2}" -NoUi' -f $RepairCopy,$InstallRoot,$Desktop
    Start-Process -FilePath 'powershell.exe' -ArgumentList $arguments -WindowStyle Hidden | Out-Null
}

function Invoke-FollowUp {
    $mutex = New-Object Threading.Mutex($false, 'Local\MAESTRO_AUTOPILOT_V4_SELFHEAL_V4_1')
    $acquired = $false
    try {
        $acquired = $mutex.WaitOne(0)
        if (-not $acquired) { return }
        if (-not (Test-Path -LiteralPath $InstalledPs1 -PathType Leaf)) { return }

        [void](Write-ExactNoticeFromState)
        $initialState = Read-JsonSafe -Path $StatePath
        $initialRun = [string](Get-PropertyValue -Object $initialState -Name 'last_run_at_utc' -Default '')

        for ($attempt = 1; $attempt -le 30; $attempt++) {
            [void](Reset-AutopilotNotificationState)
            $arguments = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "{0}" -Mode Run -NoUi' -f $InstalledPs1
            try {
                $process = Start-Process -FilePath 'powershell.exe' -ArgumentList $arguments -WindowStyle Hidden -Wait -PassThru
            } catch { }

            $currentState = Read-JsonSafe -Path $StatePath
            $currentRun = [string](Get-PropertyValue -Object $currentState -Name 'last_run_at_utc' -Default '')
            [void](Write-ExactNoticeFromState)
            if (-not [string]::IsNullOrWhiteSpace($currentRun) -and $currentRun -ne $initialRun) {
                break
            }
            Start-Sleep -Seconds 120
        }

        $watchArguments = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "{0}" -Mode Watch -NoUi' -f $InstalledPs1
        try { Start-Process -FilePath 'powershell.exe' -ArgumentList $watchArguments -WindowStyle Hidden | Out-Null } catch { }
        Write-Utf8NoBom -Path $MarkerPath -Content ((Get-Date).ToUniversalTime().ToString('o'))
    } finally {
        if ($acquired) { try { $mutex.ReleaseMutex() } catch { } }
        $mutex.Dispose()
    }
}

function Write-Receipt {
    param([string]$Status, $Patch, $Notice, [string]$ErrorMessage = '')
    $receipt = [ordered]@{
        schema_version = 1
        status = $Status
        generated_at_utc = (Get-Date).ToUniversalTime().ToString('o')
        install_root = $InstallRoot
        installed_ps1_exists = (Test-Path -LiteralPath $InstalledPs1 -PathType Leaf)
        patch = $Patch
        notice = $Notice
        follow_up_started = ($Mode -eq 'Repair' -and $Status -eq 'PASS')
        branch_deletion = $false
        force_push = $false
        history_rewrite = $false
        git_reset_hard = $false
        git_clean = $false
        user_files_deleted = $false
        private_zip_published = $false
        money_spent_rub = 0
        error = $ErrorMessage
    }
    Write-JsonAtomic -Path $ReceiptPath -Value $receipt
    return $receipt
}

if ($Mode -eq 'FollowUp') {
    Invoke-FollowUp
    exit 0
}

$patchResult = $null
$noticeResult = $null
try {
    Ensure-Directory -Path $InstallRoot
    $patchResult = Patch-InstalledAutopilot
    if ($patchResult.status -eq 'AUTOPILOT_NOT_INSTALLED') {
        [void](Write-Receipt -Status 'NOT_APPLICABLE' -Patch $patchResult -Notice $null)
        exit 0
    }
    [void](Reset-AutopilotNotificationState)
    $noticeResult = Write-ExactNoticeFromState
    if ($Mode -eq 'Repair') {
        Start-FollowUpHidden
    }
    [void](Write-Receipt -Status 'PASS' -Patch $patchResult -Notice $noticeResult)
    if (-not $NoUi) {
        Write-Host 'MAESTRO_AUTOPILOT_V4_SELFHEAL_V4_1_PASS'
    }
    exit 0
} catch {
    try {
        [void](Write-Receipt -Status 'FAIL' -Patch $patchResult -Notice $noticeResult -ErrorMessage $_.Exception.Message)
    } catch { }
    if (-not $NoUi) {
        Write-Error $_
    }
    exit 1
}
