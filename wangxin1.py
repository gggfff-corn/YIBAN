import time
import random
import cv2
import os
import sys
import numpy as np
from PIL import Image
from paddleocr import PaddleOCR
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
import tiezi
import configparser

# 全局初始化PaddleOCR（只加载一次，提升效率）
ocr = PaddleOCR(
    use_textline_orientation=True,
    lang="ch"
)

# 配置参数
TARGET_URL = "https://www.yiban.cn/login?go=https%3A%2F%2Fwww.yiban.cn%2F"

# 全局配置
CONFIG = None

def load_config(config_path='config.ini'):
    """加载配置文件"""
    global CONFIG
    CONFIG = configparser.ConfigParser()
    if os.path.exists(config_path):
        CONFIG.read(config_path, encoding='utf-8')
    else:
        print(f"配置文件 {config_path} 不存在，请创建配置文件")
        sys.exit(1)

def get_account_password():
    """从配置文件获取账号密码"""
    try:
        account = CONFIG.get('account', 'username')
        password = CONFIG.get('account', 'password')
        return account, password
    except Exception as e:
        print(f"读取账号密码失败：{str(e)}")
        sys.exit(1)

# 颜色-HSV映射表
COLOR_HSV_MAP = {
    "红色": [(0, 50, 50), (10, 255, 255), (156, 50, 50), (180, 255, 255)],
    "蓝色": [(80, 40, 40), (130, 255, 255)],
    "绿色": [(35, 50, 50), (77, 255, 255)],
    "黄色": [(20, 50, 50), (34, 255, 255)]
}

def get_shape_rules(cnt, area, perimeter):
    epsilon = 0.03 * perimeter
    approx = cv2.approxPolyDP(cnt, epsilon, True)
    edge_count = len(approx)
    
    x, y, w, h = cv2.boundingRect(cnt)
    rect_area = w * h
    rectangularity = area / rect_area if rect_area != 0 else 0
    
    circularity = 4 * np.pi * area / (perimeter**2) if perimeter != 0 else 0
    
    return {
        "球体": circularity > 0.85,
        "圆柱体": (edge_count == 4 and rectangularity > 0.7) and (0.3 < h / w < 3),
        "长方体": edge_count == 4 and rectangularity > 0.9 and 0.3 < h / w < 3,
        "六棱柱": edge_count == 6 and 0.3 < h / w < 3,
        "三棱柱": (edge_count == 3 or edge_count == 6) and 0.5 < h / w < 2,
        "圆锥": (2 <= edge_count <= 4) and circularity > 0.4 and h / w > 0.8,
        "三棱锥": edge_count == 3 and h / w > 0.8 and rectangularity < 0.7
    }


def init_browser(headless=True):
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # 无头模式配置
    if headless:
        chrome_options.add_argument("--headless=new")
        print("使用无头浏览器模式")
    else:
        chrome_options.add_argument("--start-maximized")

    # 根据操作系统选择驱动路径
    if sys.platform.startswith('linux'):
        driver_path = os.path.join(os.path.dirname(__file__), "chromedriver")
    else:
        driver_path = os.path.join("yiban", "chromedriver.exe")
    
    print(f"驱动路径：{os.path.abspath(driver_path)}")
    
    if not os.path.exists(driver_path):
        print(f"错误：驱动文件不存在 - {driver_path}")
        sys.exit(1)
    
    service = ChromeService(driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })
    driver.get(TARGET_URL)
    time.sleep(random.uniform(1, 2))
    return driver


# 已在配置文件部分定义了 get_account_password 函数


def fill_account_password(driver, account, password):
    wait = WebDriverWait(driver, 10)
    account_input = wait.until(EC.presence_of_element_located((By.ID, "account-txt")))
    password_input = wait.until(EC.presence_of_element_located((By.ID, "password-txt")))
    
    account_input.clear()
    account_input.send_keys(account)
    time.sleep(1)
    password_input.clear()
    password_input.send_keys(password)
    time.sleep(1)


def trigger_captcha(driver):
    wait = WebDriverWait(driver, 10)
    login_btn = wait.until(EC.element_to_be_clickable((By.ID, "login-btn")))
    login_btn.click()
    time.sleep(1)


def get_captcha_elements(driver):
    wait = WebDriverWait(driver, 15)
    captcha_img = wait.until(EC.presence_of_element_located(
        (By.CLASS_NAME, "shumei_captcha_loaded_img_bg")
    ))
    prompt_element = wait.until(EC.presence_of_element_located(
        (By.CLASS_NAME, "shumei_captcha_slide_tips")
    ))
    return captcha_img, prompt_element


