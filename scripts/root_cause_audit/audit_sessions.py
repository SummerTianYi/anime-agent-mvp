from probe import get,db_connect
import json
db=db_connect(get(8765,'/health'))
print(json.dumps([dict(r) for r in db.execute("SELECT id,request_id,conversation_id,created_at,substr(content,1,80) AS audit_prefix FROM messages WHERE role='user' AND (content LIKE '[RA-%' OR content LIKE '天依你好，这是根因审计%')")],ensure_ascii=False))
