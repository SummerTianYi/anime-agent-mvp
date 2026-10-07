"""Read-only compact status, no keys, logs or private message contents."""
import json
from probe import get
result={}
for port in (8765,8770):
    try:
        data=get(port,'/health')
        result[str(port)]={k:data[k] for k in ('status','llm','tts','wake','roles','phase','model_ready','ready') if k in data}
    except Exception as e:result[str(port)]={'error':type(e).__name__}
print(json.dumps(result,ensure_ascii=False,indent=2))
