param(
    [string]$ImageDir = "C:\Users\Alejandro\Documents\Proyecto Pignatelli\Api_PG\output\sothebys_pages_hi",
    [string]$OutFile = "C:\Users\Alejandro\Documents\Proyecto Pignatelli\Api_PG\data\sothebys_ocr_pages.json",
    [int]$StartPage = 1,
    [int]$EndPage = 115
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime

$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType=WindowsRuntime]
$null = [Windows.Storage.Streams.IRandomAccessStreamWithContentType, Windows.Storage.Streams, ContentType=WindowsRuntime]
$null = [Windows.Media.Ocr.OcrResult, Windows.Foundation, ContentType=WindowsRuntime]

function Await-Op($op, [Type]$resultType) {
    $method = [System.WindowsRuntimeSystemExtensions].GetMethods() |
        Where-Object {
            $_.Name -eq 'AsTask' -and
            $_.IsGenericMethodDefinition -and
            $_.GetGenericArguments().Count -eq 1 -and
            $_.GetParameters().Count -eq 1 -and
            $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
        } |
        Select-Object -First 1

    $generic = $method.MakeGenericMethod(@($resultType))
    $task = $generic.Invoke($null, @($op))
    return $task.Result
}

function Get-OcrLines([string]$path) {
    $ocrEngine = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime]::TryCreateFromUserProfileLanguages()
    $file = Await-Op ([Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime]::GetFileFromPathAsync($path)) ([Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime])
    $stream = Await-Op ($file.OpenReadAsync()) ([Windows.Storage.Streams.IRandomAccessStreamWithContentType, Windows.Storage.Streams, ContentType=WindowsRuntime])
    $decoder = Await-Op ([Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime])
    $bitmap = Await-Op ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType=WindowsRuntime])
    $result = Await-Op ($ocrEngine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult, Windows.Foundation, ContentType=WindowsRuntime])
    return @($result.Lines | ForEach-Object { $_.Text })
}

$pages = @()
foreach ($page in $StartPage..$EndPage) {
    $file = Join-Path $ImageDir ("page_{0:d3}.png" -f $page)
    if (-not (Test-Path $file)) {
        Write-Warning "missing $file"
        continue
    }

    Write-Host "ocr page $page"
    $lines = Get-OcrLines -path $file
    $pages += [pscustomobject]@{
        page = $page
        file = $file
        lines = $lines
        text = ($lines -join "`n")
    }
}

$outDir = Split-Path -Parent $OutFile
if (-not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
}

$pages | ConvertTo-Json -Depth 6 | Set-Content -Path $OutFile -Encoding UTF8
Write-Host "saved $OutFile"
