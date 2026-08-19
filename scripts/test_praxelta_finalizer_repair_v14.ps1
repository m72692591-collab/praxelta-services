[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Repair-FinalizerFile {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Finalizer source is missing: $Path"
    }

    $utf8Strict = New-Object Text.UTF8Encoding($false, $true)
    $source = [IO.File]::ReadAllText($Path, $utf8Strict)
    $matchesBefore = [Regex]::Matches($source, '(?<!\{)\$Branch:').Count
    $repaired = [Regex]::Replace(
        $source,
        '(?<!\{)\$Branch:',
        [System.Text.RegularExpressions.MatchEvaluator]{
            param($Match)
            return '${Branch}:'
        }
    )
    if ([Regex]::IsMatch($repaired, '(?<!\{)\$Branch:')) {
        throw 'Unsafe $Branch: interpolation remains after repair.'
    }

    [IO.File]::WriteAllText(
        $Path,
        $repaired,
        (New-Object Text.UTF8Encoding($true))
    )

    $tokens = $null
    $parseErrors = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile(
        $Path,
        [ref]$tokens,
        [ref]$parseErrors
    )
    if (@($parseErrors).Count -gt 0) {
        $details = @($parseErrors | ForEach-Object {
            '{0}:{1} {2}' -f $_.Extent.StartLineNumber, $_.Extent.StartColumnNumber, $_.Message
        }) -join "`n"
        throw "Finalizer still fails to parse after repair:`n$details"
    }
    return $matchesBefore
}

$fixture = Join-Path $env:TEMP (
    'praxelta-finalizer-repair-v14-' + [Guid]::NewGuid().ToString('N') + '.ps1'
)
try {
    $fixtureText = @'
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
function Test-BranchInterpolation {
    param([string]$Branch)
    if ($Branch -eq 'rebase') {
        throw "Cannot rebase finalization worktree for $Branch: simulated"
    }
    throw "Cannot push finalization worktree to $Branch: simulated"
}
'@
    [IO.File]::WriteAllText(
        $fixture,
        $fixtureText,
        (New-Object Text.UTF8Encoding($false))
    )

    $count = Repair-FinalizerFile -Path $fixture
    if ($count -ne 2) {
        throw "Expected two repaired interpolations, got $count."
    }

    $bytes = [IO.File]::ReadAllBytes($fixture)
    if ($bytes.Length -lt 3 -or $bytes[0] -ne 0xEF -or $bytes[1] -ne 0xBB -or $bytes[2] -ne 0xBF) {
        throw 'Repaired file does not contain a UTF-8 BOM.'
    }

    $text = [IO.File]::ReadAllText($fixture)
    if ([Regex]::Matches($text, [Regex]::Escape('${Branch}:')).Count -ne 2) {
        throw 'Repaired interpolation count is incorrect.'
    }
    if ([Regex]::IsMatch($text, '(?<!\{)\$Branch:')) {
        throw 'Unsafe interpolation remains in repaired file.'
    }

    Write-Host 'PRAXELTA_FINALIZER_REPAIR_V14_PASS replacements=2 bom=true parser=true'
} finally {
    Remove-Item -LiteralPath $fixture -Force -ErrorAction SilentlyContinue
}
