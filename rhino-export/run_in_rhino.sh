#!/bin/sh
D="$(dirname "$0")"
export PYTHONIOENCODING=utf-8
python -I -c "import json,sys;print(json.dumps({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'run_python','arguments':{'script':open(sys.argv[1],encoding='utf-8').read()}}}))" "$1" > "$D/_body.json"
curl -s -m 600 -X POST http://localhost:10500/ -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" --data-binary @"$D/_body.json" | python -I -c "import json,sys;sys.stdout.reconfigure(encoding='utf-8');j=json.load(sys.stdin);r=j.get('result') or j;[print(c.get('text','')) for c in r.get('content',[])] if 'content' in r else print(j)"
