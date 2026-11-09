"""User-scoped public lookups. Only catalogue terms cross the public search boundary."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import json
import os
import re
import socket
import urllib.error
import urllib.parse
import urllib.request

TOOL = "public_web_search"
ENDPOINT = "https://api.tavily.com/search"
# Canonical public entities/fields, not answers. An unrecognised or private topic
# has no automatic egress grant. In particular, no history or arbitrary model
# string can become a query, URL, domain filter, body, or HTTP header.
SUBJECTS = {
    "F1": r"(?<![A-Za-z0-9])F\s?1(?![A-Za-z0-9])|一级方程式",
    "英超":r"英超|英格兰足球超级联赛", "NBA":r"\bNBA\b|美职篮", "中超":r"中超",
    "世界杯":r"世界杯", "欧冠":r"欧冠", "意甲":r"意甲", "德甲":r"德甲", "西甲":r"西甲",
    "诺贝尔物理学奖":r"诺贝尔物理(?:学)?奖", "诺贝尔化学奖":r"诺贝尔化学奖",
    "诺贝尔文学奖":r"诺贝尔文学奖", "诺贝尔生理学或医学奖":r"诺贝尔(?:生理学或医学|医学)奖",
    "戛纳金棕榈奖":r"戛纳.{0,9}金棕榈|金棕榈奖", "奥斯卡最佳影片":r"奥斯卡.{0,4}最佳影片",
    "Ubuntu":r"(?<![A-Za-z])Ubuntu(?![A-Za-z])", "Python":r"(?<![A-Za-z])Python(?![A-Za-z])",
    "Godot":r"(?<![A-Za-z])Godot(?![A-Za-z])",
    "国际空间站":r"国际空间站", "美元兑人民币":r"美元(?:兑|对|换)人民币",
}
FIELDS = {"赛程":r"哪一?站|下[一场站轮]|赛程|日程|进行到|上一站|最近一站",
          "积分榜":r"积分|排名|排行榜|榜首|射手榜|领跑", "获奖理由及得主":r"获奖|奖.{0,6}谁|得主|拿奖|花落谁家",
          "最新稳定版本":r"稳定版|最新版本|最新.{0,3}版|版本号","位置":r"(?:飞到|位于|位置|在哪)",
          "汇率":r"汇率|兑换价"}
QUESTION = re.compile(r"(?:查|搜|看看|告诉我|想知道|你知道|现在|目前|今年|本届|这[一届季]|最近|最新|谁|哪[位站一]|如何|多少|排第|怎么样|情况)")
EXPLANATION = re.compile(r"^(?:[他她]说|引用|原文|假如|假设|如果|为什么|解释|举例|翻译)|(?:什么意思|是什么原理|怎么查|怎么搜索|如何查询|需要授权|不要查|别查|不用查|先别查|别联网|不要联网|不联网|别搜|不要搜|只.{0,3}(?:解释|讨论))")
QUOTES = re.compile(r'~~~[\s\S]*?~~~|\x60{3}[\s\S]*?\x60{3}|\x60[^\x60]*\x60|“[^”]*”|「[^」]*」|『[^』]*』|‘[^’]*’|"[^"]*"')
MAIL = re.compile(r"(?:发(?:送)?(?:一封)?邮件|邮件发给|(?:发|转发|寄|发送)给|电邮给)")
NO_MAIL = re.compile(r"(?:别|不要|不用|无需|不必|先不|不准|禁止).{0,12}(?:发|寄|电邮)|(?:勿发|不发)")
ADDRESS = re.compile(r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![A-Za-z0-9.-])",re.ASCII)
LITERAL_LOOKUP = re.compile(r"^\s*(?:请|帮我|请帮我|麻烦你)?(?:在|从)?(?:公开网页|公开资料|公网|官网)(?:上)?(?:查询|搜索|查找|检索)[：:\s]*[《“「]([^》”」\n]{2,60})[》”」][。！？!? ]*$")
PUBLIC_EVENT = re.compile(r"(?P<subject>[A-Za-z0-9\u4e00-\u9fff· -]{2,28}(?:联赛|公开赛|锦标赛|大奖赛|电影节|运动会|世界杯))")
PRIVATE = re.compile(r"我家|我的|我们|同学|同事|朋友|老板|客户|私人|内部|账号|帐号|密码|令牌|密钥|通讯录|住址|地址|电话|手机号|网盘|邮件|身份证|病历|secret|token|password|api.?key|\d{7,}",re.I)


def safe_literal(value):
    return (isinstance(value,str) and re.fullmatch(r"[A-Za-z0-9\u4e00-\u9fff· +.-]{2,60}",value) is not None
            and not PRIVATE.search(value) and not re.search(r"[A-Za-z0-9_-]{25,}",value))


def manual_query_allowed(intent, args):
    """Legacy search still needs consent. Only explicitly requested literal keywords may leave."""
    query = args.get("query")
    if not safe_literal(query):
        return False
    options = {"search_depth":{"basic","advanced","fast","ultra-fast"},"topic":{"general","news","finance"},
               "time_range":{"day","week","month","year"}}
    for key,value in args.items():
        if key=="query" or key=="max_results" and type(value) is int and 1<=value<=10:
            continue
        if key not in options or not isinstance(value,str) or value not in options[key]:
            return False
    literal = LITERAL_LOOKUP.fullmatch(intent)
    if literal:
        return query.casefold()==literal[1].strip().casefold()
    for clause in re.split(r"[，,。；;！？!?\n]",intent):
        match = re.match(r"^\s*(?:天依|请你?|帮我|麻烦你?|在网上|去网上|上网|\s)*(?:搜索(?:网页)?|检索|搜一下|查一下|查询)\s*[：:]?\s*(.{2,100})$",clause)
        if match and safe_literal(match[1].strip()) and query.casefold() in match[1].casefold():
            return True
    return False


@dataclass(frozen=True)
class Lookup:
    subject: str
    fields: tuple[str, ...]
    year: int
    share: bool = False
    recipient: str = ""

    def arguments(self):
        return {"subject":self.subject,"fields":list(self.fields),"year":self.year}


def plan(text, prior_subject=""):
    literal = LITERAL_LOOKUP.fullmatch(text)
    if literal and safe_literal(literal[1]):
        return Lookup(literal[1],("公开资料",),date.today().year)
    clean = QUOTES.sub(" ",text).strip()
    if not QUESTION.search(clean) or EXPLANATION.search(clean):
        return None
    # Treat a send's recipient/body as data, even when it names another sport.
    parts = MAIL.split(clean,maxsplit=1)
    query = parts[0]
    subjects = [term for term, pattern in SUBJECTS.items() if re.search(pattern,query,re.I)]
    fields = tuple(term for term, pattern in FIELDS.items() if re.search(pattern,query))
    if not subjects and fields:
        lead = re.sub(r"^(?:(?:你知道|我想知道|麻烦你|请|帮我|搜索网页|查一下|查查|今年|现在|最近|目前|的|最新)\s*)+","",query)
        event = PUBLIC_EVENT.match(lead)
        if event and safe_literal(event["subject"]) and not re.search(r"[我你他她]|参加|去了|住在|带上|告诉",event["subject"]):
            subjects = [event["subject"]]
    if not fields and not re.search(r"查|搜|想知道|你知道|告诉我|情况如何|怎么样",query):
        return None
    if len(subjects) > 1 or not (subjects or fields and re.search(r"查|搜|积分榜|赛程",query)):
        return None
    subject = subjects[0] if subjects else prior_subject if prior_subject in SUBJECTS or PUBLIC_EVENT.fullmatch(prior_subject) else ""
    if not subject and not fields:
        return None
    if not fields:
        if subject in {"Python","Godot","Ubuntu","国际空间站","美元兑人民币"} or not re.search(r"最近|目前|现在|最新|今年|这一届|本届",query):
            return None  # The user needs to specify the requested public field.
        fields = ("获奖理由及得主",) if "奖" in subject or "最佳影片" in subject else ("赛程","积分榜")
    year_match = re.search(r"(?<!\d)(20\d{2})\s*(?:年|赛季|届)",query)
    year = int(year_match[1]) if year_match else date.today().year - int("去年" in query)
    share = len(parts)>1 and not NO_MAIL.search(clean)
    emails = ADDRESS.findall(parts[1]) if share else []
    return Lookup(subject,fields,year,share,emails[0] if len(emails)==1 else "")


def valid(args):
    if not isinstance(args,dict) or set(args)!={"subject","fields","year"}:
        return False
    fields = args["fields"]
    subject = args["subject"]
    if not safe_literal(subject):
        return False
    known = subject in SUBJECTS or PUBLIC_EVENT.fullmatch(subject) or fields==["公开资料"]
    return (bool(known) and type(args["year"]) is int
            and 2000 <= args["year"] <= 2099 and isinstance(fields,list) and 1 <= len(fields) <= len(FIELDS)
            and all(isinstance(f,str) and (f in FIELDS or f=="公开资料") for f in fields) and len(set(fields))==len(fields))


def describe(args):
    return f"{args['year']} 年{args['subject']}的" + "和".join(args["fields"])


def latest_scheduled_round(rows, today, year):
    dates = []
    for row in rows:
        for match in re.finditer(r"ROUND\s*\d{1,2}\s*\n+([A-Za-zÀ-ž .-]{2,36})\s*\n+.{0,130}?\n+\s*"
                r"\d{1,2}(?:\s+[A-Z][a-z]{2})?\s*[-–]\s*(\d{1,2}\s+[A-Z][a-z]{2})",row["content"],re.S):
            try:
                end = datetime.strptime(f"{match[2]} {year}","%d %b %Y").date()
            except ValueError:
                continue
            if end <= today:
                dates.append((end,match[1].strip()))
    return max(dates)[1] if dates else ""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url,code,"Redirect refused",headers,fp)


def search(args):
    if not valid(args):
        return {"ok":False,"kind":"scope"}
    key = os.getenv("TAVILY_API_KEY","").strip()
    if not key:
        return {"ok":False,"kind":"credentials"}
    subject, year = args["subject"], args["year"]
    now = date.today()
    today = now.isoformat()
    evidence = []
    failures = []
    # Separate necessary fields may need different source documents. No retries.
    for field in args["fields"]:
        query = f"{year} {subject} {field} 截至 {today}"
        domains = []
        if subject == "F1":
            domains = ["formula1.com","fia.com"]
            query = (f"{year} F1 race calendar latest finished Grand Prix result next race {now:%B %d %Y}" if field == "赛程"
                     else f"F1 drivers championship standings points after {latest_scheduled_round(evidence,now,year)} Grand Prix {now:%B %d} {year}")
        elif subject.startswith("诺贝尔"):
            domains = ["nobelprize.org"]
            query = f"{year} {subject} {field} Nobel Prize laureates prize motivation"
        body = {"query":query,"search_depth":"advanced","max_results":5,"include_answer":False}
        if domains:
            body["include_domains"] = domains
        if year==now.year and subject=="F1" and field=="积分榜":
            body.update(start_date=(now-timedelta(days=16)).isoformat(),end_date=today)
            domains = ["fia.com","formula1.com","autosport.com","motorsport.com"]
            body["include_domains"] = domains
        req = urllib.request.Request(ENDPOINT,data=json.dumps(body).encode(),headers={
            "Authorization":"Bearer "+key,"Content-Type":"application/json"},method="POST")
        try:
            with urllib.request.build_opener(_NoRedirect()).open(req,timeout=15) as res:
                payload = json.loads(res.read(2_000_000))
            for row in payload["results"]:
                url, content = str(row.get("url","")), str(row.get("content","")).strip()
                url_parts = urllib.parse.urlsplit(url)
                if url_parts.scheme not in {"https","http"} or not url_parts.hostname or not content:
                    continue
                if domains and not any(url_parts.hostname==d or url_parts.hostname.endswith("."+d) for d in domains):
                    continue
                if subject=="F1" and re.search(r"sim.racing|penalty.points|fantasy|f1.academy",url+" "+str(row.get("title","")),re.I):
                    continue
                if any(s["field"]==field and s["content"][:500]==content[:500] for s in evidence):
                    continue
                evidence.append({"field":field,"title":str(row.get("title",""))[:180],"url":url,"content":content[:2600]})
        except urllib.error.HTTPError as exc:
            failures.append("credentials" if exc.code in {401,403} else "service")
            if exc.code in {401,403,429}:
                break
        except (TimeoutError,socket.timeout):
            failures.append("timeout")
        except urllib.error.URLError as exc:
            failures.append("timeout" if isinstance(exc.reason,TimeoutError) else "service")
        except (OSError,ValueError,KeyError,TypeError):
            failures.append("service")
    return {"ok":bool(evidence),"sources":evidence,"as_of":today,"failures":failures,
            "kind":failures[0] if failures else "results" if evidence else "empty"}


def failure(kind):
    return {"credentials":"公开查询服务的密钥尚未配置或已失效，我现在查不到这项资料。",
            "timeout":"这次公开查询超时了，我还没能核实结果。",
            "empty":"我没有查到能核实这项问题的公开资料。",
            "scope":"这次查询的范围已改变，请重新指定要查的公开信息。"}.get(kind,"公开查询服务暂时不可用，我还没能核实结果。")


def source_name(url):
    domain = (urllib.parse.urlsplit(url).hostname or "").removeprefix("www.")
    return {"formula1.com":"F1 官网","fia.com":"国际汽联","nobelprize.org":"诺贝尔奖官网",
            "motorsport.com":"赛车运动网","autosport.com":"Autosport"}.get(domain,domain)
