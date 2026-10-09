#!/usr/bin/env python3
"""铁板神数·六亲推算复现与审计工具（纯标准库，无第三方依赖）。

本工具做三件事，且只做这三件事：
  1. 复现「可复算」的部分：干支取数、五音、八卦滚的变爻规则与条文号配对规则；
  2. 复现并校验「条文号 → 生肖」的固定对应表（本工具作者独立复算所得）；
  3. 审计一组声称的六亲断语：检查它们是否落在同一编号空间、是否存在算术冗余，
     从而判断「六亲全中」到底等于几次独立命中。

本工具不做的事：不预测吉凶，不给婚姻/财运/流年结论，不填补资料缺失的口径。
凡遇到本工具无法确定的口径，一律显式报出 UNRESOLVED，不猜、不补。

用法：
  python tieban.py zodiac 1950                # 条文号 → 生肖
  python tieban.py zodiac-table               # 条文号→生肖表的完整统计
  python tieban.py taixuan 乙丑               # 太玄数
  python tieban.py wuyin 戊                   # 年干 → 五音
  python tieban.py bagua-gun --basic 乾,坤 --seq 4410 --year 乙丑 --era 下元
  python tieban.py bagua-gun --basic 乾,坤 --verify-published   # 用公开例题校验配对规则
  python tieban.py examples                   # 复现公开例题的六亲核查（10 个数据点）
  python tieban.py audit --entry 父=1950:蛇,母=1151:兔,兄弟=1251:牛,妻=1651:蛇,子=1751:兔,女=1851:牛
  python tieban.py capability                 # 能力矩阵：哪些已复现、哪些口径待考
"""
from __future__ import annotations

import argparse
import itertools
import sys

# ---------------------------------------------------------------------------
# 基础常量
# ---------------------------------------------------------------------------
GAN = "甲乙丙丁戊己庚辛壬癸"
ZHI = "子丑寅卯辰巳午未申酉戌亥"
ZIDX = {z: i for i, z in enumerate(ZHI)}
GAN_WUXING = {"甲乙": "木", "丙丁": "火", "戊己": "土", "庚辛": "金", "壬癸": "水"}
WUXING_GAN = {g: wx for gans, wx in GAN_WUXING.items() for g in gans}

# 生肖 → 地支
SX2ZHI = {"鼠": "子", "牛": "丑", "虎": "寅", "兔": "卯", "龙": "辰", "蛇": "巳",
          "马": "午", "羊": "未", "猴": "申", "鸡": "酉", "狗": "戌", "猪": "亥"}
ZHI2SX = {v: k for k, v in SX2ZHI.items()}

# 五音配五行（宫商角徵羽 ↔ 土金木火水）
WUXING_YIN = {"土": "宫", "金": "商", "木": "角", "火": "徵", "水": "羽"}

# 太玄数：甲己子午九，乙庚丑未八，丙辛寅申七，丁壬卯酉六，戊癸辰戌五，巳亥单四数
TAIXUAN_GAN = {"甲": 9, "己": 9, "乙": 8, "庚": 8, "丙": 7, "辛": 7,
               "丁": 6, "壬": 6, "戊": 5, "癸": 5}
TAIXUAN_ZHI = {"子": 9, "午": 9, "丑": 8, "未": 8, "寅": 7, "申": 7,
               "卯": 6, "酉": 6, "辰": 5, "戌": 5, "巳": 4, "亥": 4}

# 八卦：爻序自初爻起，1 为阳、0 为阴
BAGUA = {
    "乾": (1, 1, 1), "兑": (1, 1, 0), "离": (1, 0, 1), "震": (1, 0, 0),
    "巽": (0, 1, 1), "坎": (0, 1, 0), "艮": (0, 0, 1), "坤": (0, 0, 0),
}
BAGUA_R = {v: k for k, v in BAGUA.items()}
XIANTIAN = {"乾": 1, "兑": 2, "离": 3, "震": 4, "巽": 5, "坎": 6, "艮": 7, "坤": 8}
HOUTIAN = {"坎": 1, "坤": 2, "震": 3, "巽": 4, "中": 5, "乾": 6, "兑": 7, "艮": 8, "离": 9}

