# 环境与依赖准备

本仓库用于处理“智联招聘数据库2019.dta”等 Stata 数据并转换为 Parquet/DuckDB。以下记录当前环境评估、目录结构、依赖准备与示例脚本。

## 资源评估
- CPU：17 cores（`nproc`）
- 内存：总计约 65 GiB，可用约 64 GiB（`free -h`）
- 磁盘：根分区 63 GiB，剩余约 37 GiB（`df -h .`）

## 目录结构
- `data/raw/`：原始数据存放目录。
- `data/processed/`：转换后的 Parquet 等产物输出目录（版本控制忽略大文件，仅保留 `.gitkeep` 方便结构落地）。
- `tmp/`：临时文件与摘要输出目录（同样只保留结构）。
- `scripts/`：环境检查与示例脚本存放目录。

三类目录均已创建并附带 `.gitkeep` 以保证结构落地。

## 依赖与虚拟环境
- 建议使用 Python 3.10+，通过虚拟环境隔离依赖：
  ```bash
  python -m venv .venv --system-site-packages
  source .venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
  ```
- 核心依赖：`pandas`、`pyreadstat`、`duckdb`、`pyarrow`（已在 `requirements.txt` 固定版本）。
- 当前网络通过代理访问外部源返回 403，pip/apt 无法拉取包；待网络恢复后执行上述命令即可安装。若仍受限，可使用内网 PyPI 镜像或预下载的 wheel 包进行离线安装。

## 示例验证脚本
- `scripts/env_check.py`：
  - 读取指定的 `.dta` 文件（默认 `智联招聘数据库2019.dta`）抽样最多 200 行。
  - 将数据写入 `data/processed/sample_jobs.parquet` 并用 DuckDB 校验行数。
  - 输出资源与依赖版本信息，保存到 `tmp/env_summary.json`。

执行示例（需先完成依赖安装）：
```bash
source .venv/bin/activate
python scripts/env_check.py --row-limit 200 \
  --data 智联招聘数据库2019.dta \
  --output-dir data/processed \
  --tmp-dir tmp
```

若依赖安装受限，可先运行标准库脚本采集资源，再待网络恢复后补跑转换验证。
