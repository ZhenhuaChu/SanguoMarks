import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

from extract_characters import clip_event, read_chapters


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CHARACTER_DATA = DATA_DIR / "三国演义人物数据.json"
REFERENCE_CACHE = DATA_DIR / "三国地名参考词表.json"
OUT_JSON = DATA_DIR / "三国演义地点数据.json"
OUT_HTML = ROOT / "三国演义地点可视化.html"
REFERENCE_URL = "https://zh.wikipedia.org/zh-hans/%E4%B8%89%E5%9B%BD%E8%A1%8C%E6%94%BF%E5%8C%BA%E5%88%92"
HAN_RE = re.compile(r"^[\u3400-\u9fff]{1,8}$")
SENTENCE_RE = re.compile(r"[^。！？；\n]+[。！？；]?")

SPECIAL_LOCATIONS = set(
    """
    荆州 东吴 汉中 江东 徐州 成都 许都 许昌 洛阳 祁山 襄阳 西川 西凉 长安 江南 樊城 中原
    冀州 江夏 蜀中 南郡 河北 兖州 南安 汝南 益州 泸水 淮南 平原 剑阁     青州 南阳 长沙 陈留 天水 幽州 吴郡 两川 河内 三江 当阳
    阳平关 豫州 辽东 陇西 江陵 定军山 雍州 长江 山东 绵竹 长坂 濮阳 黎阳 北海 南郑
    常山 新城 桃园 魏国 土山 渭水 武昌 泰山 潼关 东川 宛城 扬州 洮阳 阆中 北原 江北
    渭南 巴西 广陵 柳城 桂阳 永安 涪城 皖城 颍川 上庸 襄平 并州 西城 中山 巴丘 涪关
    黄河 乌戈国 古城 土城 金城 麦城 临淄 冀城 华夏 山阳 武都 洮水 渭滨 陇上 丹阳
    庐江 武城山 河东 涿郡 西平 东兴 南屏山 武陵 永昌 江汉 河西 渭河 漳河 甘泉
    石头城 耒阳 荥阳 东莱 关东 关西 凉州 卧牛山 岘山 河南 渤海 白河 虎牢关 蜀道
    襄江 西凉州 西洱河 鄄城 长安城 阳安关 巢湖 樊口 汉川 汉江 沛城 济北 渭北 渭桥
    蜀地 豫章 镇国寺 阳城 东海 东郡 东阿 乌林 乐城 冀县 南彝陵 南顿 咸阳 天荡山
    宜都 摩陂 汉阳 沛国 泾县 涪水 涪江 湖口 盱眙 秭归 蜀汉 褒州 邯郸 鄱阳湖 铜雀台
    东关 临洮 京城 仙庄 北平 北彝陵 华阴 南谷 巴山 巴郡 广汉 延津 新野 新野县
    柏梁台 柴桑 檀溪 武关 汉津 沛县 洛水 涿县 清河 渑池 渭口 砀山 磐河 秦川 萧关
    襄城 辽西 邳城 长乐宫 东城 东山 东岭 东都 临漳 兴平 冀北 南昌 南漳 南越 南郊
    塞北 壶关 夏口 孟津 安丰 安喜 安喜县 定州 宣城 嵩山 巴州 德阳 景山 曲阳 武阳
    永宁 汉南 汉宁 江州 沂都 泗水 洛阳城 洮西 淮水 淮河 湘江 白沟 竟陵 终南山
    荆南 葛陂 蒲阪津 鄱阳 钱塘 长坂坡 青城山 马鞍山 驻马坡 鲁国 黄县 黄州 东原
    东平 东武城 东莞 中牟 中牟县 临淮 云安 交州 会稽 会稽山 北固山 北河 南海 博陵
    商州 垫江 塔郎甸 夔关 太原 宁陵 安众 安众县 安邑 宜阳 宣平门 富池口 寿春 巫峡
    平原县 广州 彝陵 夷陵 猇亭 攸县 易京 曲阜 松滋 柴桑口 梁城 梁州 楚地 武城
    汉东 汉津口 江西 江都 江阳 汶山 沂水 河朔 洛河 洞庭湖 济南 济阳 济阴 浙江
    海州 润州 涿鹿 淝县 淝城 淮阳 淮阴 清水河 渔阳 犍为 甘陵 石城 石邑 石邑县
    祁阳 神州 秦国 繁阳 罗川 翼城 芜湖 荆山 荆湖 荆门 襄樊 襄武 襄武县 西乡 西河
    西津 西郡 西都 西陵 许田 谯县 赤壁 辽水 辽河 邙山 郢州 鄂县 铜雀宫 锦城
    锦官城 锦江 锦里 阆州 雁门 雍城 霸河 青泥 青泥镇 首阳山 黑山
    博望坡 华容道 华容 白门楼 凤仪亭 落凤坡 上方谷 五丈原 乌巢 官渡 街亭 濡须口
    逍遥津 大兴山 长坂桥 草庐 白帝城 七星坛 三江口 瓦口隘 佛寺 雒城 葭萌关 斜谷
    铜雀台 猇亭 八阵图 阴平 绵竹 木门道 陈仓 箕谷 子午谷 褒斜道 葫芦谷 盘蛇谷
    祁山寨 五关 白马坡 黄巾寨 汜水关 虎牢关 辕门 小沛 下邳 下邳城 白马 延津
    官渡口 仓亭 漳河 黎阳城 冀州城 邺城 邺 壶关口 檀溪水 隆中 博望 新野城
    长坂坡 当阳 汉津口 夏口 柴桑 南徐 甘露寺 桂阳郡 江陵城 公安 油江口
    涪水关 落凤坡 雒县 成都城 巴郡 葭萌关 瓦口关 天荡山 米仓山 汉水 定军山
    斜谷界口 襄阳郡 罾口 麦城 临沮 玉泉山 建业 武昌 白帝城 永安宫 夷陵 江口
    鱼腹浦 泸水 银坑洞 秃龙洞 盘蛇谷 三江城 桃花渡 西平关 祁山 天水 南安郡
    安定郡 街亭 列柳城 西城 祁山寨 陈仓口 武都 阴平 剑阁 五丈原 北原 渭桥
    上方谷 葫芦谷 辽东 襄平 牛头山 铁笼山 寿春 长城 沓中 汉中道 定军山 绵竹
    成都 祖庙 建宁 襄阳 西陵 武昌 建业 洛阳 狄道 汉寿 河间 彭城 上洛 苍梧 牂牁
    梓潼 汉嘉 代郡 历阳 朐县 马邑 邾县 八纳洞 芳林园 羊山 箕山 南阙 东华门
    """.split()
)

