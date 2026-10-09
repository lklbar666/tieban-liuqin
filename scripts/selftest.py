#!/usr/bin/env python3
"""自检：本工具所有「复现」级结论的断言化测试。全部通过时退出码 0。

用法：python selftest.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tieban as T  # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}{(' — ' + detail) if detail else ''}")
    if not cond:
        FAILS.append(name)


print("=== 1. 干支取数 ===")
check("太玄数 乙丑 = 8+8 = 16", T.taixuan("乙丑") == 16)
check("太玄数 甲子 = 9+9 = 18", T.taixuan("甲子") == 18)
check("五音：年干戊（土）→ 宫", T.wuyin("戊") == "宫")
check("五音：年干庚（金）→ 商", T.wuyin("庚") == "商")
check("加数 乙丑·下元 = 8×10 + 8×1 = 88", T.year_addend("乙丑", "下元") == 88)

print("\n=== 2. 条文号 → 生肖 固定表 ===")
ok, miss, out = T.run_examples(verbose=False)
check("公开例题同余网格内 10/10 命中", ok == 10 and miss == 0, f"{ok}/10")
check("两组例题的『父』均落在网格外", out == 2)
check("周期为 120", T.PERIOD == 120)
check("zodiac(1151) = 卯/兔", T.zodiac(1151) == ("卯", "兔"))
check("zodiac(1751) = 卯/兔（与 1151 同生肖，差 600 = 5×120）", T.zodiac(1751) == ("卯", "兔"))
check("zodiac(1950) 落在网格外", T.zodiac(1950) == (None, None))
nums = T.numbers_for("卯")
check("卯对应条文号数量与 120 周期一致",
      len(nums) > 5 and all((b - a) == 120 for a, b in zip(nums, nums[1:])))

print("\n=== 3. 八卦滚 ===")
h, mine = T.verify_hex_names(verbose=False)
check("八卦滚八条卦名 8/8 与公开例题一致", h == 8, "、".join(mine))
r = T.gun8("乾", "坤", 4410, 88)
check("和 = 4410 + 88 = 4498", r["和"] == 4498)
check("÷9 余 7 → 变爻 初、四", r["r9"] == 7 and r["变爻9"] == [1, 4])
check("÷6 余 4 → 变爻 四", r["r6"] == 4 and r["变爻6"] == [4])
check("第 3、4 卦为第 1、2 卦的錯卦（六爻全变）",
      r["卦"][2] == tuple(1 - b for b in r["卦"][0]) and
      r["卦"][3] == tuple(1 - b for b in r["卦"][1]))
hit, mism = T.verify_published(verbose=False)
check("条文号配对规则 46/48 吻合（2 处为资料转录错误）", hit == 46 and len(mism) == 2)
check("六条＝三数序的全部有序对", sorted(T.combine6([57, 48, 26])) ==
      sorted([5748, 5726, 4857, 4826, 2657, 2648]))

print("\n=== 4. 审计 ===")
rep = T.audit([("父", 1950, "蛇"), ("母", 1151, "兔"), ("兄弟", 1251, "牛"),
               ("妻", 1651, "蛇"), ("子", 1751, "兔"), ("女", 1851, "牛")])
check("审计：网格外 1 项（父）", rep["网格外"] == 1)
check("审计：冗余对 2 对（母–子、兄弟–女，差 600）", len(rep["冗余对"]) == 2)
check("审计：等效独立命中数 = 3 种生肖", rep["等效独立命中数"] == 3)

print(f"\n{'全部通过' if not FAILS else '失败项：' + '、'.join(FAILS)}")
sys.exit(1 if FAILS else 0)
