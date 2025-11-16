# -*- coding: utf-8 -*-
"""
@Author: Yuheng Feng

@Date: 2025/11/16 11:33

@Description: FireRedASR实时ASR推理windows本地客户端，本地音频采集并通过websocket发送到服务器
"""
import asyncio
import struct
import argparse
import sys
import configparser
import os
from datetime import datetime

import websockets
import sounddevice as sd

SAMPLE_RATE = 16000


def load_config(config_path: str) -> argparse.Namespace:
    """
    从.cfg文件加载客户端配置

    Args:
        config_path: 配置文件路径

    Returns:
        args: 包含配置参数的Namespace对象
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    config = configparser.ConfigParser()
    config.read(config_path, encoding='utf-8')

    server = config.get('client', 'server')
    frame_duration = config.getfloat('client', 'frame_duration')

    args = argparse.Namespace(
        server=server,
        frame_duration=frame_duration
    )

    return args


async def send_audio(uri: str, frame_duration: float):
    """
    采集音频并通过websocket发送到服务器
    :param uri: 服务器地址
    :param frame_duration: 每帧音频长度(秒)
    :return:
    """
    samples_per_frame = int(SAMPLE_RATE * frame_duration)
    print("=" * 60)
    print(f"[配置] 采样率={SAMPLE_RATE}Hz, 帧长度={frame_duration}s")
    print(f"[配置] 每帧采样数={samples_per_frame}")
    print("=" * 60)

    try:
        async with websockets.connect(
                uri,
                ping_interval=20,
                ping_timeout=20,
                max_size=None
        ) as ws:
            print(f"[连接] 已连接到服务器: {uri}")
            print("=" * 60)

            # 异步接收服务器消息
            async def receive_results():
                try:
                    async for message in ws:
                        if message.startswith("SUBMIT|"):
                            uttid = message.split("|")[1]
                            print(f"[提交] {uttid} 已提交推理")
                        elif message.startswith("RESULT|"):
                            parts = message.split("|", 2)
                            uttid = parts[1]
                            text = parts[2]
                            timestamp = datetime.now().strftime("%H:%M:%S")
                            print(f"\n{'=' * 60}")
                            print(f"[识别] [{timestamp}] {uttid}")
                            print(f"文本: {text}")
                            print("=" * 60 + "\n")
                except websockets.ConnectionClosed:
                    print("[接收] 连接已关闭")

            # 启动接收协程
            receive_task = asyncio.create_task(receive_results())

            # 音频回调函数
            def audio_callback(indata, frames, time_info, status):
                if status:
                    print(f"[录音警告] {status}", file=sys.stderr)

                # 转换 float32 -> int16
                pcm16 = (indata[:, 0] * 32767).astype("int16")

                # 打包为字节流
                payload = struct.pack("<" + "h" * len(pcm16), *pcm16)

                # 发送到服务器
                asyncio.run_coroutine_threadsafe(ws.send(payload), loop)

            # 启动录音流
            print("[录音] 开始录音... (按 Ctrl+C 停止)\n")
            with sd.InputStream(
                    samplerate=SAMPLE_RATE,
                    channels=1,
                    dtype="float32",
                    blocksize=samples_per_frame,
                    callback=audio_callback
            ):
                try:
                    await receive_task
                except asyncio.CancelledError:
                    pass

    except websockets.exceptions.WebSocketException as e:
        print(f"\n[错误] WebSocket连接失败: {e}")
        print("请检查:")
        print("  1. 服务器是否已启动")
        print("  2. 服务器地址和端口是否正确")
        print("  3. 网络连接是否正常")

    except KeyboardInterrupt:
        print("\n[停止] 用户中断录音")

    except Exception as e:
        print(f"\n[错误] {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FireRedASR 流式音频客户端")
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="配置文件路径 (如: client.cfg)"
    )

    cmd_args = parser.parse_args()

    # 加载配置
    try:
        args = load_config(cmd_args.config)
        print(f"\n[配置] 已加载: {cmd_args.config}")
        print(f"[配置] 服务器: {args.server}")
        print(f"[配置] 帧长度: {args.frame_duration}s\n")
    except Exception as e:
        print(f"[错误] 配置加载失败: {e}")
        exit(1)

    # 检查sounddevice可用性
    print("可用音频设备:")
    print(sd.query_devices())
    print()

    # 运行客户端
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(send_audio(args.server, args.frame_duration))
    except KeyboardInterrupt:
        print("\n程序已退出")