NON_LOCATIONS = set(
    """
    天下 上马 城中 军中 心中 朝廷 城上 城下 城外 山上 手下 阵前 门外 江边 山坡 宫中
    馆驿 船上 水中 阵中 岸上 山中 入川 入城 渡江 下山 路上 手中 车中 山下 山前 桥上
    桥边 林中 地下 殿下 关上 关内 关外 寨中 寨外 营中 帐中 家中 口中 胸中 头上 身上
    园中 城内 城边 城南 门前 车前 阵上 江岸 江中 上山 入寨 回城 离城 大寨 四门 中路
    正东 正南 正西 正北 东南 东北 西南 西北 东方 西方 内外 东西 左右 城池 山川 江山
    高山 山林 山野 高冈 高阜 河边 四海 海内 中国 大国 三国 江湖 大江 江水 河 路 门 山
    中 东 西 南 北 英雄 莫非 匹夫 立马 之士 哥哥 木牛流马 大汉 黄门 屯田 那马 奉天
    鞍马 匹马 虎威 长大 青龙 相国 镇东 镇西 镇南 天威 歇马 之德 伏路 城东 安乐 山城
    登城 绕城 蛟龙 遂拜 中兴 中堂 中道 城垣 威镇 安东 山峪 布列 择吉 望北 朝贺 沿河
    满城 焉能 猛省 阴阳 之劳 之盟 云汉 云集 关津 北风 土阜 安国 安邦定国 密林 山寨
    山岩 平南 平川 归国 扬武 故耳 无虞 望南 满口 满谷 漫山塞野 登山 美丽 英灵 莫大
    蜀锦 西寨 西州 西番 西路 诸县 连城 陕西 青旗 顿开茅塞 东西南北 东连吴 享国
    势如劈竹 半山 南寨 叙旧 古庙 合吾意 嘉平 土冈 土坡 圣明 城西 大兴土木 大海 大溪
    太仓 太阳 太阴 夹江 奉汉 如林 威胜 官拜 扎寨 扬威 攀木 故特 无马 昔为 望城 望西
    朝野 朝阳 来京 桥东 桥西 永镇 汝原 江渚 江畔 河口 河水 泉水 泽及 洞丁 深山 深渊
    绕江 罗拜 荷蒙 虎林 蜀寨 蜀连 西连 赞拜 赞美 越岭 跃龙 长戈 长随 青春 非关 非君
    黄马 龙兴 龙尾 入宫 东门 西门 南门 北门 开城 回本 渡河 白马 上城 太平 辕门
    入山 上殿 下江 九郡 上关 入南 四郡 川口 朝中 之耳 乃东 北山 南山 西山 山口 山脚
    回南 回京 入京 两山 上岭 下城 四州 治国 九州 中门 蒙头 三洞 入海 山河 绕河 上国
    入寿 山岭 安营下寨 山坞 虎口 两京 东市 瓮城 之口 五关 上坛 北渡 望西川 阜为 登门
    牡丹 并川 陵坡 五湖 入庙 归城 包原 沈岭 湖山 郡县 北宫 桐宫 西村 卫国 德州
    大河 牡丹亭 荷池 北掖 古寺 且州县 城邑 六宫 西安 大阳 天津 天关 枫桥 城上城
    玄德县 运七 十县 两河 抚河 沧海 冀四州 防江 冠江 大州 北寨 北河 满县 下河 上京
    东皇 斯台 开国 悉召江 九河 百川 洪荒 西观夏口 合江 满江 北南 归南 远镇 兰干
    中寨 夹河 屯冀城 冰城 西郡 阜如 回川 荒州 榆桥 治建业 平城 诸州 涪水西 盖州
    建安二十年 虹桥 温州 翼德兵屯瓦口 云回本寨 上庸诸郡 山水 阳江 四山 越城
    上建庙 彰德 中州 青城 合寨 塞江 泛湖 江道 河港 夹山 甘南 泉台 旧都 领汉中
    深城 羌胡 三城 下川 四县 非一州 石山 满山 赤坡 摩坡 渭登原 安镇
    """.split()
)

