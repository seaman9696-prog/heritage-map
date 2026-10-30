"""世界遺産マップ用: 全件の代表画像(Wikidata P18)を Commons から取得する。

使い方: python3 -I fetch_all.py heritage_map.json out_dir
照合の順位(上位で画像のある項目が見つかれば下位は見ない):
  1 = P757 が登録番号と完全一致 / 2 = 数字のあとに英字(166rev, 123bis) / 3 = 構成資産(1133-001)
  同じ順位で画像のある項目が2つ以上 → 保留(pending)
出力: out_dir/match.json(照合結果), out_dir/images/<id>.<ext>, out_dir/meta/<id>.json(撮影者・ライセンス等)
途中で止まっても、もう一度同じコマンドで続きから再開する(取得済みは取り直さない)。並列では取りに行かない。
"""
import json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from html import unescape

UA = 'HeritageMapPersonal/1.0 (https://github.com/seaman9696-prog; personal non-commercial map) python-urllib'
WIDTH = 330  # Wikimediaは決まった幅(…250/330/500…)のサムネイルしか作らない
BATCH = 50


def log(*a):
    print(*a, flush=True)


def get(url, binary=False):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    for i in range(20):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                data = r.read()
                return data if binary else json.loads(data)
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                wait = max(int(e.headers.get('Retry-After') or 30), 5 * (i + 1)) + 2
                log(f'  {e.code} → {wait}秒待って再試行')
                time.sleep(wait)
                continue
            raise
        except Exception as e:
            log(f'  通信エラー({e}) → {2 ** (i + 1)}秒待って再試行')
            time.sleep(2 ** (i + 1))
    raise RuntimeError('再試行の上限: ' + url)


def strip_html(s):
    s = re.sub(r'<table class="licensetpl".*?</table>', '', s or '', flags=re.S)  # 非表示のライセンス表を除く
    return re.sub(r'\s+', ' ', unescape(re.sub(r'<[^>]+>', '', s))).strip()


def artist_of(artist, uploader):
    # 作者欄が空・定型文・「own work」だけのときは、アップロード者(=自作申告の作者)の名前にする
    if not artist or re.search(r'no machine-readable|^own ?work$|copyright holder', artist, re.I):
        return uploader
    return artist


def all_p757():
    q = 'SELECT ?item ?id ?img WHERE { ?item wdt:P757 ?id . OPTIONAL { ?item wdt:P18 ?img } }'
    res = get('https://query.wikidata.org/sparql?format=json&query=' + urllib.parse.quote(q))
    rows = {}
    for b in res['results']['bindings']:
        key = (b['item']['value'].rsplit('/', 1)[1], b['id']['value'])
        img = urllib.parse.unquote(b['img']['value'].rsplit('/', 1)[1]) if 'img' in b else None
        r = rows.setdefault(key, set())
        if img:
            r.add(img)
    return [{'qid': q, 'p757': i, 'imgs': sorted(imgs)} for (q, i), imgs in rows.items()]


def match(site_ids, rows):
    rules = [
        (1, lambda n, v: v == n),
        (2, lambda n, v: re.fullmatch(re.escape(n) + r'[a-z]+', v, re.I)),
        (3, lambda n, v: re.fullmatch(re.escape(n) + r'-\d+', v)),
    ]
    by_num = {}
    for r in rows:
        lead = re.match(r'\d+', r['p757'])
        if lead and r['imgs']:
            by_num.setdefault(lead.group(), []).append(r)
    out = {}
    for n in site_ids:
        for rank, ok in rules:
            hits = [r for r in by_num.get(n, []) if ok(n, r['p757'])]
            items = {r['qid'] for r in hits}
            if len(items) == 1:
                h = hits[0]
                out[n] = {'rank': rank, 'qid': h['qid'], 'p757': h['p757'], 'file': h['imgs'][0]}
                break
            if len(items) > 1:
                out[n] = {'rank': rank, 'pending': True,
                          'candidates': [{'qid': r['qid'], 'p757': r['p757'], 'file': r['imgs'][0]} for r in hits]}
                break
    return out


