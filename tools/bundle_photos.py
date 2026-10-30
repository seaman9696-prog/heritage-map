"""fetch_all.py の結果を、アプリに同梱する形(photos/index.json と photos/pNN.json)にまとめる。

使い方: python3 -I bundle_photos.py work_dir app_dir [chunks]
  画像は幅320px以内・JPEG(品質80)に統一し、base64 の data URL にして JSON に入れる。
  遺産の番号 % chunks 番目のファイルに入る。ポップアップを開くと、その1ファイルだけ読む。
  あわせて work_dir/report.json に、照合のルールごとの件数・保留の一覧・飛ばした画像を書く。
"""
import base64, io, json, os, sys
from collections import Counter
from PIL import Image

work, app, *rest = sys.argv[1:]
chunks = int(rest[0]) if rest else 20
match = json.load(open(os.path.join(work, 'match.json')))
images = {f.split('.')[0]: f for f in os.listdir(os.path.join(work, 'images'))}
out = os.path.join(app, 'photos')
os.makedirs(out, exist_ok=True)
groups, ranks, skipped, missing = {}, Counter(), [], []
for sid in sorted(match, key=int):
    m = match[sid]
    if m.get('pending'):
        continue
    meta_path = os.path.join(work, 'meta', sid + '.json')
    if not os.path.exists(meta_path) or sid not in images:
        missing.append(sid)
        continue
    meta = json.load(open(meta_path))
    if meta.get('skipped'):
        skipped.append({'id': sid, 'reason': meta['skipped'], 'file': meta['file']})
        continue
    im = Image.open(os.path.join(work, 'images', images[sid]))
    im.seek(0)  # GIF などは最初のコマ
    if im.mode not in ('RGB', 'L'):
        rgba = im.convert('RGBA')
        bg = Image.new('RGB', im.size, 'white')
        bg.paste(rgba, mask=rgba.split()[-1])
        im = bg
    im.thumbnail((320, 640))
    buf = io.BytesIO()
    im.convert('RGB').save(buf, 'JPEG', quality=80, optimize=True, progressive=True)
    groups.setdefault(int(sid) % chunks, {})[sid] = {
        'data': 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode(),
        'w': im.width, 'h': im.height,
        'artist': meta['artist'], 'license': meta['license'], 'license_url': meta['license_url'], 'page_url': meta['page_url'],
        # 照合のルール: 1=完全一致 2=英字付き 3=構成資産の画像
        'rank': meta['rank'], 'component': meta['rank'] == 3, 'qid': meta['qid'], 'p757': meta['p757'],
    }
    ranks[meta['rank']] += 1
for f in os.listdir(out):
    if f.startswith('p') and f.endswith('.json'):
        os.remove(os.path.join(out, f))
for n, g in groups.items():
    json.dump(g, open(os.path.join(out, f'p{n:02d}.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
ids = sorted(int(k) for g in groups.values() for k in g)
json.dump({'chunks': chunks, 'ids': ids}, open(os.path.join(out, 'index.json'), 'w'))
pending = [{'id': k, 'rank': v['rank'], 'candidates': v['candidates']} for k, v in match.items() if v.get('pending')]
report = {'by_rank': {str(k): v for k, v in sorted(ranks.items())}, 'total': len(ids), 'pending': pending,
          'skipped': skipped, 'not_fetched_yet': missing,
          'bytes': sum(os.path.getsize(os.path.join(out, f)) for f in os.listdir(out))}
json.dump(report, open(os.path.join(work, 'report.json'), 'w'), ensure_ascii=False, indent=1)
print(f"画像あり {len(ids)}件 {dict(ranks)} / 保留 {len(pending)} / 使わない {len(skipped)} / 未取得 {len(missing)} / 合計 {report['bytes']/1048576:.1f}MB")