VARIANT_GROUPS = {
    "合肥": ["合淝"],
    "夷陵": ["彝陵"],
    "曹魏": ["魏国"],
    "许昌": ["许都"],
    "邺城": ["邺"],
    "新野": ["新野县", "新野城"],
    "洛阳": ["洛阳城"],
    "长安": ["长安城"],
    "安喜县": ["安喜"],
    "襄武县": ["襄武"],
    "中牟县": ["中牟"],
    "石邑县": ["石邑"],
}

PLACE_SUFFIXES = (
    "州", "郡", "县", "城", "关", "隘", "山", "岭", "峰", "谷", "坡", "原",
    "川", "河", "江", "水", "湖", "海", "津", "渡", "口", "桥", "道", "寨",
    "营", "宫", "殿", "台", "楼", "亭", "寺", "庙", "观", "洞", "庄", "村",
    "邑", "镇", "坞", "陵", "陂", "浦", "坛", "园",
)


class TableCellParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_cell = False
        self.parts = []
        self.cells = []

    def handle_starttag(self, tag, attrs):
        if tag in {"td", "th"}:
            self.in_cell = True
            self.parts = []

    def handle_data(self, data):
        if self.in_cell:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.in_cell:
            self.cells.append("".join(self.parts).strip())
            self.in_cell = False


def context_count(corpus, name):
    escaped = re.escape(name)
    before = (
        r"(?:在|于|往|至|到|从|自|向|赴|回|还|离|出|入|屯|守|攻|取|围|据|抵|过|奔|"
        r"投|驻|居|住|迁|退|进|路经|途经|兵至|兵屯)"
    )
    after = r"(?:人氏|人也|人，|人。|太守|刺史|牧|界|地|路|道|口|城|关|山|水|县|郡|州)"
    return len(re.findall(before + escaped, corpus)) + len(re.findall(escaped + after, corpus))


def download_reference(corpus):
    request = Request(REFERENCE_URL, headers={"User-Agent": "RTK-location-index/1.0"})
    source = urlopen(request, timeout=30).read().decode("utf-8")
    parser = TableCellParser()
    parser.feed(source)
    names = set()
    for cell in parser.cells:
        cleaned = re.sub(r"\[[^\]]*]|\([^)]*\)|（[^）]*）|[0-9¹²³#*]", "", cell)
        for token in re.split(r"[、，,；;：:\s↓→/]+", cleaned):
            token = token.strip()
            if (
                2 <= len(token) <= 7
                and HAN_RE.fullmatch(token)
                and token in corpus
                and (token.endswith(PLACE_SUFFIXES) or context_count(corpus, token))
            ):
                names.add(token)
    payload = {"source": REFERENCE_URL, "locations": sorted(names)}
    REFERENCE_CACHE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return names


def load_reference(corpus):
    if REFERENCE_CACHE.exists():
        return set(json.loads(REFERENCE_CACHE.read_text(encoding="utf-8"))["locations"])
    return download_reference(corpus)


