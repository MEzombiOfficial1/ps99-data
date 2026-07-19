import json, urllib.request, re, datetime, time

def fetch_json(url, timeout=30):
    req = urllib.request.Request(url, headers={'User-Agent': 'PS99-Hub'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())

def extract_asset_id(icon_str):
    if not icon_str:
        return None
    m = re.search(r'(\d+)', str(icon_str))
    return m.group(1) if m else None

def resolve_thumbnails_batch(asset_ids, size='150x150', max_retries=3):
    """Resolve a batch of up to 100 asset IDs to image URLs.
    Returns dict {assetId: imageUrl}. Handles 429 with backoff."""
    result = {}
    if not asset_ids:
        return result
    ids_str = ','.join(asset_ids)
    url = f'https://thumbnails.roblox.com/v1/assets?assetIds={ids_str}&returnPolicy=PlaceHolder&size={size}&format=Png&isCircular=false'
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'PS99-Hub'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                d = json.loads(resp.read())
            for item in d.get('data', []):
                if item.get('state') == 'Completed':
                    result[str(item['targetId'])] = item['imageUrl']
            return result
        except Exception as e:
            if attempt < max_retries - 1:
                wait = (attempt + 1) * 2
                print(f'    batch failed (attempt {attempt+1}), retrying in {wait}s: {e}')
                time.sleep(wait)
            else:
                print(f'    batch FAILED after {max_retries} attempts: {e}')
    return result

def resolve_all_thumbnails(asset_ids, batch_size=100, delay_between_batches=0.5):
    """Resolve all asset IDs in batches with delay + retry. Returns {assetId: url}."""
    unique_ids = list(set(asset_ids))
    print(f'  resolving {len(unique_ids)} unique asset IDs in batches of {batch_size}...')
    result = {}
    failed = 0
    for i in range(0, len(unique_ids), batch_size):
        batch = unique_ids[i:i+batch_size]
        batch_result = resolve_thumbnails_batch(batch)
        result.update(batch_result)
        failed += len(batch) - len(batch_result)
        if i % (batch_size * 10) == 0 and i > 0:
            print(f'    {i+batch_size}/{len(unique_ids)} done, {len(result)} resolved so far')
        time.sleep(delay_between_batches)
    print(f'  resolved {len(result)}/{len(unique_ids)} ({failed} failed)')
    return result

# ============ PETS ============
print("Fetching pets...")
pets_data = fetch_json('https://ps99.biggamesapi.io/api/collection/Pets')
pets = pets_data.get('data', [])
print(f'  {len(pets)} pets from API')

resolved_pets = []
for i, p in enumerate(pets):
    cd = p.get('configData', {})
    thumb = cd.get('thumbnail', '')
    asset_id = extract_asset_id(thumb)
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

# Resolve ALL pet thumbnails with rate-limit-safe batching
pet_asset_ids = [p['assetId'] for p in resolved_pets if p['assetId']]
print(f'  {len(pet_asset_ids)} pets have assetIds, resolving images...')
pet_img_map = resolve_all_thumbnails(pet_asset_ids, batch_size=100, delay_between_batches=0.5)
for p in resolved_pets:
    if p['assetId'] and p['assetId'] in pet_img_map:
        p['imgUrl'] = pet_img_map[p['assetId']]

with_img = len([p for p in resolved_pets if p['imgUrl']])
with_desc = len([p for p in resolved_pets if p['desc']])
print(f'  pets with imgUrl: {with_img}/{len(resolved_pets)} ({100*with_img/len(resolved_pets):.0f}%)')
print(f'  pets with desc: {with_desc}/{len(resolved_pets)} ({100*with_desc/len(resolved_pets):.0f}%)')

with open('pets.json', 'w') as f: json.dump(resolved_pets, f, separators=(',', ':'))
print(f'{len(resolved_pets)} pets written to pets.json')

# ============ LEAGUES ============
print("\nFetching leagues...")
all_leagues = []
total_leagues = 0
for page in range(1, 6):
    try:
        d = fetch_json(f'https://ps99.biggamesapi.io/v1/leagues?page={page}&pageSize=100&sort=Points&sortOrder=desc')
        leagues = d.get('data', {}).get('leagues', [])
        total_leagues = d.get('data', {}).get('total', 0)
        all_leagues.extend(leagues)
        print(f'  page {page}: {len(leagues)} leagues (total: {len(all_leagues)})')
        if not leagues: break
        time.sleep(0.3)
    except Exception as e:
        print(f'  page {page} error: {e}')
        break

# Resolve league icons
league_asset_ids = [extract_asset_id(l.get('Icon', '')) for l in all_leagues if l.get('Icon')]
league_asset_ids = [a for a in league_asset_ids if a]
print(f'  resolving {len(league_asset_ids)} league icons...')
league_img_map = resolve_all_thumbnails(league_asset_ids, batch_size=100, delay_between_batches=0.5)

league_output = []
for l in all_leagues:
    asset_id = extract_asset_id(l.get('Icon', ''))
    league_output.append({
        'Name': l.get('Name', ''),
        'NameLower': l.get('NameLower', l.get('Name', '').lower()),
        'ID': l.get('ID', ''),
        'Icon': l.get('Icon'),
        'IconUrl': league_img_map.get(asset_id) if asset_id else None,
        'Level': l.get('Level', 1),
        'Points': l.get('Points', 0),
        'Members': l.get('Members', 0),
        'MemberCapacity': l.get('MemberCapacity', 4),
        'ContributorCount': l.get('ContributorCount', 0),
        'Owner': l.get('Owner'),
        'Created': l.get('Created')
    })

leagues_payload = {
    'leagues': league_output,
    'totalLeagues': total_leagues,
    'updatedAt': datetime.datetime.now(datetime.timezone.utc).isoformat()
}
with open('leagues.json', 'w') as f: json.dump(leagues_payload, f, separators=(',', ':'))
print(f'{len(league_output)} leagues written to leagues.json')

# ============ CLANS ============
print("\nFetching clans...")
clans_data = fetch_json('https://ps99.biggamesapi.io/api/clans?page=1&pageSize=100&sort=Points&sortOrder=desc')
clan_list_raw = clans_data.get('data', [])
print(f'  {len(clan_list_raw)} clans from API')

# Resolve clan icons
clan_asset_ids = [extract_asset_id(c.get('Icon', '')) for c in clan_list_raw if c.get('Icon')]
clan_asset_ids = [a for a in clan_asset_ids if a]
print(f'  resolving {len(clan_asset_ids)} clan icons...')
clan_img_map = resolve_all_thumbnails(clan_asset_ids, batch_size=100, delay_between_batches=0.5)

all_clans = []
for idx, c in enumerate(clan_list_raw):
    asset_id = extract_asset_id(c.get('Icon', ''))
    all_clans.append({
        'name': c.get('Name', ''),
        'iconUrl': clan_img_map.get(asset_id) if asset_id else None,
        'countryCode': c.get('CountryCode', ''),
        'totalDiamonds': c.get('DepositedDiamonds', 0),
        'members': c.get('Members', 0),
        'memberCapacity': c.get('MemberCapacity', 75),
        'points': c.get('Points', 0),
        'battlesParticipated': 0,
        'bestRank': 999,
        'bestMedal': None,
        'created': c.get('Created'),
        'rank': idx + 1
    })

# Fetch active battle
active_battle = None
try:
    battle_res = fetch_json('https://ps99.biggamesapi.io/api/activeClanBattle')
    battle_cfg = battle_res.get('data', {})
    if battle_cfg.get('configName'):
        cn = battle_cfg['configName']
        title = re.sub(r'([a-z])([A-Z])', r'\1 \2', cn)
        title = re.sub(r'([A-Za-z])(\d)', r'\1 \2', title).replace('_', ' ').strip()
        rewards = []
        seen = set()
        for pr in battle_cfg.get('configData', {}).get('PlacementRewards', []):
            item = pr.get('Item', {}).get('_data', {}).get('id', 'Unknown')
            if item in seen: continue
            seen.add(item)
            b = pr.get('Best', 0)
            w = pr.get('Worst', 0)
            placement = f'#{b}' if b == w else f'#{b}-{w}'
            rewards.append({'placement': placement, 'item': item})
            if len(rewards) >= 6: break
        active_battle = {'configName': cn, 'title': title, 'rewards': rewards}
except Exception as e:
    print(f'  active battle fetch failed: {e}')

clans_payload = {
    'allClans': all_clans,
    'allBattles': [],
    'totalClans': len(all_clans),
    'activeBattle': active_battle,
    'mostRecentBattle': active_battle,
    'updatedAt': datetime.datetime.now(datetime.timezone.utc).isoformat()
}
with open('clans.json', 'w') as f: json.dump(clans_payload, f, separators=(',', ':'))
print(f'{len(all_clans)} clans written to clans.json')
