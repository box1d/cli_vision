#!/usr/bin/env python3
"""
AI 智能控制系统 (命令行版本)
"""

import json
import os
import signal
import sys
import threading

from vl_model_cli import auto_control_computer, set_coordinate_callback, set_config_path

# 全局控制变量
running = False
stop_event = threading.Event()


def signal_handler(signum, frame):
    """信号处理器，用于优雅退出"""
    global running
    print("\n\n收到退出信号，正在停止AI执行...")
    running = False
    stop_event.set()
    sys.exit(0)


def coordinate_callback(x, y):
    """坐标回调函数"""
    print(f"AI正在操作坐标: ({x:.0f}, {y:.0f})")


def main():
    """主函数"""
    global running

    # 设置信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 设置坐标回调
    set_coordinate_callback(coordinate_callback)

    print("=" * 50)
    print("AI 智能控制系统 (命令行版本)")
    print("=" * 50)
    
    # 让用户选择配置
    print("\n请选择要使用的模型配置：")
    print("1. 智谱 (zhipu)")
    print("2. 豆包 (doubao)")
    
    while True:
        choice = input("请输入选择 (1 或 2): ").strip()
        if choice == "1":
            config_path = "config_zhipu.json"
            print("已选择智谱配置")
            break
        elif choice == "2":
            config_path = "config_doubao.json"
            print("已选择豆包配置")
            break
        else:
            print("无效选择，请输入 1 或 2")
    
    # 设置配置路径
    set_config_path(config_path)

    # 启动时清空label文件夹
    label_dir = "imgs/label"
    if os.path.exists(label_dir):
        for file in os.listdir(label_dir):
            if file.startswith("screen_label") and file.endswith(".png"):
                file_path = os.path.join(label_dir, file)
                try:
                    os.remove(file_path)
                    print(f"删除旧标记图片: {file}")
                except Exception as e:
                    print(f"删除文件失败 {file}: {e}")
        print("已清空之前的标记图片")
    else:
        os.makedirs(label_dir, exist_ok=True)
        print("创建label目录")

    print("\n使用说明:")
    print("- 输入您的需求，AI将自动控制电脑完成任务")
    print("- 输入 'quit' 或 'exit' 退出程序")
    print("- 按 Ctrl+C 可以随时停止AI执行")
    print("-" * 50)

    while True:
        try:
            # 获取用户输入
            print("\n请输入您的需求:")
            user_input = input("> ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["quit", "exit", "q"]:
                print("程序退出")
                break

            # 开始AI执行
            print(f"\n开始执行任务: {user_input}")
            print("=" * 30)

            running = True
            stop_event.clear()

            # 在新线程中执行AI控制
            def run_ai():
                global running
                try:
                    result = auto_control_computer(user_input)
                    if running:
                        print(f"\n任务完成: {result}")
                except Exception as e:
                    if running:
                        print(f"\n执行错误: {e}")
                finally:
                    running = False

            ai_thread = threading.Thread(target=run_ai, daemon=True)
            ai_thread.start()

            # 等待AI执行完成或用户中断
            try:
                while running and ai_thread.is_alive():
                    ai_thread.join(timeout=0.1)
            except KeyboardInterrupt:
                print("\n用户中断执行")
                running = False
                stop_event.set()

            print("=" * 30)

        except KeyboardInterrupt:
            print("\n\n程序退出")
            break
        except Exception as e:
            print(f"程序错误: {e}")


if __name__ == "__main__":
    main()