# 六十四卦名（键为「上卦,下卦」）
HEX_NAME = {}
_NAMES = [
    ("乾", [("乾", "乾为天"), ("兑", "天泽履"), ("离", "天火同人"), ("震", "天雷无妄"),
            ("巽", "天风姤"), ("坎", "天水讼"), ("艮", "天山遁"), ("坤", "天地否")]),
    ("兑", [("乾", "泽天夬"), ("兑", "兑为泽"), ("离", "泽火革"), ("震", "泽雷随"),
            ("巽", "泽风大过"), ("坎", "泽水困"), ("艮", "泽山咸"), ("坤", "泽地萃")]),
    ("离", [("乾", "火天大有"), ("兑", "火泽睽"), ("离", "离为火"), ("震", "火雷噬嗑"),
            ("巽", "火风鼎"), ("坎", "火水未济"), ("艮", "火山旅"), ("坤", "火地晋")]),
    ("震", [("乾", "雷天大壮"), ("兑", "雷泽归妹"), ("离", "雷火丰"), ("震", "震为雷"),
            ("巽", "雷风恒"), ("坎", "雷水解"), ("艮", "雷山小过"), ("坤", "雷地豫")]),
    ("巽", [("乾", "风天小畜"), ("兑", "风泽中孚"), ("离", "风火家人"), ("震", "风雷益"),
            ("巽", "巽为风"), ("坎", "风水涣"), ("艮", "风山渐"), ("坤", "风地观")]),
    ("坎", [("乾", "水天需"), ("兑", "水泽节"), ("离", "水火既济"), ("震", "水雷屯"),
            ("巽", "水风井"), ("坎", "坎为水"), ("艮", "水山蹇"), ("坤", "水地比")]),
    ("艮", [("乾", "山天大畜"), ("兑", "山泽损"), ("离", "山火贲"), ("震", "山雷颐"),
            ("巽", "山风蛊"), ("坎", "山水蒙"), ("艮", "艮为山"), ("坤", "山地剥")]),
    ("坤", [("乾", "地天泰"), ("兑", "地泽临"), ("离", "地火明夷"), ("震", "地雷复"),
            ("巽", "地风升"), ("坎", "地水师"), ("艮", "地山谦"), ("坤", "坤为地")]),
]
for _up, _items in _NAMES:
    for _low, _nm in _items:
        HEX_NAME[(_up, _low)] = _nm

# 六亲 ↔ 十神（传统口径；男命/女命在配偶与子女上不同）
LIUQIN_SHISHEN = {
    "父": {"男": ["偏财"], "女": ["偏财"]},
    "母": {"男": ["正印"], "女": ["正印"]},
    "兄弟": {"男": ["比肩", "劫财"], "女": ["比肩", "劫财"]},
    "配偶": {"男": ["正财"], "女": ["正官", "七杀"]},
    "子女": {"男": ["官杀"], "女": ["食神", "伤官"]},
}

# 条文号 → 生肖 的固定表（本工具作者由公开例题独立复算所得，见 references/item-number-table.md）
ANCHOR_NO = 1151          # 锚点条文号
ANCHOR_ZHI = 3            # 锚点对应地支序（卯 = 3，子 = 0 起）
STEP = 10                 # 每 +10 条文号，地支顺行一位
PERIOD = 120              # 12 生肖 × 10 步长


# ---------------------------------------------------------------------------
# 1. 干支取数
# ---------------------------------------------------------------------------
def taixuan(gz: str) -> int:
    """太玄数：干数与支数之和。gz 形如 '乙丑'。"""
    if len(gz) != 2 or gz[0] not in TAIXUAN_GAN or gz[1] not in TAIXUAN_ZHI:
        raise ValueError(f"需要两字干支，收到 {gz!r}")
    return TAIXUAN_GAN[gz[0]] + TAIXUAN_ZHI[gz[1]]


def wuyin(gan: str) -> str:
    """年干 → 五音。土宫、金商、木角、火徵、水羽。"""
    wx = WUXING_GAN.get(gan)
    if wx is None:
        raise ValueError(f"不是天干：{gan!r}")
    return WUXING_YIN[wx]


def year_addend(gz: str, era: str, sex: str = "男") -> int:
    """出生年干支的加数（八卦滚用）。三条权重规则按上/中/下元分别给出。"""
    g, z = TAIXUAN_GAN.get(gz[0]), TAIXUAN_ZHI.get(gz[1])
    if g is None or z is None:
        raise ValueError(f"需要两字干支，收到 {gz!r}")
    if era == "上元":
        return g * 10 + z * 1
    if era == "下元":
        return z * 10 + g * 1
    if era == "中元":
        yang = GAN.index(gz[0]) % 2 == 0
        if (yang and sex == "男") or (not yang and sex == "女"):
            return g * 100 + z * 10
        return z * 100 + g * 10
    raise ValueError(f"era 需为上元/中元/下元，收到 {era!r}")


