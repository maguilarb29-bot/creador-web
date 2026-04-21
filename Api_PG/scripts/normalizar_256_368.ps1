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

function Get-NewFileName {
  param([Parameter(Mandatory = $true)][string]$Name)

  switch -Regex ($Name) {
    '^261-cascanueces-abridor-de-conchas-de-laton-vintage(?<ext>\.[^.]+)$' { return "261A-1-cascanueces-abridor-de-conchas-de-laton-vintage$($matches.ext)" }
    '^261-platos-decorativos-de-metal-plateado-con-medallon-conmemorativo(?<ext>\.[^.]+)$' { return "261B-1-platos-decorativos-de-metal-plateado-con-medallon-conmemorativo$($matches.ext)" }
    '^265a-(?<rest>.+)$' { return "265A-1-$($matches.rest)" }
    '^265b-(?<rest>.+)$' { return "265B-1-$($matches.rest)" }
    '^294a-(?<rest>.+)$' { return "294A-1-$($matches.rest)" }
    '^294ab-(?<rest>.+)$' { return "294A-2-$($matches.rest)" }
    '^314-(?<rest>.+)$' { return "314A-1-$($matches.rest)" }
    '^314a-(?<rest>.+)$' { return "314A-2-$($matches.rest)" }
    '^355a-(?<rest>.+)$' { return "355A-1-$($matches.rest)" }
    '^358A-2-(?<rest>.+)$' { return "358A-1-$($matches.rest)" }
    '^359 mesa de cafe china(?<ext>\.[^.]+)$' { return "359A-1-mesa-de-cafe-china$($matches.ext)" }
    '^361A-1-\s+juego de lentes de sol(?<ext>\.[^.]+)$' { return "361A-1-juego-de-lentes-de-sol$($matches.ext)" }
    '^362A-1-(?<ext>\.[^.]+)$' { return "362A-1$($matches.ext)" }
    '^364-1-(?<rest>.+)$' { return "364A-1-$($matches.rest)" }
    '^(?<num>(25[7-9]|2[6-9]\d|3[0-5]\d|360))-(?<rest>.+)$' { return "$($matches.num)A-1-$($matches.rest)" }
    default { return $null }
  }
}

function Update-PhotoNames {
  param(
    [Parameter(Mandatory = $true)]$Object,
    [Parameter(Mandatory = $true)][hashtable]$FileMap
  )
  if ($null -eq $Object.PSObject.Properties['fotos']) { return }
  $newFotos = @()
  foreach ($foto in @($Object.fotos)) {
    if ($FileMap.ContainsKey($foto)) { $newFotos += $FileMap[$foto] } else { $newFotos += $foto }
  }
  Set-Prop -Object $Object -Name 'fotos' -Value $newFotos
}

$root = 'c:\Users\Alejandro\Documents\Proyecto Pignatelli'
$imagesRoot = Join-Path $root 'Api_PG\images\fotos-Solaris-inventory'
$catalogPath = Join-Path $root 'Api_PG\data\solaris_catalogo.json'
$estructuraPath = Join-Path $root 'Api_PG\data\solaris_fotos_estructura.json'
$docsRoot = Join-Path $root 'docs'

$timestamp = Get-Date -Format 'yyyy-MM-dd-HHmmss'
Copy-Item -LiteralPath $catalogPath -Destination ($catalogPath + ".bak-$timestamp-256-368") -Force
Copy-Item -LiteralPath $estructuraPath -Destination ($estructuraPath + ".bak-$timestamp-256-368") -Force

$renames = @()
$fileMap = @{}

Get-ChildItem -LiteralPath $imagesRoot -Recurse -File | ForEach-Object {
  $newName = Get-NewFileName -Name $_.Name
  if ($null -eq $newName -or $newName -eq $_.Name) { return }

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
}

$catalog = Get-Content -LiteralPath $catalogPath -Raw -Encoding UTF8 | ConvertFrom-Json
$estructura = Get-Content -LiteralPath $estructuraPath -Raw -Encoding UTF8 | ConvertFrom-Json

