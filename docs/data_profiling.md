# 数据抽样与结构摸底脚本使用说明

本脚本用于对 Stata 数据集进行字段探查、缺失率统计与质量提示，并输出脱敏示例抽样。

## 快速开始

```bash
python scripts/data_profile.py \
  --data 智联招聘数据库2019.dta \
  --report data/reports/2019_profile.json \
  --chunk-size 50000 \
  --sample-rows 50 \
  --missing-threshold 0.5
```

参数说明：

- `--data`：Stata `.dta` 输入路径，默认使用仓库根目录的 2019 样例。
- `--report`：输出报告的 JSON 路径，会自动创建父目录。
- `--chunk-size`：分块读取行数，避免一次性占用过多内存。
- `--sample-rows`：输出脱敏示例的行数，仅用于快速人工感知。
- `--missing-threshold`：缺失率超过该阈值会在质量问题中提示。
- `--row-limit`：可选，只读取指定行数做快速预览；省略则遍历全量数据。

## 输出内容

报告包含：

- 全量数据的行数与列数统计。
- 每列的 dtype、非空计数、缺失率、常量列提示。
- 质量问题列表（高缺失、常量值）。
- 脱敏示例数据，字符串字段仅保留前后片段。

## 复现建议

- 在运行前确认已安装 `pandas`、`pyreadstat`、`pyarrow`、`duckdb` 等依赖，可复用 `requirements.txt`。
- 对大体量数据建议调低 `--chunk-size` 或设置 `--row-limit` 做预检，再跑全量。