def commons_batch(files):
    params = {'action': 'query', 'format': 'json', 'prop': 'imageinfo', 'titles': '|'.join('File:' + f for f in files),
              'iiprop': 'url|user|extmetadata', 'iiurlwidth': WIDTH,
              'iiextmetadatafilter': 'Artist|Credit|LicenseShortName|LicenseUrl'}
    res = get('https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(params))
    q = res['query']
    # API はタイトルを正規化する(_→空白など)ので、元の名前に戻して返す
    back = {x['to']: x['from'] for x in q.get('normalized', [])}
    out = {}
    for page in q['pages'].values():
        if 'imageinfo' not in page:
            continue
        ii = page['imageinfo'][0]
        m = ii.get('extmetadata', {})
        val = lambda k: strip_html(m.get(k, {}).get('value', ''))
        title = back.get(page['title'], page['title'])
        out[title[len('File:'):]] = {
            # thumb.wikimedia.org と同じパスで upload.wikimedia.org からも取れる
            'thumb_url': ii['thumburl'].split('?')[0].replace('//thumb.wikimedia.org/', '//upload.wikimedia.org/'),
            'page_url': ii['descriptionurl'],
            'artist': artist_of(val('Artist'), ii.get('user', '')),
            'license': val('LicenseShortName'), 'license_url': val('LicenseUrl'),
        }
    return out


def main():
    src, out_dir = sys.argv[1:3]
    os.makedirs(os.path.join(out_dir, 'images'), exist_ok=True)
    os.makedirs(os.path.join(out_dir, 'meta'), exist_ok=True)
    sites = json.load(open(src))['sites']
    ids = sorted({str(s['id']) for s in sites if s.get('id') is not None}, key=int)

    mpath = os.path.join(out_dir, 'match.json')
    if os.path.exists(mpath):
        matched = json.load(open(mpath))
    else:
        log('Wikidata から P757 の全項目を取得中…')
        matched = match(ids, all_p757())
        json.dump(matched, open(mpath, 'w'), ensure_ascii=False, indent=1)
    todo = [n for n, m in matched.items() if not m.get('pending') and not os.path.exists(os.path.join(out_dir, 'meta', n + '.json'))]
    log(f'照合 {len(matched)}件 / 未取得 {len(todo)}件')

    for i in range(0, len(todo), BATCH):
        chunk = todo[i:i + BATCH]
        info = commons_batch(sorted({matched[n]['file'] for n in chunk}))
        for n in chunk:
            m, inf = matched[n], info.get(matched[n]['file'])
            meta_path = os.path.join(out_dir, 'meta', n + '.json')
            if not inf or not inf['license']:
                # Commons に無い・ライセンスが読めない画像は使わない(記録は残して取り直さない)
                json.dump({**m, 'skipped': 'no_license' if inf else 'not_found'}, open(meta_path, 'w'), ensure_ascii=False)
                continue
            ext = inf['thumb_url'].rsplit('.', 1)[-1].lower()
            try:
                img = get(inf['thumb_url'], binary=True)
            except Exception as e:
                # 取れなかった画像は記録せず次へ(次に実行したときに取り直す)
                log(f'  {n}: 取得できず飛ばす({e})')
                continue
            open(os.path.join(out_dir, 'images', f'{n}.{ext}'), 'wb').write(img)
            # meta は画像を保存したあとに書く(meta があれば取得済みとみなすため)
            json.dump({**m, **inf, 'bytes': len(img)}, open(meta_path, 'w'), ensure_ascii=False)
            time.sleep(1)
        log(f'{min(i + BATCH, len(todo))}/{len(todo)}')
    log('完了')


if __name__ == '__main__':
    main()
