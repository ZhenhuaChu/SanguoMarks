import json
import math
import re
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DATA_DIR = ROOT / "data"
REFERENCE_CACHE = DATA_DIR / "三国演义人物档案.json"
OUT_JSON = DATA_DIR / "三国演义人物数据.json"
OUT_HTML = ROOT / "三国演义人物可视化.html"
REFERENCE_URL = (
    "https://zh.wikisource.org/zh-hans/"
    "%E4%B8%89%E5%9C%8B%E6%BC%94%E7%BE%A9/%E9%99%84%E9%8C%844"
)

SENTENCE_RE = re.compile(r"[^。！？；\n]+[。！？；]?")
CHAPTER_RE = re.compile(r"^(\d+)\.")
HAN_RE = re.compile(r"^[\u3400-\u9fff]{1,12}$")

# The appendix occasionally joins a person's name and familiar title in one cell.
JOINED_LABELS = {
    "刘宏汉灵帝": ("刘宏", ["汉灵帝", "灵帝"]),
    "刘辩汉少帝": ("刘辩", ["汉少帝", "少帝"]),
    "刘协汉献帝": ("刘协", ["汉献帝", "献帝"]),
    "刘备汉先主": ("刘备", ["汉先主", "先主"]),
    "刘禅汉后主": ("刘禅", ["汉后主", "后主"]),
    "孙仁孙夫人": ("孙仁", ["孙夫人"]),
    "伏寿伏皇后": ("伏寿", ["伏皇后"]),
    "曹节曹贵人曹皇后": ("曹节", ["曹贵人", "曹皇后"]),
    "张星张皇后": ("张星", ["张皇后"]),
    "张彩张皇后": ("张彩", ["张皇后"]),
    "全惠解全皇后": ("全惠解", ["全皇后"]),
    "王异王氏": ("王异", ["王氏"]),
    "王荣王美人": ("王荣", ["王美人"]),
    "王元姬王氏": ("王元姬", ["王氏"]),
}

VARIANT_TRANSLATION = str.maketrans(
    {
        "鍾": "钟",
        "锺": "钟",
        "麋": "糜",
        "毌": "毋",
        "覈": "核",
        "彊": "强",
        "寗": "宁",
        "䜣": "欣",
        "祕": "秘",
    }
)

# Frequent names are often replaced entirely by a courtesy name, title, or nickname.
KNOWN_ALIASES = {
    "刘备": ["玄德", "刘玄德", "刘皇叔", "皇叔", "刘豫州", "使君"],
    "关羽": ["云长", "关云长", "关公", "关君侯", "美髯公", "汉寿亭侯"],
    "张飞": ["翼德", "张翼德"],
    "曹操": ["孟德", "曹孟德", "曹阿瞒", "阿瞒", "曹公", "魏王"],
    "诸葛亮": ["孔明", "诸葛孔明", "卧龙", "武侯", "武乡侯"],
    "司马懿": ["仲达", "司马仲达"],
    "姜维": ["伯约", "姜伯约"],
    "吕布": ["奉先", "吕奉先", "吕温侯"],
    "周瑜": ["公瑾", "周公瑾"],
    "赵云": ["子龙", "赵子龙"],
    "孙权": ["仲谋", "孙仲谋", "吴侯"],
    "鲁肃": ["子敬", "鲁子敬"],
    "庞统": ["士元", "庞士元", "凤雏"],
    "徐庶": ["元直", "徐元直", "单福"],
    "贾诩": ["文和", "贾文和"],
    "夏侯惇": ["元让", "夏侯元让"],
    "张辽": ["文远", "张文远"],
    "庞德": ["令明", "庞令明"],
    "孙策": ["伯符", "孙伯符", "小霸王"],
    "袁绍": ["本初", "袁本初"],
    "袁术": ["公路", "袁公路"],
    "刘表": ["景升", "刘景升"],
    "刘璋": ["季玉", "刘季玉"],
    "马超": ["孟起", "马孟起"],
    "黄忠": ["汉升", "黄汉升"],
    "陆逊": ["伯言", "陆伯言"],
    "曹丕": ["子桓", "曹子桓"],
    "曹植": ["子建", "曹子建"],
    "曹叡": ["曹睿", "魏明帝"],
    "郭嘉": ["奉孝", "郭奉孝"],
    "荀彧": ["文若", "荀文若"],
    "许褚": ["仲康", "许仲康", "虎痴"],
    "甘宁": ["兴霸", "甘兴霸"],
    "太史慈": ["子义", "太史子义"],
    "孙坚": ["文台", "孙文台"],
    "董卓": ["仲颖", "董仲颖", "董太师"],
    "貂蝉": ["貂蝉"],
    "司马徽": ["德操", "水镜先生"],
    # Common glyph/name variants in this repository's edition.
    "冷苞": ["泠苞"],
    "华核": ["华覈"],
    "田预": ["田豫"],
    "傅肜": ["傅彤"],
    "苏颙": ["苏顒"],
    "范强": ["范疆", "范彊"],
    "潘濬": ["潘浚"],
    "姜冏": ["姜囧"],
    "桥瑁": ["乔瑁"],
    "太史享": ["太史亨"],
    "郤虑": ["郗虑"],
    "霍弋": ["霍戈"],
}

