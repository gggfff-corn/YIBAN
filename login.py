import time
import random
import cv2
import os
import sys
import numpy as np
import configparser
import tiezi
from paddleocr import PaddleOCR
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import traceback

# -------------------------- 全局配置 --------------------------
LOGIN_URL = "https://www.yiban.cn/login?go=https%3A%2F%2Fwww.yiban.cn%2F"
COLOR_HSV_MAP = {
    "红色": [(0, 50, 50), (10, 255, 255), (156, 50, 50), (180, 255, 255)],
    "蓝色": [(80, 40, 40), (130, 255, 255)],
    "绿色": [(35, 50, 50), (77, 255, 255)],
    "黄色": [(20, 50, 50), (34, 255, 255)]
}
PICTURE_DIR = os.path.join(os.getcwd(), "yiban_picture")
if not os.path.exists(PICTURE_DIR):
    os.makedirs(PICTURE_DIR)

# 全局配置对象
CONFIG = None
ACCOUNTS = []
MAX_THREADS = 5

def load_config(config_path='config.ini'):
    """加载配置文件"""
    global CONFIG, ACCOUNTS, MAX_THREADS
    CONFIG = configparser.ConfigParser()
    
    if not os.path.exists(config_path):
        print(f"❌ 配置文件 {config_path} 不存在，请创建配置文件")
        print("配置文件格式示例：")
        print("""[settings]
max_threads = 5

[account_1]
username = 14749891747
password = 123456ab

[account_2]
username = 15883227827
password = password123""")
        sys.exit(1)
    
    CONFIG.read(config_path, encoding='utf-8')
    
    # 加载设置
    if 'settings' in CONFIG:
        MAX_THREADS = CONFIG.getint('settings', 'max_threads', fallback=5)
    
    # 加载账号列表
    ACCOUNTS = []
    for section in CONFIG.sections():
        if section.startswith('account_'):
            try:
                ACCOUNTS.append({
                    'account': CONFIG.get(section, 'username'),
                    'password': CONFIG.get(section, 'password')
                })
            except Exception as e:
                print(f"⚠️  读取账号配置 {section} 失败: {e}")
    
    if not ACCOUNTS:
        print("❌ 配置文件中没有有效的账号信息")
        sys.exit(1)
    
    # 更新线程数
    MAX_THREADS = min(MAX_THREADS, len(ACCOUNTS))
    print(f"✅ 已加载 {len(ACCOUNTS)} 个账号，使用 {MAX_THREADS} 个线程")

# -------------------------- 账号级持久化用户数据目录 --------------------------
def get_account_user_data_dir(account):
    user_data_dir = os.path.join(os.getcwd(), "yiban_user_data", f"account_{account}")
    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir)
    return user_data_dir

# -------------------------- 获取持久化浏览器（复用Cookie，跳过手机号验证） --------------------------
# def get_persistent_browser(account, thread_id):
#     user_data_dir = get_account_user_data_dir(account)
    
#     edge_options = EdgeOptions()
#     edge_options.add_argument(f"--user-data-dir={user_data_dir}")  # 每个账号独立Cookie目录
#     edge_options.add_argument("--disable-blink-features=AutomationControlled")
#     edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
#     edge_options.add_experimental_option("useAutomationExtension", False)
#     edge_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.0.0")
#     edge_options.add_argument("--start-maximized")
#     edge_options.add_argument("--ignore-certificate-errors")

#     driver_path = os.path.join("yiban", "msedgedriver.exe")  # 修改驱动名称
#     service = EdgeService(driver_path)
#     driver = webdriver.Edge(service=service, options=edge_options)
#     driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
#         "source": """Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"""
#     })
#     return driver

