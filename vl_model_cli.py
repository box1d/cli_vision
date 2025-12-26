"""
包豆电脑 - AI 智能控制系统 (命令行版本核心模块)
完全照搬GUI版本逻辑
"""

import os
import base64
import cv2
import numpy as np
from openai import OpenAI
import json
import re
import time
import pyautogui
import pyperclip
import signal
from pydantic import BaseModel
import platform

# 全局退出标志
should_exit = False

# 全局回调函数，用于通知主程序AI输出的坐标
coordinate_callback = None

# 全局上下文历史记录（保存最近3次）
conversation_history = []

current_os = platform.system()

# 命令行日志打印函数
def log_print(*args, **kwargs):
    """命令行日志打印函数"""
    print(*args, **kwargs)

# 设置坐标回调函数
def set_coordinate_callback(callback):
    global coordinate_callback
    coordinate_callback = callback

# 信号处理函数
def signal_handler(sig, frame):
    global should_exit
    log_print("\n收到中断信号，正在优雅退出...")
    should_exit = True

# 设置信号处理器
signal.signal(signal.SIGINT, signal_handler)

# 加载配置文件
def load_config(config_path="config.json"):
    """加载配置文件"""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        log_print(f"成功加载配置文件: {config_path}")
        return config
    except Exception as e:
        log_print(f"加载配置文件失败: {e}")
        return None

# 截图函数
def capture_screen_and_save(save_path="imgs/screen.png", optimize_for_speed=True, max_png=1280):
    """截图并保存"""
    # 创建输出目录
    output_dir = os.path.dirname(save_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    try:
        # 截图
        screenshot = pyautogui.screenshot()
        screenshot_np = np.array(screenshot)
        screenshot_bgr = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)

        scale = 1
        if optimize_for_speed:
            height, width, _ = screenshot_bgr.shape
            max_edge = max(height, width)
            if max_edge > max_png:
                scale = max_png / max_edge
                screenshot_bgr = cv2.resize(screenshot_bgr, None, fx=scale, fy=scale)
        
        # 保存
        save_params = [int(cv2.IMWRITE_PNG_COMPRESSION), 1] if optimize_for_speed else []
        success = cv2.imwrite(save_path, screenshot_bgr, save_params)
        
        return success, scale
    except Exception as e:
        log_print(f"截图失败: {e}")
        return False, 1

# 坐标标记函数
def mark_coordinate_on_image(coordinates, input_path=None, output_path=None, point_radius=10, point_color=(0, 0, 255), thickness=-1):
    """在图片上标记坐标点"""
    if input_path is None:
        input_path = "imgs/screen.png"
    if output_path is None:
        output_path = "imgs/label/screen_label.png"
    
    # 创建输出目录
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    try:
        # 读取图片
        img = cv2.imread(input_path)
        if img is None:
            log_print(f"无法读取图片: {input_path}")
            return False
        
        # 标记坐标点
        if isinstance(coordinates[0], list):
            # 多个坐标点
            for coord in coordinates:
                cv2.circle(img, (int(coord[0]), int(coord[1])), point_radius, point_color, thickness)
        else:
            # 单个坐标点
            cv2.circle(img, (int(coordinates[0]), int(coordinates[1])), point_radius, point_color, thickness)
        
        # 保存标记后的图片
        success = cv2.imwrite(output_path, img)
        if success:
            log_print(f"坐标标记图片已保存: {output_path}")
        return success
        
    except Exception as e:
        log_print(f"标记坐标失败: {e}")
        return False

# 坐标映射（完全照搬GUI版本）
def map_coordinates(x, y, scale, img_width=None, img_height=None):
    """
    将坐标映射到实际屏幕上
    完全照搬GUI版本的逻辑
    """
    # 确保坐标值在合理范围内
    x = max(-100000, min(100000, x))
    y = max(-100000, min(100000, y))
    
    # 如果提供了图像宽高，使用相对坐标到绝对坐标的转换公式
    if img_width and img_height:
        # 将相对坐标转换为绝对坐标
        x_abs = (x / 1000) * img_width
        y_abs = (y / 1000) * img_height
    else:
        # 保持原有逻辑，直接除以缩放比例
        x_abs = x
        y_abs = y
    
    # 应用缩放比例映射到实际屏幕
    x_r = x_abs / scale
    y_r = y_abs / scale
    
    # 确保最终坐标在有效范围内
    x_r = max(0, min(100000, x_r))
    y_r = max(0, min(100000, y_r))
    
    return x_r, y_r