def ocr_prompt_text(prompt_img_path, max_attempts=3):  # 建议max_attempts=3提升识别成功率
    """复用全局OCR实例，增加多次识别投票机制"""
    try:
        if not os.path.exists(prompt_img_path):
            print(f"提示文字图片不存在：{prompt_img_path}")
            return None, None
        
        colors = ["红色", "蓝色", "黄色", "绿色"]
        shapes = ["三棱柱", "圆柱体", "球体", "三棱锥", "圆锥", "六棱柱", "长方体"]
        color_candidates = []
        shape_candidates = []
        
        # 复用全局ocr实例，不再重复初始化
        for attempt in range(max_attempts):
            print(f"\n第{attempt+1}次识别：")
            result = ocr.ocr(prompt_img_path)  # 直接使用全局ocr
            
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
            print(f"清洗后文本：{clean_text}")
            
            curr_color = None
            curr_shape = None
            for color in colors:
                for shape in shapes:
                    if f"{color}{shape}" in clean_text:
                        curr_color = color
                        curr_shape = shape
                        break
                if curr_color:
                    break
            if not curr_color:
                for color in colors:
                    if color in clean_text:
                        curr_color = color
                        break
            if not curr_shape:
                for shape in shapes:
                    if shape in clean_text:
                        curr_shape = shape
                        break
            
            color_candidates.append(curr_color)
            shape_candidates.append(curr_shape)
            print(f"第{attempt+1}次提取：颜色={curr_color}，形状={curr_shape}")
            time.sleep(0.5)
        
        from collections import Counter
        valid_colors = [c for c in color_candidates if c is not None]
        valid_shapes = [s for s in shape_candidates if s is not None]
        
        final_color = Counter(valid_colors).most_common(1)[0][0] if valid_colors else None
        final_shape = Counter(valid_shapes).most_common(1)[0][0] if valid_shapes else None
        
        if not final_color or not final_shape:
            print("多次识别仍失败，请手动输入目标：")
            final_color = input("目标颜色（红色/蓝色/黄色/绿色）：")
            final_shape = input("目标形状（三棱柱/圆柱体/球体等）：")
            if final_color not in colors or final_shape not in shapes:
                print("输入无效，终止流程")
                return None, None
        
        return final_color, final_shape
    
    except Exception as e:
        print(f"OCR识别过程出错：{str(e)}")
        colors = ["红色", "蓝色", "黄色", "绿色"]
        shapes = ["三棱柱", "圆柱体", "球体", "三棱锥", "圆锥", "六棱柱", "长方体"]
        final_color = input("目标颜色：")
        final_shape = input("目标形状：")
        return (final_color, final_shape) if final_color in colors and final_shape in shapes else (None, None)

def extract_target_from_prompt(text):
    # 定义常见提示模板
    templates = [
        "点击图中最小的{color}{shape}",
        "请点击最小的{color}{shape}",
        "{color}{shape}，最小的那个"
    ]
    # 颜色和形状列表
    colors = ["红色", "蓝色", "黄色", "绿色"]
    shapes = ["三棱柱", "圆柱体", "球体", "六棱柱", "长方体"]
    
    for template in templates:
        for color in colors:
            for shape in shapes:
                if template.format(color=color, shape=shape) in text:
                    return color, shape
    return None, None

# 在ocr_prompt_text中调用
text = "提取到的OCR文字"
target_color, target_shape = extract_target_from_prompt(text)

# def find_smallest_target(captcha_img_path, target_color, target_shape):
#     try:
#         print(f"开始查找目标：{target_color}{target_shape}")
#         img = cv2.imread(captcha_img_path)
#         if img is None:
#             print("验证码图片加载失败")
#             return None
        
#         hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
#         img_h, img_w = img.shape[:2]  # 获取图片尺寸用于边缘过滤
        
#         # 颜色筛选
#         mask = None
#         if target_color == "红色":
#             lower1, upper1 = COLOR_HSV_MAP[target_color][0], COLOR_HSV_MAP[target_color][1]
#             lower2, upper2 = COLOR_HSV_MAP[target_color][2], COLOR_HSV_MAP[target_color][3]
#             mask1 = cv2.inRange(hsv, lower1, upper1)
#             mask2 = cv2.inRange(hsv, lower2, upper2)
#             mask = cv2.bitwise_or(mask1, mask2)
#         else:
#             lower, upper = COLOR_HSV_MAP[target_color][0], COLOR_HSV_MAP[target_color][1]
#             mask = cv2.inRange(hsv, lower, upper)
        
#         # 轮廓提取（改用RETR_CCOMP保留所有层级轮廓）
#         contours, _ = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
#         print(f"颜色筛选后找到轮廓数量：{len(contours)}")
        
