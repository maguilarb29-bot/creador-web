import json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

CAT_PATH = 'c:/Users/Alejandro/Documents/Proyecto Pignatelli/Api_PG/data/solaris_catalogo.json'
cat = json.load(open(CAT_PATH, encoding='utf-8'))

def nueva_entrada(codigo, foto, desc_orig, nombre_es, cantidad, materiales, cat_item):
    num = int(''.join(c for c in codigo if c.isdigit()))
    return {
        'fotos': [foto], 'refs': [],
        'categoria': 'Decorative', 'numItem': num,
        'catCodigo': 'D', 'codigoItem': codigo,
        'descripcionOriginal': desc_orig,
        'ubicacion': cat_item.get('ubicacion', ''),
        'precioUSD': None,
        'tieneSothebys': False, 'refSothebys': '', 'notas': '',
        'nombreES': nombre_es, 'descripcionES': '',
        'cantidad': cantidad, 'materiales': materiales, 'estilo': '', 'estado': ''
    }

nombre_d72 = cat['D72'].get('nombreES', 'Esculturas decorativas de bronce ciervos y flamencos')
nombre_d74 = cat['D74'].get('nombreES', 'Esculturas abstractas doradas para centro de mesa')

# ── D72: Ref + D72a + D72b ────────────────────────────────────────────────
cat['D72']['fotos'] = ['D72-esculturas-decorativas-de-bronce-ciervos - Ref.jpg']
cat['D72']['notas'] = 'Ref del set. Articulos: D72a, D72b'
cat['D72a'] = nueva_entrada('D72a', 'D72a-esculturas-decorativas-de-bronce-ciervos.jpg',
    '4 bronze statuettes animals (2 deer, 2 flamingos)', nombre_d72, 2, 'Bronce', cat['D72'])
cat['D72b'] = nueva_entrada('D72b', 'D72b-4 bronze statuettes animals (2 deer, 2 flamingos).jpg',
    '4 bronze statuettes animals (2 deer, 2 flamingos)', nombre_d72, 2, 'Bronce', cat['D72'])
print('D72: Ref + D72a + D72b OK')

# ── D74: Ref + D74a + D74b ────────────────────────────────────────────────
cat['D74']['fotos'] = ['D74-esculturas-abstractas-doradas-para-centro - Ref.jpg']
cat['D74']['notas'] = 'Ref del set. Articulos: D74a, D74b'
cat['D74a'] = nueva_entrada('D74a', 'D74a-esculturas-abstractas-doradas-para-centro.jpg',
    '', nombre_d74, 1, 'Metal dorado', cat['D74'])
cat['D74b'] = nueva_entrada('D74b', 'D74b-esculturas-abstractas-doradas-para-centro.jpg',
    '', nombre_d74, 1, 'Metal dorado', cat['D74'])
print('D74: Ref + D74a + D74b OK')

# ── D87: Ref + D87a + D87b ────────────────────────────────────────────────
cat['D87']['fotos'] = ['D87-3 objects - 2 bronze dogs + 1 sphere in circles - Ref.JPG']
cat['D87']['notas'] = 'Ref del set. Articulos: D87a (perros), D87b (esfera)'
cat['D87a'] = nueva_entrada('D87a', 'D87a- 2 bronze dogs.JPG',
    '2 bronze dogs', 'Par de perros de bronce decorativos', 2, 'Bronce', cat['D87'])
cat['D87b'] = nueva_entrada('D87b', 'D87b- 1 sphere in circles.JPG',
    '1 sphere in circles', 'Esfera orbital decorativa de metal', 1, 'Metal', cat['D87'])
print('D87: Ref + D87a + D87b OK')

# ── D89: Ref + D89a + D89b + D89c ─────────────────────────────────────────
cat['D89']['fotos'] = ['D89-3 misc objects - leaves, red vase and gold coloured circular sculpture - Ref.JPG']
cat['D89']['notas'] = 'Ref del set. Articulos: D89a, D89b, D89c'
cat['D89a'] = nueva_entrada('D89a', 'D89a-, red vase.JPG',
    'red vase', 'Jarron rojo de ceramica decorativa', 1, 'Ceramica', cat['D89'])
cat['D89b'] = nueva_entrada('D89b', 'D89b- gold coloured circular sculpture.JPG',
    'gold coloured circular sculpture', 'Escultura circular dorada abstracta', 1, 'Metal dorado', cat['D89'])
cat['D89c'] = nueva_entrada('D89c', 'D89c- objects - leaves,  sculpture.JPG',
    'leaves sculpture', 'Esculturas decorativas de hojas doradas', 1, 'Metal', cat['D89'])
print('D89: Ref + D89a + D89b + D89c OK')

json.dump(cat, open(CAT_PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print()
print('Catalogo guardado.')
