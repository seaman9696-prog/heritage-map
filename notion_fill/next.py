import json,glob,os,sys
O=sys.argv[1]; n=int(sys.argv[2])
done=set(open(O+'/done.txt').read().split())
hits=[]
for f in sorted(glob.glob(O+'/wiki/*.json')):
    d=json.load(open(f)); k=os.path.basename(f)[:-5]
    if d['wiki'] and k not in done: hits.append((k,d))
print('pending hits',len(hits))
for k,d in hits[:n]:
    w=d['wiki']; t=w['text']
    for cut in ['\n== 脚注','\n== 参考文献','\n== 外部リンク','\n== 関連項目','\n== ギャラリー','\n== 交通','\n== アクセス']:
        if cut in t: t=t[:t.index(cut)]
    print('#####',k,'|',d['name_ja'],'|',d['name_en'],'|',d['year'],d['criteria'],d['category'],d['countries'],'| wiki:',w['title'])
    print(t[:2400]); print()