#         valid_contours = []
#         for i, cnt in enumerate(contours):
#             area = cv2.contourArea(cnt)
#             if area < 20:  # 降低面积阈值，避免漏检小目标
#                 print(f"轮廓{i}面积过小（{area}），跳过")
#                 continue
                
#             perimeter = cv2.arcLength(cnt, True)
#             if perimeter == 0:
#                 continue
                
#             # 形状匹配（核心：恢复形状判断）
#             shape_matches = get_shape_rules(cnt, area, perimeter)
#             if not shape_matches.get(target_shape, False):
#                 print(f"轮廓{i}形状不匹配{target_shape}，跳过")
#                 continue
                
#             # 计算中心坐标并过滤边缘目标
#             M = cv2.moments(cnt)
#             if M["m00"] == 0:
#                 continue
#             cX = int(M["m10"] / M["m00"])
#             cY = int(M["m01"] / M["m00"])
            
#             # 目标中心距离边缘至少10px
#             if cX < 10 or cX > img_w - 10 or cY < 10 or cY > img_h - 10:
#                 print(f"轮廓{i}中心({cX},{cY})靠近边缘，跳过")
#                 continue
                
#             valid_contours.append((cnt, area, cX, cY))
#             print(f"轮廓{i}有效：面积{area}，中心({cX},{cY})")
        
#         if not valid_contours:
#             print("未找到有效轮廓")
#             return None
        
#         # 找到最小面积的轮廓
#         smallest = min(valid_contours, key=lambda x: x[1])
#         cnt, area, cX, cY = smallest
#         print(f"找到最小目标：面积{area}，中心({cX},{cY})")
#         return (cX, cY)
        
#     except Exception as e:
#         print(f"目标查找出错：{str(e)}")
#         return None
        
def find_smallest_target(captcha_img_path, target_color, target_shape):
    try:
        print(f"开始查找目标：{target_color}{target_shape}")
        img = cv2.imread(captcha_img_path)
        if img is None:
            print("验证码图片加载失败")
            return None
        
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # 颜色筛选
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
        
        # 轮廓提取
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        print(f"颜色筛选后找到轮廓数量：{len(contours)}")
        
        valid_contours = []
        for i, cnt in enumerate(contours):
            area = cv2.contourArea(cnt)
            # 修复：正确缩进，只有面积过小的才跳过
            if area < 50:
                print(f"轮廓{i}面积过小（{area}），跳过")
                continue
                
            perimeter = cv2.arcLength(cnt, True)
            if perimeter == 0:
                continue
                
            # 计算中心坐标
            M = cv2.moments(cnt)
            if M["m00"] == 0:
                continue
                
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
            
            valid_contours.append((cnt, area, cX, cY))
            print(f"轮廓{i}有效：面积{area}，中心({cX},{cY})")
        
        if not valid_contours:
            print("未找到有效轮廓")
            return None
        
        # 找到最小面积的轮廓
        smallest = min(valid_contours, key=lambda x: x[1])
        cnt, area, cX, cY = smallest
        print(f"找到最小目标：面积{area}，中心({cX},{cY})")
        return (cX, cY)
        
    except Exception as e:
        print(f"目标查找出错：{str(e)}")
        return None
# 2. 形状判断辅助函数（根据轮廓特征判断形状）
def get_shape_rules(cnt, area, perimeter):
    """判断轮廓是否匹配目标形状（长方体/圆形/三角形等）"""
    shape_matches = {
        "长方体": False,  # 2D表现为矩形
        "圆形": False,
        "三角形": False
    }
    # 轮廓近似（减少点数，方便判断边数）
    approx = cv2.approxPolyDP(cnt, 0.02 * perimeter, True)
    # 矩形（长方体2D）：4条边，且长宽比合理（非细长）
    if len(approx) == 4:
        x, y, w, h = cv2.boundingRect(approx)
        aspect_ratio = float(w) / h
        if 0.5 < aspect_ratio < 2:  # 排除过于细长的矩形
            shape_matches["长方体"] = True
    # 圆形：轮廓近似边数多（>8），且面积与外接圆面积比接近1
    elif len(approx) > 8:
        (x, y), radius = cv2.minEnclosingCircle(cnt)
        circle_area = np.pi * radius **2
        if 0.7 < area / circle_area < 1.3:  # 面积比在合理范围
            shape_matches["圆形"] = True
    # 三角形：3条边
    elif len(approx) == 3:
        shape_matches["三角形"] = True
    return shape_matches

