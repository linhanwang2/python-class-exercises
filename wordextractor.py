#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""网页单词提取（课堂练习一）

抓取网页 -> 提取单词 -> 统计词频 -> 排序 -> 生成密码变体 -> 输出
"""

import random
import re
import sys
from datetime import datetime
from urllib.parse import urljoin, urlparse

import click
import requests
from bs4 import BeautifulSoup


def get_html_of(url):
    """下载网页，返回 HTML 文本。"""
    resp = requests.get(url, timeout=10)
    if resp.status_code != 200:
        print(f'HTTP status code of {resp.status_code} returned, '
              f'but 200 was expected. Exiting...')
        sys.exit(1)
    return resp.content.decode(errors='replace')


def get_all_words_from(html):
    """从 HTML 文本中提取所有单词。"""
    soup = BeautifulSoup(html, 'html.parser')
    raw_text = soup.get_text()
    return re.findall(r'\w+', raw_text)


def count_occurrences_in(word_list, min_length):
    """统计词频，忽略长度小于 min_length 的单词。"""
    word_count = {}
    for word in word_list:
        if len(word) < min_length:
            continue
        if word not in word_count:
            word_count[word] = 1
        else:
            current_count = word_count.get(word)
            word_count[word] = current_count + 1
    return word_count


def get_top_words_from(all_words, min_length):
    """按词频从高到低排序，返回 (单词, 次数) 列表。"""
    occurrences = count_occurrences_in(all_words, min_length)
    return sorted(occurrences.items(), key=lambda item: item[1], reverse=True)


def crawl_pages(start_url, max_depth):
    """按同一域名、广度优先抓取页面，返回各页面 HTML 列表。"""
    domain = urlparse(start_url).netloc
    visited = []
    queue = [(start_url, 0)]
    pages = []

    while queue:
        url, level = queue.pop(0)
        if url in visited:
            continue
        visited.append(url)

        try:
            html = get_html_of(url)
        except requests.RequestException:
            continue

        pages.append(html)

        if level >= max_depth:
            continue

        soup = BeautifulSoup(html, 'html.parser')
        for link in soup.find_all('a', href=True):
            next_url = urljoin(url, link['href'])
            parsed = urlparse(next_url)
            if parsed.scheme not in ('http', 'https'):
                continue
            if parsed.netloc != domain:
                continue
            if next_url not in visited:
                queue.append((next_url, level + 1))

    return pages


def make_variants(word):
    """为一个单词生成常见密码变体。"""
    suffixes = []

    # 近年年份
    for year in range(2019, datetime.now().year + 1):
        suffixes.append(str(year))

    # 常见数字与数字符号
    suffixes += ['1', '01', '12', '123', '1234', '1!', '2!', '3!']

    # 常见符号
    suffixes += ['!', '@', '#', '$', '.', '?']

    # 随机数字
    for _ in range(3):
        suffixes.append(str(random.randint(1, 9999)))

    bases = [word, word.lower(), word.upper(), word.capitalize()]

    variants = []
    for base in bases:
        if base not in variants:
            variants.append(base)
        for suffix in suffixes:
            item = base + suffix
            if item not in variants:
                variants.append(item)

    return variants


def build_wordlist(top_words, mutate):
    """把高频词变成最终词表，每行一个候选。"""
    wordlist = []
    for word, count in top_words:
        if mutate:
            wordlist += make_variants(word)
        else:
            wordlist.append(word)
    return wordlist


@click.command()
@click.option('--url', '-u', prompt='Web URL',
              help='URL of webpage to extract from.')
@click.option('--length', '-l', default=0, show_default=True,
              help='Minimum word length (default: 0, no limit).')
@click.option('--output', '-o', default=None,
              help='Output file. Write results here instead of the console.')
@click.option('--depth', '-d', default=0, show_default=True,
              help='Crawl depth (0 = single page).')
@click.option('--top', '-t', default=10, show_default=True,
              help='How many of the most frequent words to keep.')
@click.option('--mutations/--no-mutations', default=True, show_default=True,
              help='Generate common password mutations for each word.')
@click.option('--seed', default=None,
              help='Random seed, for reproducible random suffixes.')
def main(url, length, output, depth, top, mutations, seed):
    """抓取网页、提取单词、统计词频，并生成密码变体词表。"""
    if seed is not None:
        random.seed(int(seed))

    # 1. 抓取页面
    if depth > 0:
        pages = crawl_pages(url, depth)
    else:
        pages = [get_html_of(url)]

    if not pages:
        print('没有抓到任何页面，请检查 URL。')
        sys.exit(1)

    # 2. 提取所有单词
    all_words = []
    for html in pages:
        all_words += get_all_words_from(html)

    # 3. 统计词频并排序
    top_words = get_top_words_from(all_words, length)

    # 4. 只取前 top 个。
    #    课堂示例这里是 for i in range(10): print(top_words[i][0])
    #    单词不足 10 个时会越界，这就是 IndexError 的原因。
    if top > 0:
        top_words = top_words[:top]

    if not top_words:
        print('没有满足条件的单词，请调小 --length 后重试。')
        sys.exit(1)

    # 5. 生成词表
    wordlist = build_wordlist(top_words, mutations)

    # 6. 输出
    if output:
        with open(output, 'w', encoding='utf-8') as f:
            for word in wordlist:
                f.write(word + '\n')
        print(f'已写入 {len(wordlist)} 条候选到 {output}')
    else:
        for word in wordlist:
            print(word)


if __name__ == '__main__':
    main()
