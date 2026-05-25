# TCM-Ancient-Books

中医古籍 OCR 文本与专题整理仓库，面向知识检索、专题语料整理与健康管理相关知识库构建。

本仓库当前包含：

- 约 708 本中医古籍 OCR 文本，按书名拼音首字母归档在 `原文/`。
- 7 个面向现代应用场景的专题目录，便于按主题浏览、筛选和构建知识库。
- 可直接用于检索、切块和语料加工的 `processed/topics/` 预处理产物。

## 快速导航

- [BOOK_INDEX_AZ.md](BOOK_INDEX_AZ.md) —— 全量书目 A-Z 索引，可直接定位到 `原文/` 下对应文本。
- [BOOK_CLASSIFICATION.md](BOOK_CLASSIFICATION.md) —— 全量书目粗分类总览。
- [TOPIC_SUBDIVISION.md](TOPIC_SUBDIVISION.md) —— 专题候选与精选清单。
- [专题细分/README.md](专题细分/README.md) —— 7 个专题目录及其当前收录文件。
- [中医体质分类与判定.md](中医体质分类与判定.md) —— 基于 GB/T 46939-2025 整理的体质分类与判定说明。
- [processed/topics/README.md](processed/topics/README.md) —— 预处理语料、压缩包与脚本使用说明。

## 仓库结构

```text
.
├── README.md
├── BOOK_CLASSIFICATION.md         # 全量书目初步分类
├── BOOK_INDEX_AZ.md               # 全量书目 A-Z 索引
├── TOPIC_SUBDIVISION.md           # 专题细分索引
├── 中医体质分类与判定.md            # 体质分类与判定说明
├── 原文/                           # 全量 OCR 文本
│   ├── A/
│   ├── B/
│   ├── ...
│   ├── Z/
│   └── #/
├── 专题细分/
│   ├── README.md                  # 专题目录说明
│   ├── 01-中医食疗/
│   ├── 02-穴位应用/
│   ├── 03-中医运动/
│   ├── 04-作息与情绪管理/
│   ├── 05-慢病管理/
│   ├── 06-体重管理/
│   └── 07-中医体质调养/
├── processed/
│   └── topics/                    # 预处理后的专题语料产物
└── scripts/
    ├── build_topic_corpus.py
    ├── compress_topic_corpus.py
    └── decompress_topic_corpus.py
```

## 专题概览

| 专题 | 数量 | 说明 |
|---|---:|---|
| 01-中医食疗 | 48 | 食疗、饮膳、本草与饮食宜忌相关文本。 |
| 02-穴位应用 | 38 | 针灸、经络、经穴、刺灸与穴位歌赋相关文本。 |
| 03-中医运动 | 10 | 导引、按摩、推拿、易筋洗髓等身体练习相关文本。 |
| 04-作息与情绪管理 | 25 | 养生、起居作息、心性调摄与情志相关文本。 |
| 05-慢病管理 | 79 | 消渴、中风、虚劳、脾胃、痰湿、医案验案等相关文本。 |
| 06-体重管理 | 22 | 饮食、脾胃、痰湿、导引按摩等可映射到体重管理的文本。 |
| 07-中医体质调养 | 10 | 以国标体质分类为主线整理的体质调养相关资料。 |

## 如何使用

### 1. 浏览原始古籍

如果你想查找具体书目或直接阅读 OCR 文本，建议按下面的顺序使用：

1. 先看 [BOOK_INDEX_AZ.md](BOOK_INDEX_AZ.md) 按书名定位。
2. 再进入 `原文/` 查看对应文本。
3. 如需按类别而不是按书名浏览，可看 [BOOK_CLASSIFICATION.md](BOOK_CLASSIFICATION.md)。

### 2. 按专题筛选资料

如果你更关心具体应用场景，例如食疗、穴位、慢病管理或体质调养：

1. 先看 [TOPIC_SUBDIVISION.md](TOPIC_SUBDIVISION.md) 了解专题划分逻辑。
2. 再看 [专题细分/README.md](专题细分/README.md) 查看每个专题当前实际收录的文本。
3. 最后进入 `专题细分/` 下对应目录浏览专题文本。

### 3. 使用预处理语料

`processed/topics/` 中保存了按专题整理后的预处理产物，适合后续检索、切块、嵌入、知识库构建等用途。

常用命令：

```bash
python3 scripts/decompress_topic_corpus.py
python3 scripts/build_topic_corpus.py
python3 scripts/compress_topic_corpus.py
```

更多说明见 [processed/topics/README.md](processed/topics/README.md)。

## 数据说明

- `原文/` 保留全量 OCR 文本，是仓库中的基础数据层。
- `专题细分/` 按主题整理精选文本，适合直接用于专题阅读和知识抽取。
- `processed/topics/` 提供进一步清洗、切块和质检后的语料产物。
- `中医体质分类与判定.md` 是围绕体质分类标准整理的结构化说明文档。

## 注意

- OCR 文本可能存在错字、缺段、残本、异体字或版本不明等问题，严肃引用前需要人工校对。
- 专题划分服务于知识整理与检索，不等同于传统文献学意义上的严格学术分类。
- 仓库内容适合用于知识库、检索和健康管理相关场景，不替代临床诊断或专业医疗意见。

## 鸣谢

- 本项目大部分书籍来自 [ZouJiu1/TCM-Ancient-Books](https://github.com/ZouJiu1/TCM-Ancient-Books)，特此致谢。
