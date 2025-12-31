#!/usr/bin/env python3
"""Data profiling script for Stata datasets."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd


def mask_value(value: Any, max_length: int = 30) -> Any:
    """Mask potential sensitive strings while keeping readability."""
    if pd.isna(value):
        return None
    if isinstance(value, str):
        if len(value) > max_length:
            return value[: max_length // 2] + "…" + value[-max_length // 2 :]
        return value
    return value


def ensure_directory(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def iter_stata_chunks(path: Path, chunk_size: int, limit_rows: Optional[int] = None) -> Iterable[pd.DataFrame]:
    """Yield Stata data in chunks, respecting an optional row limit."""
    reader = pd.read_stata(path, chunksize=chunk_size, iterator=True, convert_categoricals=False)
    total = 0
    for chunk in reader:
        if limit_rows is not None and total >= limit_rows:
            break
        if limit_rows is not None:
            remaining = limit_rows - total
            if remaining <= 0:
                break
            chunk = chunk.head(remaining)
        total += len(chunk)
        yield chunk


def collect_profile(
    data_path: Path,
    chunk_size: int,
    sample_rows: int,
    missing_threshold: float,
    row_limit: Optional[int] = None,
) -> Dict[str, Any]:
    column_stats: Dict[str, Dict[str, Any]] = {}
    total_rows = 0
    sample: List[Dict[str, Any]] = []

    for chunk in iter_stata_chunks(data_path, chunk_size, row_limit):
        total_rows += len(chunk)

        if len(sample) < sample_rows:
            need = sample_rows - len(sample)
            masked = chunk.head(need).applymap(mask_value)
            sample.extend(masked.to_dict(orient="records"))

        for column in chunk.columns:
            series = chunk[column]
            non_null_mask = series.notna()
            non_null_count = int(non_null_mask.sum())

            stats = column_stats.setdefault(
                column,
                {
                    "dtype": None,
                    "non_null": 0,
                    "constant": True,
                    "constant_value_raw": None,
                },
            )

            stats["non_null"] += non_null_count
            if stats["dtype"] is None:
                stats["dtype"] = str(series.dtype)

            if non_null_count > 0 and stats["constant"]:
                first_non_null = series[non_null_mask].iloc[0]
                if stats["constant_value_raw"] is None:
                    stats["constant_value_raw"] = first_non_null
                else:
                    if not series[non_null_mask].eq(stats["constant_value_raw"]).all():
                        stats["constant"] = False

    columns_report: List[Dict[str, Any]] = []
    quality_issues: List[str] = []

    for name, stats in column_stats.items():
        non_null = stats["non_null"]
        missing = max(total_rows - non_null, 0)
        missing_rate = (missing / total_rows) if total_rows else None

        issues: List[str] = []
        if missing_rate is not None and missing_rate > missing_threshold:
            issues.append(f"缺失率 {missing_rate:.2%} 超过阈值 {missing_threshold:.0%}")
        if stats["constant"] and non_null > 0:
            issues.append("值几乎不变或常量列")

        if issues:
            quality_issues.extend([f"{name}: {msg}" for msg in issues])

        columns_report.append(
            {
                "name": name,
                "dtype": stats["dtype"],
                "non_null": non_null,
                "missing": missing,
                "missing_rate": missing_rate,
                "constant": bool(stats["constant"]),
                "example": mask_value(stats.get("constant_value_raw")),
                "issues": issues,
            }
        )

    return {
        "data_path": str(data_path),
        "row_count": total_rows,
        "column_count": len(column_stats),
        "columns": sorted(columns_report, key=lambda x: x["name"]),
        "quality_issues": quality_issues,
        "sample": sample,
        "parameters": {
            "chunk_size": chunk_size,
            "sample_rows": sample_rows,
            "missing_threshold": missing_threshold,
            "row_limit": row_limit,
        },
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate structure and quality report for a Stata dataset")
    parser.add_argument("--data", type=Path, default=Path("智联招聘数据库2019.dta"), help="Stata .dta 文件路径")
    parser.add_argument("--report", type=Path, default=Path("data/reports/data_profile.json"), help="报告输出路径 (JSON)")
    parser.add_argument("--chunk-size", type=int, default=50000, help="分块读取行数，避免一次性占用内存")
    parser.add_argument("--sample-rows", type=int, default=50, help="示例抽样行数，字符串值会被脱敏")
    parser.add_argument("--missing-threshold", type=float, default=0.5, help="缺失率告警阈值，0-1 之间")
    parser.add_argument("--row-limit", type=int, default=None, help="可选的最大读取行数，用于快速预览")
    args = parser.parse_args(argv)

    if not args.data.exists():
        raise FileNotFoundError(f"数据文件不存在: {args.data}")

    ensure_directory(args.report)

    report = collect_profile(
        data_path=args.data,
        chunk_size=args.chunk_size,
        sample_rows=args.sample_rows,
        missing_threshold=args.missing_threshold,
        row_limit=args.row_limit,
    )

    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"数据行数: {report['row_count']}，列数: {report['column_count']}")
    print(f"质量问题条目: {len(report['quality_issues'])}")
    print(f"报告已保存到: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
