import json
import re
from collections import Counter
from pathlib import Path

from extract_characters import clip_event, read_chapters


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CHARACTER_DATA = DATA_DIR / "三国演义人物数据.json"
LOCATION_DATA = DATA_DIR / "三国演义地点数据.json"
OUT_JSON = DATA_DIR / "三国演义官职数据.json"
OUT_HTML = ROOT / "三国演义官职可视化.html"
REFERENCE_URL = "https://zh.wikipedia.org/zh-hans/三国官制"
SENTENCE_RE = re.compile(r"[^。！？；\n]+[。！？；]?")

# Titles are retained only when they occur in the local novel text. Nobility,
# kinship, honorifics and forms of address are deliberately excluded.
CENTRAL_OFFICES = """
丞相 相国 太师 太傅 太保 大司马 太尉 司徒 司空 御史大夫 御史中丞 御史
尚书令 尚书仆射 尚书 尚书郎 录尚书事 侍中 散骑常侍 常侍 中常侍 给事中
中书令 中书监 中书侍郎 黄门侍郎 门下侍郎 工部侍郎 侍郎 黄门郎 郎中
治书侍御史 侍御史
议郎 谏议大夫 博士 议曹
太常 光禄勋 卫尉 太仆 廷尉 大鸿胪 宗正 大司农 司农 少府 执金吾
将作大匠 太史令 太史令丞 太医令 太医 太仓令 符节令 典客 羽林监
太子太傅 太子少傅 太子舍人 太子洗马 太子中庶子 太子文学 太史 鼓吏
枢密使 枢密院使 户部尚书 工部尚书 兵部尚书 礼部尚书 吏部尚书
""".split()

LOCAL_OFFICES = """
州牧 刺史 太守 京兆尹 河南尹 县令 县尉 县丞 县长 邑宰 令尹 督邮
别驾 别驾从事 治中 从事 军中从事 东郡从事 从事中郎 主簿 主记 长史
散骑长史 左将军长史 昭府下长史 功曹 郡丞 典农中郎将 典农校尉
丞相府主簿 丞相门下掌库主簿 刘璋府下主簿
盐铁官 市令 里正 啬夫
""".split()

MILITARY_OFFICES = """
将军 大将军 骠骑大将军 车骑大将军 卫大将军 中军大将军 征西大将军 征南大将军
征东大将军 征北大将军 镇东大将军 镇西大将军 镇南大将军 镇北大将军
辅国大将军 上军大将军 抚军大将军 骠骑将军 车骑将军 左车骑将军
右车骑将军 卫将军
前将军 后将军 左将军 右将军 中将军 上将军 偏将军 裨将军 副将军
征东将军 征西将军 征南将军 征北将军 镇东将军 镇西将军 镇南将军 镇北将军
安东将军 安西将军 安南将军 安北将军 平东将军 平西将军 平南将军 平北将军
辅国将军 辅汉将军 建威将军 建武将军 建德将军 扬威将军 扬武将军 扬烈将军
奋威将军 奋武将军 武卫将军 虎威将军 伏波将军 讨逆将军 讨虏将军
荡寇将军 征虏将军 殄寇将军 殄虏将军 折冲将军 破虏将军 镇远将军 靖北将军
神威天将军 天公将军 地公将军 人公将军 白马将军 杂号将军 横江将军
横野将军 牙门将军 龙骧将军 广武将军 冠军将军 威远将军 绥军将军
安汉将军 护卫将军 昭信将军 建忠将军 完体将军 武威将军 抚彝将军
大都督 都督 副都督 左都督 右都督 水军都督 水军副都督 平西都督
征西大都督 征西副都督 天下兵马大都督 都元帅 副都元帅 元帅
中军师 军师 副军师 军师祭酒 司马祭酒 参军 行军司马 军司马
别部司马 点军司马 典军司马 营中司马 都军司马 领军 护军 中护军
左护军 右护军 监军 先锋 副先锋 副将 牙将 统军 管军 典军 督军
都尉 骑都尉 驸马都尉 奉车都尉 破贼都尉 中郎将 虎贲中郎将 司金中郎将
镇南中郎将 掌军中郎将 副军师中郎将 军师中郎将 武略中郎将
抚军中郎将 镇威中郎将 发丘中郎将 从事中郎将 帐下中郎将 昭武中郎将
校尉 司隶校尉 典军校尉 骁骑校尉 折冲校尉 怀义校尉 赞军校尉
军前校尉 从征校尉 长水校尉 殿中校尉 城门校尉 后军校尉 中军校尉
越骑校尉 东羌校尉 帐前校尉 行军校尉 正议校尉 平虏校尉 摸金校尉
左军校尉 右军校尉 护军校尉 管军校尉 统兵校尉 羽林中郎将 五官中郎将
帐前都尉 领军都尉 奉军都尉 会稽都尉 平北都尉 承烈都尉 武卫都尉
绥戎都尉 泰山都尉 房陵都尉 九江都尉
""".split()

