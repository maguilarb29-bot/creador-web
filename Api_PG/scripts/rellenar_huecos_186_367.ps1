$ErrorActionPreference = 'Stop'

function Clone-Object {
  param([Parameter(Mandatory = $true)]$InputObject)
  return ($InputObject | ConvertTo-Json -Depth 20 | ConvertFrom-Json)
}

function Set-Prop {
  param(
    [Parameter(Mandatory = $true)]$Object,
    [Parameter(Mandatory = $true)][string]$Name,
    $Value
  )
  $prop = $Object.PSObject.Properties[$Name]
  if ($null -ne $prop) {
    $prop.Value = $Value
  }
  else {
    $Object | Add-Member -NotePropertyName $Name -NotePropertyValue $Value
  }
}

$root = 'c:\Users\Alejandro\Documents\Proyecto Pignatelli'
$imagesRoot = Join-Path $root 'Api_PG\images\fotos-Solaris-inventory'
$catalogPath = Join-Path $root 'Api_PG\data\solaris_catalogo.json'
$estructuraPath = Join-Path $root 'Api_PG\data\solaris_fotos_estructura.json'
$docsRoot = Join-Path $root 'docs'

$mapping = [ordered]@{
  '367A' = '263A'
  '366A' = '266A'
  '365A' = '267A'
  '364A' = '316A'
  '363A' = '320A'
  '362A' = '322A'
  '361A' = '327A'
  '358A' = '328A'
  '357A' = '334A'
  '356A' = '335A'
  '355A' = '336A'
  '354A' = '359A'
  '353A' = '360A'
}

$timestamp = Get-Date -Format 'yyyy-MM-dd-HHmmss'
Copy-Item -LiteralPath $catalogPath -Destination ($catalogPath + ".bak-$timestamp-fill-gaps") -Force
Copy-Item -LiteralPath $estructuraPath -Destination ($estructuraPath + ".bak-$timestamp-fill-gaps") -Force

$renames = @()
$fileMap = @{}

Get-ChildItem -LiteralPath $imagesRoot -Recurse -File | ForEach-Object {
  foreach ($oldCode in $mapping.Keys) {
    if ($_.BaseName -match ("^" + [regex]::Escape($oldCode) + "(?=-|$)")) {
      $newCode = $mapping[$oldCode]
      $newName = ($_.Name -replace ("^" + [regex]::Escape($oldCode)), $newCode)
      $target = Join-Path $_.DirectoryName $newName
      if (Test-Path -LiteralPath $target) {
        throw "Conflicto de renombre: '$($_.FullName)' -> '$target'"
      }
      Rename-Item -LiteralPath $_.FullName -NewName $newName
      $renames += [pscustomobject]@{
        carpeta = $_.DirectoryName
        origen = $_.Name
        destino = $newName
      }
      $fileMap[$_.Name] = $newName
      break
    }
  }
}

$catalog = Get-Content -LiteralPath $catalogPath -Raw -Encoding UTF8 | ConvertFrom-Json
$estructura = Get-Content -LiteralPath $estructuraPath -Raw -Encoding UTF8 | ConvertFrom-Json

foreach ($pair in $mapping.GetEnumerator()) {
  $oldKey = $pair.Key
  $newKey = $pair.Value

  if ($catalog.PSObject.Properties[$oldKey]) {
    $item = Clone-Object $catalog.$oldKey
    if ($item.PSObject.Properties['fotos']) {
      $newFotos = @()
      foreach ($foto in @($item.fotos)) {
        if ($fileMap.ContainsKey($foto)) { $newFotos += $fileMap[$foto] } else { $newFotos += $foto }
      }
      Set-Prop -Object $item -Name 'fotos' -Value $newFotos
    }
    Set-Prop -Object $item -Name 'codigoItem' -Value $newKey
    if ($newKey -match '^(\d+)') {
      Set-Prop -Object $item -Name 'numItem' -Value ([int]$matches[1])
    }
    $catalog.PSObject.Properties.Remove($oldKey)
    $catalog | Add-Member -NotePropertyName $newKey -NotePropertyValue $item
  }

  if ($estructura.PSObject.Properties[$oldKey]) {
    $item = Clone-Object $estructura.$oldKey
    if ($item.PSObject.Properties['fotos']) {
      $newFotos = @()
      foreach ($foto in @($item.fotos)) {
        if ($fileMap.ContainsKey($foto)) { $newFotos += $fileMap[$foto] } else { $newFotos += $foto }
      }
      Set-Prop -Object $item -Name 'fotos' -Value $newFotos
    }
    Set-Prop -Object $item -Name 'codigoItem' -Value $newKey
    if ($newKey -match '^(\d+)') {
      Set-Prop -Object $item -Name 'numItem' -Value ([int]$matches[1])
    }
    $estructura.PSObject.Properties.Remove($oldKey)
    $estructura | Add-Member -NotePropertyName $newKey -NotePropertyValue $item
  }
}

$catalog | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $catalogPath -Encoding UTF8
$estructura | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $estructuraPath -Encoding UTF8

$mapPath = Join-Path $docsRoot 'mapa_relleno_huecos_186_367.csv'
$renames | Export-Csv -LiteralPath $mapPath -NoTypeInformation -Encoding UTF8

Write-Output "Renombres aplicados: $($renames.Count)"
Write-Output "Mapa: $mapPath"
