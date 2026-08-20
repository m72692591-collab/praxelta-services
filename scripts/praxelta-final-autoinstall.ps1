param(
    [Parameter(Mandatory = $true)][string]$SelfPath,
    [Parameter(Mandatory = $true)][string]$RawFile,
    [Parameter(Mandatory = $true)][string]$ZipMarker
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$ExpectedInnerSha256 = '396551a0ef5e0e2af22e849d12b93a839ec213be27f7e65b53896fda3e9ecf33'
$Documents = [Environment]::GetFolderPath([Environment+SpecialFolder]::MyDocuments)
if ([string]::IsNullOrWhiteSpace($Documents)) {
    $Documents = Join-Path $env:USERPROFILE 'Documents'
}
$Target = if (-not [string]::IsNullOrWhiteSpace($env:PRAXELTA_CI_TARGET)) {
    [IO.Path]::GetFullPath($env:PRAXELTA_CI_TARGET)
} else {
    Join-Path $Documents 'PRAXELTA\Travel'
}
$State = Join-Path $Target 'state'
$LogDir = Join-Path $State 'logs'
$Log = Join-Path $LogDir 'final-autonomous-install.log'
$Evidence = Join-Path $State 'FINAL_AUTONOMOUS_INSTALL.json'
$Temporary = Join-Path $env:TEMP ('praxelta-final-install-' + [Guid]::NewGuid().ToString('N'))
$ZipPath = Join-Path $Temporary 'praxelta-travel-ops-0.3.0.zip'
$Extract = Join-Path $Temporary 'release'
$Timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$Backup = Join-Path $Documents ('PRAXELTA\Backups\Travel\preinstall-' + $Timestamp)
$Media = Join-Path $Documents 'PRAXELTA\Installation Media\Travel-0.3.0'
$started = [DateTimeOffset]::UtcNow
$steps = New-Object System.Collections.Generic.List[object]

function Ensure-Directory {
    param([Parameter(Mandatory = $true)][string]$Path)
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
}

function Write-Log {
    param([Parameter(Mandatory = $true)][string]$Message)
    Ensure-Directory -Path $LogDir
    ('[{0}] {1}' -f ([DateTimeOffset]::Now.ToString('o')), $Message) | Add-Content -LiteralPath $Log -Encoding UTF8
    Write-Host $Message
}

function Add-Step {
    param([string]$Id, [bool]$Passed, [string]$Message, $Data = $null)
    $steps.Add([pscustomobject][ordered]@{
        id = $Id
        passed = $Passed
        message = $Message
        data = $Data
    })
    Write-Log ('{0}: {1}' -f $Id, $Message)
}

function Get-Sha256Bytes {
    param([Parameter(Mandatory = $true)][byte[]]$Bytes)
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        return (-join ($sha.ComputeHash($Bytes) | ForEach-Object { $_.ToString('x2') }))
    } finally {
        $sha.Dispose()
    }
}

function Copy-PreservedState {
    param([string]$From, [string]$To)
    if (-not (Test-Path -LiteralPath $From -PathType Container)) { return }
    Ensure-Directory -Path $To
    foreach ($relative in @('.env', 'state', 'data\partner_links_input.json')) {
        $source = Join-Path $From $relative
        if (-not (Test-Path -LiteralPath $source)) { continue }
        $destination = Join-Path $To $relative
        $parent = Split-Path -Parent $destination
        if (-not [string]::IsNullOrWhiteSpace($parent)) { Ensure-Directory -Path $parent }
        Copy-Item -LiteralPath $source -Destination $destination -Recurse -Force
    }
}

function Invoke-CheckedPowerShell {
    param([Parameter(Mandatory = $true)][string]$File, [string[]]$Arguments = @())
    Write-Log ('Running: {0}' -f $File)
    & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $File @Arguments *>> $Log
    $code = [int]$LASTEXITCODE
    if ($code -ne 0) {
        throw ('PowerShell script failed with exit code {0}: {1}' -f $code, $File)
    }
}

