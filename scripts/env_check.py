#!/usr/bin/env python3
"""Quick environment check and sample Stata-to-Parquet flow.

This script validates core dependencies, inspects host resources, and
runs a tiny .dta -> Parquet round trip using DuckDB for verification.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any, Dict

import duckdb
import pandas as pd
import pyreadstat


def gather_resources(base_path: Path) -> Dict[str, Any]:
    cpu_count = os.cpu_count() or 1
    mem_total_gb = None
    mem_available_gb = None
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        data = {}
        with meminfo.open() as f:
            for line in f:
                if ":" in line:
                    key, value = line.split(":", 1)
                    data[key.strip()] = value.strip()
        def _to_gb(value: str | None) -> float | None:
            if value is None:
                return None
            parts = value.split()
            try:
                kb = float(parts[0])
            except (ValueError, IndexError):
                return None
            return round(kb / 1024 / 1024, 2)
        mem_total_gb = _to_gb(data.get("MemTotal"))
        mem_available_gb = _to_gb(data.get("MemAvailable"))

    usage = shutil.disk_usage(base_path)
    disk_total_gb = round(usage.total / 1024 / 1024 / 1024, 2)
    disk_free_gb = round(usage.free / 1024 / 1024 / 1024, 2)

    return {
        "cpu_count": cpu_count,
        "memory_total_gb": mem_total_gb,
        "memory_available_gb": mem_available_gb,
        "disk_total_gb": disk_total_gb,
        "disk_free_gb": disk_free_gb,
        "base_path": str(base_path.resolve()),
    }


def ensure_directories(*paths: Path) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def run_sample_conversion(data_path: Path, output_dir: Path, row_limit: int) -> Dict[str, Any]:
    if not data_path.exists():
        raise FileNotFoundError(f"数据文件不存在: {data_path}")

    print(f"读取 Stata 数据（最多 {row_limit} 行）: {data_path}")
    df, meta = pyreadstat.read_dta(data_path, limit=row_limit)
    print(f"读取完成，获取 {len(df)} 行，{len(df.columns)} 列。")

    output_file = output_dir / "sample_jobs.parquet"
    df.to_parquet(output_file, index=False)
    print(f"已写入 Parquet: {output_file}")

    con = duckdb.connect(database=":memory:")
    result = con.execute("SELECT count(*) AS rows FROM parquet_scan(?)", [str(output_file)]).fetchone()
    con.close()
    rows_in_parquet = int(result[0]) if result else 0
    print(f"DuckDB 校验行数: {rows_in_parquet}")

    return {
        "rows_read": len(df),
        "columns": list(df.columns),
        "parquet_path": str(output_file),
        "rows_in_parquet": rows_in_parquet,
        "variable_labels": meta.column_labels,
    }


def dependency_versions() -> Dict[str, str]:
    return {
        "pandas": pd.__version__,
        "pyreadstat": pyreadstat.__version__,
        "duckdb": duckdb.__version__,
        "pyarrow": pd.io.common.pyarrow_version(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Environment readiness check")
    parser.add_argument("--data", type=Path, default=Path("智联招聘数据库2019.dta"), help="Stata .dta 输入路径")
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"), help="Parquet 输出目录")
    parser.add_argument("--tmp-dir", type=Path, default=Path("tmp"), help="临时目录 (当前脚本仅保证存在)")
    parser.add_argument("--row-limit", type=int, default=200, help="示例读取的最大行数")
    parser.add_argument("--summary", type=Path, default=Path("tmp/env_summary.json"), help="输出资源与依赖摘要路径")
    args = parser.parse_args(argv)

    ensure_directories(args.output_dir, args.tmp_dir)

    summary: Dict[str, Any] = {
        "resource": gather_resources(Path.cwd()),
        "dependencies": dependency_versions(),
    }

    try:
        summary["sample_conversion"] = run_sample_conversion(args.data, args.output_dir, args.row_limit)
    except Exception as exc:  # noqa: BLE001
        print(f"示例转换失败: {exc}", file=sys.stderr)
        return 1

    args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"环境与示例摘要已写入: {args.summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