# ---------------------------------------------------------------------------
# 2. 条文号 → 生肖（固定表）
# ---------------------------------------------------------------------------
def zodiac(item_no: int):
    """条文号 → (地支, 生肖)。不在同余网格上时返回 None, None。"""
    d = item_no - ANCHOR_NO
    if d % STEP:
        return None, None
    z = ZHI[(ANCHOR_ZHI + d // STEP) % 12]
    return z, ZHI2SX[z]


def numbers_for(zhi: str, within: int = 12000):
    """给定地支，列出条文库中所有属于该生肖的条文号。"""
    if zhi not in ZIDX:
        raise ValueError(f"不是地支：{zhi!r}")
    out = []
    k = (ZIDX[zhi] - ANCHOR_ZHI) % 12
    n = ANCHOR_NO + k * STEP
    while n <= within:
        out.append(n)
        n += PERIOD
    return out


def table_stats():
    """条文号→生肖表的统计：周期、每生肖条数、常见误区。"""
    within = 12000
    grid = [n for n in range(1, within + 1) if (n - ANCHOR_NO) % STEP == 0]
    per = {}
    for n in grid:
        _, sx = zodiac(n)
        per.setdefault(sx, []).append(n)
    return {
        "条文库上限": within,
        "落在同余网格上的条文数": len(grid),
        "格上每条对应生肖": True,
        "周期": PERIOD,
        "每生肖条数（在网格内）": {k: len(v) for k, v in sorted(per.items())},
        "非格条文": within - len(grid),
    }


# ---------------------------------------------------------------------------
# 3. 八卦滚
# ---------------------------------------------------------------------------
def hexagram(basic_upper: str, basic_lower: str):
    """基本卦 → 六爻元组（自初爻起）。"""
    if basic_upper not in BAGUA or basic_lower not in BAGUA:
        raise ValueError("上卦/下卦需为八卦名之一")
    return BAGUA[basic_lower] + BAGUA[basic_upper]


def split(y: tuple):
    """六爻 → (上卦名, 下卦名)。"""
    return BAGUA_R[y[3:]], BAGUA_R[y[:3]]


def roll_first(y: tuple):
    """二三四爻为内卦、三四五爻为外卦 → 八卦滚第一卦。"""
    inner = (y[1], y[2], y[3])
    outer = (y[2], y[3], y[4])
    return inner + outer


def interlock(y: tuple):
    """錯卦：六爻全变。

    注：所据资料把第 3、4 卦称作「互卦」，但按其六爻结构复算，取法实为
    **錯卦（六爻全变）**——8/8 卦名吻合；标准互卦取法（二三四 / 三四五）
   与资料所列不符。本工具从复算结果，并保留此注以便复核。
    """
    return tuple(1 - b for b in y)


def swap(y: tuple):
    """上下卦对调。"""
    return y[3:] + y[:3]


def name_of(y: tuple) -> str:
    up, low = split(y)
    return HEX_NAME[(up, low)]


def gun8(basic_upper: str, basic_lower: str, basic_seq: int, addend: int):
    """完整八卦滚：基本卦 + 基本数序 + 加数 → 八卦。"""
    y0 = hexagram(basic_upper, basic_lower)
    total = basic_seq + addend
    r9, r6 = total % 9, total % 6
    g1 = roll_first(y0)
    g2 = flip(g1, CHANGE_BY_9[r9])
    g3 = interlock(g1)
    g4 = interlock(g2)
    g5 = swap(flip(g1, CHANGE_BY_6[r6]))
    g6 = swap(flip(g2, CHANGE_BY_6[r6]))
    g7 = swap(flip(g3, CHANGE_BY_6[r6]))
    g8 = swap(flip(g4, CHANGE_BY_6[r6]))
    return dict(和=total, r9=r9, r6=r6, 变爻9=CHANGE_BY_9[r9], 变爻6=CHANGE_BY_6[r6],
                卦=[g1, g2, g3, g4, g5, g6, g7, g8])


def flip(y: tuple, positions):
    """按 1 起的爻位翻转。"""
    y = list(y)
    for p in positions:
        y[p - 1] ^= 1
    return tuple(y)


CHANGE_BY_9 = {1: [1], 2: [2], 3: [3], 4: [4], 5: [5], 6: [6],
               7: [1, 4], 8: [2, 5], 0: [3, 6]}
CHANGE_BY_6 = {1: [1], 2: [2], 3: [3], 4: [4], 5: [5], 0: [6]}


def bagua_gun(basic_upper: str, basic_lower: str, basic_seq: int,
              addend: int, third_seq=None):
    """八卦滚：输出八条卦、各自数序，以及可由数序导出的条文号。

    third_seq：每卦的「第三个数序」取法在所据资料中未能确定（见 capability）。
    仅当调用方显式传入（单值或长度 8 的序列）时，才产出该卦的 6 条条文号；
    否则显式标 UNRESOLVED，不猜补。
    """
    r = gun8(basic_upper, basic_lower, basic_seq, addend)
    out = {k: r[k] for k in ("和", "r9", "r6", "变爻9", "变爻6")}
    out["基本卦"] = HEX_NAME[(basic_upper, basic_lower)]
    out["基本数序"] = basic_seq
    out["加数"] = addend
    seqs = None
    if third_seq is not None:
        seqs = [third_seq] * 8 if isinstance(third_seq, int) else list(third_seq)
    rows = []
    for i, y in enumerate(r["卦"], 1):
        up, low = split(y)
        x, h = f"{XIANTIAN[up]}{XIANTIAN[low]}", f"{HOUTIAN[up]}{HOUTIAN[low]}"
        t = seqs[i - 1] if seqs else None
        row = {"序": i, "卦名": HEX_NAME[(up, low)], "上卦": up, "下卦": low,
               "先天数序": x, "后天数序": h, "第三数序": t}
        row["条文号"] = combine6([int(x), int(h), int(t)]) if t else None
        rows.append(row)
    out["八卦"] = rows
    return out


def print_gun(out):
    print(f"  基本卦 {out['基本卦']}  基本数序 {out['基本数序']}  "
          f"加数 {out['加数']}  和 {out['和']}")
    print(f"  ÷9 余 {out['r9']} → 变爻 {out['变爻9']}；÷6 余 {out['r6']} → 变爻 {out['变爻6']}")
    print(f"  {'序':<3}{'卦名':<10}{'上/下':<10}{'先天':<6}{'后天':<6}{'第三':<6}条文号")
    for r in out["八卦"]:
        nums = "、".join(str(n) for n in r["条文号"]) if r["条文号"] else "UNRESOLVED（缺第三数序）"
        print(f"  {r['序']:<3}{r['卦名']:<10}{r['上卦']+'/'+r['下卦']:<10}"
              f"{r['先天数序']:<6}{r['后天数序']:<6}{r['第三数序'] or '—':<6}{nums}")


def combine6(nums):
    """三个数序 → 六个条文号（全部有序对，a×100+b）。"""
    nums = [int(n) for n in nums]
    return [a * 100 + b for a, b in itertools.permutations(nums, 2)]


# 公开例题的 8 卦数序（先天 / 第三数序 / 后天）。第三数序为原资料直接给出；
# 其取法本工具未能确定，此处仅作「配对规则」的校验夹具。
PUBLISHED_8 = [
    ("風山漸", 57, 26, 48), ("天火同人", 13, 93, 69), ("雷澤歸妹", 42, 84, 37),
    ("地水師", 86, 17, 21), ("山天大畜", 71, 69, 86), ("火風鼎", 35, 32, 94),
    ("澤地萃", 28, 41, 72), ("水雷屯", 64, 78, 13),
]
PUBLISHED_NUMBERS = [
    5726, 5748, 2657, 2648, 4857, 5726,   # 漸：第 6 条应为 4826（资料排印为 5726，重复）
    1393, 1369, 9313, 9369, 6913, 6993,
    4284, 4237, 8442, 8437, 3742, 3784,
    8617, 8621, 1786, 1721, 2186, 2117,
    7169, 7186, 6971, 6986, 8671, 8669,
    3532, 3594, 3235, 3294, 9435, 9432,
    2841, 2872, 4128, 4172, 7228, 7241,
    6478, 6413, 7864, 7813, 6478, 1378,   # 屯：第 5 条应为 1364（资料排印为 6478，重复）
]


PUBLISHED_8_GUA = ["风山渐", "天火同人", "雷泽归妹", "地水师",
                   "山天大畜", "火风鼎", "泽地萃", "水雷屯"]


def verify_hex_names(verbose=True):
    """校验八卦滚的八条卦名是否与公开例题一致（天地否 + 4410 + 乙丑·下元）。"""
    r = gun8("乾", "坤", 4410, year_addend("乙丑", "下元"))
    mine = [name_of(y) for y in r["卦"]]
    hit = sum(1 for a, b in zip(mine, PUBLISHED_8_GUA) if a == b)
    if verbose:
        print(f"八卦滚卦名校验：{hit}/{len(mine)} 与公开例题一致")
        for i, (a, b) in enumerate(zip(mine, PUBLISHED_8_GUA), 1):
            print(f"  第{i}卦 {a:<8}{'✓' if a == b else '✗ 资料作 ' + b}")
        print("→ 第3、4卦的取法实为錯卦（六爻全变），非标准互卦；此点已更正。")
    return hit, mine


def verify_published(verbose=True):
    """用公开例题校验「六条＝三数序的六个有序对」这条规则。"""
    mine = []
    for _, a, b, c in PUBLISHED_8:
        mine += combine6([a, b, c])
    hit = sum(1 for x, y in zip(mine, PUBLISHED_NUMBERS) if x == y)
    mismatch = [(i + 1, m, p) for i, (m, p) in enumerate(zip(mine, PUBLISHED_NUMBERS)) if m != p]
    if verbose:
        print(f"配对规则校验：{hit}/{len(mine)} 条与公开资料一致")
        for i, m, p in mismatch:
            print(f"  第 {i} 条：按规则应为 {m}，资料印作 {p} → 判定为资料排印重复/错误")
        print(f"→ 规则本身 {len(mine) - len(mismatch)}/{len(mine)} 成立；"
              f"其余 {len(mismatch)} 条为资料转录错误")
    return hit, mismatch


# ---------------------------------------------------------------------------
# 4. 例题复现
# ---------------------------------------------------------------------------
EXAMPLES = [
    ("例1", "乾造 1988-08-19 辰时（戊辰 辛酉 丁亥 甲辰）",
     [("父", 1950, "蛇"), ("母", 1151, "兔"), ("兄弟", 1251, "牛"),
      ("妻", 1651, "蛇"), ("子", 1751, "兔"), ("女", 1851, "牛")]),
    ("例2", "乾造（甲子 丁卯 丙辰 癸巳）",
     [("父", 1920, "虎"), ("母", 1171, "蛇"), ("兄弟", 1251, "牛"),
      ("妻", 1611, "牛"), ("长子", 1741, "虎"), ("次子", 1751, "兔")]),
]


def run_examples(verbose=True):
    ok = miss = grid_out = 0
    rows = []
    for case, desc, entries in EXAMPLES:
        for who, n, real in entries:
            z, sx = zodiac(n)
            if z is None:
                verdict = "网格外（父走『气数＋卦数』路径）"
                grid_out += 1
            elif sx == real:
                verdict = "一致"
                ok += 1
            else:
                verdict = "不一致"
                miss += 1
            rows.append((case, desc, who, n, real, sx, verdict))
    if verbose:
        for case, _, who, n, real, sx, verdict in rows:
            print(f"  {case} {who:<4} 条文号 {n:>5}  实录 {real}  预测 {sx or '—'}  {verdict}")
        print(f"\n同余网格内：{ok}/{ok + miss} 一致，{miss} 不一致；网格外 {grid_out} 条（父）")
    return ok, miss, grid_out


# ---------------------------------------------------------------------------
# 5. 六亲断语审计（本工具的主要用途）
# ---------------------------------------------------------------------------
def audit(entries):
    """entries: [(亲, 条文号, 生肖), ...]

    返回：同余表一致性、差值冗余、以及「六亲全中等于几次独立命中」的结论。
    """
    rep = {"逐条": [], "一致": 0, "不一致": 0, "网格外": 0, "位差": [], "冗余对": []}
    for who, n, real in entries:
        z, sx = zodiac(n)
        if z is None:
            rep["网格外"] += 1
            rep["逐条"].append((who, n, real, None, "网格外：不在同一编号空间"))
        else:
            same = sx == real
            rep["一致" if same else "不一致"] += 1
            rep["逐条"].append((who, n, real, sx, "一致" if same else "不一致"))
    grid = [(w, n, s) for w, n, s in entries if (n - ANCHOR_NO) % STEP == 0]
    for (w1, n1, _), (w2, n2, _) in itertools.combinations(grid, 2):
        d = abs(n2 - n1)
        rep["位差"].append((w1, w2, d, d % PERIOD == 0))
        if d % PERIOD == 0:
            rep["冗余对"].append((w1, w2, d))
    n_eff = None
    if grid:
        # 每条的生肖由同余表完全决定；被表强制相同的条目不再提供额外信息。
        # 故「等效独立命中数」＝网格内条目中出现的不同生肖个数。
        n_eff = len({zodiac(n)[1] for _, n, _ in grid})
        rep["不同生肖"] = sorted({zodiac(n)[1] for _, n, _ in grid})
    rep["等效独立命中数"] = n_eff
    return rep


def print_audit(rep):
    print("逐条核验：")
    for who, n, real, pred, verdict in rep["逐条"]:
        print(f"  {who:<4} {n:>6}  实录 {real}  同余表预测 {pred or '—'}  {verdict}")
    print(f"\n汇总：一致 {rep['一致']}，不一致 {rep['不一致']}，网格外 {rep['网格外']}")
    if rep["位差"]:
        print("\n两两编号差与 120 周期检查：")
        for w1, w2, d, red in rep["位差"]:
            tag = "差为 120 的倍数 → 生肖被编号表强制相同（非独立信息）" if red else "无强制关系"
            print(f"  {w1} vs {w2}：差 {d:>4}  {tag}")
    if rep["等效独立命中数"] is not None:
        print(f"\n网格内条目出现的不同生肖：{'、'.join(rep['不同生肖'])}"
              f"（共 {rep['等效独立命中数']} 种）")
        print(f"→ 判读：{len(rep['逐条'])} 项断语中，有 {rep['网格外']} 项不在同一编号空间、"
              f"另有 {len(rep['冗余对'])} 对受同余表强制约束，"
              f"故『六亲全中』实际只承载 {rep['等效独立命中数']} 个生肖的独立信息，"
              f"不是 {len(rep['逐条'])} 次独立命中。")


# ---------------------------------------------------------------------------
# 6. 能力矩阵
# ---------------------------------------------------------------------------
CAPABILITY = [
    ("干支太玄数", "复现", "由公开例题验证：乙丑 → 乙8 + 丑8 = 16（例中加数为 80+8）"),
    ("五音（年干起）", "复现", "宫商角徵羽 ↔ 土金木火水，与例题『年干戊土入宫音』一致"),
    ("出生年加数（上/中/下元权重）", "复现", "下元规则经例题验证（乙丑 → 支×10 + 干×1 = 88）"),
    ("八卦滚：二三四/三四五取卦", "复现", "由例题验证：天地否 → 風山漸"),
    ("八卦滚：÷9 取余定变爻", "复现", "4498 ÷ 9 余 7 → 初爻与四爻同变，与例题一致"),
    ("八卦滚：÷6 取余定变爻", "复现", "4498 ÷ 6 余 4 → 四爻变，与例题一致"),
    ("八卦滚：六条＝三数序的六个有序对", "复现", "48 条中 46 条吻合，2 条为资料排印错误"),
    ("先天/后天八卦数序", "复现", "先天 8/8 吻合；后天 7/8（第 8 例经有序对数据反证为 OCR 错误）"),
    ("八卦滚：第三、第四卦", "复现", "资料称「互卦」，复算为**錯卦（六爻全变）**，8/8 卦名吻合（口径更正）"),
    ("八卦滚：第五至第八卦", "复现", "÷6 变爻后上下卦对调，4/4 与例题一致"),
    ("条文号 → 生肖 固定表", "复现", "同余式在两组例题 10 个数据点上 10/10 命中"),
    ("《八卦基本配数》表", "UNRESOLVED", "仅由例题得 天地否 = 4410 一例，无表可复原，需外部输入 basic_seq"),
    ("八卦滚第三数序的取法", "UNRESOLVED", "资料逐例给出数值但未给规则；本工具只校验配对规则，不猜规则"),
    ("五音考刻表 / 考刻十表 / 五音化气表 / 五十气数表", "UNRESOLVED", "四张表均未获，无法复原『父』条文号的完整链路"),
    ("条文正文（12000 条）", "未纳入", "本工具不含条文库正文；条文按编号查书"),
    ("吉凶流年推演", "不提供", "本工具不做预测，仅做复现与审计"),
]


def print_capability():
    print(f"{'项目':<34}{'状态':<12}说明")
    print("-" * 100)
    for name, status, note in CAPABILITY:
        print(f"{name:<34}{status:<12}{note}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_entry(s):
    """'父=1950:蛇' → ('父', 1950, '蛇')"""
    left, _, real = s.partition(":")
    who, _, no = left.partition("=")
    return who.strip(), int(no), real.strip()


def main(argv=None):
    ap = argparse.ArgumentParser(description="铁板神数·六亲推算复现与审计工具")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("zodiac", help="条文号 → 生肖")
    p.add_argument("item_no", type=int)

    sub.add_parser("zodiac-table", help="条文号→生肖表统计")
    p = sub.add_parser("taixuan", help="太玄数")
    p.add_argument("gz")

    p = sub.add_parser("wuyin", help="年干 → 五音")
    p.add_argument("gan")

    p = sub.add_parser("bagua-gun", help="八卦滚")
    p.add_argument("--basic", required=True, help="上卦,下卦，如 乾,坤")
    p.add_argument("--seq", type=int, help="基本数序（查《八卦基本配数》，如 4410）")
    p.add_argument("--year", help="出生年干支，如 乙丑")
    p.add_argument("--era", default="下元", choices=["上元", "中元", "下元"])
    p.add_argument("--sex", default="男", choices=["男", "女"])
    p.add_argument("--third", type=int, help="第三数序（口径待考，显式传入时才产出条文号）")
    p.add_argument("--verify-published", action="store_true")

    sub.add_parser("examples", help="复现公开例题的六亲核查")

    p = sub.add_parser("audit", help="审计一组六亲断语")
    p.add_argument("--entry", required=True, help="逗号分隔，如 父=1950:蛇,母=1151:兔")

    sub.add_parser("capability", help="能力矩阵")

    a = ap.parse_args(argv)

    if a.cmd == "zodiac":
        z, sx = zodiac(a.item_no)
        print(f"{a.item_no} → {z or 'UNRESOLVED'}（{sx or '不在同余网格上'}）")
    elif a.cmd == "zodiac-table":
        st = table_stats()
        for k, v in st.items():
            print(f"{k}：{v}")
        print(f"\n→ 周期 {PERIOD} 意味着：凡两条条文号之差为 120 的倍数，其生肖必然相同。")
    elif a.cmd == "taixuan":
        print(f"{a.gz} → {taixuan(a.gz)}（干 {TAIXUAN_GAN.get(a.gz[0])} + 支 {TAIXUAN_ZHI.get(a.gz[1])}）")
    elif a.cmd == "wuyin":
        wx = WUXING_GAN[a.gan]
        print(f"年干 {a.gan}（{wx}）→ 五音「{wuyin(a.gan)}」")
    elif a.cmd == "bagua-gun":
        up, low = [x.strip() for x in a.basic.split(",")]
        if a.verify_published:
            print("【① 八卦滚卦名校验】以 天地否 + 4410 + 乙丑（下元）为例")
            verify_hex_names()
            print("\n【② 条文号配对规则校验】以公开例题的 8 卦数序为夹具")
            verify_published()
            print("\n【③ 完整输出】基本卦 天地否 + 基本数序 4410 + 乙丑（下元）")
            print("    夹具：第三数序取自公开资料（其取法本工具未能确定，仅作演示）")
            add = year_addend("乙丑", "下元")
            print_gun(bagua_gun("乾", "坤", 4410, add,
                                third_seq=[x[2] for x in PUBLISHED_8]))
            print("\n    对照：以上 48 条条文号与公开资料的差别，即【②】中列出的 2 处转录错误。")
        else:
            if a.seq is None or a.year is None:
                sys.exit("需同时提供 --seq 与 --year（或用 --verify-published）")
            add = year_addend(a.year, a.era, a.sex)
            third = a.third
            print_gun(bagua_gun(up, low, a.seq, add, third_seq=third))
    elif a.cmd == "examples":
        print("【公开例题六亲核查】")
        run_examples()
        print("\n说明：两组例题的『父』均落在同余网格之外，走『气数＋卦数』路径，")
        print("故本表的适用域是除『父』以外的亲位。")
    elif a.cmd == "audit":
        entries = [parse_entry(s) for s in a.entry.split(",") if s.strip()]
        print_audit(audit(entries))
    elif a.cmd == "capability":
        print_capability()


if __name__ == "__main__":
    main()