function Write-Evidence {
    param([string]$Status, [string]$ErrorMessage = '')
    Ensure-Directory -Path $State
    $payload = [ordered]@{
        schema = 1
        status = $Status
        generated_at_utc = [DateTimeOffset]::UtcNow.ToString('o')
        duration_seconds = [Math]::Round(([DateTimeOffset]::UtcNow - $started).TotalSeconds, 1)
        target = $Target
        source_installer = $SelfPath
        embedded_release_sha256 = $ExpectedInnerSha256
        backup = $Backup
        permanent_media = $Media
        steps = $steps.ToArray()
        error = $ErrorMessage
        remaining_owner_actions = @(
            'BotFather: create or confirm a Telegram bot and provide its token locally',
            'Travelpayouts: personally accept the current terms and provide account identifiers locally',
            'Official services: complete OTP or CAPTCHA when requested',
            'Confirm IP legal details, personal-data operator and advertising classification'
        )
    }
    [IO.File]::WriteAllText(
        $Evidence,
        ($payload | ConvertTo-Json -Depth 40),
        (New-Object Text.UTF8Encoding($true))
    )
}

try {
    Ensure-Directory -Path $Temporary
    Ensure-Directory -Path $Extract
    Ensure-Directory -Path $LogDir
    Write-Log 'PRAXELTA Travel final autonomous installation started.'

    $markerIndex = $RawFile.IndexOf($ZipMarker)
    if ($markerIndex -lt 0) { throw 'Embedded ZIP marker not found.' }
    $encoded = $RawFile.Substring($markerIndex + $ZipMarker.Length)
    $encoded = $encoded -replace '[^A-Za-z0-9+/=]', ''
    $releaseBytes = [Convert]::FromBase64String($encoded)
    $actualHash = Get-Sha256Bytes -Bytes $releaseBytes
    if ($actualHash -ne $ExpectedInnerSha256) {
        throw ('Embedded release SHA-256 mismatch: {0}' -f $actualHash)
    }
    [IO.File]::WriteAllBytes($ZipPath, $releaseBytes)
    Add-Step -Id 'embedded-release' -Passed $true -Message 'Embedded release decoded and SHA-256 verified.' -Data $actualHash

    Expand-Archive -LiteralPath $ZipPath -DestinationPath $Extract -Force
    $Source = Join-Path $Extract 'praxelta-travel-ops-0.3.0'
    foreach ($required in @(
        'START_HERE.cmd',
        'pyproject.toml',
        'scripts\setup_windows.ps1',
        'scripts\create_shortcuts.ps1',
        'scripts\install_automation.ps1',
        'scripts\write_pending_actions.ps1'
    )) {
        if (-not (Test-Path -LiteralPath (Join-Path $Source $required))) {
            throw ('Embedded release is missing required file: {0}' -f $required)
        }
    }
    Add-Step -Id 'release-layout' -Passed $true -Message 'Embedded release layout verified.'

    if (Test-Path -LiteralPath (Join-Path $Target 'STOP_PRIVATE_BOT.cmd') -PathType Leaf) {
        try { & (Join-Path $Target 'STOP_PRIVATE_BOT.cmd') | Out-Null } catch { }
    }

    if (Test-Path -LiteralPath $Target -PathType Container) {
        Copy-PreservedState -From $Target -To $Backup
        Remove-Item -LiteralPath $Target -Recurse -Force
        Add-Step -Id 'previous-state' -Passed $true -Message 'Existing secrets and state backed up before clean install.' -Data $Backup
    }

    Ensure-Directory -Path $Target
    Copy-Item -Path (Join-Path $Source '*') -Destination $Target -Recurse -Force
    Copy-PreservedState -From $Backup -To $Target
    Get-ChildItem -LiteralPath $Target -Recurse -File -Include *.ps1,*.cmd | Unblock-File -ErrorAction SilentlyContinue
    Add-Step -Id 'files-installed' -Passed $true -Message 'Clean release installed and preserved state restored.' -Data $Target

    Ensure-Directory -Path $Media
    Copy-Item -LiteralPath $SelfPath -Destination (Join-Path $Media 'PRAXELTA_AUTO_INSTALL_FINAL.cmd') -Force
    [IO.File]::WriteAllBytes((Join-Path $Media 'praxelta-travel-ops-0.3.0.zip'), $releaseBytes)
    [IO.File]::WriteAllText(
        (Join-Path $Media 'praxelta-travel-ops-0.3.0.zip.sha256'),
        ($ExpectedInnerSha256 + '  praxelta-travel-ops-0.3.0.zip' + [Environment]::NewLine),
        [Text.Encoding]::ASCII
    )
    Add-Step -Id 'permanent-media' -Passed $true -Message 'Permanent offline restore media created.' -Data $Media

    Invoke-CheckedPowerShell -File (Join-Path $Target 'scripts\setup_windows.ps1')
    Add-Step -Id 'setup-windows' -Passed $true -Message 'Python, tests, SQLite, doctor, demo and initial backup completed.'

    if ($env:PRAXELTA_CI -ne '1') {
        Invoke-CheckedPowerShell -File (Join-Path $Target 'scripts\create_shortcuts.ps1')
        Invoke-CheckedPowerShell -File (Join-Path $Target 'scripts\install_automation.ps1')
    }
    Invoke-CheckedPowerShell -File (Join-Path $Target 'scripts\write_pending_actions.ps1')
    Add-Step -Id 'local-automation' -Passed $true -Message 'Shortcuts, safe automation and owner-action report prepared.'

    $Python = Join-Path $Target '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { throw 'Virtual-environment Python is missing.' }
    $doctor = (& $Python -m praxelta_travel_ops.cli doctor) -join [Environment]::NewLine
    if ($LASTEXITCODE -ne 0) { throw 'Final doctor failed.' }
    $activation = (& $Python -m praxelta_travel_ops.cli activation-status) -join [Environment]::NewLine
    if ($LASTEXITCODE -ne 0) { throw 'Activation status failed.' }
    Add-Step -Id 'final-verification' -Passed $true -Message 'Final doctor and activation status completed.' -Data ([ordered]@{ doctor = $doctor; activation = $activation })

    if ($env:PRAXELTA_CI -ne '1') {
        foreach ($url in @(
            'https://t.me/BotFather',
            'https://app.travelpayouts.com/',
            'https://lknpd.nalog.ru/'
        )) {
            try { Start-Process $url | Out-Null } catch { }
        }
        try { Start-Process notepad.exe (Join-Path $State 'OWNER_PENDING_ACTIONS.txt') | Out-Null } catch { }
        try { Start-Process explorer.exe $Target | Out-Null } catch { }
    }

    Write-Evidence -Status 'TECHNICAL_INSTALL_COMPLETED'
    Write-Log 'PRAXELTA_OWNER_MACHINE_TECHNICAL_INSTALL_COMPLETED'
    Write-Host ''
    Write-Host 'PRAXELTA_OWNER_MACHINE_TECHNICAL_INSTALL_COMPLETED' -ForegroundColor Green
    Write-Host ('Installed at: {0}' -f $Target) -ForegroundColor Green
    Write-Host ('Evidence: {0}' -f $Evidence) -ForegroundColor Green
    exit 0
} catch {
    try {
        Add-Step -Id 'fatal' -Passed $false -Message $_.Exception.Message
        Write-Evidence -Status 'FAILED' -ErrorMessage $_.Exception.Message
    } catch { }
    Write-Error $_
    exit 1
} finally {
    Remove-Item -LiteralPath $Temporary -Recurse -Force -ErrorAction SilentlyContinue
}