def location_type(name):
    if name in {
        "中原", "平原", "北原", "五原", "太原", "包原", "天水", "北海",
        "东海", "渤海", "庐江", "九江", "临江", "垫江",
    }:
        return "地区与其他"
    rules = [
        ("州郡县邑", ("州", "郡", "县", "邑", "国")),
        ("城池关隘", ("城", "关", "隘", "寨", "营", "坞")),
        ("山岭谷原", ("山", "岭", "峰", "谷", "坡", "原")),
        ("江河湖海", ("江", "河", "水", "湖", "海", "浦")),
        ("建筑地点", ("宫", "殿", "台", "楼", "亭", "寺", "庙", "观", "坛", "园", "庄")),
        ("道路渡口", ("口", "桥", "道", "津", "渡")),
    ]
    for kind, suffixes in rules:
        if name.endswith(suffixes):
            return kind
    return "地区与其他"


def discover_locations(corpus, character_data):
    people = {item["name"] for item in character_data["characters"]}
    people.update(
        alias for item in character_data["characters"] for alias in item["aliases"]
    )
    candidates = {name for name in SPECIAL_LOCATIONS if name in corpus}
    for name in load_reference(corpus):
        if (
            re.fullmatch(r"[\u3400-\u9fff]{1,5}(?:州|郡|县|国)", name)
            and not any(char in name for char in "一二三四五六七八九十百千万两数诸各")
            and not name.startswith(("非", "且", "地", "治", "大"))
        ):
            candidates.add(name)

    candidates.difference_update(NON_LOCATIONS)
    candidates.difference_update(people)
    aliases_by_name = {name: [name] for name in candidates}
    alias_to_canonical = {}
    for canonical, variants in VARIANT_GROUPS.items():
        present = [item for item in [canonical, *variants] if item in corpus]
        if not present:
            continue
        aliases_by_name.setdefault(canonical, [canonical])
        aliases_by_name[canonical] = present
        for variant in variants:
            aliases_by_name.pop(variant, None)

    # Merge simple administrative suffix spellings, while retaining named compounds.
    for name in sorted(list(aliases_by_name), key=len, reverse=True):
        for suffix in ("城", "县", "郡", "州"):
            if name.endswith(suffix) and name[:-1] in aliases_by_name:
                aliases_by_name[name[:-1]].append(name)
                aliases_by_name.pop(name, None)
                break

    for canonical, aliases in aliases_by_name.items():
        for alias in aliases:
            alias_to_canonical[alias] = canonical
    return aliases_by_name, alias_to_canonical


def make_pattern(alias_to_canonical):
    return re.compile(
        "|".join(
            re.escape(alias)
            for alias in sorted(alias_to_canonical, key=lambda value: (-len(value), value))
        )
    )


