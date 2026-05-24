# processed/topics 数据说明

`processed/topics/` 保存按专题整理后的预处理语料产物，供检索、切分和后续知识库构建使用。为减小仓库体积，核心 JSONL / JSON 文件可以只保留对应的 `.gz` 压缩版本。

## 目录中的主要文件

- `documents.jsonl.gz`：文档级元数据清单。
- `chunks.jsonl.gz`：全量切块语料。
- `01-中医食疗_chunks.jsonl.gz` ~ `07-中医体质调养_chunks.jsonl.gz`：按专题拆分的切块语料。
- `qc_report.json.gz`：构建时生成的质量检查结果。
- `cleaned/`：清洗后的原始文本副本，由 `scripts/build_topic_corpus.py` 生成。

如果目录中已经存在同名未压缩文件，例如 `documents.jsonl`，说明这些压缩包已经被解压过一次。

## 如何解压

在仓库根目录执行：

```bash
python3 scripts/decompress_topic_corpus.py
```

默认会递归扫描 `processed/topics/` 下的所有 `.gz` 文件，并把解压结果写回压缩包旁边：

- `documents.jsonl.gz` -> `documents.jsonl`
- `chunks.jsonl.gz` -> `chunks.jsonl`
- `qc_report.json.gz` -> `qc_report.json`

如果目标文件已经存在，脚本默认跳过，不会覆盖。

如需强制覆盖：

```bash
python3 scripts/decompress_topic_corpus.py --force
```

如需解压其他目录，也可以显式传入路径：

```bash
python3 scripts/decompress_topic_corpus.py /absolute/path/to/processed/topics
```

## 如何压缩

在仓库根目录执行：

```bash
python3 scripts/compress_topic_corpus.py
```

默认会递归扫描 `processed/topics/` 下的 `.jsonl` 与 `.json` 文件，并在原文件旁生成对应压缩包：

- `documents.jsonl` -> `documents.jsonl.gz`
- `chunks.jsonl` -> `chunks.jsonl.gz`
- `qc_report.json` -> `qc_report.json.gz`

脚本只处理 `.jsonl` 与 `.json`，不会压缩 `cleaned/` 里的 `.txt` 文件。

如果目标压缩包已经存在，脚本默认跳过，不会覆盖。

如需强制覆盖：

```bash
python3 scripts/compress_topic_corpus.py --force
```

如需压缩其他目录，也可以显式传入路径：

```bash
python3 scripts/compress_topic_corpus.py /absolute/path/to/processed/topics
```

## 如何重新生成

如需从 `原文/` 和 `专题细分/` 重新构建这些产物，请执行：

```bash
python3 scripts/build_topic_corpus.py
```
