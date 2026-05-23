#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
TOPIC_DIR = ROOT / "专题细分"
SOURCE_DIR = ROOT / "原文"
OUTPUT_DIR = ROOT / "processed" / "topics"
CLEANED_DIR = OUTPUT_DIR / "cleaned"
STRUCTURED_REFERENCE = "中医体质分类与判定.md"

TOPIC_DIR_RE = re.compile(r"^\d{2}-.+")
STRUCTURED_SECTION_RE = re.compile(r"^(.+?)\s*\(([A-I])型\)\s*$")
STRUCTURED_FIELD_RE = re.compile(
    r"^(总体特征|形体特征|常见表现|心理特征|发病倾向|对外界环境适应能力)：(.*)$"
)
NON_PRINTABLE_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
BMP_PLACEHOLDER_RE = re.compile(r"\\p[^\s\\]*?\.bmp")
LITERAL_ESCAPE_RE = re.compile(r"\\[xrtn]")
MULTI_BLANK_RE = re.compile(r"\n{3,}")
ENUM_RE = re.compile(r"^[（(][一二三四五六七八九十百千0-9]+[）)]")
VOLUME_RE = re.compile(r"^卷[上中下前后首末一二三四五六七八九十百零〇0-9]")
META_RE = re.compile(r"^(书名|作者|朝代|年份)：\s*(.*)$")
SECTION_MARKERS = ("<篇名>", "<目录>", "书名：", "作者：", "朝代：", "年份：", "内容：", "属性：")
MAX_CHARS = 900
OVERLAP_UNITS = 0


@dataclass
class CleanResult:
    text: str
    stats: Counter
    flags: set[str]


@dataclass
class Section:
    title: str
    path: list[str]
    text: str