AMBIGUOUS_ALIASES = {
    "主公",
    "丞相",
    "都督",
    "将军",
    "先生",
    "夫人",
    "太后",
    "皇后",
    "大王",
    "陛下",
    "天子",
    "先帝",
    "后主",
    "先主",
    "使君",
    "王氏",
    "张皇后",
}


class CharacterTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_row = False
        self.in_cell = False
        self.cell_parts = []
        self.row = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.in_row = True
            self.row = []
        elif tag in {"td", "th"} and self.in_row:
            self.in_cell = True
            self.cell_parts = []

    def handle_data(self, data):
        if self.in_cell:
            self.cell_parts.append(data)

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.in_cell:
            self.row.append(" ".join("".join(self.cell_parts).split()))
            self.in_cell = False
        elif tag == "tr" and self.in_row:
            if self.row:
                self.rows.append(self.row)
            self.in_row = False


def chapter_number(path):
    match = CHAPTER_RE.match(path.name)
    return int(match.group(1)) if match else 0


def read_chapters():
    chapters = []
    for path in sorted(SRC.glob("*.txt"), key=chapter_number):
        number = chapter_number(path)
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        _, _, body = text.partition("\n")
        title = re.sub(r"^\d+\.", "", path.stem).strip()
        chapters.append(
            {"number": number, "title": title, "text": body.strip(), "file": path.name}
        )
    if len(chapters) != 120:
        raise RuntimeError(f"Expected 120 chapters, found {len(chapters)}")
    return chapters


def normalized(value):
    return re.sub(r"\s+", "", value.translate(VARIANT_TRANSLATION)).strip()


def split_reference_label(label):
    label = normalized(label)
    if label in JOINED_LABELS:
        return JOINED_LABELS[label]
    primary = re.sub(r"（.*$", "", label)
    return primary, []