PALACE_OFFICES = """
中涓 黄门 内侍 内官 内监 太监 羽林郎 谒者 门下督 门下掾 典仪
""".split()

SPECIFIC_LOCAL_OFFICES = """
九江太守 零陵太守 上党太守 安定太守 建平太守 高陵太守 琅琊太守
安平太守 新兴太守 扶风太守 越嶲太守 洛阳令 许都令 平原令 冀城令
上邽令 洛阳北部尉
""".split()

OFFICE_ALIASES = {
    "丞相": ["丞相", "汉丞相", "汉相", "蜀相", "晋丞相"],
    "点军司马": ["点军司马", "典军司马"],
    "县令": ["县令", "县宰"],
    "州牧": ["州牧", "牧守"],
    "太史": ["官居太史"],
    "太常": ["太常", "太常卿"],
    "常侍": ["常侍", "黄门常侍"],
}

MILITARY_MARKERS = (
    "将军",
    "都督",
    "元帅",
    "军师",
    "司马",
    "校尉",
    "中郎将",
    "都尉",
    "护军",
    "领军",
    "监军",
    "先锋",
    "副将",
    "牙将",
    "统军",
    "管军",
    "典军",
    "督军",
    "参军",
)


def office_type(name):
    if name in PALACE_OFFICES:
        return "宫廷侍从"
    if name in {"丞相", "相国", "太师", "太傅", "太保", "大司马", "太尉", "司徒", "司空"}:
        return "中枢宰辅"
    if name in CENTRAL_OFFICES:
        return "中央文官"
    if any(marker in name for marker in MILITARY_MARKERS):
        return "军事职任"
    if name in LOCAL_OFFICES or name in SPECIFIC_LOCAL_OFFICES or name.endswith(
        ("州牧", "刺史", "太守", "县令", "县尉")
    ):
        return "地方行政"
    return "中央文官"


def discover_offices(corpus, location_data):
    candidates = set(
        CENTRAL_OFFICES
        + LOCAL_OFFICES
        + MILITARY_OFFICES
        + PALACE_OFFICES
        + SPECIFIC_LOCAL_OFFICES
    )
    candidates = {title for title in candidates if title in corpus}
    aliases_by_name = {title: [title] for title in candidates}
    for item in location_data["locations"]:
        if not 1 < len(item["name"]) <= 5:
            continue
        for suffix in ("州牧", "刺史", "太守", "县令", "县尉"):
            variants = [
                alias + suffix
                for alias in item["aliases"]
                if 1 < len(alias) <= 5 and alias + suffix in corpus
            ]
            if variants:
                canonical = item["name"]
                if canonical.endswith("县") and suffix.startswith("县"):
                    canonical += suffix[1:]
                else:
                    canonical += suffix
                aliases_by_name[canonical] = variants

    for canonical, variants in OFFICE_ALIASES.items():
        present = [variant for variant in variants if variant in corpus]
        if not present:
            continue
        aliases_by_name[canonical] = present
        for variant in variants:
            if variant != canonical:
                aliases_by_name.pop(variant, None)

    alias_to_canonical = {}
    for canonical, aliases in aliases_by_name.items():
        for alias in aliases:
            owner = alias_to_canonical.get(alias)
            if owner and owner != canonical:
                raise RuntimeError(f"Office alias collision: {alias}: {owner}/{canonical}")
            alias_to_canonical[alias] = canonical
    return aliases_by_name, alias_to_canonical