@dataclass
class StructuredChunk:
    title: str
    code: str
    fields: dict[str, str]
    text: str


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)

    source_index, duplicate_sources = build_source_index()
    topic_map, topic_file_count = build_topic_map()

    documents: list[dict] = []
    chunks: list[dict] = []
    chunks_by_topic: dict[str, list[dict]] = defaultdict(list)
    qc = {
        "topic_file_count": topic_file_count,
        "duplicate_source_filenames": {k: sorted(v) for k, v in duplicate_sources.items()},
        "unmatched_topic_files": [],
        "cleaning_totals": Counter(),
        "missing_author_count": 0,
        "missing_dynasty_count": 0,
        "missing_year_count": 0,
        "doc_type_counts": Counter(),
    }

    for filename in sorted(topic_map):
        topics = sorted(topic_map[filename])
        source_path = source_index.get(filename)
        source_origin = "source"
        if source_path is None:
            fallback_path = locate_topic_copy(filename)
            if fallback_path is None:
                qc["unmatched_topic_files"].append(filename)
                continue
            source_path = fallback_path
            source_origin = "topic_fallback"

        raw_text = source_path.read_text(encoding="utf-8", errors="ignore")
        clean_result = clean_ocr_text(raw_text)
        cleaned_path = CLEANED_DIR / filename
        cleaned_path.write_text(clean_result.text, encoding="utf-8")

        metadata = extract_metadata(clean_result.text, filename)
        document = {
            "doc_id": Path(filename).stem,
            "title": metadata["title"],
            "source_filename": filename,
            "canonical_source_path": to_repo_relative(source_path),
            "topic_labels": topics,
            "doc_type": "ocr_text",
            "author": metadata["author"],
            "dynasty": metadata["dynasty"],
            "year_raw": metadata["year_raw"],
            "year_normalized": metadata["year_normalized"],
            "cleaning_flags": sorted(clean_result.flags),
            "cleaning_stats": dict(clean_result.stats),
            "source_origin": source_origin,
        }
        documents.append(document)

        qc["cleaning_totals"].update(clean_result.stats)
        qc["doc_type_counts"]["ocr_text"] += 1
        if not metadata["author"]:
            qc["missing_author_count"] += 1
        if not metadata["dynasty"]:
            qc["missing_dynasty_count"] += 1
        if not metadata["year_normalized"]:
            qc["missing_year_count"] += 1

        sections = parse_sections(clean_result.text, metadata["title"])
        for chunk_index, chunk in enumerate(build_chunk_records(sections, document), start=1):
            chunk["chunk_index"] = chunk_index
            chunks.append(chunk)
            for topic in topics:
                chunks_by_topic[topic].append(chunk)

    structured_path = TOPIC_DIR / STRUCTURED_REFERENCE
    if structured_path.exists():
        structured_raw = structured_path.read_text(encoding="utf-8", errors="ignore")
        structured_clean = clean_structured_reference(structured_raw)
        structured_output = CLEANED_DIR / STRUCTURED_REFERENCE
        structured_output.write_text(structured_clean, encoding="utf-8")
        structured_chunks = parse_structured_reference(structured_clean)
        structured_doc = {
            "doc_id": Path(STRUCTURED_REFERENCE).stem,
            "title": Path(STRUCTURED_REFERENCE).stem,
            "source_filename": STRUCTURED_REFERENCE,
            "canonical_source_path": to_repo_relative(structured_path),
            "topic_labels": ["07-中医体质调养"],
            "doc_type": "structured_reference",
            "author": None,
            "dynasty": None,
            "year_raw": None,
            "year_normalized": None,
            "cleaning_flags": [],
            "cleaning_stats": {},
            "source_origin": "topic_reference",
        }
        documents.append(structured_doc)
        qc["doc_type_counts"]["structured_reference"] += 1
        for chunk_index, chunk in enumerate(build_structured_chunk_records(structured_chunks, structured_doc), start=1):
            chunk["chunk_index"] = chunk_index
            chunks.append(chunk)
            chunks_by_topic["07-中医体质调养"].append(chunk)

    chunks.sort(key=lambda item: (item["doc_id"], item["chunk_index"]))
    for topic, topic_chunks in chunks_by_topic.items():
        topic_chunks.sort(key=lambda item: (item["doc_id"], item["chunk_index"]))
    documents.sort(key=lambda item: item["doc_id"])

    write_jsonl(OUTPUT_DIR / "documents.jsonl", documents)
    write_jsonl(OUTPUT_DIR / "chunks.jsonl", chunks)
    write_topic_chunk_files(chunks_by_topic)

    avg_chunk_chars = round(sum(item["char_count"] for item in chunks) / len(chunks), 2) if chunks else 0
    oversized_chunks = sum(1 for item in chunks if item["char_count"] > 1200)
    multi_topic_documents = sum(1 for item in documents if len(item["topic_labels"]) > 1)

    qc_report = {
        "topic_file_count": qc["topic_file_count"],
        "canonical_document_count": sum(1 for item in documents if item["doc_type"] == "ocr_text"),
        "document_count": len(documents),
        "chunk_count": len(chunks),
        "multi_topic_document_count": multi_topic_documents,
        "unmatched_topic_files": qc["unmatched_topic_files"],
        "duplicate_source_filenames": qc["duplicate_source_filenames"],
        "missing_author_count": qc["missing_author_count"],
        "missing_dynasty_count": qc["missing_dynasty_count"],
        "missing_year_count": qc["missing_year_count"],
        "avg_chunk_chars": avg_chunk_chars,
        "oversized_chunk_count": oversized_chunks,
        "doc_type_counts": dict(qc["doc_type_counts"]),
        "cleaning_totals": dict(qc["cleaning_totals"]),
        "topic_chunk_counts": {topic: len(topic_chunks) for topic, topic_chunks in sorted(chunks_by_topic.items())},
        "output_files": {
            "documents": "processed/topics/documents.jsonl",
            "chunks": "processed/topics/chunks.jsonl",
            "cleaned_dir": "processed/topics/cleaned",
            "topic_chunk_files_parent": "processed/topics",
        },
    }
    (OUTPUT_DIR / "qc_report.json").write_text(
        json.dumps(qc_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def build_source_index() -> tuple[dict[str, Path], dict[str, list[str]]]:
    grouped: dict[str, list[Path]] = defaultdict(list)
    for path in SOURCE_DIR.rglob("*.txt"):
        grouped[path.name].append(path)
    index: dict[str, Path] = {}
    duplicates: dict[str, list[str]] = {}
    for filename, paths in grouped.items():
        if len(paths) == 1:
            index[filename] = paths[0]
            continue
        duplicates[filename] = [to_repo_relative(path) for path in sorted(paths)]
        index[filename] = sorted(paths)[0]
    return index, duplicates


def build_topic_map() -> tuple[dict[str, set[str]], int]:
    topic_map: dict[str, set[str]] = defaultdict(set)
    file_count = 0
    for directory in sorted(TOPIC_DIR.iterdir()):
        if not directory.is_dir() or not TOPIC_DIR_RE.match(directory.name):
            continue
        for path in sorted(directory.glob("*.txt")):
            topic_map[path.name].add(directory.name)
            file_count += 1
    return topic_map, file_count


def locate_topic_copy(filename: str) -> Path | None:
    for directory in TOPIC_DIR.iterdir():
        if not directory.is_dir() or not TOPIC_DIR_RE.match(directory.name):
            continue
        candidate = directory / filename
        if candidate.exists():
            return candidate
    return None


def clean_ocr_text(raw_text: str) -> CleanResult:
    stats: Counter = Counter()
    flags: set[str] = set()
    text = raw_text.replace("﻿", "")

    control_chars = NON_PRINTABLE_RE.findall(text)
    if control_chars:
        stats["control_chars_removed"] += len(control_chars)
        flags.add("control_chars_removed")
        text = NON_PRINTABLE_RE.sub("", text)

    image_placeholders = BMP_PLACEHOLDER_RE.findall(text)
    if image_placeholders:
        stats["image_placeholders_removed"] += len(image_placeholders)
        flags.add("image_placeholders_removed")
        text = BMP_PLACEHOLDER_RE.sub("", text)

    literal_escapes = LITERAL_ESCAPE_RE.findall(text)
    if literal_escapes:
        stats["literal_escape_markers_removed"] += len(literal_escapes)
        flags.add("literal_escape_markers_removed")
        text = LITERAL_ESCAPE_RE.sub("", text)

    if "\\" in text:
        backslash_count = text.count("\\")
        stats["backslashes_normalized"] += backslash_count
        flags.add("backslashes_normalized")
        text = text.replace("\\", " ")

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)

    merged_lines = 0
    output_lines: list[str] = []
    paragraph_buffer = ""

    def flush_buffer() -> None:
        nonlocal paragraph_buffer
        if paragraph_buffer:
            output_lines.append(paragraph_buffer)
            paragraph_buffer = ""

    for raw_line in text.splitlines():
        line = raw_line.strip(" \t")
        if not line:
            flush_buffer()
            if output_lines and output_lines[-1] != "":
                output_lines.append("")
            continue
        if is_structure_line(line):
            flush_buffer()
            output_lines.append(line)
            continue
        if paragraph_buffer and should_start_new_paragraph(line):
            output_lines.append(paragraph_buffer)
            paragraph_buffer = line
            continue
        if paragraph_buffer:
            paragraph_buffer += line
            merged_lines += 1
        else:
            paragraph_buffer = line

    flush_buffer()
    cleaned = "\n".join(output_lines)
    cleaned = MULTI_BLANK_RE.sub("\n\n", cleaned).strip() + "\n"
    if merged_lines:
        stats["merged_line_breaks"] += merged_lines
        flags.add("merged_line_breaks")
    return CleanResult(text=cleaned, stats=stats, flags=flags)


def clean_structured_reference(raw_text: str) -> str:
    text = raw_text.replace("﻿", "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.splitlines()]
    return MULTI_BLANK_RE.sub("\n\n", "\n".join(lines)).strip() + "\n"


def is_structure_line(line: str) -> bool:
    return line.startswith(SECTION_MARKERS)


def should_start_new_paragraph(line: str) -> bool:
    return bool(ENUM_RE.match(line))


def extract_metadata(cleaned_text: str, filename: str) -> dict[str, str | None]:
    metadata = {"书名": None, "作者": None, "朝代": None, "年份": None}
    for line in cleaned_text.splitlines()[:20]:
        match = META_RE.match(line)
        if match:
            metadata[match.group(1)] = match.group(2).strip() or None
    title = metadata["书名"] or Path(filename).stem.split("-", 1)[-1]
    year_raw = metadata["年份"]
    return {
        "title": title,
        "author": metadata["作者"],
        "dynasty": metadata["朝代"],
        "year_raw": year_raw,
        "year_normalized": normalize_year(year_raw),
    }


def normalize_year(year_raw: str | None) -> str | None:
    if not year_raw:
        return None
    groups = re.findall(r"\d{3,4}", year_raw)
    plausible = [value for value in groups if 1 <= int(value) <= 2100]
    if len(plausible) >= 2 and any(token in year_raw for token in ("-", "—", "–", "至")):
        return f"{plausible[0]}-{plausible[1]}"
    if plausible:
        return plausible[0]
    return None


def parse_sections(cleaned_text: str, title: str) -> list[Section]:
    lines = cleaned_text.splitlines()
    sections: list[Section] = []
    current_lines: list[str] = []
    current_title: str | None = None
    current_volume: str | None = None
    current_context: str | None = None

    def flush_section() -> None:
        nonlocal current_lines, current_title
        body = "\n".join(current_lines).strip()
        current_lines = []
        if not body and not current_title:
            return
        path: list[str] = []
        for value in (current_volume, current_context, current_title or title):
            if value and (not path or path[-1] != value):
                path.append(value)
        section_title = current_title or title
        sections.append(Section(title=section_title, path=path, text=body))
        current_title = None

    for line in lines:
        if META_RE.match(line):
            continue
        if line.startswith("<目录>"):
            payload = normalize_marker_content(line.removeprefix("<目录>"))
            if payload:
                volume, context = split_directory_context(payload)
                if volume:
                    current_volume = volume
                if context:
                    current_context = context
            continue
        if line.startswith("<篇名>"):
            payload = normalize_marker_content(line.removeprefix("<篇名>")) or title
            if VOLUME_RE.match(payload) and len(payload) <= 6:
                current_volume = payload
                current_context = None
                continue
            flush_section()
            current_title = payload
            continue
        current_lines.append(line)

    flush_section()
    if not sections:
        body = "\n".join(line for line in lines if not META_RE.match(line)).strip()
        return [Section(title=title, path=[title], text=body)]
    return [section for section in sections if section.text]


def normalize_marker_content(value: str) -> str:
    normalized = value.replace("/", " ").strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def split_directory_context(payload: str) -> tuple[str | None, str | None]:
    parts = payload.split()
    if not parts:
        return None, None
    if VOLUME_RE.match(parts[0]):
        volume = parts[0]
        context = " ".join(parts[1:]).strip() or None
        return volume, context
    return None, payload


def build_chunk_records(sections: list[Section], document: dict) -> Iterable[dict]:
    chunk_order = 0
    for section in sections:
        for piece in split_section_text(section.text):
            if should_skip_chunk(piece):
                continue
            chunk_order += 1
            chunk_id = make_chunk_id(document["doc_id"], chunk_order, piece)
            yield {
                "chunk_id": chunk_id,
                "doc_id": document["doc_id"],
                "title": document["title"],
                "topic_labels": document["topic_labels"],
                "doc_type": document["doc_type"],
                "section_path": section.path,
                "text": piece,
                "char_count": len(piece),
                "content_hash": hashlib.sha1(piece.encode("utf-8")).hexdigest(),
                "source_path": document["canonical_source_path"],
            }


def parse_structured_reference(cleaned_text: str) -> list[StructuredChunk]:
    chunks: list[StructuredChunk] = []
    current_title: str | None = None
    current_code: str | None = None
    current_fields: dict[str, str] = {}

    def flush() -> None:
        nonlocal current_title, current_code, current_fields
        if not current_title or not current_code:
            return
        ordered_keys = [
            "总体特征",
            "形体特征",
            "常见表现",
            "心理特征",
            "发病倾向",
            "对外界环境适应能力",
        ]
        lines = [f"{current_title} ({current_code}型)"]
        for key in ordered_keys:
            value = current_fields.get(key)
            if value:
                lines.append(f"{key}：{value}")
        chunks.append(
            StructuredChunk(
                title=current_title,
                code=current_code,
                fields=dict(current_fields),
                text="\n".join(lines),
            )
        )
        current_title = None
        current_code = None
        current_fields = {}

    for line in cleaned_text.splitlines():
        line = line.strip()
        if not line:
            continue
        section_match = STRUCTURED_SECTION_RE.match(line)
        if section_match:
            flush()
            current_title = section_match.group(1)
            current_code = section_match.group(2)
            continue
        field_match = STRUCTURED_FIELD_RE.match(line)
        if field_match and current_title:
            current_fields[field_match.group(1)] = field_match.group(2).strip()

    flush()
    return chunks


def build_structured_chunk_records(structured_chunks: list[StructuredChunk], document: dict) -> Iterable[dict]:
    chunk_order = 0
    for item in structured_chunks:
        chunk_order += 1
        chunk_id = make_chunk_id(document["doc_id"], chunk_order, item.text)
        yield {
            "chunk_id": chunk_id,
            "doc_id": document["doc_id"],
            "title": document["title"],
            "topic_labels": document["topic_labels"],
            "doc_type": document["doc_type"],
            "section_path": [item.title],
            "text": item.text,
            "char_count": len(item.text),
            "content_hash": hashlib.sha1(item.text.encode("utf-8")).hexdigest(),
            "source_path": document["canonical_source_path"],
            "structured_fields": {
                "constitution_name": item.title,
                "constitution_code": item.code,
                "overall_traits": item.fields.get("总体特征"),
                "body_traits": item.fields.get("形体特征"),
                "common_manifestations": item.fields.get("常见表现"),
                "psychological_traits": item.fields.get("心理特征"),
                "disease_tendency": item.fields.get("发病倾向"),
                "environmental_adaptation": item.fields.get("对外界环境适应能力"),
            },
        }


def split_section_text(text: str) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n{2,}", text) if part.strip()]
    if not paragraphs:
        return []
    if len(paragraphs) == 1:
        units = split_sentences(paragraphs[0])
    else:
        units = []
        for paragraph in paragraphs:
            if len(paragraph) > MAX_CHARS:
                units.extend(split_sentences(paragraph))
            else:
                units.append(paragraph)
    normalized_units: list[str] = []
    for unit in units:
        normalized_units.extend(split_long_unit(unit))
    return pack_units(normalized_units)


def split_sentences(text: str) -> list[str]:
    pieces = re.split(r"(?<=[。！？；])", text)
    return [piece.strip() for piece in pieces if piece.strip()]


def split_long_unit(unit: str) -> list[str]:
    if len(unit) <= MAX_CHARS:
        return [unit]
    pieces = re.split(r"(?<=[，、：])", unit)
    if len(pieces) == 1:
        return [unit[index:index + MAX_CHARS] for index in range(0, len(unit), MAX_CHARS)]
    buckets: list[str] = []
    current = ""
    for piece in pieces:
        if current and len(current) + len(piece) > MAX_CHARS:
            buckets.append(current)
            current = piece
        else:
            current += piece
    if current:
        buckets.append(current)
    refined: list[str] = []
    for bucket in buckets:
        if len(bucket) <= MAX_CHARS:
            refined.append(bucket)
        else:
            refined.extend(bucket[index:index + MAX_CHARS] for index in range(0, len(bucket), MAX_CHARS))
    return [item.strip() for item in refined if item.strip()]


def pack_units(units: list[str]) -> list[str]:
    if not units:
        return []
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for unit in units:
        tentative_len = current_len + len(unit) + (1 if current else 0)
        if current and tentative_len > MAX_CHARS:
            chunks.append("\n".join(current).strip())
            overlap = current[-OVERLAP_UNITS:] if OVERLAP_UNITS else []
            current = overlap.copy()
            current_len = sum(len(item) for item in current)
            tentative_len = current_len + len(unit) + (1 if current else 0)
        if current and tentative_len > MAX_CHARS:
            chunks.append("\n".join(current).strip())
            current = []
            current_len = 0
        if current:
            current_len += 1
        current.append(unit)
        current_len += len(unit)
    if current:
        chunks.append("\n".join(current).strip())
    return chunks


def should_skip_chunk(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    body = stripped.removeprefix("属性：").strip()
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if not lines:
        return True
    if len(body) <= 80 and all(line.endswith("图") for line in lines):
        return True
    return False


def make_chunk_id(doc_id: str, order: int, text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
    return f"{doc_id}-{order:04d}-{digest}"


def write_jsonl(path: Path, records: Iterable[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_topic_chunk_files(chunks_by_topic: dict[str, list[dict]]) -> None:
    for topic, topic_chunks in chunks_by_topic.items():
        write_jsonl(OUTPUT_DIR / f"{topic}_chunks.jsonl", topic_chunks)


def to_repo_relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


if __name__ == "__main__":
    main()
