import html
import json
import re
from collections import Counter
from pathlib import Path

from extract_characters import read_chapters


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CHARACTER_DATA = DATA_DIR / "三国演义人物数据.json"
LOCATION_DATA = DATA_DIR / "三国演义地点数据.json"
OFFICE_DATA = DATA_DIR / "三国演义官职数据.json"
OUT_HTML = ROOT / "三国演义标注版电子书.html"

KIND_CONFIG = {
    "person": {
        "label": "人物",
        "collection": "characters",
        "detail_page": "三国演义人物可视化.html",
    },
    "place": {
        "label": "地点",
        "collection": "locations",
        "detail_page": "三国演义地点可视化.html",
    },
    "office": {
        "label": "官职",
        "collection": "offices",
        "detail_page": "三国演义官职可视化.html",
    },
}

TOKEN_DEFAULT_OVERRIDES = {
    "许昌": "place:许昌",
    "督邮": "office:督邮",
}


def load_data():
    return {
        "person": json.loads(CHARACTER_DATA.read_text(encoding="utf-8")),
        "place": json.loads(LOCATION_DATA.read_text(encoding="utf-8")),
        "office": json.loads(OFFICE_DATA.read_text(encoding="utf-8")),
    }


def build_entity_index(data):
    entities = {}
    token_owner = {}
    priorities = {"person": 3, "place": 2, "office": 1}
    collisions = Counter()

    for kind, payload in data.items():
        config = KIND_CONFIG[kind]
        for item in payload[config["collection"]]:
            key = f"{kind}:{item['name']}"
            first = item["first_appearance"]
            profile = {
                "key": key,
                "kind": kind,
                "kind_label": config["label"],
                "name": item["name"],
                "aliases": item["aliases"],
                "mention_count": item["mention_count"],
                "event_count": item["event_count"],
                "chapter_count": len(item["chapter_mentions"]),
                "first_chapter": first["chapter"],
                "first_title": first["chapter_title"],
                "first_text": first["text"],
                "detail_url": f"./{config['detail_page']}#{item['name']}",
            }
            if kind == "person":
                profile.update(
                    {
                        "category": item["faction"],
                        "courtesy_name": item["courtesy_name"],
                        "birthplace": item["birthplace"],
                        "biography": item["biography"],
                        "historical": item["historical"],
                        "titles": item["titles_in_text"],
                    }
                )
            else:
                profile["category"] = item["type"]
            entities[key] = profile

            for token in item["aliases"]:
                if len(token) < 2 or not token.strip():
                    continue
                previous = token_owner.get(token)
                if previous:
                    collisions[token] += 1
                    previous_kind = previous.split(":", 1)[0]
                    if priorities[kind] <= priorities[previous_kind]:
                        continue
                token_owner[token] = key

    pattern = re.compile(
        "|".join(
            re.escape(token)
            for token in sorted(token_owner, key=lambda value: (-len(value), value))
        )
    )
    for token, key in TOKEN_DEFAULT_OVERRIDES.items():
        if token in token_owner and key in entities:
            token_owner[token] = key
    return entities, token_owner, pattern, collisions


def annotate_paragraph(text, token_owner, pattern, counts):
    parts = []
    cursor = 0
    for match in pattern.finditer(text):
        parts.append(html.escape(text[cursor : match.start()]))
        token = match.group(0)
        key = token_owner[token]
        if token == "许昌" and text[max(0, match.start() - 1) : match.start()] == "斩":
            key = "person:许昌"
        kind = key.split(":", 1)[0]
        counts[kind] += 1
        parts.append(
            f'<button class="entity entity-{kind}" data-entity="{html.escape(key, quote=True)}" '
            f'title="查看{KIND_CONFIG[kind]["label"]}：{html.escape(key.split(":", 1)[1], quote=True)}">'
            f"{html.escape(token)}</button>"
        )
        cursor = match.end()
    parts.append(html.escape(text[cursor:]))
    return "".join(parts)


def render_chapters(chapters, token_owner, pattern):
    counts = Counter()
    rendered = []
    chapter_stats = {}
    for chapter in chapters:
        paragraphs = [
            paragraph.strip()
            for paragraph in chapter["text"].split("\n")
            if paragraph.strip()
        ]
        before = counts.copy()
        body = "".join(
            f'<p id="chapter-{chapter["number"]}-p-{index}">'
            f"{annotate_paragraph(paragraph, token_owner, pattern, counts)}</p>"
            for index, paragraph in enumerate(paragraphs, 1)
        )
        chapter_stats[str(chapter["number"])] = {
            kind: counts[kind] - before[kind] for kind in KIND_CONFIG
        }
        rendered.append(
            f'<section class="chapter" id="chapter-{chapter["number"]}" '
            f'data-chapter="{chapter["number"]}" data-title="{html.escape(chapter["title"], quote=True)}">'
            f'<div class="chapter-no">第 {chapter["number"]} 回</div>'
            f"<h2>{html.escape(chapter['title'])}</h2>{body}</section>"
        )
    return "".join(rendered), dict(counts), chapter_stats


