# tieban-liuqin

> 铁板神数「六亲」推算方法的**复现**与**可信度审计**工具。
> 它复现这套算法里可以算的部分，也把它"为什么显得准"算清楚。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-SKILL.md-green)](SKILL.md)
[![Python](https://img.shields.io/badge/Python-3.8%2B%20%C2%B7%20stdlib%20only-blue)](scripts/tieban.py)

---

## 它是什么

铁板神数是一套把**出生时刻**映射到**条文编号**、再查表输出断语的检索系统。它在"六亲生肖"上以"准得可怕"著称。

本仓库做两件事：

1. **复现**可复算的算法：干支取数、五音、出生年加数、八卦滚的取卦与变爻、条文号配对规则、以及**条文号 → 生肖的固定表**。
2. **审计**一组声称的六亲断语：它们落在什么编号空间、是否存在算术冗余、"六亲全中"究竟承载几次**独立**信息。

它**不**做预测。不批吉凶、婚期、寿数、财运、流年。

## 三个可以直接验证的结论

| # | 结论 | 证据 |
|---|---|---|
| 1 | **条文号 → 生肖 是一张固定表**：`地支序 ≡ 3 + (条文号−1151)÷10 (mod 12)`，周期 **120** | 两组独立例题 **10/10** 数据点吻合（`item-number-table.md`） |
| 2 | **凡两条条文号之差为 120 的倍数，其生肖必然相同** —— 与命主、八字无关 | 由 1 直接推演；例题中 3 处印证。例："儿子属兔（与母亲同）""女儿属牛（与兄弟同）"是**算术必然** |
| 3 | 八卦滚的第 3、4 卦取法是**錯卦（六爻全变）**，不是资料所称的"互卦" | 八条卦名 **8/8** 吻合；标准互卦取法与资料不符 |

由此得到本仓库最实用的一句：

> **"六亲全中"必须减去同余表强制的重复，才等于独立命中的次数。** 见 `audit` 子命令。

## 为什么需要它

体系自己的技术文档写着，考刻（决定刻分的那一步）的实质是 **"以果推因"**——「命理师必须以求测者**父母生肖、兄弟同胞数量**等既定且不可篡改的『客观六亲数据』作为**已知参数**」。也就是说，**六亲数据在这套流程里是输入。**

再加上刻分只有 **96 局**（8 刻 × 12 时辰）可以试，而"对不上就换一组"是公开承认的常规操作——**"六亲准"在自然使用状态下不能作为独立验证。**

这不等于证明铁板神数没有预测力。它只说明：要判定有没有，需要一次真正的对照实验。本仓库在 `references/audit.md` 给出了可执行的设计。

## 快速开始

```bash
git clone https://github.com/lklbar666/tieban-liuqin.git
cd tieban-liuqin
python scripts/selftest.py          # 19 项断言，全通过退出码 0
```

```bash
python scripts/tieban.py capability                      # 能力矩阵：哪些已复现、哪些口径待考
python scripts/tieban.py zodiac 1251                     # 条文号 → 生肖
python scripts/tieban.py zodiac-table                    # 同余表的完整统计
python scripts/tieban.py taixuan 乙丑                    # 太玄数
python scripts/tieban.py wuyin 戊                        # 年干 → 五音
python scripts/tieban.py examples                        # 复现两个公开例题
python scripts/tieban.py bagua-gun --basic 乾,坤 --verify-published
python scripts/tieban.py audit --entry "父=1950:蛇,母=1151:兔,兄弟=1251:牛,妻=1651:蛇,子=1751:兔,女=1851:牛"
```

`audit` 的输出长这样：

```
逐条核验：
  父      1950  实录 蛇  同余表预测 —  网格外：不在同一编号空间
  母      1151  实录 兔  同余表预测 兔  一致
  ...
汇总：一致 5，不一致 0，网格外 1

两两编号差与 120 周期检查：
  母 vs 子：差  600  差为 120 的倍数 → 生肖被编号表强制相同（非独立信息）
  兄弟 vs 女：差  600  差为 120 的倍数 → 生肖被编号表强制相同（非独立信息）
  ...

网格内条目出现的不同生肖：兔、牛、蛇（共 3 种）
→ 判读：6 项断语中，有 1 项不在同一编号空间、另有 2 对受同余表强制约束，
  故『六亲全中』实际只承载 3 个生肖的独立信息，不是 6 次独立命中。
```

## 已复现 / 未解

由 `capability` 子命令实时给出。要点：

**已复现**：太玄数 · 五音 · 出生年加数（上/中/下元权重）· 八卦滚取卦 · ÷9 与 ÷6 变爻 · 錯卦 · 上下卦对调 · 六条＝三数序的六个有序对 · 先天/后天八卦数序 · 条文号→生肖固定表。

**未解**（显式标 `UNRESOLVED`，不猜不补）：《八卦基本配数》表 · 八卦滚第三数序的取法 · 五音考刻表／考刻十表／五音化气表／五十气数表 · 「父」条文号的完整链路 · 条文正文库。

## 仓库结构

```text
tieban-liuqin/
├── SKILL.md                          入口（Agent 读这个）
├── README.md                         本文件
├── LICENSE                           MIT
├── scripts/
│   ├── tieban.py                     核心库与 CLI（纯标准库）
│   └── selftest.py                   19 项断言自检
├── references/
│   ├── method.md                     推算步骤
│   ├── rules.md                      判断规则与判读纪律
│   ├── item-number-table.md          条文号→生肖固定表
│   ├── examples.md                   例题与全部核查结果
│   ├── audit.md                      可信度审计与盲测设计
│   ├── sources.md                    史源、来源分级、版权说明
│   └── glossary.md                   术语表
└── assets/
    └── kaoke-loop.svg                考刻闭环示意图
```

## 用法（作为 Agent Skill）

把本仓库放到 Agent 的 skills 目录，目录名用 `tieban-liuqin`（与仓库内 `SKILL.md` 的 `name` 一致）：

```bash
REPO="https://github.com/lklbar666/tieban-liuqin.git"

# Claude Code
git clone "$REPO" ~/.claude/skills/tieban-liuqin

# OpenAI Codex CLI 及其他支持 SKILL.md 开放标准的 Agent
git clone "$REPO" ~/.agents/skills/tieban-liuqin
```

也可以直接对 Agent 说："帮我审计这组铁板神数六亲断语：父=1950:蛇，母=1151:兔……"

## 三条硬规则

1. **只做复现与审计，不做预测。**
2. **口径缺失即报 `UNRESOLVED`**，不用"通常""大概"填缝。
3. **任何输出都带确定度标注**：`[复现]` / `[有据]` / `[存疑]` / `[未解]`。

## 来源与版权

- 条文诗句出自清代道光刻本《神机妙算铁版数》系统（约 19 世纪上半叶，**已过版权保护期**），本仓库仅少量引用单句用于编号核对。
- 本仓库的叙述文字、代码与结构**均为自撰**，未复制任何现代商业教材、函授课程或收费讲义的文本。
- 所据公开材料按 A–E 五级标注来源质量（见 `references/sources.md`），并**把同源转载的多个站点计为一份证据**。
- 代码以 MIT 发布。

## 声明

本仓库不构成对铁板神数预测力的认可或否认。它只回答"这套算法在算什么"，并在需要时回答"它算得准不准——用什么方法才能知道"。涉及健康、法律、财务问题时，请以专业诊断与合规意见为准。