# Catalogo: renombres simples de clave
$simpleCatalogRenames = @{
  '257'='257A'; '258'='258A'; '259'='259A'; '260'='260A'; '262'='262A'; '263'='263A'; '264'='264A';
  '266'='266A'; '267'='267A'; '268'='268A'; '269'='269A'; '270'='270A'; '271'='271A'; '272'='272A';
  '273'='273A'; '274'='274A'; '275'='275A'; '276'='276A'; '277'='277A'; '278'='278A'; '279'='279A';
  '280'='280A'; '281'='281A'; '282'='282A'; '283'='283A'; '284'='284A'; '285'='285A'; '286'='286A';
  '287'='287A'; '288'='288A'; '289'='289A'; '290'='290A'; '291'='291A'; '292'='292A'; '293'='293A';
  '295'='295A'; '296'='296A'; '297'='297A'; '298'='298A'; '299'='299A'; '300'='300A'; '301'='301A';
  '302'='302A'; '303'='303A'; '304'='304A'; '305'='305A'; '306'='306A'; '307'='307A'; '308'='308A';
  '309'='309A'; '310'='310A'; '311'='311A'; '312'='312A'; '313'='313A'; '315'='315A'; '316'='316A';
  '317'='317A'; '318'='318A'; '319'='319A'; '320'='320A'; '321'='321A'; '322'='322A'; '323'='323A';
  '324'='324A'; '325'='325A'; '326'='326A'; '327'='327A'; '328'='328A'; '329'='329A'; '330'='330A';
  '331'='331A'; '332'='332A'; '333'='333A'; '334'='334A'; '335'='335A'; '336'='336A'; '337'='337A';
  '338'='338A'; '339'='339A'; '340'='340A'; '341'='341A'; '342'='342A'; '343'='343A'; '344'='344A';
  '345'='345A'; '346'='346A'; '347'='347A'; '348'='348A'; '349'='349A'; '350'='350A'; '351'='351A';
  '352'='352A'; '353'='353A'; '354'='354A'; '356'='356A'; '359'='359A'; '360'='360A'; '364'='364A';
  '355a'='355A'
}

foreach ($oldKey in $simpleCatalogRenames.Keys) {
  $prop = $catalog.PSObject.Properties[$oldKey]
  if ($null -eq $prop) { continue }
  $newKey = $simpleCatalogRenames[$oldKey]
  $item = Clone-Object $prop.Value
  Update-PhotoNames -Object $item -FileMap $fileMap
  Set-Prop -Object $item -Name 'codigoItem' -Value $newKey
  $catalog.PSObject.Properties.Remove($oldKey)
  $catalog | Add-Member -NotePropertyName $newKey -NotePropertyValue $item
}

# Catalogo: 261 se divide en A/B
if ($catalog.PSObject.Properties['261']) {
  $base = $catalog.'261'
  $fotoA = '261A-1-cascanueces-abridor-de-conchas-de-laton-vintage.jpg'
  $fotoB = '261B-1-platos-decorativos-de-metal-plateado-con-medallon-conmemorativo.jpg'
  $itemA = Clone-Object $base
  $itemB = Clone-Object $base
  Set-Prop -Object $itemA -Name 'codigoItem' -Value '261A'
  Set-Prop -Object $itemA -Name 'fotos' -Value @($fotoA)
  Set-Prop -Object $itemA -Name 'descripcionOriginal' -Value 'Cascanueces abridor de conchas de laton vintage'
  Set-Prop -Object $itemA -Name 'nombreES' -Value 'Cascanueces abridor de conchas de laton vintage'
  Set-Prop -Object $itemA -Name 'materiales' -Value 'Laton'
  Set-Prop -Object $itemA -Name 'estilo' -Value 'Vintage'

  Set-Prop -Object $itemB -Name 'codigoItem' -Value '261B'
  Set-Prop -Object $itemB -Name 'fotos' -Value @($fotoB)
  Set-Prop -Object $itemB -Name 'descripcionOriginal' -Value 'Platos decorativos de metal plateado con medallon conmemorativo'
  Set-Prop -Object $itemB -Name 'nombreES' -Value 'Platos decorativos de metal plateado con medallon conmemorativo'
  Set-Prop -Object $itemB -Name 'materiales' -Value 'Metal plateado'
  Set-Prop -Object $itemB -Name 'estilo' -Value 'Clasico / Conmemorativo'

  $catalog.PSObject.Properties.Remove('261')
  $catalog | Add-Member -NotePropertyName '261A' -NotePropertyValue $itemA
  $catalog | Add-Member -NotePropertyName '261B' -NotePropertyValue $itemB
}