def make_pattern(alias_to_canonical):
    return re.compile(
        "|".join(
            re.escape(alias)
            for alias in sorted(alias_to_canonical, key=lambda value: (-len(value), value))
        )
    )


def extract_offices(chapters, aliases_by_name, alias_to_canonical):
    pattern = make_pattern(alias_to_canonical)
    records = {
        name: {
            "name": name,
            "aliases": sorted(set(aliases), key=lambda value: (-len(value), value)),
            "type": office_type(name),
            "mention_count": 0,
            "event_count": 0,
            "chapter_mentions": Counter(),
            "first_appearance": None,
            "last_appearance": None,
            "events": [],
        }
        for name, aliases in aliases_by_name.items()
    }
    absolute_offset = 0
    for chapter in chapters:
        paragraphs = [
            paragraph.strip()
            for paragraph in chapter["text"].split("\n")
            if paragraph.strip()
        ]
        chapter_offset = 0
        for paragraph_number, paragraph in enumerate(paragraphs, 1):
            for sentence_match in SENTENCE_RE.finditer(paragraph):
                sentence = sentence_match.group(0).strip()
                mentions = {}
                for match in pattern.finditer(sentence):
                    name = alias_to_canonical[match.group(0)]
                    mentions.setdefault(name, []).append(match)
                for name, matches in mentions.items():
                    record = records[name]
                    count = len(matches)
                    position = (
                        absolute_offset
                        + chapter_offset
                        + sentence_match.start()
                        + matches[0].start()
                    )
                    event = {
                        "chapter": chapter["number"],
                        "chapter_title": chapter["title"],
                        "paragraph": paragraph_number,
                        "position": position,
                        "alias": matches[0].group(0),
                        "mentions": count,
                        "text": clip_event(
                            paragraph,
                            sentence_match.start() + matches[0].start(),
                            sentence_match.start() + matches[-1].end(),
                        ),
                    }
                    record["mention_count"] += count
                    record["chapter_mentions"][str(chapter["number"])] += count
                    record["events"].append(event)
                    if record["first_appearance"] is None:
                        record["first_appearance"] = event
                    record["last_appearance"] = event
            chapter_offset += len(paragraph) + 1
        absolute_offset += len(chapter["text"]) + 1

    offices = []
    for record in records.values():
        if not record["events"]:
            continue
        record["chapter_mentions"] = dict(
            sorted(record["chapter_mentions"].items(), key=lambda item: int(item[0]))
        )
        record["event_count"] = len(record["events"])
        offices.append(record)
    offices.sort(
        key=lambda item: (
            -item["mention_count"],
            item["first_appearance"]["position"],
            item["name"],
        )
    )
    return offices


def build_payload(chapters, offices):
    types = Counter(item["type"] for item in offices)
    return {
        "meta": {
            "title": "三国演义官职志",
            "chapter_count": len(chapters),
            "office_count": len(offices),
            "mention_count": sum(item["mention_count"] for item in offices),
            "event_count": sum(item["event_count"] for item in offices),
            "sort": "出现次数倒序",
            "counting_rule": "按正文中正式官职、军职及明确异称的实际出现次数统计；爵位、亲属身份和一般尊称不计。",
            "event_rule": "包含该官职的一句话为一个事件，并补充所在段落的前后文。",
            "source": "src/ 下 120 回正文",
            "reference_source": REFERENCE_URL,
        },
        "chapters": [
            {"number": item["number"], "title": item["title"]} for item in chapters
        ],
        "stats": {"types": dict(types)},
        "offices": offices,
    }


