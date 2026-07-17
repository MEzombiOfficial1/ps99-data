import json, urllib.request, re, sys

req = urllib.request.Request('https://ps99.biggamesapi.io/api/collection/Pets', headers={'User-Agent': 'PS99-Hub'})
with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read())

pets = data.get('data', [])
resolved = []

for i, p in enumerate(pets):
    cd = p.get('configData', {})
    thumb = cd.get('thumbnail', '')
    asset_id = None
    if thumb:
        m = re.search(r'(\d+)', thumb)
        if m:
            asset_id = m.group(1)
    
    name = cd.get('name', p.get('configName', f'Pet {i}'))
    cat = p.get('category', 'Regular')
    config_name = p.get('configName', name)
    
    cat_lower = cat.lower()
    name_lower = name.lower()
    if 'gargantuan' in cat_lower or 'gargantuan' in name_lower:
        tier = 'Gargantuan'
    elif 'titanic' in cat_lower or 'titanic' in name_lower:
        tier = 'Titanic'
    elif cd.get('huge') or 'huge' in cat_lower or name_lower.startswith('huge '):
        tier = 'Huge'
    elif 'exclusive' in cat_lower or (cd.get('rarity') and cd['rarity'].get('_id') == 'Exclusive'):
        tier = 'Exclusive'
    elif 'secret' in cat_lower:
        tier = 'Secret'
    else:
        tier = 'Regular'
    
    rarity = 'Regular'
    if cd.get('rarity'):
        rarity = cd['rarity'].get('DisplayName', cd['rarity'].get('_id', 'Regular'))
    
    resolved.append({
        'id': config_name,
        'name': name,
        'tier': tier,
        'rarity': rarity,
        'category': cat,
        'desc': cd.get('indexDesc', ''),
        'assetId': asset_id,
        'imgUrl': None
    })

with_assets = [p for p in resolved if p['assetId']]
for i in range(0, len(with_assets), 50):
    batch = with_assets[i:i+50]
    ids = [p['assetId'] for p in batch]
    try:
        req = urllib.request.Request(
            f'https://thumbnails.roblox.com/v1/assets?assetIds={",".join(ids)}&returnPolicy=PlaceHolder&size=420x420&format=Png&isCircular=false',
            headers={'User-Agent': 'PS99-Hub'}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            img_data = json.loads(resp.read())
        for item in img_data.get('data', []):
            if item.get('state') == 'Completed':
                pet = next((p for p in batch if p['assetId'] == str(item['targetId'])), None)
                if pet:
                    pet['imgUrl'] = item['imageUrl']
    except:
        pass
    if i % 500 == 0 and i > 0:
        import time
        time.sleep(2)

with open('pets.json', 'w') as f:
    json.dump(resolved, f, separators=(',', ':'))

print(f'{len(resolved)} pets written')
