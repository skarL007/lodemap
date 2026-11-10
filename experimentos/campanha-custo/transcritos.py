import json,sys,glob,os,collections
d=sys.argv[1]
arqs=[f for f in glob.glob(d+'/**/*.jsonl',recursive=True)]
uso=collections.defaultdict(lambda: collections.Counter()); vistos=set(); cmds=[]; agentes=[]
for f in arqs:
    for l in open(f,encoding='utf-8'):
        try: j=json.loads(l)
        except: continue
        m=j.get('message') or {}
        if j.get('type')=='assistant' and m.get('usage'):
            k=(m.get('id'),f)
            if m.get('id') in vistos: continue
            vistos.add(m.get('id'))
            u=m['usage']; mod=m.get('model')
            for c in ('input_tokens','output_tokens','cache_read_input_tokens','cache_creation_input_tokens'): uso[mod][c]+=u.get(c) or 0
            uso[mod]['msgs']+=1
            for b in m.get('content') or []:
                if b.get('type')=='tool_use' and b['name']=='Bash': cmds.append(b['input'].get('command','')[:160])
                if b.get('type')=='tool_use' and b['name'] in('Agent','Task'): agentes.append((b['input'].get('subagent_type'),b['input'].get('model'),b['input'].get('description')))
for f in glob.glob(d+'/**/*.meta.json',recursive=True): print('meta',open(f).read()[:200])
print(json.dumps(uso,indent=1)); print('agentes',agentes)
print('\n'.join(c for c in cmds if 'descrever' in c or 'pip' in c or 'playwright' in c))