def compact_entities(entities):
    return json.dumps(entities, ensure_ascii=False, separators=(",", ":")).replace(
        "</", "<\\/"
    )


def render_html(chapters, entities, chapter_html, annotation_counts, chapter_stats):
    entity_data = compact_entities(entities)
    chapter_data = json.dumps(
        [
            {"number": chapter["number"], "title": chapter["title"]}
            for chapter in chapters
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    stats_data = json.dumps(chapter_stats, separators=(",", ":"))
    toc = "".join(
        f'<button class="toc-item" data-go="{chapter["number"]}">'
        f'<b>{chapter["number"]:03}</b><span>{html.escape(chapter["title"])}</span></button>'
        for chapter in chapters
    )
    template = r"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>三国演义 · 人物地名官职标注版电子书</title>
<style>
:root{--paper:#f5efe3;--paper2:#fffaf0;--ink:#2d261f;--muted:#827568;--line:#d7c9b5;--red:#9c342d;--green:#3d704f;--blue:#315f87;--gold:#a77a32;--shadow:#3a2b1b1c;--font-size:19px;--content-width:820px}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:70px}body{margin:0;color:var(--ink);background:var(--paper);font-family:"Microsoft YaHei","Noto Serif SC",serif}button,input,select{font:inherit}button{color:inherit}.topbar{position:fixed;z-index:20;inset:0 0 auto 0;height:58px;display:flex;align-items:center;gap:12px;padding:0 18px;color:#f5ede1;background:#252f35;box-shadow:0 2px 14px #0004}.brand{font:700 21px STKaiti,KaiTi,serif;letter-spacing:.08em;white-space:nowrap}.current{min-width:0;flex:1;color:#d4d9da;font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.toolbar{display:flex;align-items:center;gap:7px}.tool{border:1px solid #ffffff3d;background:#ffffff0c;color:#f3eadc;border-radius:3px;padding:6px 9px;cursor:pointer}.tool:hover{background:#ffffff1e}.progress{position:absolute;left:0;bottom:0;height:3px;background:var(--gold);width:0}
.toc-panel{position:fixed;z-index:18;left:0;top:58px;bottom:0;width:340px;transform:translateX(-102%);transition:.25s;background:#eee4d4;border-right:1px solid var(--line);box-shadow:8px 0 30px #0002;display:flex;flex-direction:column}.toc-panel.open{transform:none}.panel-head{padding:17px;border-bottom:1px solid var(--line)}.panel-head h2{font:700 26px STKaiti,KaiTi,serif;margin:0 0 10px}.search{width:100%;padding:10px 11px;border:1px solid #b6a58e;background:#fffaf2;outline:none}.search:focus{border-color:var(--gold)}.legend{display:flex;gap:12px;flex-wrap:wrap;margin-top:11px;font-size:12px;color:var(--muted)}.legend i{width:9px;height:9px;display:inline-block;margin-right:4px;border-radius:50%}.toc{overflow:auto;padding:8px 10px 30px}.toc-item{width:100%;display:grid;grid-template-columns:40px 1fr;gap:8px;text-align:left;padding:10px 7px;border:0;border-bottom:1px solid #d9cdbc;background:transparent;cursor:pointer}.toc-item:hover,.toc-item.active{background:#fff9ee}.toc-item.active{box-shadow:inset 3px 0 var(--gold)}.toc-item b{font:14px Georgia;color:var(--gold)}.toc-item span{font-size:13px;line-height:1.5}.search-results{display:none;overflow:auto;padding:8px 10px}.searching .toc{display:none}.searching .search-results{display:block}.search-result{width:100%;border:0;border-bottom:1px solid var(--line);background:transparent;text-align:left;padding:11px 8px;cursor:pointer}.search-result:hover{background:#fff9ee}.search-result b{display:block;color:var(--gold)}.search-result small{color:var(--muted)}
.book{max-width:var(--content-width);margin:0 auto;padding:90px 34px 120px}.cover{min-height:75vh;display:grid;place-content:center;text-align:center;border:1px solid var(--line);background:linear-gradient(145deg,#fffaf0,#ede1ce);box-shadow:0 18px 55px var(--shadow);position:relative}.cover:before,.cover:after{content:"";position:absolute;inset:14px;border:1px solid #bba57f}.cover:after{inset:20px;border-color:#bba57f66}.cover-kicker{letter-spacing:.45em;color:var(--red);font-size:13px}.cover h1{font:700 clamp(54px,10vw,92px) STKaiti,KaiTi,serif;letter-spacing:.13em;margin:22px 0 8px}.cover-sub{color:var(--muted);letter-spacing:.2em}.cover-stats{display:flex;justify-content:center;gap:28px;margin-top:36px}.cover-stats b{display:block;font:24px Georgia;color:var(--gold)}.cover-stats span{font-size:11px;color:var(--muted)}.cover-hint{margin-top:30px;font-size:12px;color:var(--muted)}
.chapter{padding:110px 0 30px;border-bottom:1px solid var(--line)}.chapter-no{text-align:center;color:var(--gold);font-size:13px;letter-spacing:.35em}.chapter h2{text-align:center;font:700 clamp(29px,5vw,42px)/1.45 STKaiti,KaiTi,serif;margin:14px 0 55px}.chapter p{font-size:var(--font-size);line-height:2.08;text-align:justify;text-indent:2em;margin:0 0 1.15em;letter-spacing:.035em}.entity{display:inline;padding:0 1px;border:0;background:transparent;cursor:pointer;text-indent:0;line-height:inherit}.entity-person{color:var(--red);border-bottom:1px dashed var(--red)}.entity-place{color:var(--green);border-bottom:1px dashed var(--green)}.entity-office{color:var(--blue);border-bottom:1px dashed var(--blue)}.entity:hover,.entity:focus{color:#fff;outline:0}.entity-person:hover,.entity-person:focus{background:var(--red)}.entity-place:hover,.entity-place:focus{background:var(--green)}.entity-office:hover,.entity-office:focus{background:var(--blue)}
.detail-panel{position:fixed;z-index:25;right:0;top:0;bottom:0;width:min(440px,94vw);transform:translateX(103%);transition:.25s;background:var(--paper2);box-shadow:-10px 0 35px #0003;overflow:auto}.detail-panel.open{transform:none}.detail-close{position:sticky;z-index:2;top:0;width:100%;text-align:right;padding:14px 17px;border:0;border-bottom:1px solid var(--line);background:#fffaf0eF;cursor:pointer}.detail-body{padding:12px 28px 40px}.kind{display:inline-block;padding:4px 8px;color:#fff;font-size:11px;letter-spacing:.12em}.kind-person{background:var(--red)}.kind-place{background:var(--green)}.kind-office{background:var(--blue)}.detail-body h2{font:700 45px STKaiti,KaiTi,serif;margin:13px 0 3px}.detail-aliases{color:var(--muted);line-height:1.7}.detail-stats{display:grid;grid-template-columns:repeat(3,1fr);margin:22px 0;border:1px solid var(--line)}.detail-stats div{padding:12px 7px;text-align:center;border-right:1px solid var(--line)}.detail-stats div:last-child{border:0}.detail-stats b{display:block;font:22px Georgia;color:var(--gold)}.detail-stats small{color:var(--muted)}.detail-section{margin-top:22px}.detail-section h3{font-size:12px;letter-spacing:.18em;color:var(--gold);border-bottom:1px solid var(--line);padding-bottom:8px}.detail-section p{line-height:1.8;font-size:14px}.facts{display:grid;gap:8px}.fact{display:grid;grid-template-columns:72px 1fr;font-size:13px}.fact span{color:var(--muted)}.full-link{display:block;margin-top:24px;padding:12px;text-align:center;text-decoration:none;color:#fff;background:#273947}.full-link:hover{background:#18252e}.scrim{display:none;position:fixed;z-index:17;inset:0;background:#0005}.scrim.open{display:block}
body.night{--paper:#1c2224;--paper2:#252c2e;--ink:#ddd5c7;--muted:#9f9a91;--line:#454b4a;--shadow:#0004}.night .cover{background:linear-gradient(145deg,#242c2e,#1c2224)}.night .search,.night .toc-item:hover,.night .toc-item.active,.night .search-result:hover{background:#2b3233}.night .toc-panel{background:#22292b}.night .detail-close{background:#252c2eef}.night .full-link{background:#496272}
@media(max-width:720px){.current{display:none}.brand{flex:1}.topbar{padding:0 9px}.tool-label{display:none}.book{padding:75px 17px 90px}.cover{min-height:70vh}.cover-stats{gap:15px}.chapter{padding-top:85px}.chapter h2{margin-bottom:38px}.chapter p{text-align:left}.toc-panel{width:min(340px,90vw)}}
@media print{.topbar,.toc-panel,.detail-panel,.scrim{display:none!important}.book{max-width:none;padding:0}.cover,.chapter{break-after:page;box-shadow:none}.entity{color:inherit;border:0}}
</style></head><body>
<header class="topbar"><button id="tocButton" class="tool" title="目录">☰ <span class="tool-label">目录</span></button><div class="brand">三国演义</div><div id="current" class="current">人物 · 地名 · 官职标注版</div><div class="toolbar"><button id="fontDown" class="tool" title="缩小字号">字−</button><button id="fontUp" class="tool" title="放大字号">字＋</button><button id="theme" class="tool" title="切换夜间模式">◐</button></div><div id="progress" class="progress"></div></header>
<aside id="tocPanel" class="toc-panel"><div class="panel-head"><h2>一百二十回</h2><input id="search" class="search" type="search" placeholder="搜索回目或正文…" autocomplete="off"><div class="legend"><span><i style="background:var(--red)"></i>人物</span><span><i style="background:var(--green)"></i>地点</span><span><i style="background:var(--blue)"></i>官职</span></div></div><div id="toc" class="toc">__TOC__</div><div id="searchResults" class="search-results"></div></aside>
<div id="scrim" class="scrim"></div><aside id="detailPanel" class="detail-panel"><button id="detailClose" class="detail-close">关闭 ×</button><div id="detailBody" class="detail-body"></div></aside>
<main class="book"><section class="cover"><div><div class="cover-kicker">全本 · 一百二十回</div><h1>三国演义</h1><div class="cover-sub">人物 · 地名 · 官职标注版</div><div class="cover-stats"><div><b>__PERSON_COUNT__</b><span>人物标记</span></div><div><b>__PLACE_COUNT__</b><span>地点标记</span></div><div><b>__OFFICE_COUNT__</b><span>官职标记</span></div></div><div class="cover-hint">点击彩色虚线词条，展开对应详细信息</div></div></section>__CHAPTERS__</main>
<script id="entity-data" type="application/json">__ENTITIES__</script><script id="chapter-data" type="application/json">__CHAPTER_DATA__</script><script id="chapter-stats" type="application/json">__CHAPTER_STATS__</script>
<script>
const entities=JSON.parse(document.getElementById("entity-data").textContent),chapters=JSON.parse(document.getElementById("chapter-data").textContent),chapterStats=JSON.parse(document.getElementById("chapter-stats").textContent);const $=id=>document.getElementById(id),esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])),num=n=>new Intl.NumberFormat("zh-CN").format(n);let fontSize=Number(localStorage.getItem("ebook-font")||19),currentChapter=1;
function setFont(value){fontSize=Math.max(15,Math.min(28,value));document.documentElement.style.setProperty("--font-size",fontSize+"px");localStorage.setItem("ebook-font",fontSize)}setFont(fontSize);if(localStorage.getItem("ebook-theme")==="night")document.body.classList.add("night");
function toggleToc(force){const open=force??!$("tocPanel").classList.contains("open");$("tocPanel").classList.toggle("open",open);$("scrim").classList.toggle("open",open)}
function closeDetail(){$("detailPanel").classList.remove("open")}
function openDetail(key){const e=entities[key];if(!e)return;const aliases=e.aliases.filter(a=>a!==e.name);const person=e.kind==="person";const facts=person?`<div class="fact"><span>阵营</span><b>${esc(e.category)}</b></div>${e.courtesy_name?`<div class="fact"><span>字</span><b>${esc(e.courtesy_name)}</b></div>`:""}${e.birthplace?`<div class="fact"><span>籍贯</span><b>${esc(e.birthplace)}</b></div>`:""}${e.titles?.length?`<div class="fact"><span>称号</span><b>${esc(e.titles.join(" / "))}</b></div>`:""}`:`<div class="fact"><span>类别</span><b>${esc(e.category)}</b></div>`;const description=person?(e.biography||e.historical||`${e.name}是《三国演义》中出现的人物。`):`${e.name}是《三国演义》中出现的${esc(e.category)}。`;$("detailBody").innerHTML=`<span class="kind kind-${e.kind}">${esc(e.kind_label)}</span><h2>${esc(e.name)}</h2><div class="detail-aliases">${aliases.length?esc(aliases.join(" / ")):"原著通用名称"}</div><div class="detail-stats"><div><b>${num(e.mention_count)}</b><small>次提及</small></div><div><b>${num(e.event_count)}</b><small>条事件</small></div><div><b>${e.chapter_count}</b><small>个回目</small></div></div><section class="detail-section"><h3>档案概览</h3><div class="facts">${facts}<div class="fact"><span>首次出现</span><b>第 ${e.first_chapter} 回</b></div></div><p>${esc(description)}</p></section><section class="detail-section"><h3>首次出现上下文</h3><p>${esc(e.first_text)}</p></section><a class="full-link" href="${esc(e.detail_url)}">打开完整${esc(e.kind_label)}档案 →</a>`;$("detailPanel").classList.add("open")}
function goChapter(number){const target=$("chapter-"+number);if(!target)return;toggleToc(false);target.scrollIntoView({behavior:"smooth",block:"start"});history.replaceState(null,"","#chapter-"+number)}
function updateCurrent(number){currentChapter=number;const c=chapters[number-1];$("current").textContent=`第 ${number} 回 · ${c.title}`;document.querySelectorAll(".toc-item").forEach(x=>x.classList.toggle("active",Number(x.dataset.go)===number))}
document.addEventListener("click",event=>{const entity=event.target.closest("[data-entity]");if(entity)openDetail(entity.dataset.entity);const go=event.target.closest("[data-go]");if(go)goChapter(Number(go.dataset.go))});
$("tocButton").onclick=()=>toggleToc();$("scrim").onclick=()=>toggleToc(false);$("detailClose").onclick=closeDetail;$("fontDown").onclick=()=>setFont(fontSize-1);$("fontUp").onclick=()=>setFont(fontSize+1);$("theme").onclick=()=>{document.body.classList.toggle("night");localStorage.setItem("ebook-theme",document.body.classList.contains("night")?"night":"day")};
const observer=new IntersectionObserver(entries=>{const visible=entries.filter(e=>e.isIntersecting).sort((a,b)=>Math.abs(a.boundingClientRect.top)-Math.abs(b.boundingClientRect.top))[0];if(visible)updateCurrent(Number(visible.target.dataset.chapter))},{rootMargin:"-10% 0px -75% 0px",threshold:0});document.querySelectorAll(".chapter").forEach(x=>observer.observe(x));
addEventListener("scroll",()=>{const max=document.documentElement.scrollHeight-innerHeight;$("progress").style.width=(max?scrollY/max*100:0)+"%"},{passive:true});
let searchTimer;$("search").addEventListener("input",event=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>{const q=event.target.value.trim().toLowerCase(),panel=$("tocPanel");panel.classList.toggle("searching",!!q);if(!q)return;const matches=[];document.querySelectorAll(".chapter").forEach(section=>{const title=section.dataset.title,text=section.innerText.toLowerCase(),count=text.split(q).length-1;if(title.toLowerCase().includes(q)||count)matches.push({number:Number(section.dataset.chapter),title,count})});$("searchResults").innerHTML=matches.length?matches.map(x=>`<button class="search-result" data-go="${x.number}"><b>第 ${x.number} 回</b><span>${esc(x.title)}</span><small>${x.count?` · 正文约 ${x.count} 处`:" · 回目命中"}</small></button>`).join(""):`<p style="padding:15px;color:var(--muted)">未找到“${esc(q)}”</p>`},180)});
const requested=Number((location.hash.match(/chapter-(\d+)/)||[])[1]);if(requested>=1&&requested<=120)setTimeout(()=>goChapter(requested),0);
</script></body></html>"""
    replacements = {
        "__TOC__": toc,
        "__CHAPTERS__": chapter_html,
        "__ENTITIES__": entity_data,
        "__CHAPTER_DATA__": chapter_data,
        "__CHAPTER_STATS__": stats_data,
        "__PERSON_COUNT__": f"{annotation_counts['person']:,}",
        "__PLACE_COUNT__": f"{annotation_counts['place']:,}",
        "__OFFICE_COUNT__": f"{annotation_counts['office']:,}",
    }
    for marker, value in replacements.items():
        template = template.replace(marker, value)
    return template


def main():
    chapters = read_chapters()
    data = load_data()
    entities, token_owner, pattern, collisions = build_entity_index(data)
    chapter_html, annotation_counts, chapter_stats = render_chapters(
        chapters, token_owner, pattern
    )
    output = render_html(
        chapters, entities, chapter_html, annotation_counts, chapter_stats
    )
    OUT_HTML.write_text(output, encoding="utf-8")
    print(
        f"Done: {len(chapters)} chapters, {len(entities)} profiles, "
        f"{sum(annotation_counts.values())} annotations "
        f"({annotation_counts['person']} people, {annotation_counts['place']} places, "
        f"{annotation_counts['office']} offices), {len(collisions)} alias collisions resolved"
    )
    print("Annotated standalone ebook written successfully.")


if __name__ == "__main__":
    main()
