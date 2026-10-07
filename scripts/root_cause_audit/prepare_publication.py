"""Codex: redact audit-only public evidence, retaining private originals and hashes.

Never operates on V0/V1, live databases, assets, configuration or source code.
This is a mechanical publication transform, not evidence rescoring.
"""
import argparse,hashlib,json,os,re,shutil,subprocess
from pathlib import Path
from probe import ROOT
p=argparse.ArgumentParser();p.add_argument('--production',type=Path,required=True);a=p.parse_args()
package=ROOT/'docs/assessments/root-cause-audit'
private=a.production/'runs/private-audit-preservation/secrets.publication-20261007'
private.mkdir(parents=True,exist_ok=True)
subprocess.run(['git','-C',str(a.production),'check-ignore',str(private.relative_to(a.production))+'/check.json'],check=True,stdout=subprocess.DEVNULL)
secret_values=[]
for line in (a.production/'.env').read_text(encoding='utf-8-sig').splitlines():
    key,sep,value=line.partition('=')
    if sep and not key.startswith('#') and any(s in key.upper() for s in ('KEY','TOKEN','SECRET','PASSWORD')):
        value=value.strip().strip('\"').strip("'")
        if len(value)>8:secret_values.append(value)
replacements=[(str(ROOT),'<SOURCE>'),(str(a.production),'<PRODUCTION>'),
              (str(a.production.parent),'<WORK>'),(str(Path.home()),'<USER>')]
def scrub(text):
    for raw,to in replacements:
        for form in (raw,raw.replace('\\','/'),raw.replace('/','\\')):
            for n in (4,2,1):text=text.replace(form.replace('\\','\\'*n),to)
    text=re.sub(r'\\+localhost\\+c\$\\+Users\\+[^\\/]+',r'<USER-PHYSICAL>',text,flags=re.I)
    text=re.sub(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', 'OWNER_TEST_MAILBOX', text)
    text=re.sub(r'(?im)(From:|To:)\s*[^\r\n<]*<OWNER_TEST_MAILBOX>', r'\1 OWNER_DISPLAY_NAME <OWNER_TEST_MAILBOX>', text)
    return text
manifest=[]
for file in sorted((package/'evidence').iterdir()):
    if not file.is_file() or file.suffix not in ('.json','.md','.txt'):continue
    raw=file.read_bytes();dest=private/file.name
    if dest.exists():raise SystemExit('Private originals already exist; do not overwrite or re-sanitize')
    dest.write_bytes(raw)
    source=raw.decode('utf-8')
    # Keep original reviewer file links navigable from the public checkout.
    if file.suffix=='.md':
        def link(m):
            path=Path(m.group(1));relative=os.path.relpath(path,file.parent).replace('\\','/')
            return ']('+relative+('#L'+m.group(2) if m.group(2) else '')+')'
        prefix=str(ROOT).replace('\\','/')
        source=re.sub(r'\]\(/?('+re.escape(prefix)+r'/[^):]+)(?::(\d+))?\)',link,source)
    if file.suffix=='.json':
        def transform(x):
            if isinstance(x,str):return scrub(x)
            if isinstance(x,list):return [transform(v) for v in x]
            if isinstance(x,dict):return {scrub(k):transform(v) for k,v in x.items()}
            return x
        public=json.dumps(transform(json.loads(source)),ensure_ascii=False,indent=2)+'\n'
    else:public=scrub(source)
    if any(value in public for value in secret_values):
        raise SystemExit('Secret-value scan failed; value withheld')
    file.write_text(public,encoding='utf-8',newline='\n')
    manifest.append({'path':'evidence/'+file.name,'original_sha256':hashlib.sha256(raw).hexdigest(),
        'published_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'private_original_retained':True})
out=package/'publication-manifest.json'
if out.exists():raise SystemExit('Refusing to overwrite publication manifest')
out.write_text(json.dumps({'method':'path/contact redaction only; no scores, IDs, timestamps or event ordering changed',
    'private_location':'production/runs/private-audit-preservation/secrets.publication-20261007 (gitignored)',
    'files':manifest,'secret_scan':'current .env secret values checked without output'},ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
print(json.dumps({'published_files':len(manifest),'raw_originals_preserved':True,'secret_values_found':0}))
