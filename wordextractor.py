#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""网页单词提取与密码变体生成器（示例一 / 练习一）。

本脚本改写自课堂示例一，实现以下流程：

    抓取网页 -> 提取单词 -> 统计词频 -> 排序 -> 生成密码变体 -> 输出

在课堂示例的基础上新增了以下能力：

* ``--url / -u``      指定目标网页 URL；
* ``--length / -l``   只统计长度不小于该值的单词（默认 0，即不限）；
* ``--output / -o``   把结果写入指定文件，而不是仅打印到控制台；
* 密码变体            对高频单词自动生成常见密码变形：首字母大写、全小写、
                       全大写，以及在末尾追加年份、数字与符号后缀；
* ``--depth / -d``    （可选）按同一域名范围、广度优先爬取指定深度内的页面。

课堂示例在 ``--length`` 取较大值（>= 10）时会抛出 ``IndexError`` 崩溃，
本脚本已修复（见实验报告“Bug 分析与修复”一节）。

作者：<你的姓名 / 学号>
日期：2026-10-14
"""

from __future__ import annotations

import random
import re
import sys
from collections import deque
from datetime import datetime
from urllib.parse import urljoin, urlparse

import click
import requests
from bs4 import BeautifulSoup

# --------------------------------------------------------------------------- #
# 常量配置
# --------------------------------------------------------------------------- #

USER_AGENT = "wordextractor/1.0 (course lab; +https://example.local)"
DEFAULT_TIMEOUT = 10  # 单次请求超时（秒）

# 常见密码后缀：符号类
SYMBOL_SUFFIXES = ["!", "@", "#", "$", ".", "?"]

# 常见密码后缀：数字 / 数字+符号类
NUMERIC_SUFFIXES = ["1", "01", "12", "123", "1234", "1!", "2!", "3!"]

# 随机数字后缀的个数（用于生成如 "2026" -> "20261234" 之类的变体）
RANDOM_SUFFIX_COUNT = 3


# --------------------------------------------------------------------------- #
# 网页抓取
# --------------------------------------------------------------------------- #

def get_html_of(url: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """下载指定 URL 的网页内容并返回其文本形式。

    非 200 状态码（如 404）会抛出 ``requests.HTTPError``，由调用方决定
    是继续爬取其他页面还是终止程序。
    """
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
    )
    response.raise_for_status()
    # 使用 replace 策略，避免个别网页的非 UTF-8 字节导致解码失败
    return response.content.decode(errors="replace")


def extract_words(html: str) -> list[str]:
    """从 HTML 文本中提取所有单词，忽略标签与元数据。

    先用 BeautifulSoup 的 ``get_text()`` 去掉所有标签，再用正则 ``\\w+``
    匹配单词字符（字母、数字、下划线）。
    """
    soup = BeautifulSoup(html, "html.parser")
    raw_text = soup.get_text()
    return re.findall(r"\w+", raw_text)


def crawl_pages(start_url: str, max_depth: int) -> list[str]:
    """按同域名范围广度优先爬取页面，返回各页面的 HTML 文本列表。

    ``max_depth`` 为 0 时只抓取起始页；为 1 时还会抓取起始页中的
    同域名链接；以此类推。
    """
    domain = urlparse(start_url).netloc
    visited: set[str] = set()
    queue: deque[tuple[str, int]] = deque([(start_url, 0)])
    pages: list[str] = []

    while queue:
        current_url, level = queue.popleft()
        if current_url in visited:
            continue
        visited.add(current_url)

        try:
            html = get_html_of(current_url)
        except requests.HTTPError as exc:
            click.echo(f"[warn] 抓取失败 {current_url}: {exc}", err=True)
            continue
        except requests.RequestException as exc:
            click.echo(f"[warn] 网络错误 {current_url}: {exc}", err=True)
            continue

        pages.append(html)
        click.echo(f"[info] 已抓取 (depth={level}) {current_url}", err=True)

        if level >= max_depth:
            continue

        soup = BeautifulSoup(html, "html.parser")
        for link in soup.find_all("a", href=True):
            next_url = urljoin(current_url, link["href"])
            parsed = urlparse(next_url)
            # 只跟踪 http/https，且限制在同一域名内
            if parsed.scheme not in ("http", "https"):
                continue
            if parsed.netloc != domain:
                continue
            if next_url not in visited:
                queue.append((next_url, level + 1))

    return pages


# --------------------------------------------------------------------------- #
# 词频统计
# --------------------------------------------------------------------------- #

def count_occurrences_in(
    word_list: list[str], min_length: int
) -> dict[str, int]:
    """统计单词出现次数，忽略长度小于 ``min_length`` 的单词。"""
    word_count: dict[str, int] = {}
    for word in word_list:
        if len(word) < min_length:
            continue
        if word not in word_count:
            word_count[word] = 1
        else:
            word_count[word] = word_count[word] + 1
    return word_count


def get_top_words_from(
    all_words: list[str], min_length: int
) -> list[tuple[str, int]]:
    """按出现次数从高到低排序，返回 ``(单词, 次数)`` 列表。"""
    occurrences = count_occurrences_in(all_words, min_length)
    return sorted(occurrences.items(), key=lambda item: item[1], reverse=True)


# --------------------------------------------------------------------------- #
# 密码变体生成
# --------------------------------------------------------------------------- #

def year_suffixes(start_year: int = 2019) -> list[str]:
    """返回从 ``start_year`` 到当前年份的所有年份字符串。"""
    this_year = datetime.now().year
    return [str(year) for year in range(start_year, this_year + 1)]


def random_suffixes(count: int = RANDOM_SUFFIX_COUNT) -> list[str]:
    """生成若干个随机数字后缀。"""
    return [str(random.randint(1, 9999)) for _ in range(count)]


def generate_variants(word: str) -> list[str]:
    """对一个单词生成常见密码变体并去重、排序。

    变体规则：

    * 大小写：原样、全小写、全大写、首字母大写；
    * 后缀：追加年份（2019~今年）、数字/数字符号、符号，以及随机数字。
    """
    suffixes = year_suffixes() + NUMERIC_SUFFIXES + SYMBOL_SUFFIXES
    suffixes += random_suffixes()

    bases = {word, word.lower(), word.upper(), word.capitalize()}

    variants: set[str] = set()
    for base in bases:
        variants.add(base)
        for suffix in suffixes:
            variants.add(base + suffix)
    return sorted(variants)


def build_wordlist(
    top_words: list[tuple[str, int]], mutate: bool
) -> list[str]:
    """根据高频词生成最终词表（每行一个候选密码）。"""
    wordlist: list[str] = []
    for word, _count in top_words:
        if mutate:
            wordlist.extend(generate_variants(word))
        else:
            wordlist.append(word)
    return wordlist


# --------------------------------------------------------------------------- #
# 命令行入口
# --------------------------------------------------------------------------- #

@click.command()
@click.option(
    "--url", "-u",
    prompt="Web URL",
    help="URL of webpage to extract from.",
)
@click.option(
    "--length", "-l",
    default=0,
    show_default=True,
    help="Minimum word length (default: 0, no limit).",
)
@click.option(
    "--output", "-o",
    default=None,
    type=click.Path(dir_okay=False, writable=True),
    help="Output file. Write results to this file instead of the console.",
)
@click.option(
    "--depth", "-d",
    default=0,
    show_default=True,
    help=(
        "Crawl depth. Follow same-domain links up to this depth "
        "(0 = single page)."
    ),
)
@click.option(
    "--top", "-t",
    default=10,
    show_default=True,
    help="How many of the most frequent words to keep.",
)
@click.option(
    "--mutations/--no-mutations",
    default=True,
    show_default=True,
    help="Generate common password mutations for each word.",
)
@click.option(
    "--seed",
    default=None,
    type=int,
    help="Random seed, for reproducible random suffixes.",
)
def main(
    url: str,
    length: int,
    output: str | None,
    depth: int,
    top: int,
    mutations: bool,
    seed: int | None,
) -> None:
    """抓取网页、提取单词、统计词频，并生成密码变体词表。"""
    if seed is not None:
        random.seed(seed)

    # 1. 抓取页面（单页或按深度爬取）
    pages = crawl_pages(url, depth)
    if not pages:
        click.echo("未能抓取到任何页面，请检查 URL 是否可访问。", err=True)
        sys.exit(1)

    # 2. 汇总所有页面的单词
    all_words: list[str] = []
    for html in pages:
        all_words.extend(extract_words(html))

    # 3. 统计并排序
    top_words = get_top_words_from(all_words, length)

    # 4. 取前 top 个（注意：这里用切片，避免课堂示例的越界崩溃）
    top_words = top_words[:top] if top > 0 else top_words
    if not top_words:
        click.echo("没有满足条件的单词，请调小 --length 后重试。", err=True)
        sys.exit(1)

    # 5. 生成词表
    wordlist = build_wordlist(top_words, mutate=mutations)

    # 6. 输出：写入文件或打印到控制台
    if output:
        with open(output, "w", encoding="utf-8") as writer:
            for word in wordlist:
                writer.write(word + "\n")
        click.echo(f"已写入 {len(wordlist)} 条候选到 {output}", err=True)
    else:
        for word in wordlist:
            click.echo(word)


if __name__ == "__main__":
    main()