def click_target(driver, captcha_img, target_center):
    try:
        print(f"准备点击目标中心：{target_center}")
        img_loc = captcha_img.location
        img_size = captcha_img.size
        img_real = cv2.imread("captcha_img.png")
        img_h, img_w = img_real.shape[:2]
        
        scale_x = img_size["width"] / img_w
        scale_y = img_size["height"] / img_h
        click_x = img_loc["x"] + target_center[0] * scale_x
        click_y = img_loc["y"] + target_center[1] * scale_y
        
        # 获取浏览器窗口大小，强制限制坐标在范围内
        window_size = driver.get_window_size()
        max_x = window_size["width"] - 10  # 留10像素余量
        max_y = window_size["height"] - 10
        click_x = max(10, min(click_x, max_x))
        click_y = max(10, min(click_y, max_y))
        
        print(f"计算点击坐标（已限制在窗口内）：({click_x}, {click_y})")
        actions = ActionChains(driver)
        actions.move_by_offset(
            click_x + random.uniform(-2, 2),
            click_y + random.uniform(-2, 2)
        ).pause(random.uniform(0.2, 0.5)).click().perform()
        print("点击完成")
    
    except Exception as e:
        print(f"点击目标出错：{str(e)}")

# 2. 修复签到判断逻辑（确保正确识别已签到状态）
def click_sign_in(driver):
    """检查签到状态，未签到则处理问卷"""
    try:
        print("开始检查签到状态...")
        # 优化：直接定位签到按钮（避免父元素定位失败）
        sign_element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "tool-sign"))
        )
        
        # 检查按钮是否包含"已签到"相关样式（如class或文本）
        # 方案1：通过父元素class判断（兼容原逻辑）
        try:
            sign_li_element = sign_element.find_element(By.XPATH, "./parent::li")
            if "sign-done" in sign_li_element.get_attribute("class"):
                print("检测到已签到，无需重复操作")
                return
        except:
            print("父元素定位失败，尝试直接判断按钮状态")
        
        # 方案2：通过按钮文本或禁用状态判断（备选方案）
        if "已签到" in sign_element.text or not sign_element.is_enabled():
            print("检测到已签到，无需重复操作")
            return
        
        # 未签到：点击并处理问卷
        print("未检测到已签到，点击签到按钮...")
        sign_element.click()
        time.sleep(2)  # 等待问卷弹窗加载
        random_choose_survey(driver)
    
    except Exception as e:
        print(f"签到流程出错：{str(e)}")


# 3. 问卷处理函数（保持不变，增加容错）
def random_choose_survey(driver):
    try:
        print("开始处理签到问卷...")
        # 等待选项加载（增加显式等待，确保元素可点击）
        options = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "survey-option"))
        )
        # 定位所有选项（兼容多个选项的情况）
        options = driver.find_elements(By.CLASS_NAME, "survey-option")
        print(f"找到{len(options)}个可选答案，随机选择...")
        if options:
            random.choice(options).click()
            time.sleep(1)
        
        # 点击完成按钮（兼容不同class名，如"submit-btn"）
        try:
            confirm_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "dialog-confirm"))
            )
        except:
            confirm_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "submit-btn"))
            )
        confirm_btn.click()
        print("问卷提交成功")
        time.sleep(2)
    except Exception as e:
        print(f"处理问卷时出错：{str(e)}")



import requests

def check_login_status_api(driver):
    """通过登录状态接口验证是否登录（返回True/False）"""
    try:
        # 从浏览器中获取登录Cookie（保持会话一致）
        cookies = driver.get_cookies()
        cookie_dict = {cookie["name"]: cookie["value"] for cookie in cookies}
        
        # 调用登录状态接口
        login_api = "https://minyaun.yiban.cn/ajax/my/getLogin"
        response = requests.get(login_api, cookies=cookie_dict, timeout=5)
        response_json = response.json()
        
        # 假设接口返回{"code":200, "data":{"isLogin":true}}表示登录成功
        if response_json.get("code") == 200 and response_json.get("data", {}).get("isLogin"):
            print("登录状态接口验证：已登录")
            return True
        else:
            print(f"登录状态接口验证：未登录（响应：{response_json}）")
            return False
    except Exception as e:
        print(f"调用登录状态接口出错：{str(e)}")
        return False

# 3. 检测是否为未登录页面（核心：根据你提供的URL和文本）
def is_need_login_page(driver):
    """检测当前页面是否是未登录页面（模糊匹配更容错）"""
    try:
        # 模糊匹配URL（避免精确匹配的空格/参数问题）
        if "needlogin" in driver.current_url:
            return True
        # 检测"您还没登录"文本
        coming_soon = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.ID, "coming-soon"))
        )
        if "您还没登录" in coming_soon.text:
            return True
        return False
    except:
        return False