# Catalogo: 265a/265b se vuelven 265A/265B
foreach ($pair in @(@('265a','265A'), @('265b','265B'))) {
  $oldKey, $newKey = $pair
  if ($catalog.PSObject.Properties[$oldKey]) {
    $item = Clone-Object $catalog.$oldKey
    Update-PhotoNames -Object $item -FileMap $fileMap
    Set-Prop -Object $item -Name 'codigoItem' -Value $newKey
    $catalog.PSObject.Properties.Remove($oldKey)
    $catalog | Add-Member -NotePropertyName $newKey -NotePropertyValue $item
  }
}

# Catalogo: 294a + 294ab => 294A con dos fotos
if ($catalog.PSObject.Properties['294a']) {
  $item = Clone-Object $catalog.'294a'
  $fotos = @()
  if ($fileMap.ContainsKey('294a-coleccion-de-ceramica-blanca-decorativa.jpg')) { $fotos += $fileMap['294a-coleccion-de-ceramica-blanca-decorativa.jpg'] }
  if ($fileMap.ContainsKey('294ab-coleccion-de-ceramica-blanca-decorativa.jpg')) { $fotos += $fileMap['294ab-coleccion-de-ceramica-blanca-decorativa.jpg'] }
  Set-Prop -Object $item -Name 'codigoItem' -Value '294A'
  Set-Prop -Object $item -Name 'fotos' -Value $fotos
  $catalog.PSObject.Properties.Remove('294a')
  if ($catalog.PSObject.Properties['294ab']) { $catalog.PSObject.Properties.Remove('294ab') }
  $catalog | Add-Member -NotePropertyName '294A' -NotePropertyValue $item
}

# Catalogo: 314 + 314a => 314A con dos fotos
if ($catalog.PSObject.Properties['314']) {
  $item = Clone-Object $catalog.'314'
  $fotos = @()
  if ($fileMap.ContainsKey('314-estuche-de-almacenamiento-vintage-de-cuero-y-madera.jpg')) { $fotos += $fileMap['314-estuche-de-almacenamiento-vintage-de-cuero-y-madera.jpg'] }
  if ($fileMap.ContainsKey('314a-estuche-de-almacenamiento-vintage.jpg')) { $fotos += $fileMap['314a-estuche-de-almacenamiento-vintage.jpg'] }
  Set-Prop -Object $item -Name 'codigoItem' -Value '314A'
  Set-Prop -Object $item -Name 'fotos' -Value $fotos
  $catalog.PSObject.Properties.Remove('314')
  if ($catalog.PSObject.Properties['314a']) { $catalog.PSObject.Properties.Remove('314a') }
  $catalog | Add-Member -NotePropertyName '314A' -NotePropertyValue $item
}

# Catalogo: 358A/361A/362A mantienen clave y solo cambian foto
foreach ($key in @('358A','361A','362A')) {
  if ($catalog.PSObject.Properties[$key]) {
    $item = $catalog.$key
    Update-PhotoNames -Object $item -FileMap $fileMap
  }
}

$catalog | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $catalogPath -Encoding UTF8