def download_reference():
    request = Request(
        REFERENCE_URL,
        headers={"User-Agent": "Romance-of-the-Three-Kingdoms-Visualizer/1.0"},
    )
    source = urlopen(request, timeout=30).read().decode("utf-8")
    parser = CharacterTableParser()
    parser.feed(source)

    profiles = {}
    for row in parser.rows:
        if len(row) < 6 or row[0] in {"姓名", ""}:
            continue
        primary, aliases = split_reference_label(row[0])
        if not primary or not HAN_RE.fullmatch(primary):
            continue
        courtesy = normalized(row[1])
        profile = profiles.setdefault(
            primary,
            {
                "name": primary,
                "courtesy_name": "",
                "birthplace": "",
                "biography": "",
                "reference_first_chapter": None,
                "historical": "",
                "aliases": [],
            },
        )
        if courtesy and HAN_RE.fullmatch(courtesy):
            profile["courtesy_name"] = courtesy
            aliases.append(courtesy)
        profile["birthplace"] = profile["birthplace"] or row[2].strip()
        profile["biography"] = profile["biography"] or row[3].strip()
        match = re.search(r"第(\d+)回", row[4])
        if match:
            profile["reference_first_chapter"] = int(match.group(1))
        profile["historical"] = profile["historical"] or row[5].strip()
        profile["aliases"].extend(aliases)

    result = list(profiles.values())
    for profile in result:
        profile["aliases"] = sorted(set(profile["aliases"]))
    DATA_DIR.mkdir(exist_ok=True)
    REFERENCE_CACHE.write_text(
        json.dumps(
            {
                "source": REFERENCE_URL,
                "license": "CC BY-SA 4.0",
                "characters": result,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return result


def load_reference():
    if REFERENCE_CACHE.exists():
        return json.loads(REFERENCE_CACHE.read_text(encoding="utf-8"))["characters"]
    return download_reference()


def local_aliases(profile, corpus):
    name = profile["name"]
    candidates = {name, *profile["aliases"], *KNOWN_ALIASES.get(name, [])}

    escaped = re.escape(name)
    patterns = [
        rf"{escaped}[，、]?\s*字([\u3400-\u9fff]{{1,4}}?)(?=[，。！？；：、\s]|者|也|乃|系|为)",
        rf"{escaped}[，、]?\s*号([\u3400-\u9fff]{{2,6}}?)(?=[，。！？；：、\s]|者|也|乃|系|为)",
    ]
    if len(name) in {2, 3}:
        surname_length = 2 if name[:2] in {
            "司马", "诸葛", "夏侯", "皇甫", "公孙", "太史", "毋丘", "令狐"
        } else 1
        surname = re.escape(name[:surname_length])
        given = re.escape(name[surname_length:])
        patterns.append(
            rf"姓{surname}[，、]?\s*名{given}[，、]?\s*字"
            rf"([\u3400-\u9fff]{{1,4}}?)(?=[，。！？；：、\s]|者|也|乃|系|为)"
        )
    for pattern in patterns:
        candidates.update(match.group(1) for match in re.finditer(pattern, corpus))

    aliases = []
    for alias in candidates:
        alias = normalized(alias)
        if (
            len(alias) >= 2
            and HAN_RE.fullmatch(alias)
            and alias not in AMBIGUOUS_ALIASES
            and alias in corpus
        ):
            aliases.append(alias)
    return sorted(set(aliases), key=lambda item: (-len(item), item))


def infer_faction(profile):
    text = profile["biography"] + profile["birthplace"]
    rules = [
        ("蜀汉", ("蜀汉", "刘备", "季汉")),
        ("曹魏", ("曹魏", "魏国", "魏将")),
        ("东吴", ("东吴", "孙吴", "吴国", "吴将")),
        ("西晋", ("西晋", "晋朝", "晋将", "晋国")),
        ("东汉", ("东汉", "汉室", "汉朝", "汉灵帝", "汉献帝")),
        ("群雄", ("袁绍", "袁术", "董卓", "吕布", "黄巾")),
    ]
    for faction, clues in rules:
        if any(clue in text for clue in clues):
            return faction
    return "其他"


def resolve_profiles(reference, corpus):
    candidates = []
    for profile in reference:
        profile = dict(profile)
        aliases = local_aliases(profile, corpus)
        if aliases:
            profile["aliases"] = aliases
            profile["faction"] = infer_faction(profile)
            candidates.append(profile)

    owners = defaultdict(set)
    for profile in candidates:
        for alias in profile["aliases"]:
            owners[alias].add(profile["name"])

    for profile in candidates:
        profile["aliases"] = [
            alias
            for alias in profile["aliases"]
            if len(owners[alias]) == 1 or alias == profile["name"]
        ]
    return [profile for profile in candidates if profile["aliases"]]


def make_alias_pattern(profiles):
    alias_to_name = {}
    for profile in profiles:
        for alias in profile["aliases"]:
            alias_to_name[alias] = profile["name"]
    alternatives = "|".join(
        re.escape(alias) for alias in sorted(alias_to_name, key=lambda x: (-len(x), x))
    )
    return re.compile(alternatives), alias_to_name


def clip_event(paragraph, start, end, radius=135):
    left = max(0, start - radius)
    right = min(len(paragraph), end + radius)
    prefix = "…" if left else ""
    suffix = "…" if right < len(paragraph) else ""
    return prefix + re.sub(r"\s+", "", paragraph[left:right]) + suffix


def extract_characters(chapters, profiles):
    alias_pattern, alias_to_name = make_alias_pattern(profiles)
    records = {
        profile["name"]: {
            **profile,
            "mention_count": 0,
            "first_appearance": None,
            "last_appearance": None,
            "chapter_mentions": Counter(),
            "events": [],
            "titles_in_text": set(),
        }
        for profile in profiles
    }
    absolute_offset = 0
    title_pattern = re.compile(
        r"(?:拜|封|升|迁|任|领|为)([\u3400-\u9fff]{0,8}?"
        r"(?:将军|丞相|都督|太守|刺史|军师|太尉|司徒|司空|尚书|侍中|校尉|侯|王))"
    )

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
                if not sentence:
                    continue
                mentions = defaultdict(list)
                for match in alias_pattern.finditer(sentence):
                    mentions[alias_to_name[match.group(0)]].append(match)
                for name, matches in mentions.items():
                    record = records[name]
                    count = len(matches)
                    position = (
                        absolute_offset
                        + chapter_offset
                        + sentence_match.start()
                        + matches[0].start()
                    )
                    appearance = {
                        "chapter": chapter["number"],
                        "chapter_title": chapter["title"],
                        "paragraph": paragraph_number,
                        "position": position,
                        "alias": matches[0].group(0),
                        "text": clip_event(
                            paragraph,
                            sentence_match.start() + matches[0].start(),
                            sentence_match.start() + matches[-1].end(),
                        ),
                        "mentions": count,
                    }
                    record["mention_count"] += count
                    record["chapter_mentions"][str(chapter["number"])] += count
                    record["events"].append(appearance)
                    if record["first_appearance"] is None:
                        record["first_appearance"] = appearance
                    record["last_appearance"] = appearance
                    nearby = sentence[
                        max(0, matches[0].start() - 16): matches[-1].end() + 24
                    ]
                    for title_match in title_pattern.finditer(nearby):
                        record["titles_in_text"].add(title_match.group(1))
            chapter_offset += len(paragraph) + 1
        absolute_offset += len(chapter["text"]) + 1

    characters = []
    for record in records.values():
        if not record["events"]:
            continue
        record["chapter_mentions"] = dict(
            sorted(record["chapter_mentions"].items(), key=lambda item: int(item[0]))
        )
        record["titles_in_text"] = sorted(record["titles_in_text"])
        record["event_count"] = len(record["events"])
        characters.append(record)

    characters.sort(
        key=lambda item: (
            -item["first_appearance"]["position"],
            -item["mention_count"],
            item["name"],
        )
    )
    return characters


def build_payload(chapters, characters):
    totals = Counter()
    first_appearances = Counter()
    factions = Counter()
    for character in characters:
        factions[character["faction"]] += 1
        first_appearances[str(character["first_appearance"]["chapter"])] += 1
        for chapter, count in character["chapter_mentions"].items():
            totals[chapter] += count
    return {
        "meta": {
            "title": "三国演义人物志",
            "chapter_count": len(chapters),
            "character_count": len(characters),
            "mention_count": sum(item["mention_count"] for item in characters),
            "event_count": sum(item["event_count"] for item in characters),
            "sort": "出现次数倒序",
            "counting_rule": "姓名、字、号及明确别称在正文中的实际出现次数；同一句多次出现会分别计数。",
            "event_rule": "包含该人物的一句话为一个事件，并补充所在段落的前后文；事件依回目、段落及句内位置升序排列。",
            "source": "src/ 下 120 回正文",
            "profile_source": REFERENCE_URL,
        },
        "chapters": [
            {"number": chapter["number"], "title": chapter["title"]}
            for chapter in chapters
        ],
        "stats": {
            "mentions_by_chapter": dict(totals),
            "first_appearances_by_chapter": dict(first_appearances),
            "factions": dict(factions),
        },
        "characters": characters,
    }


def render_html(payload):
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    template = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>三国演义人物志 · 全人物可视化</title>
<style>
:root{--paper:#f3ead8;--ink:#211b16;--muted:#786b5c;--red:#9e2f24;--gold:#bd8b3d;--line:#d8c9ac;--panel:#fffaf0;--dark:#18211d}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;color:var(--ink);background:var(--paper);font-family:"Microsoft YaHei","Noto Serif SC",serif}
body:before{content:"";position:fixed;inset:0;pointer-events:none;opacity:.3;background-image:radial-gradient(#7d6340 0.55px,transparent .7px);background-size:6px 6px}
button,input,select{font:inherit}.hero{position:relative;overflow:hidden;padding:54px clamp(20px,6vw,88px) 42px;color:#f7ecd8;background:linear-gradient(120deg,#17211d,#293228 58%,#55261f)}
.hero:after{content:"三國";position:absolute;right:5vw;top:-46px;font-size:min(28vw,320px);font-family:serif;font-weight:900;color:#fff;opacity:.035;line-height:1}
.kicker{letter-spacing:.35em;color:#d8b879;font-size:13px}.hero h1{font-size:clamp(38px,6vw,76px);margin:10px 0 8px;letter-spacing:.08em;font-family:STKaiti,KaiTi,serif}.hero p{max-width:760px;color:#d8d0c3;line-height:1.8;margin:0}.nav-link{display:inline-block;margin:14px 15px 0 0;color:#e8cf98;text-decoration:none;border-bottom:1px dashed #e8cf98}
.stats{display:flex;gap:1px;margin-top:30px;max-width:850px;background:#ffffff24;border:1px solid #ffffff24}.stat{flex:1;padding:16px 18px;background:#10191488}.stat b{display:block;font-size:27px;color:#f3d49b}.stat span{font-size:12px;color:#c9c1b4}
.layout{display:grid;grid-template-columns:minmax(320px,460px) 1fr;min-height:calc(100vh - 260px)}.sidebar{border-right:1px solid var(--line);background:#eee3cfcc}.controls{position:sticky;top:0;z-index:4;padding:16px;background:#eee3cff5;border-bottom:1px solid var(--line);backdrop-filter:blur(10px)}
.search{width:100%;padding:11px 13px;border:1px solid #bda98a;background:#fffaf0;border-radius:3px;outline:none}.search:focus{border-color:var(--red);box-shadow:0 0 0 2px #9e2f2418}
.control-row{display:flex;gap:8px;margin-top:9px}.control-row select{min-width:0;flex:1;padding:8px;border:1px solid #c8b79b;background:#f9f1e2;color:var(--ink)}
.result-note{margin-top:9px;font-size:12px;color:var(--muted)}.people{height:calc(100vh - 125px);overflow:auto;padding:8px 10px 32px}.person{width:100%;display:grid;grid-template-columns:46px 1fr auto;gap:10px;align-items:center;text-align:left;border:0;border-bottom:1px solid #dacbad;background:transparent;padding:13px 9px;cursor:pointer;color:inherit}
.person:hover,.person.active{background:#fff9ed}.person.active{box-shadow:inset 3px 0 var(--red)}.rank{font:20px Georgia;color:#9a876b}.person-name{font-size:17px;font-weight:700}.person-meta{font-size:11px;color:var(--muted);margin-top:4px}.count{text-align:right;color:var(--red);font-weight:700}.count small{display:block;color:var(--muted);font-weight:400}
.content{min-width:0;padding:clamp(20px,4vw,58px);background:#f7efdf}.empty{height:60vh;display:grid;place-content:center;text-align:center;color:var(--muted)}.seal{width:76px;height:76px;border:3px double var(--red);color:var(--red);display:grid;place-items:center;margin:0 auto 20px;font:30px STKaiti;transform:rotate(-4deg)}
.profile{display:none;max-width:1050px;margin:auto}.profile.visible{display:block}.profile-head{display:grid;grid-template-columns:1fr auto;gap:20px;padding-bottom:24px;border-bottom:2px solid var(--ink)}.profile h2{font:700 clamp(35px,5vw,58px) STKaiti,KaiTi,serif;margin:0}.aliases{color:var(--red);margin-top:7px}.badges{display:flex;gap:7px;flex-wrap:wrap;margin-top:14px}.badge{padding:4px 8px;border:1px solid #bca98b;color:#635543;font-size:12px;background:#fff8ea}
.mention-big{text-align:right}.mention-big b{display:block;font:46px Georgia;color:var(--red)}.mention-big span{font-size:12px;color:var(--muted)}.profile-grid{display:grid;grid-template-columns:1.25fr .75fr;gap:24px;margin:24px 0}.card{background:#fffaf1;border:1px solid var(--line);padding:20px;box-shadow:0 8px 28px #593f1d0c}.card h3,.section-title{font-size:14px;letter-spacing:.18em;color:var(--red);margin:0 0 13px}.bio{line-height:1.9;margin:0}.facts{display:grid;gap:10px}.fact{display:grid;grid-template-columns:72px 1fr;font-size:14px}.fact span:first-child{color:var(--muted)}
.chart-wrap{margin:24px 0}.chart-title{display:flex;justify-content:space-between;align-items:end}.chapter-chart{display:flex;align-items:end;gap:2px;height:140px;border-bottom:1px solid #9f8d72;padding-top:15px}.bar{flex:1;min-width:2px;background:#cab795;position:relative;transition:.2s;cursor:default}.bar.hit{background:var(--red);cursor:pointer}.bar:hover{background:var(--gold)}.bar.selected{background:#17211d;box-shadow:0 0 0 2px #bd8b3d}.bar:after{content:attr(data-tip);display:none;position:absolute;bottom:100%;left:50%;transform:translateX(-50%);white-space:nowrap;background:#211b16;color:white;padding:5px 7px;font-size:11px;z-index:3}.bar:hover:after{display:block}
.event-tools{display:flex;align-items:center;justify-content:space-between;gap:12px;border-bottom:1px solid var(--line);padding-bottom:10px}.event-tools h3{margin:0;font-size:20px}.event-list{display:grid;gap:12px;margin-top:16px}.event{display:grid;grid-template-columns:88px 1fr;background:#fffaf1;border:1px solid var(--line)}.event-pos{padding:15px 12px;background:#292f28;color:#efe3ce;text-align:center}.event-pos b{display:block;font-size:17px}.event-pos small{opacity:.65}.event-body{padding:14px 17px;line-height:1.75}.event-title{font-size:12px;color:var(--red);margin-bottom:4px}.event em{font-style:normal;background:#ead4a8;padding:0 2px}.person-link{display:inline;padding:0;border:0;border-bottom:1px dashed var(--red);background:transparent;color:inherit;cursor:pointer}.person-link:hover{color:var(--red);border-bottom-style:solid;background:#ead4a84d}.load-more{width:100%;margin-top:14px;padding:12px;border:1px solid #bfa987;background:transparent;color:var(--red);cursor:pointer}.load-more:hover{background:#fffaf1}
.inline-action{margin-left:8px;padding:3px 7px;border:1px solid var(--red);background:transparent;color:var(--red);cursor:pointer}.inline-action:hover{background:var(--red);color:#fff}
.method{margin-top:34px;padding-top:18px;border-top:1px solid var(--line);font-size:12px;color:var(--muted);line-height:1.7}
@media(max-width:820px){.stats{display:grid;grid-template-columns:1fr 1fr}.layout{display:block}.sidebar{border-right:0}.controls{position:relative}.people{height:46vh}.content{padding:28px 16px}.profile-grid{grid-template-columns:1fr}.profile-head{grid-template-columns:1fr}.mention-big{text-align:left}.event{grid-template-columns:72px 1fr}.hero{padding-top:38px}}
</style>
</head>
<body>
<header class="hero">
  <div class="kicker">一百二十回 · 群英全录</div>
  <h1>三国演义人物志</h1>
  <p>逐回检索原著正文中的姓名、字号与明确别称。点击任一人物，查看详细档案、出场轨迹，以及按小说位置排列的全部事件。</p>
  <a class="nav-link" href="./三国演义标注版电子书.html">阅读标注版电子书 →</a>
  <a class="nav-link" href="./三国演义地点可视化.html">切换至地理志 →</a>
  <a class="nav-link" href="./三国演义官职可视化.html">切换至官职志 →</a>
  <div class="stats">
    <div class="stat"><b id="characterTotal"></b><span>位有名人物</span></div>
    <div class="stat"><b id="mentionTotal"></b><span>次人物提及</span></div>
    <div class="stat"><b id="eventTotal"></b><span>条原文事件</span></div>
    <div class="stat"><b>120</b><span>回完整检索</span></div>
  </div>
</header>
<main class="layout">
  <aside class="sidebar">
    <div class="controls">
      <input id="search" class="search" type="search" placeholder="搜索姓名、字、号、籍贯或档案…" autocomplete="off">
      <div class="control-row">
        <select id="faction"><option value="">全部阵营</option></select>
        <select id="sort">
          <option value="first-desc">登场倒序</option>
          <option value="first-asc">登场正序</option>
          <option value="mentions-desc" selected>出现次数最多（默认）</option>
          <option value="mentions-asc">出现次数最少</option>
        </select>
      </div>
      <div id="resultNote" class="result-note"></div>
    </div>
    <div id="people" class="people"></div>
  </aside>
  <section class="content">
    <div id="empty" class="empty"><div><div class="seal">人物</div><p>从左侧选择一位人物<br>展开他的三国生涯</p></div></div>
    <article id="profile" class="profile"></article>
  </section>
</main>
<script id="novel-data" type="application/json">__DATA__</script>
<script>
const data=JSON.parse(document.getElementById("novel-data").textContent);
const state={selected:null,selectedChapter:null,shown:100,filtered:[]};
const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const num=n=>new Intl.NumberFormat("zh-CN").format(n);
const aliasOwners=new Map();
data.characters.forEach(c=>c.aliases.forEach(alias=>aliasOwners.set(alias,c.name)));
const aliasPattern=new RegExp([...aliasOwners.keys()].sort((a,b)=>b.length-a.length||a.localeCompare(b)).map(s=>s.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")).join("|"),"g");
$("characterTotal").textContent=num(data.meta.character_count);
$("mentionTotal").textContent=num(data.meta.mention_count);
$("eventTotal").textContent=num(data.meta.event_count);
Object.keys(data.stats.factions).sort().forEach(f=>$("faction").insertAdjacentHTML("beforeend",`<option>${esc(f)}</option>`));
function highlighted(text,currentName){
 let out="",last=0;
 for(const match of text.matchAll(aliasPattern)){
   out+=esc(text.slice(last,match.index));
   const alias=match[0],name=aliasOwners.get(alias);
   out+=name===currentName?`<em>${esc(alias)}</em>`:`<button class="person-link" data-person="${esc(name)}" title="查看${esc(name)}人物档案">${esc(alias)}</button>`;
   last=match.index+alias.length;
 }
 return out+esc(text.slice(last));
}
function applyFilters(){
 const q=$("search").value.trim().toLowerCase(),f=$("faction").value,sort=$("sort").value;
 const factionPool=data.characters.filter(c=>!f||c.faction===f);
 const direct=q?factionPool.filter(c=>[c.name,...c.aliases].join(" ").toLowerCase().includes(q)):[];
 state.filtered=!q?factionPool:(direct.length?direct:factionPool.filter(c=>[c.birthplace,c.biography].join(" ").toLowerCase().includes(q)));
 state.filtered.sort((a,b)=>{
   if(sort==="first-asc")return a.first_appearance.position-b.first_appearance.position;
   if(sort==="mentions-desc")return b.mention_count-a.mention_count||b.first_appearance.position-a.first_appearance.position;
   if(sort==="mentions-asc")return a.mention_count-b.mention_count||b.first_appearance.position-a.first_appearance.position;
   return b.first_appearance.position-a.first_appearance.position;
 });
 renderPeople();
}
function renderPeople(){
 $("resultNote").textContent=`显示 ${state.filtered.length} / ${data.meta.character_count} 人 · 默认出现次数最多者在前`;
 $("people").innerHTML=state.filtered.map((c,i)=>`<button class="person ${state.selected===c.name?"active":""}" data-name="${esc(c.name)}"><span class="rank">${String(i+1).padStart(2,"0")}</span><span><span class="person-name">${esc(c.name)}</span><span class="person-meta">第 ${c.first_appearance.chapter} 回 · ${esc(c.faction)}</span></span><span class="count">${num(c.mention_count)}<small>次</small></span></button>`).join("");
}
function renderChart(c){
 const counts=Array.from({length:120},(_,i)=>c.chapter_mentions[String(i+1)]||0),max=Math.max(...counts,1);
 return counts.map((v,i)=>`<div class="bar ${v?"hit":""} ${state.selectedChapter===i+1?"selected":""}" style="height:${v?Math.max(5,Math.sqrt(v/max)*100):1}%" data-chapter="${i+1}" data-count="${v}" data-tip="第 ${i+1} 回：${v} 次${v?" · 点击筛选":""}"></div>`).join("");
}
function renderEvents(c){
 const allEvents=state.selectedChapter?c.events.filter(e=>e.chapter===state.selectedChapter):c.events;
 const events=allEvents.slice(0,state.shown);
 $("eventList").innerHTML=events.map((e,i)=>`<div class="event"><div class="event-pos"><b>第 ${e.chapter} 回</b><small>段 ${e.paragraph}</small></div><div class="event-body"><div class="event-title">${esc(e.chapter_title)} · 事件 ${i+1}${e.mentions>1?` · 本句 ${e.mentions} 次`:""}</div>${highlighted(e.text,c.name)}</div></div>`).join("");
 $("eventSummary").innerHTML=state.selectedChapter?`第 ${state.selectedChapter} 回 · ${num(allEvents.length)} 条 <button id="showAllEvents" class="inline-action">显示所有回数</button>`:`${num(c.event_count)} 条 · 已按原著位置排序`;
 const more=$("loadMore");more.hidden=state.shown>=allEvents.length;more.textContent=`继续加载（余 ${allEvents.length-state.shown} 条）`;
 const showAll=$("showAllEvents");if(showAll)showAll.onclick=()=>toggleChapter(c,state.selectedChapter);
}
function toggleChapter(c,chapter){
 if(!c.chapter_mentions[String(chapter)])return;
 state.selectedChapter=state.selectedChapter===chapter?null:chapter;
 state.shown=100;
 $("chapterChart").innerHTML=renderChart(c);
 renderEvents(c);
}
function jumpToCharacter(name){
 $("search").value="";
 $("faction").value="";
 applyFilters();
 selectCharacter(name);
}
function selectCharacter(name){
 const c=data.characters.find(x=>x.name===name);if(!c)return;
 state.selected=name;state.selectedChapter=null;state.shown=100;renderPeople();$("empty").style.display="none";
 const courtesy=c.courtesy_name?`字 ${esc(c.courtesy_name)}`:"字未载";
 const aliases=c.aliases.filter(a=>a!==c.name&&a!==c.courtesy_name);
 $("profile").className="profile visible";
 $("profile").innerHTML=`<div class="profile-head"><div><div class="kicker" style="color:var(--red)">第 ${c.first_appearance.chapter} 回登场</div><h2>${esc(c.name)}</h2><div class="aliases">${courtesy}${aliases.length?" · "+esc(aliases.join(" / ")):""}</div><div class="badges"><span class="badge">${esc(c.faction)}</span><span class="badge">${c.historical==="是"?"正史人物":c.historical==="否"?"演义人物":"史实未注明"}</span>${c.titles_in_text.slice(0,5).map(x=>`<span class="badge">${esc(x)}</span>`).join("")}</div></div><div class="mention-big"><b>${num(c.mention_count)}</b><span>次出现 · ${num(c.event_count)} 条事件</span></div></div>
 <div class="profile-grid"><section class="card"><h3>人物列传</h3><p class="bio">${esc(c.biography||"原著未提供完整人物小传。")}</p></section><aside class="card"><h3>档案札记</h3><div class="facts"><div class="fact"><span>籍贯</span><b>${esc(c.birthplace||"未载")}</b></div><div class="fact"><span>初登场</span><b>第 ${c.first_appearance.chapter} 回 · 第 ${c.first_appearance.paragraph} 段</b></div><div class="fact"><span>末登场</span><b>第 ${c.last_appearance.chapter} 回 · 第 ${c.last_appearance.paragraph} 段</b></div><div class="fact"><span>涉及回目</span><b>${Object.keys(c.chapter_mentions).length} 回</b></div></div></aside></div>
 <section class="chart-wrap"><div class="chart-title"><h3 class="section-title">一百二十回出场轨迹</h3><small>点击红柱筛选该回，再次点击恢复全部</small></div><div id="chapterChart" class="chapter-chart">${renderChart(c)}</div></section>
 <section><div class="event-tools"><h3>全部事件</h3><span id="eventSummary">${num(c.event_count)} 条 · 已按原著位置排序</span></div><div id="eventList" class="event-list"></div><button id="loadMore" class="load-more"></button></section>
 <div class="method">计数口径：${esc(data.meta.counting_rule)}<br>事件口径：${esc(data.meta.event_rule)} 人物档案参考维基文库《三国演义人物列表》，出场统计与事件原文均来自本仓库 120 回正文。</div>`;
 renderEvents(c);$("loadMore").onclick=()=>{state.shown+=100;renderEvents(c)};
 $("chapterChart").onclick=e=>{const bar=e.target.closest(".bar.hit");if(bar)toggleChapter(c,Number(bar.dataset.chapter))};
 $("eventList").onclick=e=>{const link=e.target.closest("[data-person]");if(link)jumpToCharacter(link.dataset.person)};
 if(innerWidth<821)$("profile").scrollIntoView({behavior:"smooth",block:"start"});
}
$("people").addEventListener("click",e=>{const b=e.target.closest("[data-name]");if(b)selectCharacter(b.dataset.name)});
["search","faction","sort"].forEach(id=>$(id).addEventListener(id==="search"?"input":"change",applyFilters));
applyFilters();
const requested=decodeURIComponent(location.hash.slice(1));
if(data.characters.some(c=>c.name===requested)){
 $("search").value=requested;
 applyFilters();
 selectCharacter(requested);
}
</script>
</body>
</html>"""
    return template.replace("__DATA__", data.replace("</", "<\\/"))


def main():
    chapters = read_chapters()
    corpus = "\n".join(chapter["text"] for chapter in chapters)
    reference = load_reference()
    profiles = resolve_profiles(reference, corpus)
    characters = extract_characters(chapters, profiles)
    payload = build_payload(chapters, characters)

    DATA_DIR.mkdir(exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    OUT_HTML.write_text(render_html(payload), encoding="utf-8")
    print(
        f"Done: {len(chapters)} chapters, {len(characters)} characters, "
        f"{payload['meta']['mention_count']} mentions, "
        f"{payload['meta']['event_count']} events"
    )
    print("Data and standalone HTML written successfully.")


if __name__ == "__main__":
    main()