def is_captcha_success(driver):
    """多方式检测验证是否成功"""
    try:
        # 方式1：检测验证成功提示
        success_element = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '验证成功')]"))
        )
        if success_element:
            print("检测到验证成功提示")
            return True
    except:
        pass
    
    try:
        # 方式2：检测验证码弹窗是否消失
        WebDriverWait(driver, 5).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, "shumei_captcha_loaded_img_bg"))
        )
        print("验证码弹窗已消失，认为验证成功")
        return True
    except:
        pass
    
    try:
        # 方式3：检测是否跳转到目标页面
        if "minyaun.yiban.cn" in driver.current_url or "www.yiban.cn" in driver.current_url:
            print("已跳转到目标页面，认为验证成功")
            return True
    except:
        pass
    
    return False

# 4. 主流程（整合周期刷新机制）
def main():
    driver = None
    max_total_attempts = 20
    cycle_attempts = 3
    total_attempts = 0
    login_and_captcha_success = False

    try:
        # 加载配置文件
        load_config()
        
        account, password = get_account_password()
        driver = init_browser()
        fill_account_password(driver, account, password)  # 假设已实现
        trigger_captcha(driver)  # 假设已实现

        while total_attempts < max_total_attempts:
            for cycle in range(cycle_attempts):
                current_attempt = total_attempts + 1
                print(f"\n=== 总第{current_attempt}次验证（周期内第{cycle+1}/{cycle_attempts}次） ===")
                
                # 1. 截图并识别验证码（原有逻辑）
                captcha_img, prompt_element = get_captcha_elements(driver)  # 假设已实现
                prompt_element.screenshot("prompt_text.png")
                captcha_img.screenshot("captcha_img.png")
                time.sleep(random.uniform(0.8, 1.2))
                
                # 2. OCR识别目标（原有逻辑）
                target_color, target_shape = ocr_prompt_text("prompt_text.png", max_attempts=1)  # 假设已实现
                if not target_color or not target_shape:
                    print("无法提取目标，刷新验证码...")
                    refresh_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CLASS_NAME, "shumei_captcha_footer_refresh_btn"))
                    )
                    refresh_btn.click()
                    total_attempts += 1
                    time.sleep(1)
                    continue
                
                # 3. 定位并点击目标（原有逻辑）
                target_center = find_smallest_target("captcha_img.png", target_color, target_shape)  # 假设已实现
                if not target_center:
                    print("未找到目标，刷新验证码...")
                    refresh_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CLASS_NAME, "shumei_captcha_footer_refresh_btn"))
                    )
                    refresh_btn.click()
                    total_attempts += 1
                    time.sleep(1)
                    continue
                
                click_target(driver, captcha_img, target_center)
                time.sleep(2)  # 等待验证反馈
                if is_captcha_success(driver):
                    print("验证成功，检查登录状态...")
                else:
                    print("未检测到验证成功提示，本次尝试失败...")
                time.sleep(1)
                # 4. 双验证：既弹窗消失，又有“验证成功”提示
                if is_captcha_success(driver):
                    print("检测到验证成功提示，检查登录状态...")
                    # 检查是否跳转到未登录页面
                    if is_need_login_page(driver):
                        print("验证成功但跳转到未登录页面，刷新重登...")
                        driver.refresh()
                        time.sleep(3)
                        fill_account_password(driver, account, password)
                        trigger_captcha(driver)
                        total_attempts += 1
                        continue
                    else:
                        login_and_captcha_success = True
                        break
                else:
                    print(f"第{current_attempt}次验证失败，未检测到成功提示...")
                    total_attempts += 1
                    refresh_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CLASS_NAME, "shumei_captcha_footer_refresh_btn"))
                    )
                    refresh_btn.click()
                    time.sleep(1)
            
            if login_and_captcha_success:
                break
            
            # 周期结束，强制刷新并重登
            print(f"\n已完成{cycle_attempts}次验证，强制刷新页面...")
            driver.refresh()
            time.sleep(5)
            fill_account_password(driver, account, password)
            trigger_captcha(driver)
            total_attempts += 1
        
        if login_and_captcha_success:
            print("验证成功且登录状态有效，执行签到...")
            click_sign_in(driver)
            tiezi.publish_tiezi(driver)
        else:
            print(f"达到最大尝试次数（{max_total_attempts}次），流程终止")
    
    except Exception as e:
        print(f"主流程出错：{str(e)}")
    finally:
        if driver:
            driver.quit()
            print("浏览器已关闭")


if __name__ == "__main__":
    main()