# 移动鼠标到坐标并执行操作（完全照搬GUI版本）
def move_mouse_to_coordinates(coordinates, action, type_information="", scale=1, img_width=None, img_height=None, duration=0.1):
    """
    移动鼠标到指定坐标并执行操作
    完全照搬GUI版本的逻辑
    """
    # 验证坐标有效性的辅助函数
    def validate_coordinate(coord):
        """确保坐标值在合理范围内"""
        if isinstance(coord, (int, float)):
            return max(-100000, min(100000, coord))
        return coord
    
    # 验证并修复坐标
    def fix_coordinates(coords):
        """修复坐标数据，确保其格式正确且值在合理范围内"""
        if isinstance(coords[0], list):
            # 拖拽坐标 [[x1, y1], [x2, y2]]
            return [
                [validate_coordinate(coords[0][0]), validate_coordinate(coords[0][1])],
                [validate_coordinate(coords[1][0]), validate_coordinate(coords[1][1])]
            ]
        else:
            # 单点坐标 [x, y]
            return [validate_coordinate(coords[0]), validate_coordinate(coords[1])]
    
    # 修复坐标
    coordinates = fix_coordinates(coordinates)
    
    action_str = ""
    
    # 处理热键操作
    if action == "hotkey":
        if type_information:
            keys = type_information.split()
            current_os = platform.system()
            if current_os == "Darwin":  # macOS
                keys = ["command" if key == "win" or key == "meta" else key for key in keys]
                keys = ["command" if key == "cmd" else key for key in keys]
            else:  # Windows和其他系统
                keys = ["win" if key == "meta" else key for key in keys]
            
            log_print(f"执行热键操作: {'+'.join(keys)}")
            pyautogui.hotkey(*keys)
            action_str = f"执行热键操作: {'+'.join(keys)}"+"\n"
        else:
            log_print("热键操作但未提供快捷键信息")
        return action_str, None
    
    # 处理拖拽操作
    if action == "drag" and isinstance(coordinates[0], list):
        start_x, start_y = coordinates[0]
        end_x, end_y = coordinates[1]
        
        # 映射坐标
        start_x, start_y = map_coordinates(start_x, start_y, scale, img_width, img_height)
        end_x, end_y = map_coordinates(end_x, end_y, scale, img_width, img_height)
        
        pyautogui.moveTo(start_x, start_y, duration=duration)
        pyautogui.dragTo(end_x, end_y, duration=duration*10)
        log_print(f"已完成拖拽操作: ({start_x}, {start_y}) -> ({end_x}, {end_y})")
        action_str = action_str + f"已完成拖拽操作: ({start_x}, {start_y}) -> ({end_x}, {end_y})"+"\n"
        
        mapped_coordinates = [[start_x, start_y], [end_x, end_y]]
    else:
        # 处理单点操作
        x, y = coordinates
        
        # 映射坐标
        x, y = map_coordinates(x, y, scale, img_width, img_height)
        
        # 移动鼠标
        pyautogui.moveTo(x, y, duration=duration)
        log_print(f"🖱️  移动到坐标: ({x:.0f}, {y:.0f})")
        action_str = f"鼠标已移动到坐标: ({x}, {y})"+"\n"
        
        # 保存映射后的坐标
        mapped_coordinates = [x, y]
        
        # 执行相应操作
        if action == "click":
            pyautogui.click()
            log_print(f"👆 点击完成")
            action_str = action_str + f"已点击 ({x}, {y})"+"\n"
        elif action == "double_click":
            pyautogui.doubleClick()
            log_print(f"已双击 ({x}, {y})")
            action_str = action_str + f"已双击 ({x}, {y})"+"\n" 
        elif action == "long_press":
            pyautogui.mouseDown()
            log_print(f"已长按 ({x}, {y})")
            action_str = action_str + f"已长按 ({x}, {y})"+"\n" 
        elif action == "right_click":
            pyautogui.rightClick()
            log_print(f"已右键点击 ({x}, {y})")
            action_str = action_str + f"已右键点击 ({x}, {y})"+"\n" 
        elif action == "scroll_up":
            pyautogui.scroll(500)
            log_print(f"已向上滚动 ({x}, {y})")
            action_str = action_str + f"已向上滚动 ({x}, {y})"+"\n" 
        elif action == "scroll_down":
            pyautogui.scroll(-500)
            log_print(f"已向下滚动 ({x}, {y})")
            action_str = action_str + f"已向下滚动 ({x}, {y})"+"\n" 
        else:
            log_print(f"未知操作: {action}")
    
    time.sleep(0.2)
    if type_information != "" and action != "hotkey":
        pyperclip.copy(type_information)
        
        # 根据操作系统执行粘贴（照搬GUI版本逻辑）
        current_os = platform.system()
        time.sleep(0.1)
        if current_os == "Darwin":  # macOS
            # macOS上使用更可靠的粘贴方法
            time.sleep(0.2)
            pyautogui.keyDown('command')
            time.sleep(0.1)
            pyautogui.press('v')
            time.sleep(0.1)
            pyautogui.keyUp('command')
        else:  # Windows和其他系统
            pyautogui.hotkey('ctrl', 'v')
        
        log_print(f"⌨️  粘贴文本: {type_information}")
        time.sleep(0.5)
        pyautogui.press('enter')
        action_str = action_str + f"已粘贴文本: {type_information}"+"\n"
    
    return action_str, mapped_coordinates