def extract_locations(chapters, aliases_by_name, alias_to_canonical):
    pattern = make_pattern(alias_to_canonical)
    records = {
        name: {
            "name": name,
            "aliases": sorted(set(aliases), key=lambda value: (-len(value), value)),
            "type": location_type(name),
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

    locations = []
    for record in records.values():
        if not record["events"]:
            continue
        record["chapter_mentions"] = dict(
            sorted(record["chapter_mentions"].items(), key=lambda item: int(item[0]))
        )
        record["event_count"] = len(record["events"])
        locations.append(record)
    locations.sort(
        key=lambda item: (
            -item["mention_count"],
            item["first_appearance"]["position"],
            item["name"],
        )
    )
    return locations


def build_payload(chapters, locations):
    types = Counter(item["type"] for item in locations)
    return {
        "meta": {
            "title": "三国演义地理志",
            "chapter_count": len(chapters),
            "location_count": len(locations),
            "mention_count": sum(item["mention_count"] for item in locations),
            "event_count": sum(item["event_count"] for item in locations),
            "sort": "出现次数倒序",
            "counting_rule": "按正文中地点名称及明确异体别称的实际出现次数统计。",
            "event_rule": "包含该地点的一句话为一个事件，并补充所在段落的前后文。",
            "source": "src/ 下 120 回正文",
            "reference_source": REFERENCE_URL,
        },
        "chapters": [
            {"number": item["number"], "title": item["title"]} for item in chapters
        ],
        "stats": {"types": dict(types)},
        "locations": locations,
    }


def render_html(payload, character_data):
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace(
        "</", "<\\/"
    )
    people = json.dumps(
        [
            {"name": item["name"], "aliases": item["aliases"]}
            for item in character_data["characters"]
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    template = r"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>三国演义地理志 · 全地点可视化</title>
<style>
:root{--paper:#edf0e6;--ink:#1d251f;--muted:#69746b;--green:#355f4a;--red:#9e2f24;--gold:#b8893d;--line:#c9d0c2;--panel:#f9fbf4;--dark:#17241d}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;color:var(--ink);background:var(--paper);font-family:"Microsoft YaHei","Noto Serif SC",serif}body:before{content:"";position:fixed;inset:0;pointer-events:none;opacity:.22;background-image:radial-gradient(#49604f .55px,transparent .7px);background-size:7px 7px}
button,input,select{font:inherit}.hero{position:relative;overflow:hidden;padding:54px clamp(20px,6vw,88px) 42px;color:#eef4e9;background:linear-gradient(120deg,#13241b,#294735 58%,#51422b)}.hero:after{content:"山河";position:absolute;right:4vw;top:-48px;font:900 min(24vw,280px)/1 serif;color:#fff;opacity:.035}.kicker{letter-spacing:.35em;color:#d7bd82;font-size:13px}.hero h1{font-size:clamp(38px,6vw,76px);margin:10px 0 8px;letter-spacing:.08em;font-family:STKaiti,KaiTi,serif}.hero p{max-width:780px;color:#d3ddd3;line-height:1.8;margin:0}.nav-link{display:inline-block;margin:14px 15px 0 0;color:#e8cf98;text-decoration:none;border-bottom:1px dashed #e8cf98}
.stats{display:flex;gap:1px;margin-top:25px;max-width:850px;background:#ffffff24;border:1px solid #ffffff24}.stat{flex:1;padding:16px 18px;background:#10191488}.stat b{display:block;font-size:27px;color:#f0d49f}.stat span{font-size:12px;color:#c9d1ca}.layout{display:grid;grid-template-columns:minmax(320px,460px) 1fr;min-height:calc(100vh - 260px)}.sidebar{border-right:1px solid var(--line);background:#e2e8dccc}.controls{position:sticky;top:0;z-index:4;padding:16px;background:#e2e8dcf5;border-bottom:1px solid var(--line);backdrop-filter:blur(10px)}.search{width:100%;padding:11px 13px;border:1px solid #9da99d;background:#f9fbf4;border-radius:3px;outline:none}.search:focus{border-color:var(--green);box-shadow:0 0 0 2px #355f4a18}.control-row{display:flex;gap:8px;margin-top:9px}.control-row select{min-width:0;flex:1;padding:8px;border:1px solid #adb8aa;background:#f4f7ee;color:var(--ink)}.result-note{margin-top:9px;font-size:12px;color:var(--muted)}.places{height:calc(100vh - 125px);overflow:auto;padding:8px 10px 32px}.place{width:100%;display:grid;grid-template-columns:46px 1fr auto;gap:10px;align-items:center;text-align:left;border:0;border-bottom:1px solid #c7d0c1;background:transparent;padding:13px 9px;cursor:pointer;color:inherit}.place:hover,.place.active{background:#f8faF3}.place.active{box-shadow:inset 3px 0 var(--green)}.rank{font:20px Georgia;color:#788778}.place-name{font-size:17px;font-weight:700}.place-meta{font-size:11px;color:var(--muted);margin-top:4px}.count{text-align:right;color:var(--green);font-weight:700}.count small{display:block;color:var(--muted);font-weight:400}
.content{min-width:0;padding:clamp(20px,4vw,58px);background:#f2f5ec}.empty{height:60vh;display:grid;place-content:center;text-align:center;color:var(--muted)}.seal{width:76px;height:76px;border:3px double var(--green);color:var(--green);display:grid;place-items:center;margin:0 auto 20px;font:30px STKaiti;transform:rotate(-4deg)}.profile{display:none;max-width:1050px;margin:auto}.profile.visible{display:block}.profile-head{display:grid;grid-template-columns:1fr auto;gap:20px;padding-bottom:24px;border-bottom:2px solid var(--ink)}.profile h2{font:700 clamp(35px,5vw,58px) STKaiti,KaiTi,serif;margin:0}.aliases{color:var(--green);margin-top:7px}.badges{display:flex;gap:7px;flex-wrap:wrap;margin-top:14px}.badge{padding:4px 8px;border:1px solid #9cac9d;color:#526056;font-size:12px;background:#f9fbf4}.mention-big{text-align:right}.mention-big b{display:block;font:46px Georgia;color:var(--green)}.mention-big span{font-size:12px;color:var(--muted)}.profile-grid{display:grid;grid-template-columns:1.25fr .75fr;gap:24px;margin:24px 0}.card{background:var(--panel);border:1px solid var(--line);padding:20px;box-shadow:0 8px 28px #324b370c}.card h3,.section-title{font-size:14px;letter-spacing:.18em;color:var(--green);margin:0 0 13px}.bio{line-height:1.9;margin:0}.facts{display:grid;gap:10px}.fact{display:grid;grid-template-columns:72px 1fr;font-size:14px}.fact span:first-child{color:var(--muted)}
.chart-wrap{margin:24px 0}.chart-title{display:flex;justify-content:space-between;align-items:end}.chapter-chart{display:flex;align-items:end;gap:2px;height:140px;border-bottom:1px solid #879588;padding-top:15px}.bar{flex:1;min-width:2px;background:#acbba9;position:relative;transition:.2s;cursor:default}.bar.hit{background:var(--green);cursor:pointer}.bar:hover{background:var(--gold)}.bar.selected{background:#17241d;box-shadow:0 0 0 2px var(--gold)}.bar:after{content:attr(data-tip);display:none;position:absolute;bottom:100%;left:50%;transform:translateX(-50%);white-space:nowrap;background:#17241d;color:white;padding:5px 7px;font-size:11px;z-index:3}.bar:hover:after{display:block}
.event-tools{display:flex;align-items:center;justify-content:space-between;gap:12px;border-bottom:1px solid var(--line);padding-bottom:10px}.event-tools h3{margin:0;font-size:20px}.event-list{display:grid;gap:12px;margin-top:16px}.event{display:grid;grid-template-columns:88px 1fr;background:var(--panel);border:1px solid var(--line)}.event-pos{padding:15px 12px;background:#26392d;color:#edf3e9;text-align:center}.event-pos b{display:block;font-size:17px}.event-pos small{opacity:.65}.event-body{padding:14px 17px;line-height:1.75}.event-title{font-size:12px;color:var(--green);margin-bottom:4px}.event em{font-style:normal;background:#cad9bd;padding:0 2px}.place-link,.person-link{display:inline;padding:0;border:0;background:transparent;color:inherit;cursor:pointer}.place-link{border-bottom:1px dashed var(--green)}.person-link{border-bottom:1px dotted var(--red);color:#6f2c27}.place-link:hover{color:var(--green);border-bottom-style:solid}.person-link:hover{color:var(--red);border-bottom-style:solid}.load-more{width:100%;margin-top:14px;padding:12px;border:1px solid #91a18f;background:transparent;color:var(--green);cursor:pointer}.load-more:hover{background:var(--panel)}.inline-action{margin-left:8px;padding:3px 7px;border:1px solid var(--green);background:transparent;color:var(--green);cursor:pointer}.method{margin-top:34px;padding-top:18px;border-top:1px solid var(--line);font-size:12px;color:var(--muted);line-height:1.7}
@media(max-width:820px){.stats{display:grid;grid-template-columns:1fr 1fr}.layout{display:block}.sidebar{border-right:0}.controls{position:relative}.places{height:46vh}.content{padding:28px 16px}.profile-grid{grid-template-columns:1fr}.profile-head{grid-template-columns:1fr}.mention-big{text-align:left}.event{grid-template-columns:72px 1fr}.hero{padding-top:38px}}
</style></head><body>
<header class="hero"><div class="kicker">一百二十回 · 山河全录</div><h1>三国演义地理志</h1><p>逐回检索原著中的州郡、城池、关隘、山川与建筑地点。点击地点，查看详细档案、出场轨迹和按原著位置排列的全部事件。</p><a class="nav-link" href="./三国演义标注版电子书.html">阅读标注版电子书 →</a><a class="nav-link" href="./三国演义人物可视化.html">切换至人物志 →</a><a class="nav-link" href="./三国演义官职可视化.html">切换至官职志 →</a><div class="stats"><div class="stat"><b id="locationTotal"></b><span>处有名地点</span></div><div class="stat"><b id="mentionTotal"></b><span>次地点提及</span></div><div class="stat"><b id="eventTotal"></b><span>条原文事件</span></div><div class="stat"><b>120</b><span>回完整检索</span></div></div></header>
<main class="layout"><aside class="sidebar"><div class="controls"><input id="search" class="search" type="search" placeholder="搜索地点、别称或回目…" autocomplete="off"><div class="control-row"><select id="type"><option value="">全部类型</option></select><select id="sort"><option value="mentions-desc" selected>出现次数最多（默认）</option><option value="first-asc">登场正序</option><option value="first-desc">登场倒序</option><option value="mentions-asc">出现次数最少</option></select></div><div id="resultNote" class="result-note"></div></div><div id="places" class="places"></div></aside>
<section class="content"><div id="empty" class="empty"><div><div class="seal">山河</div><p>从左侧选择一处地点<br>展开它的三国故事</p></div></div><article id="profile" class="profile"></article></section></main>
<script id="novel-data" type="application/json">__DATA__</script><script id="people-data" type="application/json">__PEOPLE__</script>
<script>
const data=JSON.parse(document.getElementById("novel-data").textContent),people=JSON.parse(document.getElementById("people-data").textContent);
const state={selected:null,selectedChapter:null,shown:100,filtered:[]};const $=id=>document.getElementById(id);const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));const num=n=>new Intl.NumberFormat("zh-CN").format(n);
const tokens=new Map();data.locations.forEach(l=>l.aliases.forEach(a=>tokens.set(a,{kind:"place",name:l.name})));people.forEach(p=>p.aliases.forEach(a=>{if(!tokens.has(a))tokens.set(a,{kind:"person",name:p.name})}));
const tokenPattern=new RegExp([...tokens.keys()].sort((a,b)=>b.length-a.length||a.localeCompare(b)).map(s=>s.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")).join("|"),"g");
$("locationTotal").textContent=num(data.meta.location_count);$("mentionTotal").textContent=num(data.meta.mention_count);$("eventTotal").textContent=num(data.meta.event_count);Object.keys(data.stats.types).sort().forEach(t=>$("type").insertAdjacentHTML("beforeend",`<option>${esc(t)}</option>`));
function marked(text,current){let out="",last=0;for(const m of text.matchAll(tokenPattern)){out+=esc(text.slice(last,m.index));const token=m[0],owner=tokens.get(token);if(owner.kind==="place")out+=owner.name===current?`<em>${esc(token)}</em>`:`<button class="place-link" data-place="${esc(owner.name)}" title="查看${esc(owner.name)}地点档案">${esc(token)}</button>`;else out+=`<a class="person-link" href="./三国演义人物可视化.html#${encodeURIComponent(owner.name)}" title="查看${esc(owner.name)}人物档案">${esc(token)}</a>`;last=m.index+token.length}return out+esc(text.slice(last))}
function applyFilters(){const q=$("search").value.trim().toLowerCase(),t=$("type").value,s=$("sort").value;state.filtered=data.locations.filter(l=>(!t||l.type===t)&&(!q||[l.name,...l.aliases,l.first_appearance.chapter_title].join(" ").toLowerCase().includes(q)));state.filtered.sort((a,b)=>s==="first-asc"?a.first_appearance.position-b.first_appearance.position:s==="first-desc"?b.first_appearance.position-a.first_appearance.position:s==="mentions-asc"?a.mention_count-b.mention_count||a.first_appearance.position-b.first_appearance.position:b.mention_count-a.mention_count||a.first_appearance.position-b.first_appearance.position);renderPlaces()}
function renderPlaces(){$("resultNote").textContent=`显示 ${state.filtered.length} / ${data.meta.location_count} 处 · 默认出现次数最多者在前`;$("places").innerHTML=state.filtered.map((l,i)=>`<button class="place ${state.selected===l.name?"active":""}" data-name="${esc(l.name)}"><span class="rank">${String(i+1).padStart(2,"0")}</span><span><span class="place-name">${esc(l.name)}</span><span class="place-meta">第 ${l.first_appearance.chapter} 回 · ${esc(l.type)}</span></span><span class="count">${num(l.mention_count)}<small>次</small></span></button>`).join("")}
function renderChart(l){const counts=Array.from({length:120},(_,i)=>l.chapter_mentions[String(i+1)]||0),max=Math.max(...counts,1);return counts.map((v,i)=>`<div class="bar ${v?"hit":""} ${state.selectedChapter===i+1?"selected":""}" style="height:${v?Math.max(5,Math.sqrt(v/max)*100):1}%" data-chapter="${i+1}" data-tip="第 ${i+1} 回：${v} 次${v?" · 点击筛选":""}"></div>`).join("")}
function renderEvents(l){const all=state.selectedChapter?l.events.filter(e=>e.chapter===state.selectedChapter):l.events,events=all.slice(0,state.shown);$("eventList").innerHTML=events.map((e,i)=>`<div class="event"><div class="event-pos"><b>第 ${e.chapter} 回</b><small>段 ${e.paragraph}</small></div><div class="event-body"><div class="event-title">${esc(e.chapter_title)} · 事件 ${i+1}${e.mentions>1?` · 本句 ${e.mentions} 次`:""}</div>${marked(e.text,l.name)}</div></div>`).join("");$("eventSummary").innerHTML=state.selectedChapter?`第 ${state.selectedChapter} 回 · ${num(all.length)} 条 <button id="showAllEvents" class="inline-action">显示所有回数</button>`:`${num(l.event_count)} 条 · 已按原著位置排序`;const more=$("loadMore");more.hidden=state.shown>=all.length;more.textContent=`继续加载（余 ${all.length-state.shown} 条）`;const allButton=$("showAllEvents");if(allButton)allButton.onclick=()=>toggleChapter(l,state.selectedChapter)}
function toggleChapter(l,chapter){if(!l.chapter_mentions[String(chapter)])return;state.selectedChapter=state.selectedChapter===chapter?null:chapter;state.shown=100;$("chapterChart").innerHTML=renderChart(l);renderEvents(l)}
function jumpToLocation(name){$("search").value="";$("type").value="";applyFilters();selectLocation(name)}
function selectLocation(name){const l=data.locations.find(x=>x.name===name);if(!l)return;state.selected=name;state.selectedChapter=null;state.shown=100;renderPlaces();$("empty").style.display="none";const aliases=l.aliases.filter(a=>a!==l.name);$("profile").className="profile visible";$("profile").innerHTML=`<div class="profile-head"><div><div class="kicker" style="color:var(--green)">第 ${l.first_appearance.chapter} 回出现</div><h2>${esc(l.name)}</h2><div class="aliases">${aliases.length?"别称 / 异体："+esc(aliases.join(" / ")):"原著通用地名"}</div><div class="badges"><span class="badge">${esc(l.type)}</span><span class="badge">涉及 ${Object.keys(l.chapter_mentions).length} 回</span></div></div><div class="mention-big"><b>${num(l.mention_count)}</b><span>次出现 · ${num(l.event_count)} 条事件</span></div></div><div class="profile-grid"><section class="card"><h3>地点概览</h3><p class="bio">${esc(l.name)}是《三国演义》叙事中出现的${esc(l.type)}。首次见于第 ${l.first_appearance.chapter} 回“${esc(l.first_appearance.chapter_title)}”，末次见于第 ${l.last_appearance.chapter} 回。</p></section><aside class="card"><h3>地理札记</h3><div class="facts"><div class="fact"><span>类别</span><b>${esc(l.type)}</b></div><div class="fact"><span>初出现</span><b>第 ${l.first_appearance.chapter} 回 · 第 ${l.first_appearance.paragraph} 段</b></div><div class="fact"><span>末出现</span><b>第 ${l.last_appearance.chapter} 回 · 第 ${l.last_appearance.paragraph} 段</b></div><div class="fact"><span>涉及回目</span><b>${Object.keys(l.chapter_mentions).length} 回</b></div></div></aside></div><section class="chart-wrap"><div class="chart-title"><h3 class="section-title">一百二十回地点轨迹</h3><small>点击绿色柱筛选该回，再次点击恢复全部</small></div><div id="chapterChart" class="chapter-chart">${renderChart(l)}</div></section><section><div class="event-tools"><h3>全部事件</h3><span id="eventSummary">${num(l.event_count)} 条 · 已按原著位置排序</span></div><div id="eventList" class="event-list"></div><button id="loadMore" class="load-more"></button></section><div class="method">绿色虚线为其他地点，红色点线为人物；均可点击跳转。<br>计数口径：${esc(data.meta.counting_rule)} 事件口径：${esc(data.meta.event_rule)}</div>`;renderEvents(l);$("loadMore").onclick=()=>{state.shown+=100;renderEvents(l)};$("chapterChart").onclick=e=>{const bar=e.target.closest(".bar.hit");if(bar)toggleChapter(l,Number(bar.dataset.chapter))};$("eventList").onclick=e=>{const link=e.target.closest("[data-place]");if(link)jumpToLocation(link.dataset.place)};if(innerWidth<821)$("profile").scrollIntoView({behavior:"smooth",block:"start"})}
$("places").addEventListener("click",e=>{const b=e.target.closest("[data-name]");if(b)selectLocation(b.dataset.name)});["search","type","sort"].forEach(id=>$(id).addEventListener(id==="search"?"input":"change",applyFilters));applyFilters();const requested=decodeURIComponent(location.hash.slice(1));if(data.locations.some(l=>l.name===requested))selectLocation(requested);
</script></body></html>"""
    return template.replace("__DATA__", data).replace("__PEOPLE__", people)


def main():
    DATA_DIR.mkdir(exist_ok=True)
    chapters = read_chapters()
    corpus = "\n".join(chapter["text"] for chapter in chapters)
    character_data = json.loads(CHARACTER_DATA.read_text(encoding="utf-8"))
    aliases_by_name, alias_to_canonical = discover_locations(corpus, character_data)
    locations = extract_locations(chapters, aliases_by_name, alias_to_canonical)
    payload = build_payload(chapters, locations)
    OUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    OUT_HTML.write_text(render_html(payload, character_data), encoding="utf-8")
    print(
        f"Done: {len(chapters)} chapters, {len(locations)} locations, "
        f"{payload['meta']['mention_count']} mentions, "
        f"{payload['meta']['event_count']} events"
    )
    print("Location data and standalone HTML written successfully.")


if __name__ == "__main__":
    main()
