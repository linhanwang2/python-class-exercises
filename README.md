# 信息安全基础能力训练 · 课堂练习 1-2

- **学号**：2025303715（后六位：**303715**）
- **姓名**：王林涵
- **课程**：信息安全基础能力训练
- **环境**：Ubuntu Server 24.04.5 LTS（VMware 虚拟机）/ Python 3.12

---

## 练习一：网页单词提取

`wordextractor.py` —— 爬取网页，提取单词，统计词频，并生成常见密码变体。

### 功能参数

| 参数 | 说明 |
| --- | --- |
| `-u, --url` | 目标网页 URL（必填） |
| `-l, --length` | 只统计长度不小于该值的单词（默认 0，不限） |
| `-o, --output` | 结果写入文件，而非打印到控制台 |
| `-d, --depth` | 同域名广度优先爬取深度（默认 0，仅单页） |
| `-t, --top` | 保留前多少个高频词（默认 10） |
| `--mutations / --no-mutations` | 是否生成密码变体（默认生成） |
| `--seed` | 随机种子，使随机数字后缀可复现 |

### 运行的密码变体规则

- 大小写：原样、全小写、全大写、首字母大写
- 后缀：近年年份（2019 ~ 当前年）、常见数字与符号（`1` `01` `123` `1!` `2!` `3!` `!` `@` `#` `$` `.` `?`）、随机数字

### 运行方法

```bash
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt

python wordextractor.py -u https://example.com --top 10
python wordextractor.py -u https://example.com -l 10 -o result.txt
```

### Bug 修复说明

课堂示例在 `--length` 取较大值（如 10 及以上）时会抛出 `IndexError` 而崩溃。本版已修复，详见 `实验报告.md`。

---

## 练习二：Bind Shell

`bindshell.py` —— 教学用 bind shell，在目标主机上监听指定端口，等待连接后提供命令行。

> ⚠️ **仅供已授权的信息安全课程实验使用（隔离虚拟机环境）。**
> 请勿在未经授权的主机上运行。

### 功能参数

| 参数 | 说明 |
| --- | --- |
| `-p, --port` | 监听端口（默认 4444） |
| `-t, --threaded` | 多线程模式，可同时服务多个连接 |

### 运行方法

目标机（虚拟机）：

```bash
python bindshell.py --port 4444
```

控制端：

```bash
nc <目标机IP> 4444
```

---

## 目录结构

```text
.
├── wordextractor.py     # 练习一：网页单词提取
├── bindshell.py         # 练习二：bind shell
├── requirements.txt     # 练习一依赖
├── 实验报告.md          # 实验报告
└── README.md
```

## 依赖

```text
beautifulsoup4
click
requests
```