# 编码图片为base64
def encode_image(image_path):
    """将图片编码为base64格式"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        log_print(f"图片编码失败: {e}")
        return None

# AI响应模型（新格式）
class AIResponse(BaseModel):
    status: str = "in_progress"
    description: str = ""
    target: str = ""
    action: dict = {}
    
    # 兼容旧格式字段
    current_status: str = ""
    whether_completed: str = "False"
    element_info: str = ""
    coordinates: list = []
    type_information: str = ""
    
    def __init__(self, **data):
        # 处理action字段的类型转换
        if 'action' in data and isinstance(data['action'], str):
            # 如果action是字符串，转换为字典格式
            action_str = data['action']
            data['action'] = {
                "type": action_str,
                "coordinates": data.get('coordinates', []),
                "text": data.get('type_information', '')
            }
        elif 'action' not in data or not data['action']:
            # 如果没有action字段，使用默认值
            data['action'] = {
                "type": "wait",
                "coordinates": [0, 0],
                "text": ""
            }
        
        super().__init__(**data)

def parse_ai_response(response_text):
    """解析AI的响应文本"""
    try:
        # 尝试解析JSON格式
        if response_text.strip().startswith('```json'):
            # 提取JSON部分
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                response_data = json.loads(json_str)
            else:
                response_data = {}
        elif response_text.strip().startswith('{'):
            response_data = json.loads(response_text)
        else:
            response_data = {}
        
        # 兼容不同的字段名
        action = response_data.get('action', 'wait')
        coordinate = response_data.get('coordinate', [])
        coordinates = response_data.get('coordinates', [])
        text = response_data.get('text', '')
        type_information = response_data.get('type_information', '')
        reasoning = response_data.get('reasoning', '')
        whether_completed = response_data.get('whether_completed', 'False')
        current_status = response_data.get('current_status', '')
        element_info = response_data.get('element_info', '')
        
        # 处理坐标字符串格式（如"[812, 119]"）
        if isinstance(coordinates, str):
            try:
                coordinates = json.loads(coordinates)
            except:
                coordinates = []
        
        # 如果没有找到JSON，尝试文本解析
        if not response_data:
            action_match = re.search(r'action[:\s]*["\']?([^"\'\n,]+)["\']?', response_text, re.IGNORECASE)
            coordinate_match = re.search(r'coordinate[s]?[:\s]*\[([^\]]+)\]', response_text, re.IGNORECASE)
            text_match = re.search(r'text[:\s]*["\']([^"\']+)["\']', response_text, re.IGNORECASE)
            completed_match = re.search(r'whether_completed[:\s]*["\']?([^"\'\n,]+)["\']?', response_text, re.IGNORECASE)
            
            action = action_match.group(1).strip() if action_match else "wait"
            whether_completed = completed_match.group(1).strip() if completed_match else "False"
            
            if coordinate_match:
                coord_str = coordinate_match.group(1)
                coordinates = [float(x.strip()) for x in coord_str.split(',')]
            
            text = text_match.group(1) if text_match else ""
        
        return AIResponse(
            status=response_data.get('status', 'in_progress'),
            description=response_data.get('description', ''),
            target=response_data.get('target', ''),
            action=response_data.get('action', {}),
            current_status=current_status,
            whether_completed=whether_completed,
            element_info=element_info,
            coordinates=coordinates,
            type_information=type_information or text
        )
        
    except Exception as e:
        log_print(f"解析AI响应失败: {e}")
        log_print(f"响应内容: {response_text}")
        return AIResponse(action="wait", coordinate=[], coordinates=[], text="")

# 主控制函数
def auto_control_computer(user_content):
    """自动控制电脑的主函数"""
    global should_exit
    
    # 加载配置
    config = load_config()
    if not config:
        return "配置加载失败"
    
    # 获取配置参数
    api_key = config["api_config"]["api_key"]
    base_url = config["api_config"]["base_url"]
    model_name = config["api_config"]["model_name"]
    max_iterations = config["execution_config"]["max_visual_model_iterations"]
    
    if not api_key:
        return "API密钥未配置"
    
    # 初始化OpenAI客户端
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    # 读取系统提示（使用新版本prompt）
    system_prompt_file = "get_next_action_AI_doubao_mac_new.txt" if current_os == "Darwin" else "get_next_action_AI_doubao_new.txt"
    
    try:
        # 尝试多种编码方式读取文件
        encodings = ['utf-8', 'utf-8-sig', 'gbk', 'latin1']
        system_prompt = None
        
        for encoding in encodings:
            try:
                with open(system_prompt_file, "r", encoding=encoding, errors='ignore') as f:
                    system_prompt = f.read()
                log_print(f"成功使用 {encoding} 编码读取系统提示文件")
                break
            except UnicodeDecodeError:
                continue
        
        if system_prompt is None:
            log_print("无法读取系统提示文件")
            return "系统提示文件读取失败"
        
        # 清理可能的无效字符
        system_prompt = system_prompt.encode('utf-8', errors='ignore').decode('utf-8')
        
    except Exception as e:
        log_print(f"读取系统提示文件失败: {e}")
        return "系统提示文件读取失败"
    
    log_print(f"开始执行任务: {user_content}")
    log_print(f"最大迭代次数: {max_iterations}")
    
    iteration = 0
    
    while iteration < max_iterations and not should_exit:
        iteration += 1
        log_print(f"\n🔄 === 第 {iteration} 次迭代 ===")
        
        # 截图
        log_print("📸 正在截取屏幕...")
        success, scale = capture_screen_and_save(
            save_path=config["screenshot_config"]["input_path"],
            optimize_for_speed=config["screenshot_config"]["optimize_for_speed"],
            max_png=config["screenshot_config"]["max_png"]
        )
        
        if not success:
            log_print("❌ 截图失败")
            continue
        
        # 获取图片尺寸用于坐标映射
        screenshot_path = config["screenshot_config"]["input_path"]
        img = cv2.imread(screenshot_path)
        if img is not None:
            img_height, img_width = img.shape[:2]
        else:
            img_width = img_height = None
        
        # 编码图片
        base64_image = encode_image(screenshot_path)
        
        if not base64_image:
            log_print("❌ 图片编码失败")
            continue
        
        log_print("🔍 正在调用AI模型分析...")
        
        # 清理用户输入中的无效字符
        clean_user_content = user_content.encode('utf-8', errors='ignore').decode('utf-8')
        
        # 构建消息列表，包含最近3次的上下文
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加历史上下文（最近3次）
        for history_item in conversation_history[-3:]:
            messages.append(history_item["user_message"])
            messages.append(history_item["assistant_message"])
        
        # 添加当前用户消息
        current_user_message = {
            "role": "user",
            "content": [
                {"type": "text", "text": clean_user_content},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                }
            ]
        }
        messages.append(current_user_message)
        
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=1000,
                temperature=0.1
            )
            
            ai_response_text = response.choices[0].message.content
            # 清理AI响应中的无效字符
            ai_response_text = ai_response_text.encode('utf-8', errors='ignore').decode('utf-8')
            log_print(f"🤖 AI原始响应:\n{ai_response_text}")
            
            # 保存到历史记录
            history_item = {
                "user_message": current_user_message,
                "assistant_message": {"role": "assistant", "content": ai_response_text}
            }
            conversation_history.append(history_item)
            
            # 只保留最近3次记录
            if len(conversation_history) > 3:
                conversation_history.pop(0)
            
            # 解析并执行操作
            ai_response = parse_ai_response(ai_response_text)
            
            # 检查任务是否完成（新格式）
            if ai_response.status in ['completed', 'failed']:
                if ai_response.status == 'completed':
                    log_print("✅ 任务完成!")
                    return "任务完成"
                else:
                    log_print("⚠️  任务失败或过于复杂")
                    return "任务失败或过于复杂"
            
            # 显示AI分析结果
            log_print(f"🎯 AI分析: {ai_response.description}")
            log_print(f"🔧 执行操作: {ai_response.action.get('type', 'unknown')}")
            if ai_response.action.get('coordinates'):
                log_print(f"📍 目标坐标: {ai_response.action['coordinates']}")
            
            # 执行操作（使用新格式）
            action_type = ai_response.action.get('type', 'wait')
            coordinates = ai_response.action.get('coordinates', [])
            text = ai_response.action.get('text', '')
            
            if coordinates and len(coordinates) >= 2 and action_type != 'wait':
                action_str, mapped_coordinates = move_mouse_to_coordinates(
                    coordinates, action_type, text, 
                    scale=scale, img_width=img_width, img_height=img_height
                )
                
                # 标记坐标点（照搬GUI版本逻辑）
                if mapped_coordinates:
                    if isinstance(mapped_coordinates[0], list):
                        # 拖拽坐标 [[x1, y1], [x2, y2]]
                        image_coordinates = []
                        for coord in mapped_coordinates:
                            img_x = int(coord[0] * scale)
                            img_y = int(coord[1] * scale)
                            image_coordinates.append([img_x, img_y])
                    else:
                        # 单点坐标 [x, y]
                        img_x = int(mapped_coordinates[0] * scale)
                        img_y = int(mapped_coordinates[1] * scale)
                        image_coordinates = [img_x, img_y]
                    
                    # 生成标记图片
                    output_filename = f"screen_label{iteration}.png"
                    output_path = os.path.join("imgs/label", output_filename)
                    mark_coordinate_on_image(image_coordinates, screenshot_path, output_path)
                
                # 通知坐标回调
                if coordinate_callback and mapped_coordinates:
                    if isinstance(mapped_coordinates[0], list):
                        coordinate_callback(mapped_coordinates[0][0], mapped_coordinates[0][1])
                    else:
                        coordinate_callback(mapped_coordinates[0], mapped_coordinates[1])
            else:
                log_print("⚠️  未提供有效坐标或操作")
                time.sleep(1)
            
        except Exception as e:
            log_print(f"❌ AI调用失败: {e}")
            time.sleep(2)
    
    if should_exit:
        log_print("🛑 用户中断执行")
        return "用户中断执行"
    else:
        log_print(f"⏰ 达到最大迭代次数 ({max_iterations})")
        return f"达到最大迭代次数 ({max_iterations})"