def render_html(payload, character_data, location_data):
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    people = json.dumps(
        [{"name": item["name"], "aliases": item["aliases"]} for item in character_data["characters"]],
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    places = json.dumps(
        [{"name": item["name"], "aliases": item["aliases"]} for item in location_data["locations"]],
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    template = r"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>三国演义官职志 · 全官职可视化</title>
<style>
:root{--paper:#f1ece2;--ink:#29231d;--muted:#786d60;--blue:#344f69;--red:#9e2f24;--gold:#a97829;--green:#47644d;--line:#d4c7b5;--panel:#fcf8ef;--dark:#202b36}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;color:var(--ink);background:var(--paper);font-family:"Microsoft YaHei","Noto Serif SC",serif}body:before{content:"";position:fixed;inset:0;pointer-events:none;opacity:.2;background-image:radial-gradient(#715c43 .5px,transparent .7px);background-size:7px 7px}
button,input,select{font:inherit}.hero{position:relative;overflow:hidden;padding:54px clamp(20px,6vw,88px) 42px;color:#f5efe6;background:linear-gradient(120deg,#182532,#304b62 58%,#59452c)}.hero:after{content:"职官";position:absolute;right:3vw;top:-48px;font:900 min(22vw,250px)/1 serif;color:#fff;opacity:.04}.kicker{letter-spacing:.35em;color:#e0be7c;font-size:13px}.hero h1{font-size:clamp(38px,6vw,76px);margin:10px 0 8px;letter-spacing:.08em;font-family:STKaiti,KaiTi,serif}.hero p{max-width:820px;color:#d8dfe3;line-height:1.8;margin:0}.nav-link{display:inline-block;margin:14px 15px 0 0;color:#ebcd91;text-decoration:none;border-bottom:1px dashed #ebcd91}
.stats{display:flex;gap:1px;margin-top:25px;max-width:850px;background:#ffffff24;border:1px solid #ffffff24}.stat{flex:1;padding:16px 18px;background:#10191466}.stat b{display:block;font-size:27px;color:#f0d49f}.stat span{font-size:12px;color:#d3d9dc}.layout{display:grid;grid-template-columns:minmax(320px,460px) 1fr;min-height:calc(100vh - 260px)}.sidebar{border-right:1px solid var(--line);background:#e7dfd1cc}.controls{position:sticky;top:0;z-index:4;padding:16px;background:#e7dfd1f5;border-bottom:1px solid var(--line);backdrop-filter:blur(10px)}.search{width:100%;padding:11px 13px;border:1px solid #ad9e8a;background:#fffaf1;border-radius:3px;outline:none}.search:focus{border-color:var(--blue);box-shadow:0 0 0 2px #344f6918}.control-row{display:flex;gap:8px;margin-top:9px}.control-row select{min-width:0;flex:1;padding:8px;border:1px solid #b5a792;background:#f8f1e6;color:var(--ink)}.result-note{margin-top:9px;font-size:12px;color:var(--muted)}.offices{height:calc(100vh - 125px);overflow:auto;padding:8px 10px 32px}.office{width:100%;display:grid;grid-template-columns:46px 1fr auto;gap:10px;align-items:center;text-align:left;border:0;border-bottom:1px solid #d5c9b8;background:transparent;padding:13px 9px;cursor:pointer;color:inherit}.office:hover,.office.active{background:#fffaf1}.office.active{box-shadow:inset 3px 0 var(--blue)}.rank{font:20px Georgia;color:#8f806c}.office-name{font-size:17px;font-weight:700}.office-meta{font-size:11px;color:var(--muted);margin-top:4px}.count{text-align:right;color:var(--blue);font-weight:700}.count small{display:block;color:var(--muted);font-weight:400}
.content{min-width:0;padding:clamp(20px,4vw,58px);background:#f7f1e7}.empty{height:60vh;display:grid;place-content:center;text-align:center;color:var(--muted)}.seal{width:76px;height:76px;border:3px double var(--blue);color:var(--blue);display:grid;place-items:center;margin:0 auto 20px;font:26px STKaiti;transform:rotate(-4deg)}.profile{display:none;max-width:1050px;margin:auto}.profile.visible{display:block}.profile-head{display:grid;grid-template-columns:1fr auto;gap:20px;padding-bottom:24px;border-bottom:2px solid var(--ink)}.profile h2{font:700 clamp(35px,5vw,58px) STKaiti,KaiTi,serif;margin:0}.aliases{color:var(--blue);margin-top:7px}.badges{display:flex;gap:7px;flex-wrap:wrap;margin-top:14px}.badge{padding:4px 8px;border:1px solid #9aa9b6;color:#526579;font-size:12px;background:#fbf7ef}.mention-big{text-align:right}.mention-big b{display:block;font:46px Georgia;color:var(--blue)}.mention-big span{font-size:12px;color:var(--muted)}.profile-grid{display:grid;grid-template-columns:1.25fr .75fr;gap:24px;margin:24px 0}.card{background:var(--panel);border:1px solid var(--line);padding:20px;box-shadow:0 8px 28px #453a290c}.card h3,.section-title{font-size:14px;letter-spacing:.18em;color:var(--blue);margin:0 0 13px}.bio{line-height:1.9;margin:0}.facts{display:grid;gap:10px}.fact{display:grid;grid-template-columns:72px 1fr;font-size:14px}.fact span:first-child{color:var(--muted)}
.chart-wrap{margin:24px 0}.chart-title{display:flex;justify-content:space-between;align-items:end}.chapter-chart{display:flex;align-items:end;gap:2px;height:140px;border-bottom:1px solid #8c8273;padding-top:15px}.bar{flex:1;min-width:2px;background:#b8ad9c;position:relative;transition:.2s;cursor:default}.bar.hit{background:var(--blue);cursor:pointer}.bar:hover{background:var(--gold)}.bar.selected{background:#1b2632;box-shadow:0 0 0 2px var(--gold)}.bar:after{content:attr(data-tip);display:none;position:absolute;bottom:100%;left:50%;transform:translateX(-50%);white-space:nowrap;background:#17212b;color:white;padding:5px 7px;font-size:11px;z-index:3}.bar:hover:after{display:block}
.event-tools{display:flex;align-items:center;justify-content:space-between;gap:12px;border-bottom:1px solid var(--line);padding-bottom:10px}.event-tools h3{margin:0;font-size:20px}.event-list{display:grid;gap:12px;margin-top:16px}.event{display:grid;grid-template-columns:88px 1fr;background:var(--panel);border:1px solid var(--line)}.event-pos{padding:15px 12px;background:#293847;color:#f4eee4;text-align:center}.event-pos b{display:block;font-size:17px}.event-pos small{opacity:.65}.event-body{padding:14px 17px;line-height:1.75}.event-title{font-size:12px;color:var(--blue);margin-bottom:4px}.event em{font-style:normal;background:#d6dddf;padding:0 2px}.office-link,.person-link,.place-link{display:inline;padding:0;border:0;background:transparent;color:inherit;cursor:pointer}.office-link{border-bottom:1px dashed var(--blue)}.person-link{border-bottom:1px dotted var(--red);color:#762f2b}.place-link{border-bottom:1px dotted var(--green);color:#385840}.office-link:hover,.person-link:hover,.place-link:hover{border-bottom-style:solid}.load-more{width:100%;margin-top:14px;padding:12px;border:1px solid #8d9ba6;background:transparent;color:var(--blue);cursor:pointer}.load-more:hover{background:var(--panel)}.inline-action{margin-left:8px;padding:3px 7px;border:1px solid var(--blue);background:transparent;color:var(--blue);cursor:pointer}.method{margin-top:34px;padding-top:18px;border-top:1px solid var(--line);font-size:12px;color:var(--muted);line-height:1.7}
@media(max-width:820px){.stats{display:grid;grid-template-columns:1fr 1fr}.layout{display:block}.sidebar{border-right:0}.controls{position:relative}.offices{height:46vh}.content{padding:28px 16px}.profile-grid{grid-template-columns:1fr}.profile-head{grid-template-columns:1fr}.mention-big{text-align:left}.event{grid-template-columns:72px 1fr}.hero{padding-top:38px}}
</style></head><body>
<header class="hero"><div class="kicker">一百二十回 · 职官全录</div><h1>三国演义官职志</h1><p>逐回检索原著中的中枢、文官、地方与军事职任。点击官职，查看详细档案、出现轨迹和按原著位置排列的全部事件。</p><a class="nav-link" href="./三国演义标注版电子书.html">阅读标注版电子书 →</a><a class="nav-link" href="./三国演义人物可视化.html">切换至人物志 →</a><a class="nav-link" href="./三国演义地点可视化.html">切换至地理志 →</a><div class="stats"><div class="stat"><b id="officeTotal"></b><span>种正文官职</span></div><div class="stat"><b id="mentionTotal"></b><span>次官职提及</span></div><div class="stat"><b id="eventTotal"></b><span>条原文事件</span></div><div class="stat"><b>120</b><span>回完整检索</span></div></div></header>
<main class="layout"><aside class="sidebar"><div class="controls"><input id="search" class="search" type="search" placeholder="搜索官职、异称或回目…" autocomplete="off"><div class="control-row"><select id="type"><option value="">全部类别</option></select><select id="sort"><option value="mentions-desc">出现次数最多（默认）</option><option value="mentions-asc">出现次数最少</option><option value="first-asc">首次出现最早</option><option value="first-desc">首次出现最晚</option></select></div><div id="resultNote" class="result-note"></div></div><div id="offices" class="offices"></div></aside>
<section class="content"><div id="empty" class="empty"><div><div class="seal">职官</div><p>从左侧选择一个官职<br>展开它的三国故事</p></div></div><article id="profile" class="profile"></article></section></main>
<script id="novel-data" type="application/json">__DATA__</script><script id="people-data" type="application/json">__PEOPLE__</script><script id="places-data" type="application/json">__PLACES__</script>
<script>
const data=JSON.parse(document.getElementById("novel-data").textContent),people=JSON.parse(document.getElementById("people-data").textContent),places=JSON.parse(document.getElementById("places-data").textContent);
const state={selected:null,selectedChapter:null,shown:100,filtered:[]};const $=id=>document.getElementById(id);const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));const num=n=>new Intl.NumberFormat("zh-CN").format(n);
const tokens=new Map();data.offices.forEach(o=>o.aliases.forEach(a=>tokens.set(a,{kind:"office",name:o.name})));people.forEach(p=>p.aliases.forEach(a=>{if(!tokens.has(a))tokens.set(a,{kind:"person",name:p.name})}));places.forEach(p=>p.aliases.forEach(a=>{if(!tokens.has(a))tokens.set(a,{kind:"place",name:p.name})}));
const tokenPattern=new RegExp([...tokens.keys()].sort((a,b)=>b.length-a.length||a.localeCompare(b)).map(s=>s.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")).join("|"),"g");
$("officeTotal").textContent=num(data.meta.office_count);$("mentionTotal").textContent=num(data.meta.mention_count);$("eventTotal").textContent=num(data.meta.event_count);Object.keys(data.stats.types).sort().forEach(t=>$("type").insertAdjacentHTML("beforeend",`<option>${esc(t)}</option>`));
function marked(text,current){let out="",last=0;for(const m of text.matchAll(tokenPattern)){out+=esc(text.slice(last,m.index));const token=m[0],owner=tokens.get(token);if(owner.kind==="office")out+=owner.name===current?`<em>${esc(token)}</em>`:`<button class="office-link" data-office="${esc(owner.name)}" title="查看${esc(owner.name)}官职档案">${esc(token)}</button>`;else if(owner.kind==="person")out+=`<a class="person-link" href="./三国演义人物可视化.html#${encodeURIComponent(owner.name)}" title="查看${esc(owner.name)}人物档案">${esc(token)}</a>`;else out+=`<a class="place-link" href="./三国演义地点可视化.html#${encodeURIComponent(owner.name)}" title="查看${esc(owner.name)}地点档案">${esc(token)}</a>`;last=m.index+token.length}return out+esc(text.slice(last))}
function applyFilters(){const q=$("search").value.trim().toLowerCase(),t=$("type").value,s=$("sort").value;state.filtered=data.offices.filter(o=>(!t||o.type===t)&&(!q||[o.name,...o.aliases,o.first_appearance.chapter_title].join(" ").toLowerCase().includes(q)));state.filtered.sort((a,b)=>s==="first-asc"?a.first_appearance.position-b.first_appearance.position:s==="first-desc"?b.first_appearance.position-a.first_appearance.position:s==="mentions-asc"?a.mention_count-b.mention_count||a.first_appearance.position-b.first_appearance.position:b.mention_count-a.mention_count||a.first_appearance.position-b.first_appearance.position);renderOffices()}
function renderOffices(){$("resultNote").textContent=`显示 ${state.filtered.length} / ${data.meta.office_count} 种 · 默认出现次数最多者在前`;$("offices").innerHTML=state.filtered.map((o,i)=>`<button class="office ${state.selected===o.name?"active":""}" data-name="${esc(o.name)}"><span class="rank">${String(i+1).padStart(2,"0")}</span><span><span class="office-name">${esc(o.name)}</span><span class="office-meta">第 ${o.first_appearance.chapter} 回 · ${esc(o.type)}</span></span><span class="count">${num(o.mention_count)}<small>次</small></span></button>`).join("")}
function renderChart(o){const counts=Array.from({length:120},(_,i)=>o.chapter_mentions[String(i+1)]||0),max=Math.max(...counts,1);return counts.map((v,i)=>`<div class="bar ${v?"hit":""} ${state.selectedChapter===i+1?"selected":""}" style="height:${v?Math.max(5,Math.sqrt(v/max)*100):1}%" data-chapter="${i+1}" data-tip="第 ${i+1} 回：${v} 次${v?" · 点击筛选":""}"></div>`).join("")}
function renderEvents(o){const all=state.selectedChapter?o.events.filter(e=>e.chapter===state.selectedChapter):o.events,events=all.slice(0,state.shown);$("eventList").innerHTML=events.map((e,i)=>`<div class="event"><div class="event-pos"><b>第 ${e.chapter} 回</b><small>段 ${e.paragraph}</small></div><div class="event-body"><div class="event-title">${esc(e.chapter_title)} · 事件 ${i+1}${e.mentions>1?` · 本句 ${e.mentions} 次`:""}</div>${marked(e.text,o.name)}</div></div>`).join("");$("eventSummary").innerHTML=state.selectedChapter?`第 ${state.selectedChapter} 回 · ${num(all.length)} 条 <button id="showAllEvents" class="inline-action">显示所有回数</button>`:`${num(o.event_count)} 条 · 已按原著位置排序`;const more=$("loadMore");more.hidden=state.shown>=all.length;more.textContent=`继续加载（余 ${all.length-state.shown} 条）`;const allButton=$("showAllEvents");if(allButton)allButton.onclick=()=>toggleChapter(o,state.selectedChapter)}
function toggleChapter(o,chapter){if(!o.chapter_mentions[String(chapter)])return;state.selectedChapter=state.selectedChapter===chapter?null:chapter;state.shown=100;$("chapterChart").innerHTML=renderChart(o);renderEvents(o)}
function jumpToOffice(name){$("search").value="";$("type").value="";applyFilters();selectOffice(name)}
function selectOffice(name){const o=data.offices.find(x=>x.name===name);if(!o)return;state.selected=name;state.selectedChapter=null;state.shown=100;renderOffices();$("empty").style.display="none";const aliases=o.aliases.filter(a=>a!==o.name);$("profile").className="profile visible";$("profile").innerHTML=`<div class="profile-head"><div><div class="kicker" style="color:var(--blue)">第 ${o.first_appearance.chapter} 回出现</div><h2>${esc(o.name)}</h2><div class="aliases">${aliases.length?"异称 / 异写："+esc(aliases.join(" / ")):"原著通用职名"}</div><div class="badges"><span class="badge">${esc(o.type)}</span><span class="badge">涉及 ${Object.keys(o.chapter_mentions).length} 回</span></div></div><div class="mention-big"><b>${num(o.mention_count)}</b><span>次出现 · ${num(o.event_count)} 条事件</span></div></div><div class="profile-grid"><section class="card"><h3>官职概览</h3><p class="bio">${esc(o.name)}是《三国演义》叙事中出现的${esc(o.type)}。首次见于第 ${o.first_appearance.chapter} 回“${esc(o.first_appearance.chapter_title)}”，末次见于第 ${o.last_appearance.chapter} 回。下方事件保留任命、履职、称谓及相关叙事上下文。</p></section><aside class="card"><h3>职官札记</h3><div class="facts"><div class="fact"><span>类别</span><b>${esc(o.type)}</b></div><div class="fact"><span>初出现</span><b>第 ${o.first_appearance.chapter} 回 · 第 ${o.first_appearance.paragraph} 段</b></div><div class="fact"><span>末出现</span><b>第 ${o.last_appearance.chapter} 回 · 第 ${o.last_appearance.paragraph} 段</b></div><div class="fact"><span>涉及回目</span><b>${Object.keys(o.chapter_mentions).length} 回</b></div></div></aside></div><section class="chart-wrap"><div class="chart-title"><h3 class="section-title">一百二十回官职轨迹</h3><small>点击蓝色柱筛选该回，再次点击恢复全部</small></div><div id="chapterChart" class="chapter-chart">${renderChart(o)}</div></section><section><div class="event-tools"><h3>全部事件</h3><span id="eventSummary">${num(o.event_count)} 条 · 已按原著位置排序</span></div><div id="eventList" class="event-list"></div><button id="loadMore" class="load-more"></button></section><div class="method">蓝色虚线为其他官职，红色点线为人物，绿色点线为地点；均可点击跳转。<br>计数口径：${esc(data.meta.counting_rule)} 事件口径：${esc(data.meta.event_rule)}</div>`;renderEvents(o);$("loadMore").onclick=()=>{state.shown+=100;renderEvents(o)};$("chapterChart").onclick=e=>{const bar=e.target.closest(".bar.hit");if(bar)toggleChapter(o,Number(bar.dataset.chapter))};$("eventList").onclick=e=>{const link=e.target.closest("[data-office]");if(link)jumpToOffice(link.dataset.office)};if(innerWidth<821)$("profile").scrollIntoView({behavior:"smooth",block:"start"})}
$("offices").addEventListener("click",e=>{const b=e.target.closest("[data-name]");if(b)selectOffice(b.dataset.name)});["search","type","sort"].forEach(id=>$(id).addEventListener(id==="search"?"input":"change",applyFilters));applyFilters();const requested=decodeURIComponent(location.hash.slice(1));if(data.offices.some(o=>o.name===requested))selectOffice(requested);
</script></body></html>"""
    return (
        template.replace("__DATA__", data)
        .replace("__PEOPLE__", people)
        .replace("__PLACES__", places)
    )


def main():
    chapters = read_chapters()
    character_data = json.loads(CHARACTER_DATA.read_text(encoding="utf-8"))
    location_data = json.loads(LOCATION_DATA.read_text(encoding="utf-8"))
    corpus = "\n".join(chapter["text"] for chapter in chapters)
    aliases_by_name, alias_to_canonical = discover_offices(corpus, location_data)
    offices = extract_offices(chapters, aliases_by_name, alias_to_canonical)
    payload = build_payload(chapters, offices)
    DATA_DIR.mkdir(exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    OUT_HTML.write_text(
        render_html(payload, character_data, location_data), encoding="utf-8"
    )
    print(
        f"Done: {len(chapters)} chapters, {len(offices)} offices, "
        f"{payload['meta']['mention_count']} mentions, "
        f"{payload['meta']['event_count']} events"
    )
    print("Office data and standalone HTML written successfully.")


if __name__ == "__main__":
    main()
