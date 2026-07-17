import json, urllib.request, re, datetime

def fetch_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'PS99-Hub'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

def resolve_icon(icon_str):
    if not icon_str:
        return None
    m = re.search(r'(\d+)', icon_str)
    if not m:
        return None
    asset_id = m.group(1)
    try:
        req = urllib.request.Request(
            f'https://thumbnails.roblox.com/v1/assets?assetIds={asset_id}&returnPolicy=PlaceHolder&size=150x150&format=Png&isCircular=false',
            headers={'User-Agent': 'PS99-Hub'}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            d = json.loads(resp.read())
        if d.get('data') and d['data'][0].get('state') == 'Completed':
            return d['data'][0]['imageUrl']
    except:
        pass
    return None

print("Fetching pets...")
pets_data = fetch_json('https://ps99.biggamesapi.io/api/collection/Pets')
pets = pets_data.get('data', [])
resolved_pets = []
for i, p in enumerate(pets):
    cd = p.get('configData', {})
    thumb = cd.get('thumbnail', '')
    asset_id = None
    if thumb:
        m = re.search(r'(\d+)', thumb)
        if m: asset_id = m.group(1)
    name = cd.get('name', p.get('configName', f'Pet {i}'))
    cat = p.get('category', 'Regular')
    cn = p.get('configName', name)
    cl = cat.lower()
    nl = name.lower()
    if 'gargantuan' in cl or 'gargantuan' in nl: tier = 'Gargantuan'
    elif 'titanic' in cl or 'titanic' in nl: tier = 'Titanic'
    elif cd.get('huge') or 'huge' in cl or nl.startswith('huge '): tier = 'Huge'
    elif 'exclusive' in cl or (cd.get('rarity') and cd['rarity'].get('_id') == 'Exclusive'): tier = 'Exclusive'
    elif 'secret' in cl: tier = 'Secret'
    else: tier = 'Regular'
    rarity = 'Regular'
    if cd.get('rarity'): rarity = cd['rarity'].get('DisplayName', cd['rarity'].get('_id', 'Regular'))
    resolved_pets.append({'id': cn, 'name': name, 'tier': tier, 'rarity': rarity, 'category': cat, 'desc': cd.get('indexDesc', ''), 'assetId': asset_id, 'imgUrl': None})
with_assets = [p for p in resolved_pets if p['assetId']]
for i in range(0, len(with_assets), 50):
    batch = with_assets[i:i+50]
    ids = [p['assetId'] for p in batch]
    try:
        req = urllib.request.Request(f'https://thumbnails.roblox.com/v1/assets?assetIds={",".join(ids)}&returnPolicy=PlaceHolder&size=420x420&format=Png&isCircular=false', headers={'User-Agent': 'PS99-Hub'})
        with urllib.request.urlopen(req, timeout=15) as resp: img_data = json.loads(resp.read())
        for item in img_data.get('data', []):
            if item.get('state') == 'Completed':
                pet = next((p for p in batch if p['assetId'] == str(item['targetId'])), None)
                if pet: pet['imgUrl'] = item['imageUrl']
    except: pass
    if i % 500 == 0 and i > 0: import time; time.sleep(2)
with open('pets.json', 'w') as f: json.dump(resolved_pets, f, separators=(',', ':'))
print(f'{len(resolved_pets)} pets written')

print("Fetching clans...")
players_data = fetch_json('https://ps99.biggamesapi.io/v1/clans/players')
players = players_data.get('data', {}).get('players', [])
active_battle = players_data.get('data', {}).get('activeBattleConfigName')
clans_map = {}
for p in players:
    clan = p.get('Clan', {})
    cn = clan.get('Name', 'Unknown')
    if cn not in clans_map:
        clans_map[cn] = {'name': cn, 'icon': clan.get('Icon', ''), 'country': clan.get('CountryCode', ''), 'place': clan.get('Place', 0), 'members': 0, 'totalPoints': 0, 'totalDiamonds': 0, 'players': []}
    c = clans_map[cn]
    c['members'] += 1
    c['totalPoints'] += p.get('ActiveBattlePoints', 0)
    c['totalDiamonds'] += p.get('AllTimeDiamonds', 0)
    c['players'].append({'name': p.get('DisplayName', str(p.get('UserID', ''))), 'points': p.get('ActiveBattlePoints', 0), 'diamonds': p.get('AllTimeDiamonds', 0), 'battles': p.get('TotalBattles', 0), 'medals': p.get('EarnedMedals', 0)})
clans_list = sorted(clans_map.values(), key=lambda c: c['totalDiamonds'], reverse=True)
for clan in clans_list:
    clan['iconUrl'] = resolve_icon(clan.get('icon', ''))
battle_data = None
if active_battle:
    try:
        battle_data = fetch_json(f'https://ps99.biggamesapi.io/v1/clans/battles/{active_battle}').get('data', {})
        for tc in battle_data.get('topClans', []):
            tc['iconUrl'] = resolve_icon(tc.get('icon', ''))
    except: pass
output = {'clans': clans_list, 'activeBattle': active_battle, 'battleData': battle_data, 'totalClans': len(clans_list), 'totalPlayers': len(players), 'updatedAt': datetime.datetime.now().isoformat()}
with open('clans.json', 'w') as f: json.dump(output, f, separators=(',', ':'))
print(f'{len(clans_list)} clans, battle: {active_battle}')