# -------------------------- 获取持久化浏览器 --------------------------
def get_persistent_browser(account, thread_id, headless=True):
    user_data_dir = get_account_user_data_dir(account)
    
    edge_options = EdgeOptions()
    edge_options.add_argument(f"--user-data-dir={user_data_dir}")
    edge_options.add_argument("--disable-blink-features=AutomationControlled")
    edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    edge_options.add_experimental_option("useAutomationExtension", False)
    edge_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.0.0")
    edge_options.add_argument("--ignore-certificate-errors")
    
    # 无头模式配置
    if headless:
        edge_options.add_argument("--headless=new")
        edge_options.add_argument("--window-size=1920,1080")
        edge_options.add_argument("--disable-gpu")
        edge_options.add_argument("--no-sandbox")
        edge_options.add_argument("--disable-dev-shm-usage")
        print(f"🔹 线程{thread_id} 使用无头模式")
    else:
        edge_options.add_argument("--start-maximized")
    
    # 根据操作系统选择驱动路径
    if sys.platform.startswith('linux'):
        # Linux 系统，检查多个可能的驱动路径
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "msedgedriver"),
            "/usr/local/bin/msedgedriver",
            "/usr/bin/msedgedriver"
        ]
        driver_path = None
        for path in possible_paths:
            if os.path.exists(path):
                driver_path = path
                break
        if not driver_path:
            print(f"❌ 线程{thread_id} 找不到 EdgeDriver，请安装 msedgedriver")
            return None
    else:
        # Windows 系统
        driver_path = os.path.join("yiban", "msedgedriver.exe")
    
    print(f"🔹 线程{thread_id} 驱动路径: {driver_path}")
    
    if not os.path.exists(driver_path):
        print(f"❌ 线程{thread_id} 驱动文件不存在: {driver_path}")
        return None
    
    service = EdgeService(driver_path)
    driver = webdriver.Edge(service=service, options=edge_options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"""
    })
    return driver

# -------------------------- 快速登录状态检测 --------------------------
def check_login_status(driver):
    """快速检查登录状态"""
    try:
        # 直接访问首页
        driver.get("https://www.yiban.cn/")
        time.sleep(1.5)  # 减少等待时间
        
        # 检查多个可能的登录状态标识
        checks = [
            (By.ID, "y-setting"),  # 设置按钮
            # (By.ID, "y-search"),  # 搜索
            (By.ID, "y-publish"),  # 发布
            (By.LINK_TEXT, "个人中心"),  # 个人中心链接
        ]
        
        for by, value in checks:
            try:
                element = driver.find_element(by, value)
                if element.is_displayed():
                    print("✅ 检测到已登录状态！")
                    return True
            except:
                continue
        
        # 检查登录按钮
        try:
            # login_btn = driver.find_element(By.ID, "login-btn")
            login_btn = driver.find_element(By.CLASS_NAME, "btn-sign sign-in")
            if login_btn.is_displayed():
                print("❌ 未登录，需要执行登录流程")
                return False
        except:
            pass
            
        # 如果都不确定，通过页面标题判断
        if "易班" in driver.title and "发布" not in driver.title:
            print("✅ 通过标题判断未登录")
            return False
            
        print("⚠️ 登录状态不确定，尝试登录")
        return False
        
    except Exception as e:
        print(f"❌ 登录状态检查出错: {e}")
        return False



# -------------------------- 短信验证处理（支持无人值守模式）--------------------------
def handle_sms_verification(driver, unattended_mode=False):
    """
    处理短信验证弹窗
    
    Args:
        driver: WebDriver对象
        unattended_mode: 是否为无人值守模式，True时遇到短信验证会跳过并返回False
    
    Returns:
        True: 验证成功或未检测到验证
        False: 无人值守模式下遇到验证，需要跳过该账号
    """
    try:
        # 检测短信验证弹窗
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.ID, "login-2fa-send"))
        )
        print("\n⚠️  检测到新设备短信验证弹窗！")
        
        # 无人值守模式：直接返回False，表示需要跳过该账号
        if unattended_mode:
            print("🔴 无人值守模式：遇到短信验证，将跳过该账号")
            return False
        
        # 有人值守模式：尝试自动处理
        print("🔵 有人值守模式：尝试自动处理短信验证")
        
        # 自动点击获取验证码按钮
        send_btn = driver.find_element(By.ID, "login-2fa-send")
        if send_btn.is_enabled():
            send_btn.click()
            print("✅ 已自动点击「获取验证码」按钮")
        
        # 提示用户输入
        print("\n📱 请在手机上查看短信验证码")
        
        # 输入验证循环
        sms_code = ""
        while True:
            sms_code = input("   请输入 4 位验证码（直接回车跳过）：").strip()
            
            # 允许直接回车跳过
            if sms_code == "":
                print("ℹ️  跳过自动填充，请手动在浏览器中输入验证码")
                break
            
            # 只保留数字字符（过滤 PowerShell 自动补全的内容）
            sms_code = "".join([c for c in sms_code if c.isdigit()])
            
            # 验证是否为 4 位数字
            if len(sms_code) == 4:
                print(f"✅ 验证码格式正确")
                break
            else:
                print("❌ 格式错误！请输入 4 位数字")
        
        # 如果有输入验证码，自动填充
        if sms_code and len(sms_code) == 4:
            try:
                code_input = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, "login-2fa-code"))
                )
                code_input.clear()
                code_input.send_keys(sms_code)
                print(f"✅ 已自动填充验证码")
                
                submit_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "login-2fa-submit"))
                )
                submit_btn.click()
                print("✅ 已点击「确定」按钮提交验证")
                time.sleep(1)
                
                try:
                    trust_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.ID, "login-2fa-trust"))
                    )
                    trust_btn.click()
                    print("✅ 已点击「信任此设备」，下次登录无需验证")
                except:
                    print("ℹ️  未找到「信任此设备」按钮")
                
                time.sleep(0.5)
                # 检查验证结果
                try:
                    error_elem = driver.find_element(By.CLASS_NAME, "login-2fa-error")
                    if error_elem.is_displayed() and error_elem.text.strip():
                        print(f"❌ 验证失败：{error_elem.text}")
                        print("📋 请手动在浏览器中完成验证...")
                        input("   完成后按回车继续...")
                except:
                    pass
                    
            except Exception as e:
                print(f"⚠️  自动填充失败：{e}")
                print("📋 请手动在浏览器中输入验证码并提交...")
                input("   完成后按回车继续...")
        else:
            print("📋 请手动在浏览器中输入验证码并提交...")
            input("   完成后按回车继续...")
        
        print("✅ 短信验证完成！")
        return True
        
    except Exception as e:
        print("ℹ️  未检测到短信验证弹窗，跳过短信验证")
        return True

# -------------------------- 优化的图形验证登录流程 --------------------------
def login_with_graph_captcha(account, password, thread_id, ocr_instance, unattended_mode=False):
    driver = get_persistent_browser(account, thread_id)
    
    # 检查浏览器是否成功创建
    if not driver:
        print(f"❌ 账号 {account} 无法创建浏览器，跳过任务！")
        return None
    
    # 快速检查登录状态
    if check_login_status(driver):
        print(f"✅ 账号 {account} 已登录，跳过登录流程")
        return driver

    print(f"🔐 账号 {account} 需要登录，开始执行登录流程...")
    
    # 访问登录页
    driver.get(LOGIN_URL)
    time.sleep(1)

    # 填写账号密码
    fill_account_password(driver, account, password)
    time.sleep(0.5)

    # 触发图形验证码
    trigger_captcha(driver)
    time.sleep(0.5)

    # 处理图形验证码
    captcha_success = process_captcha(driver, thread_id, account, ocr_instance)
    
    if not captcha_success:
        print(f"❌ 账号 {account} 图形验证失败，跳过任务！")
        driver.quit()
        return None

    # 处理短信验证（支持无人值守模式）
    sms_result = handle_sms_verification(driver, unattended_mode)
    
    # 无人值守模式下短信验证失败，跳过该账号
    if not sms_result:
        print(f"❌ 账号 {account} 需要短信验证，无人值守模式下跳过！")
        driver.quit()
        return None
    
    # 验证登录是否成功
    time.sleep(1.5)  # 减少等待时间
    driver.get("https://www.yiban.cn/")
    time.sleep(1)
    
    if check_login_status(driver):
        print(f"✅ 账号 {account} 登录成功！")
        return driver
    else:
        print(f"❌ 账号 {account} 登录失败，尝试重新登录...")
        # 重新尝试一次
        driver.get(LOGIN_URL)
        time.sleep(1)
        fill_account_password(driver, account, password)
        time.sleep(0.5)
        driver.find_element(By.ID, "login-btn").click()
        time.sleep(2)
        
        if check_login_status(driver):
            print(f"✅ 账号 {account} 重新登录成功！")
            return driver
        else:
            print(f"❌ 账号 {account} 最终登录失败！")
            driver.quit()
            return None

# -------------------------- 优化验证码处理流程 --------------------------
def process_captcha(driver, thread_id, account, ocr_instance, max_attempts=3):
    """处理验证码的主要流程"""
    for attempt in range(max_attempts):
        print(f"\n🔄 尝试第 {attempt + 1} 次图形验证...")
        
        try:
            # 获取验证码元素
            captcha_img, prompt_element = get_captcha_elements(driver)
            
            # 保存验证码图片
            prompt_file = os.path.join(PICTURE_DIR, f"prompt_{thread_id}_{account}_{attempt}.png")
            captcha_file = os.path.join(PICTURE_DIR, f"captcha_{thread_id}_{account}_{attempt}.png")
            
            prompt_element.screenshot(prompt_file)
            captcha_img.screenshot(captcha_file)
            
            time.sleep(0.3)  # 减少等待时间

            # OCR识别提示文本
            target_color, target_shape = ocr_prompt_text_local(prompt_file, ocr_instance, max_attempts=1)
            
            if not target_color or not target_shape:
                print(f"❌ 第{attempt+1}次OCR识别失败，刷新验证码...")
                refresh_captcha(driver)
                time.sleep(0.5)
                continue

            # 查找目标图形
            target_center = find_smallest_target(captcha_file, target_color, target_shape, thread_id)
            if not target_center:
                print(f"❌ 第{attempt+1}次未找到目标，刷新验证码...")
                refresh_captcha(driver)
                time.sleep(0.5)
                continue

            # 点击目标
            click_target(driver, captcha_img, target_center, thread_id)
            
            # 快速检查验证结果
            time.sleep(1.5)  # 减少等待时间
            
            if is_captcha_success_fast(driver):
                print("✅ 图形验证成功！")
                return True
            else:
                print(f"❌ 第{attempt+1}次验证未通过，刷新验证码...")
                refresh_captcha(driver)
                time.sleep(0.5)
                
        except Exception as e:
            print(f"❌ 验证码处理出错: {e}")
            refresh_captcha(driver)
            time.sleep(0.5)
    
    return False

# -------------------------- 快速验证码成功检测 --------------------------
def is_captcha_success_fast(driver):
    """快速检测验证码是否成功"""
    try:
        # 方法1：检查验证成功文本
        try:
            success_element = WebDriverWait(driver, 1).until(
                EC.presence_of_element_located((By.CLASS_NAME, "shumei_captcha_slide_tips"))
            )
            if "验证成功" in success_element.text:
                return True
        except:
            pass
        
        # 方法2：检查验证码图片是否消失
        try:
            WebDriverWait(driver, 1).until(
                EC.invisibility_of_element_located((By.CLASS_NAME, "shumei_captcha_loaded_img_bg"))
            )
            return True
        except:
            pass
            
        # 方法3：检查登录按钮状态
        try:
            login_btn = driver.find_element(By.ID, "login-btn")
            if "正在登录" in login_btn.text or "登录成功" in login_btn.text:
                return True
        except:
            pass
            
        return False
        
    except Exception as e:
        print(f"验证码成功检测出错: {e}")
        return False

# -------------------------- 辅助函数 --------------------------
def fill_account_password(driver, account, password):
    wait = WebDriverWait(driver, 5)
    account_input = wait.until(EC.presence_of_element_located((By.ID, "account-txt")))
    password_input = wait.until(EC.presence_of_element_located((By.ID, "password-txt")))
    account_input.clear()
    account_input.send_keys(account)
    time.sleep(0.3)
    password_input.clear()
    password_input.send_keys(password)
    time.sleep(0.3)

def trigger_captcha(driver):
    try:
        login_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, "login-btn"))
        )
        login_btn.click()
        time.sleep(0.5)
    except Exception as e:
        print(f"触发验证码出错: {e}")

def get_captcha_elements(driver):
    wait = WebDriverWait(driver, 8)
    captcha_img = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "shumei_captcha_loaded_img_bg")))
    prompt_element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "shumei_captcha_slide_tips")))
    return captcha_img, prompt_element

def ocr_prompt_text_local(prompt_img_path, ocr_instance, max_attempts=1):
    try:
        if not os.path.exists(prompt_img_path):
            print(f"图片不存在: {prompt_img_path}")
            return None, None
            
        colors = ["红色", "蓝色", "黄色", "绿色"]
        shapes = ["三棱柱", "圆柱体", "球体", "三棱锥", "圆锥", "六棱柱", "长方体"]
        
        for attempt in range(max_attempts):
            result = ocr_instance.predict(prompt_img_path)
            raw_text = ""
            
            if result and len(result) > 0:
                for page in result:
                    if isinstance(page, dict) and "rec_texts" in page:
                        raw_text += "".join(page["rec_texts"])
                    elif isinstance(page, list):
                        for line in page:
                            if line and len(line) >= 2:
                                raw_text += line[1][0]
            
            clean_text = "".join([c for c in raw_text if c.isdigit() or '\u4e00' <= c <= '\u9fff'])
            
            # 查找颜色和形状
            target_color = None
            target_shape = None
            
            for color in colors:
                if color in clean_text:
                    target_color = color
                    break
                    
            for shape in shapes:
                if shape in clean_text:
                    target_shape = shape
                    break
            
            if target_color and target_shape:
                print(f"✅ OCR识别结果: {target_color} {target_shape}")
                return target_color, target_shape
                
            time.sleep(0.2)
            
        # 如果自动识别失败，手动输入
        print("❌ OCR识别失败，请手动输入:")
        target_color = input("请输入验证码颜色（红/蓝/绿/黄）: ")
        target_shape = input("请输入验证码形状（如球体/圆柱体）: ")
        return target_color, target_shape
        
    except Exception as e:
        print(f"OCR识别出错: {e}")
        target_color = input("手动输入验证码颜色: ")
        target_shape = input("手动输入验证码形状: ")
        return target_color, target_shape

def find_smallest_target(captcha_img_path, target_color, target_shape, thread_id=0):
    try:
        img = cv2.imread(captcha_img_path)
        if img is None:
            print("验证码图片加载失败")
            return None
            
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask = None
        
        if target_color == "红色":
            lower1, upper1 = COLOR_HSV_MAP[target_color][0], COLOR_HSV_MAP[target_color][1]
            lower2, upper2 = COLOR_HSV_MAP[target_color][2], COLOR_HSV_MAP[target_color][3]
            mask1 = cv2.inRange(hsv, lower1, upper1)
            mask2 = cv2.inRange(hsv, lower2, upper2)
            mask = cv2.bitwise_or(mask1, mask2)
        else:
            lower, upper = COLOR_HSV_MAP[target_color][0], COLOR_HSV_MAP[target_color][1]
            mask = cv2.inRange(hsv, lower, upper)
            
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_contours = []
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 50:
                continue
                
            M = cv2.moments(cnt)
            if M["m00"] == 0:
                continue
                
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
            valid_contours.append((cnt, area, cX, cY))
            
        if not valid_contours:
            print("未找到对应颜色的图形")
            return None
            
        smallest_contour = min(valid_contours, key=lambda x: x[1])
        return (smallest_contour[2], smallest_contour[3])
        
    except Exception as e:
        print(f"查找目标图形出错: {e}")
        return None

def click_target(driver, captcha_img, target_center, thread_id=0):
    try:
        img_loc = captcha_img.location
        img_size = captcha_img.size
        
        # 使用相对坐标点击，避免图片文件读取问题
        click_x = img_loc["x"] + target_center[0] * (img_size["width"] / 300)
        click_y = img_loc["y"] + target_center[1] * (img_size["height"] / 300)
        
        # 确保点击在窗口内
        window_size = driver.get_window_size()
        click_x = max(10, min(click_x, window_size["width"] - 10))
        click_y = max(10, min(click_y, window_size["height"] - 10))
        
        # 模拟人类点击
        actions = ActionChains(driver)
        actions.move_to_element_with_offset(captcha_img, 0, 0)
        actions.move_by_offset(target_center[0] - img_size["width"]/2, 
                             target_center[1] - img_size["height"]/2)
        actions.pause(random.uniform(0.1, 0.3))
        actions.click()
        actions.perform()
        
        print(f"✅ 已点击验证码目标: ({int(target_center[0])}, {int(target_center[1])})")
        
    except Exception as e:
        print(f"点击验证码出错: {e}")

def refresh_captcha(driver):
    try:
        refresh_btn = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "shumei_captcha_footer_refresh_btn"))
        )
        refresh_btn.click()
        time.sleep(1)
    except Exception as e:
        print(f"刷新验证码出错: {e}")

# -------------------------- 签到功能 --------------------------
def click_sign_in(driver):
    try:
        print("开始检查签到状态...")
        driver.get("https://www.yiban.cn/")
        time.sleep(1.5)
        
        sign_element = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((By.ID, "tool-sign"))
        )
        
        if "已签到" in sign_element.text:
            print("✅ 检测到已签到，无需操作")
            return True
            
        sign_element.click()
        time.sleep(1.5)
        
        # 处理可能的问卷
        try:
            options = WebDriverWait(driver, 3).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "survey-option"))
            )
            if options:
                random.choice(options).click()
                time.sleep(0.5)
                
            confirm_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "dialog-confirm"))
            )
            confirm_btn.click()
            print("✅ 问卷提交成功")
            
        except:
            try:
                options = WebDriverWait(driver, 3).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "submit-btn"))
                )
                if options:
                    random.choice(options).click()
                    time.sleep(0.5)
                    
                confirm_btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "submit-btn"))
                )
                confirm_btn.click()
                print("✅ 问卷提交成功（旧结构）")
                
            except:
                print("ℹ️ 未检测到签到问卷，视为签到成功")
                
        return True
        
    except Exception as e:
        print(f"❌ 签到流程出错: {str(e)}")
        return False

# -------------------------- 获取cookies --------------------------
def get_cookies_from_driver(driver):
    try:
        cookies = driver.get_cookies()
        cookies_dict = {cookie["name"]: cookie["value"] for cookie in cookies}
        return cookies_dict
    except Exception as e:
        print(f"获取cookies出错: {e}")
        return {}

# -------------------------- 单个账号任务执行 --------------------------
def run_account_task(account_info, thread_id, unattended_mode=False):
    print(f"\n📌 开始处理账号: {account_info['account']}（线程{thread_id}）")
    if unattended_mode:
        print("🔹 运行模式：无人值守")
    
    # 初始化OCR
    ocr_instance = PaddleOCR(use_textline_orientation=True, lang="ch")
    
    # 登录（传递无人值守模式参数）
    driver = login_with_graph_captcha(account_info["account"], account_info["password"], thread_id, ocr_instance, unattended_mode)
    if not driver:
        print(f"❌ 账号 {account_info['account']} 登录失败，跳过后续任务")
        return
    
    # 执行任务
    try:
        # 1. 签到
        print("➡️ 开始签到任务...")
        sign_result = click_sign_in(driver)
        if sign_result:
            print("✅ 签到任务完成")
        else:
            print("❌ 签到任务失败")
        
        # 2. 点赞评论（需要导入对应模块）
        
        print("➡️ 开始点赞任务...")
        from likecomment import YibanLikeComment
        cookies_dict = get_cookies_from_driver(driver)
        like_comment = YibanLikeComment(cookies_dict, driver, account_info["account"])
        like_comment.run_like_task()
        print("✅ 点赞任务完成")
        
        
        # 3. 发帖（需要导入对应模块）
        
        print("➡️ 开始发帖任务...")
        import tiezi
        tiezi.publish_tiezi(driver, account_info["account"])
        print("✅ 发帖任务完成")
        
        
        # 4. 评论（需要导入对应模块）
        
        print("➡️ 开始评论任务...")
        from comment import YibanCommentFromSavedIds
        cookies_dict = get_cookies_from_driver(driver)
        comment_bot = YibanCommentFromSavedIds(cookies_dict, driver, account_info["account"])
        comment_bot.run_comment_task()
        print("✅ 评论任务完成")
        
        
        print(f"\n🎉 账号 {account_info['account']} 今日所有任务执行完毕！")
        
    except Exception as e:
        print(f"❌ 账号 {account_info['account']} 任务执行出错: {e}")
        traceback.print_exc()
        
    finally:
        # 关闭浏览器
        try:
            driver.quit()
            print(f"✅ 账号 {account_info['account']} 浏览器已关闭")
        except:
            pass

# -------------------------- 主函数 --------------------------
def main():
    # 解析命令行参数
    unattended_mode = "--unattended" in sys.argv or "-u" in sys.argv
    
    print(f"🚀 启动易班多账号每日任务")
    print(f"🔹 运行模式: {'无人值守' if unattended_mode else '有人值守'}")
    print("=" * 50)
    
    # 加载配置文件
    try:
        load_config()
    except Exception as e:
        print(f"❌ 加载配置文件失败: {e}")
        return
    
    if not ACCOUNTS:
        print("❌ 没有配置账号信息，请检查config.ini")
        return
    
    print(f"✅ 已加载 {len(ACCOUNTS)} 个账号，使用 {MAX_THREADS} 个线程")
    
    # 清理旧图片
    try:
        for file in os.listdir(PICTURE_DIR):
            if file.endswith(".png"):
                os.remove(os.path.join(PICTURE_DIR, file))
        print("✅ 已清理旧验证码图片")
    except Exception as e:
        print(f"⚠️ 清理旧图片失败: {e}")
    
    # 执行任务
    try:
        with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            futures = []
            
            for i, account_info in enumerate(ACCOUNTS):
                print(f"📝 提交账号 {account_info['account']} 的任务...")
                future = executor.submit(run_account_task, account_info, i, unattended_mode)
                futures.append(future)
                time.sleep(1)  # 避免同时启动导致冲突
            
            # 等待所有任务完成
            completed = 0
            for i, future in enumerate(futures):
                try:
                    future.result(timeout=300)  # 5分钟超时
                    completed += 1
                    print(f"✅ 任务 {i+1}/{len(futures)} 已完成 ({completed}/{len(futures)})")
                except TimeoutError:
                    print(f"❌ 任务 {i+1} 超时")
                except Exception as e:
                    print(f"❌ 任务 {i+1} 执行出错: {e}")
                    
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断执行")
    except Exception as e:
        print(f"\n❌ 主线程执行出错: {e}")
        traceback.print_exc()
    finally:
        print("\n" + "=" * 50)
        print("🏁 所有账号任务执行完毕！")
       

if __name__ == "__main__":
    main()