# Estructura: mismo tratamiento
foreach ($oldKey in $simpleCatalogRenames.Keys) {
  $prop = $estructura.PSObject.Properties[$oldKey]
  if ($null -eq $prop) { continue }
  $newKey = $simpleCatalogRenames[$oldKey]
  $item = Clone-Object $prop.Value
  Update-PhotoNames -Object $item -FileMap $fileMap
  Set-Prop -Object $item -Name 'codigoItem' -Value $newKey
  $estructura.PSObject.Properties.Remove($oldKey)
  $estructura | Add-Member -NotePropertyName $newKey -NotePropertyValue $item
}

if ($estructura.PSObject.Properties['261']) {
  $base = $estructura.'261'
  $itemA = Clone-Object $base
  $itemB = Clone-Object $base
  Set-Prop -Object $itemA -Name 'codigoItem' -Value '261A'
  Set-Prop -Object $itemA -Name 'fotos' -Value @('261A-1-cascanueces-abridor-de-conchas-de-laton-vintage.jpg')
  Set-Prop -Object $itemB -Name 'codigoItem' -Value '261B'
  Set-Prop -Object $itemB -Name 'fotos' -Value @('261B-1-platos-decorativos-de-metal-plateado-con-medallon-conmemorativo.jpg')
  $estructura.PSObject.Properties.Remove('261')
  $estructura | Add-Member -NotePropertyName '261A' -NotePropertyValue $itemA
  $estructura | Add-Member -NotePropertyName '261B' -NotePropertyValue $itemB
}

foreach ($pair in @(@('265a','265A'), @('265b','265B'))) {
  $oldKey, $newKey = $pair
  if ($estructura.PSObject.Properties[$oldKey]) {
    $item = Clone-Object $estructura.$oldKey
    Update-PhotoNames -Object $item -FileMap $fileMap
    Set-Prop -Object $item -Name 'codigoItem' -Value $newKey
    $estructura.PSObject.Properties.Remove($oldKey)
    $estructura | Add-Member -NotePropertyName $newKey -NotePropertyValue $item
  }
}

if ($estructura.PSObject.Properties['294a']) {
  $item = Clone-Object $estructura.'294a'
  Set-Prop -Object $item -Name 'codigoItem' -Value '294A'
  Set-Prop -Object $item -Name 'fotos' -Value @('294A-1-coleccion-de-ceramica-blanca-decorativa.jpg','294A-2-coleccion-de-ceramica-blanca-decorativa.jpg')
  $estructura.PSObject.Properties.Remove('294a')
  if ($estructura.PSObject.Properties['294ab']) { $estructura.PSObject.Properties.Remove('294ab') }
  $estructura | Add-Member -NotePropertyName '294A' -NotePropertyValue $item
}

if ($estructura.PSObject.Properties['314']) {
  $item = Clone-Object $estructura.'314'
  Set-Prop -Object $item -Name 'codigoItem' -Value '314A'
  Set-Prop -Object $item -Name 'fotos' -Value @('314A-1-estuche-de-almacenamiento-vintage-de-cuero-y-madera.jpg','314A-2-estuche-de-almacenamiento-vintage.jpg')
  $estructura.PSObject.Properties.Remove('314')
  if ($estructura.PSObject.Properties['314a']) { $estructura.PSObject.Properties.Remove('314a') }
  $estructura | Add-Member -NotePropertyName '314A' -NotePropertyValue $item
}

foreach ($key in @('358A','361A','362A')) {
  if ($estructura.PSObject.Properties[$key]) {
    $item = $estructura.$key
    Update-PhotoNames -Object $item -FileMap $fileMap
  }
}

$estructura | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $estructuraPath -Encoding UTF8

$mapPath = Join-Path $docsRoot 'mapa_normalizacion_256_368.csv'
$renames | Export-Csv -LiteralPath $mapPath -NoTypeInformation -Encoding UTF8

Write-Output "Renombres aplicados: $($renames.Count)"
Write-Output "Mapa: $mapPath"
