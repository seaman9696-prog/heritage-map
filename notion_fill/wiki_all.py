"""各遺産の日本語版Wikipedia記事を取る。一覧記事は除き、本文に「世界遺産」を含む記事だけ採用。
途中で止まっても続きから(保存済みは飛ばす)。並列なし。"""
import json, os, re, sys, time, urllib.parse, urllib.request
UA = 'HeritageMapPersonal/1.0 (https://github.com/seaman9696-prog; personal non-commercial)'
API = 'https://ja.wikipedia.org/w/api.php?'
def get(params):
    url = API + urllib.parse.urlencode({**params, 'format': 'json'})
    for i in range(10):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60) as r:
                d = json.loads(r.read())
            if 'query' not in d:
                # 混雑などでエラーが返ったときは待ってやり直す
                time.sleep(min(10 * (i + 1), 120)); continue
            return d
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(int(e.headers.get('Retry-After') or 10) + 2); continue
            raise
        except (ValueError, OSError):
            time.sleep(min(2 ** (i + 1), 60))
    raise RuntimeError(url)
BAD = re.compile(r'の世界遺産|一覧|世界遺産委員会|^世界遺産')
def extract(title):
    p = next(iter(get({'action': 'query', 'prop': 'extracts', 'explaintext': 1, 'redirects': 1, 'titles': title})['query']['pages'].values()))
    return p.get('title', title), p.get('extract', '')
rows, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
for r in json.load(open(rows)):
    key = r['notion_url'][-32:]
    path = os.path.join(out, key + '.json')
    if os.path.exists(path):
        continue
    # 名前の括弧書きや「 : 」以降を外した短い名前でも探す
    name = r['name_ja']
    short = re.split(r'[（(:：]', name)[0].strip()
    cands = []
    for q in dict.fromkeys([name, short]):
        cands += [h['title'] for h in get({'action': 'query', 'list': 'search', 'srsearch': q, 'srlimit': 4})['query']['search']]
    # 遺産名の固有部分(カタカナ3字以上・漢字2字以上の語)が記事名に含まれるものだけ候補にする
    stop = {'世界遺産', '国立公園', '歴史地区', '旧市街', '文化的景観', '建造物群', '遺跡群', '考古遺跡', '自然保護区', '保護区', '遺跡', '景観'}
    toks = [t.strip('・＝ー') for t in re.findall(r'[ァ-ヴー＝・]{3,}|[一-龥々]{2,}', name)]
    toks = [t for t in toks if len(t) >= 2 and t not in stop]
    got = None
    for t in dict.fromkeys(cands):
        if BAD.search(t) or not any(k in t for k in toks):
            continue
        title, text = extract(t)
        if '世界遺産' in text and len(text) > 300:
            got = {'title': title, 'text': text}
            break
        time.sleep(0.5)
    json.dump({'name_ja': name, 'name_en': r.get('name_en'), 'id': r['id'], 'year': r.get('year'), 'criteria': r.get('criteria'),
               'countries': r.get('countries'), 'category': r.get('category'), 'candidates': cands, 'wiki': got},
              open(path, 'w'), ensure_ascii=False)
    print(name, '→', got['title'] if got else 'なし', flush=True)
    time.sleep(0.5)
