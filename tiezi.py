from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
import time
import random
import os
import sys
import traceback
from collections import defaultdict 
from wenan import poetry_data
from yanzheng import get_captcha_elements, ocr_prompt_text, find_smallest_target

# 全局配置
MAX_POSTS_PER_DAY = 20 # 每日最多发20帖
MAX_POSTS_PER_BOARD = 4  # 每个板块最多发4帖
POST_INTERVAL = 60      # 发帖间隔（秒）

# 配置参数：仅保留发布帖子的网址（无需重新初始化浏览器）
TARGET_URL = "https://s.yiban.cn/userPost/detail"  # 目标发布帖子的网址

# -------------------- 新增图片相关配置 --------------------
# 发帖时附带图片的概率（30%~40%）
IMAGE_PROBABILITY = random.uniform(0.2, 0.3)  
# 图片文件夹路径（同目录下的 tiezi_picture 文件夹）
IMAGE_FOLDER = "tiezi_picture"  
# 支持的图片格式
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}  

def get_random_image_path():
    """
    从 IMAGE_FOLDER 文件夹中随机获取一张图片的路径。
    如果文件夹不存在或没有图片，返回 None。
    """
    if not os.path.isdir(IMAGE_FOLDER):
        print(f"❌ 图片文件夹不存在: {IMAGE_FOLDER}")
        return None

    image_files = []
    for filename in os.listdir(IMAGE_FOLDER):
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext in ALLOWED_IMAGE_EXTENSIONS:
            image_files.append(os.path.join(IMAGE_FOLDER, filename))  # 拼接完整路径

    if not image_files:
        print(f"❌ 图片文件夹中没有支持的图片: {IMAGE_FOLDER}")
        return None

    return random.choice(image_files)  # 随机选一张图片

# -------------------- 预设板块数据（保持不变） --------------------
BOARD_CONFIG = {
    "1": [  # 内江师范学院有效板块
        {"value": "zQ7SV4bYYrgoYb4", "name": "元宵最美瞬间"},
        {"value": "E3nCgYpoOMG3Kgk", "name": "镜头中的年味"},
        {"value": "zQ7SVo6wJwRmdpp", "name": "2026寒假分享"},
        {"value": "YVDfy290raKpxol", "name": "2026元旦分享"},
        {"value": "e2MIN0LK7qEaq9Y", "name": "奇遇美食记"},
        {"value": "KMefQdl27YqxYld", "name": "2026考研祝福"},
        {"value": "xpGf0ded4A2QmlY", "name": "单词打卡21天"},
        {"value": "R2eIxMWdxr4079E", "name": "2025内师秋韵"},
        {"value": "3aJT55Qnr7LxqxQ", "name": "2025国庆分享"},
        {"value": "o3QCo6wylgzzeOQ", "name": "2025暑期分享"},
        {"value": "kD2C9m1dwJyQyX1", "name": "2025毕业寄语"},
        {"value": "q1NF4OAMNaO0NOA", "name": "冲冲四六级"},
        {"value": "wJASrV4WYbzLmGy", "name": "2025晒五一"},
        {"value": "KMefkYoz2XnZkzE", "name": "2025读书日"},
        {"value": "pb6feYJo4eE9eZ7", "name": "我和春天有个约会"},
        {"value": "wJASrnW6zgLWDWJ", "name": "2025校运会"},
        {"value": "JBeI6aeJyV0N95o", "name": "新学期新起点"},
        {"value": "0aJTpaqGQdwAKy1", "name": "2025寒假日常"},
        {"value": "1aJTGn0Brrgeq9G", "name": "2025元旦"},
        {"value": "3aJTZ1XZAlDge3k", "name": "2025考研祝福"},
        {"value": "7aRTVq1ADZDJK0x", "name": "2024内师秋韵"},
        {"value": "2RefDOQ1O705K7b", "name": "2024校园美食杂烩"},

    ],
    "2": [  # 人工智能学院有效板块
        {"value": "E3nCw5VEK0mdzkX", "name": "素质活动与德育实践"},
        {"value": "6AeI4G0qOe346dl", "name": "新闻"},
        {"value": "abwfReVa2ome55e", "name": "校园活动"},
        {"value": "wJASDl2kE7GKAQY", "name": "节日专题"},
        {"value": "3aJT5bagyOe5VR3", "name": "生活纪实"},
        {"value": "Dbef01gwMlV4ROq", "name": "打卡专区"},
        {"value": "pb6f7EDLmG9XEqN", "name": "假期特辑"},
        {"value": "yVofE24eaMGAeGW", "name": "校园大杂烩"}
    ]
}

SCOPE_CONFIG = {
    "1": {"name": "内江师范学院", "value": "2004882"},
    "2": {"name": "人工智能学院", "value": "268221"}
}

def safe_click_captcha(driver, captcha_img, target_center):
    """安全点击验证码，使用多种点击方式确保成功"""
    abs_x, abs_y = calculate_absolute_coords(driver, captcha_img, target_center[0], target_center[1])
    
    print(f"尝试点击坐标: ({abs_x}, {abs_y})")
    
    # 方法1: 使用 ActionChains 精确点击
    try:
        actions = ActionChains(driver)
        actions.move_to_element(captcha_img)
        actions.move_by_offset(target_center[0] - captcha_img.size['width']/2, 
                              target_center[1] - captcha_img.size['height']/2)
        actions.pause(0.3)
        actions.click()
        actions.perform()
        print("方法1点击成功")
        return True
    except Exception as e:
        print(f"方法1点击失败: {e}")
    

def calculate_absolute_coords(driver, captcha_img, relative_x, relative_y):
    """计算绝对坐标（修复版）"""
    # 获取元素在页面中的位置
    location = captcha_img.location
    size = captcha_img.size
    
    # 计算中心点相对坐标
    center_x = location['x'] + size['width'] / 2
    center_y = location['y'] + size['height'] / 2
    
    # 计算目标绝对坐标
    abs_x = center_x + (relative_x - size['width'] / 2)
    abs_y = center_y + (relative_y - size['height'] / 2)
    
    return (abs_x, abs_y)

def is_captcha_success(driver, timeout=5):
    """检查验证码是否成功（多种判断方式）"""
    try:
        # 方式1: 检查成功文本
        success_elem = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "div.shumei_captcha_slide_tips"))
        )
        if "验证成功" in success_elem.text:
            return True
    except:
        pass
    
    try:
        # 方式2: 检查弹窗是否消失
        WebDriverWait(driver, 2).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, "div.shumei_captcha_popup_wrapper"))
        )
        return True
    except:
        pass
        
    try:
        # 方式3: 检查页面是否跳转或状态改变
        current_url = driver.current_url
        if "detail" in current_url or "success" in current_url:
            return True
    except:
        pass
        
    return False

def wait_for_publish_success(driver, timeout=20):
    """等待发布成功 - 根据实际HTML结构"""
    print("等待发布成功确认...")
    time.sleep(1)
    try:
        # 方式1: 检查mdc-alert内容（根据你提供的HTML结构）
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'mdc-alert__content') and contains(text(), '成功发布帖子')]"))
        )
        # print("✅ 检测到成功发布提示 (mdc-alert)")
        return True
    except TimeoutException:
        print("❌ 未检测到mdc-alert成功提示")
    
    # 方式2: 检查"继续添加"按钮（根据实际结构）
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@class, 'mdc-button')]//div[contains(@class, 'mdc-button__label') and text()='继续添加']"))
        )
        print("✅ 检测到继续添加按钮")
        return True
    except TimeoutException:
        print("❌ 未检测到继续添加按钮")
    
    # 方式3: 检查整个alert容器
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'mdc-alert')]//*[contains(text(), '成功发布帖子')]"))
        )
        print("✅ 检测到alert容器中的成功文本")
        return True
    except TimeoutException:
        print("❌ 未检测到alert容器")
    
    # 方式4: 直接检查页面文本内容
    if "成功发布帖子" in driver.page_source:
        print("✅ 页面源码中包含成功发布文本")
        return True
    
    return False

def wait_for_possible_captcha(driver, timeout=10):
    """
    修复版：等待可能的验证码出现，并正确处理验证后的状态
    """
    try:
        # 等待发布后的页面变化
        WebDriverWait(driver, timeout).until(
            lambda d: any([
                # 情况1: 出现验证码
                len(d.find_elements(By.CSS_SELECTOR, "div.shumei_captcha_popup_wrapper")) > 0 and 
                d.find_element(By.CSS_SELECTOR, "div.shumei_captcha_popup_wrapper").is_displayed(),
                # 情况2: 直接发布成功
                len(d.find_elements(By.XPATH, "//div[contains(@class, 'mdc-alert__content') and contains(text(), '成功发布帖子')]")) > 0,
                # 情况3: 出现继续添加按钮
                len(d.find_elements(By.XPATH, "//a[contains(@class, 'mdc-button')]//div[text()='继续添加']")) > 0,
            ])
        )
        
        # 判断具体是哪种情况
        if (len(driver.find_elements(By.CSS_SELECTOR, "div.shumei_captcha_popup_wrapper")) > 0 and 
            driver.find_element(By.CSS_SELECTOR, "div.shumei_captcha_popup_wrapper").is_displayed()):
            print("🔍 检测到验证码弹窗")
            return True
        else:
            print("✅ 直接发布成功，无需验证码")
            return False
            
    except TimeoutException:
        print("⚠️ 发布操作超时，但继续流程")
        return False

def check_current_page_state(driver):
    """检查当前页面状态 - 根据实际HTML"""
    # 检查是否在成功页面（根据你提供的HTML结构）
    if (len(driver.find_elements(By.XPATH, "//div[contains(@class, 'mdc-alert__content') and contains(text(), '成功发布帖子')]")) > 0 or
        len(driver.find_elements(By.XPATH, "//a[contains(@class, 'mdc-button')]//div[text()='继续添加']")) > 0):
        return "success"
    # 检查是否有验证码
    elif (len(driver.find_elements(By.CSS_SELECTOR, "div.shumei_captcha_popup_wrapper")) > 0 and
          driver.find_element(By.CSS_SELECTOR, "div.shumei_captcha_popup_wrapper").is_displayed()):
        return "captcha"
    # 检查是否还在编辑页面
    elif len(driver.find_elements(By.CSS_SELECTOR, "input[placeholder*='请输入帖子标题']")) > 0:
        return "editing"
    else:
        return "unknown"
    
def click_continue_add(driver):
    """点击继续添加按钮 - 根据实际HTML结构"""
    try:
        # 根据你提供的HTML结构定位按钮
        continue_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'mdc-button')]//div[contains(@class, 'mdc-button__label') and text()='继续添加']"))
        )
        # 点击父级a标签
        parent_a = continue_btn.find_element(By.XPATH, "./..")
        parent_a.click()
        print("✅ 点击继续添加按钮成功")
        return True
    except Exception as e:
        print(f"❌ 点击继续添加失败: {e}")
        return False

def safe_refresh_captcha(driver):
    """安全刷新验证码，避免页面刷新导致内容丢失"""
    try:
        # 优先尝试刷新按钮
        refresh_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.shumei_captcha_footer_refresh_btn"))
        )
        refresh_btn.click()
        print("验证码已刷新")
        time.sleep(2)  # 等待刷新完成
        return True
    except:
        print("无法刷新验证码，跳过刷新")
        return False


def handle_captcha_smart(driver, max_attempts=3):
    """
    修复版：验证码处理后等待真正的发布结果
    """
    try:
        # 首先检查是否出现验证码弹窗
        WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "div.shumei_captcha_popup_wrapper"))
        )
        print("检测到验证码弹窗，开始处理...")
    except TimeoutException:
        print("未检测到验证码弹窗，直接继续流程")
        return True
    except Exception as e:
        print(f"检查验证码弹窗时出错: {e}")
        return True

    # 生成线程安全的文件名
    base_thread_id = int(time.time() * 1000000) % 100000
    
    # 处理验证码
    for attempt in range(max_attempts):
        captcha_file = None
        prompt_file = None
        
        try:
            print(f"第 {attempt + 1} 次尝试处理验证码...")
            
            if not is_captcha_visible(driver):
                print("验证码已消失，验证通过")
                return True
                
            # 获取验证码元素并处理
            captcha_img, prompt_elem = get_captcha_elements(driver)
            
            # 截图识别
            captcha_file = f"captcha_{base_thread_id}_{attempt}.png"
            prompt_file = f"prompt_{base_thread_id}_{attempt}.png"
            
            try:
                captcha_img.screenshot(captcha_file)
                prompt_elem.screenshot(prompt_file)
            except Exception as e:
                print(f"截图保存失败: {e}")
                continue
            
            # 检查文件是否存在
            if not os.path.exists(captcha_file) or not os.path.exists(prompt_file):
                print("验证码截图文件未创建成功")
                safe_refresh_captcha(driver)
                continue
            
            # 使用全局OCR实例（从yanzheng.py导入的）
            print("开始OCR识别...")
            target_color, target_shape = ocr_prompt_text(prompt_file)
            if not target_color or not target_shape:
                print("识别目标失败，刷新验证码")
                safe_refresh_captcha(driver)
                # 清理临时文件
                for f in [captcha_file, prompt_file]:
                    if f and os.path.exists(f):
                        try:
                            os.remove(f)
                        except:
                            pass
                continue
            
            print(f"识别目标: {target_color} {target_shape}")
            
            target_center = find_smallest_target(captcha_file, target_color, target_shape)
            if not target_center:
                print("未找到目标位置，刷新验证码")
                safe_refresh_captcha(driver)
                # 清理临时文件
                for f in [captcha_file, prompt_file]:
                    if f and os.path.exists(f):
                        try:
                            os.remove(f)
                        except:
                            pass
                continue
            
            print(f"找到目标位置: {target_center}")
            
            # 安全点击
            if safe_click_captcha(driver, captcha_img, target_center):
                print("点击完成，等待验证结果...")
                
                # 等待验证码处理完成
                time.sleep(2)
                
                # 检查验证码是否成功消失
                if not is_captcha_visible(driver):
                    print("✅ 验证码验证成功，等待发布结果...")
                    # 给服务器处理时间
                    time.sleep(3)
                    
                    # 清理临时文件
                    for f in [captcha_file, prompt_file]:
                        if f and os.path.exists(f):
                            try:
                                os.remove(f)
                            except:
                                pass
                    return True
                else:
                    print("❌ 验证未成功，继续尝试")
                    safe_refresh_captcha(driver)
            else:
                print("❌ 点击失败，刷新重试")
                safe_refresh_captcha(driver)
                
            # 清理临时文件
            for f in [captcha_file, prompt_file]:
                if f and os.path.exists(f):
                    try:
                        os.remove(f)
                    except:
                        pass
                
        except Exception as e:
            print(f"验证码处理异常: {e}")
            import traceback
            traceback.print_exc()
            
            # 清理临时文件
            for f in [captcha_file, prompt_file]:
                if f and os.path.exists(f):
                    try:
                        os.remove(f)
                    except:
                        pass
            
            if not is_captcha_visible(driver):
                print("验证码已消失，验证通过")
                return True
            safe_refresh_captcha(driver)
    
    print("验证码自动处理失败，跳过验证码处理")
    # 避免使用input()导致程序阻塞
    return True
def is_captcha_visible(driver):
    """检查验证码弹窗是否可见"""
    try:
        popup = driver.find_element(By.CSS_SELECTOR, "div.shumei_captcha_popup_wrapper")
        return popup.is_displayed()
    except:
        return False



def publish_tiezi(driver, account_name: str):
    """发布帖子（带账号名）"""
    driver.get(TARGET_URL)
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='请输入帖子标题']"))
    )
    print(f"✅ [{account_name}] 已打开发布页")

    scope = SCOPE_CONFIG["1"]
    valid_boards = BOARD_CONFIG["1"]
    print(f"✅ [{account_name}] 已固定发布范围：{scope['name']}")

    board_post_counts = defaultdict(int)
    total_post_count = 0

    while total_post_count < MAX_POSTS_PER_DAY:
        available_boards = [
            b for b in valid_boards
            if board_post_counts[b["value"]] < MAX_POSTS_PER_BOARD
        ]
        if not available_boards:
            print(f"⚠️  [{account_name}] 所有板块已达上限，结束发布")
            break

        selected_board = random.choice(available_boards)
        print(f"\n===== [{account_name}] 开始发布第 {total_post_count + 1} 帖 =====")
        print(f"板块：{selected_board['name']}")

        try:
            select_board_only(driver, selected_board)
            fill_title_and_content(driver)
            click_publish(driver)
            
            has_captcha = wait_for_possible_captcha(driver)
            if has_captcha:
                print(f"🔍 [{account_name}] 检测到验证码弹窗")
                captcha_result = handle_captcha_smart(driver)
                if not captcha_result:
                    print(f"❌ [{account_name}] 验证码处理失败，跳过当前帖子")
                    driver.get(TARGET_URL)
                    time.sleep(2)
                    continue
            else:
                print(f"✅ [{account_name}] 无需验证码处理")

            if wait_for_publish_success(driver, timeout=12):
                print(f"✅ [{account_name}] 发布成功")
                
                board_post_counts[selected_board["value"]] += 1
                total_post_count += 1
                print(f"✅ [{account_name}] 第 {total_post_count} 帖发布完成")
                
                if total_post_count >= MAX_POSTS_PER_DAY:
                    print(f"🎉 [{account_name}] 已达到每日上限 {MAX_POSTS_PER_DAY} 帖，任务完成！")
                    return
                
                time.sleep(POST_INTERVAL)
                if click_continue_add(driver):
                    time.sleep(2)
                    print(f"准备发布下一帖... [{account_name}]")
                else:
                    print(f"❌ [{account_name}] 继续添加失败，刷新页面")
                    driver.get(TARGET_URL)
            else:
                print(f"❌ [{account_name}] 发布失败，刷新页面")
                driver.get(TARGET_URL)
                
        except Exception as e:
            print(f"❌ [{account_name}] 本帖异常：{e}")
            driver.get(TARGET_URL)
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='请输入帖子标题']"))
            )
            continue

    print(f"\n🎉 [{account_name}] 发布结束，共成功发布 {total_post_count} 帖")

# 添加新的只选择板块的函数
def select_board_only(driver, board):
    """只选择板块（范围已固定为内江师范学院）"""
    # 固定选择内江师范学院的范围
    scope_sel = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//label[text()='发布范围：']/following-sibling::select"))
    )
    for opt in scope_sel.find_elements(By.TAG_NAME, "option"):
        if opt.get_attribute("value") == "2004882":  # 内江师范学院的value
            opt.click()
            break
    time.sleep(0.5)

    # 选择板块
    board_sel = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//label[text()='选择版块：']/following-sibling::select"))
    )
    for opt in board_sel.find_elements(By.TAG_NAME, "option"):
        if opt.get_attribute("value") == board["value"]:
            opt.click()
            break
    time.sleep(0.5)
            
# 其他辅助函数保持不变...
def select_scope_and_board(driver, scope, board):
    """选范围+板块"""
    # 范围
    scope_sel = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//label[text()='发布范围：']/following-sibling::select"))
    )
    for opt in scope_sel.find_elements(By.TAG_NAME, "option"):
        if opt.get_attribute("value") == scope["value"]:
            opt.click()
            break
    time.sleep(0.5)

    # 板块
    board_sel = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//label[text()='选择版块：']/following-sibling::select"))
    )
    for opt in board_sel.find_elements(By.TAG_NAME, "option"):
        if opt.get_attribute("value") == board["value"]:
            opt.click()
            break
    time.sleep(0.5)

# def fill_title_and_content(driver):
#     """修复执行顺序 - 先检查编辑器再填写"""
#     max_retries = 1
    
#     for retry_count in range(max_retries + 1):
#         try:
#             # 🆕 第一步：先检查富文本编辑器是否可用
#             print("检查富文本编辑器...")
#             iframe = WebDriverWait(driver, 4).until(
#                 EC.presence_of_element_located((By.ID, "ueditor_0"))
#             )
            
#             # 🆕 第二步：编辑器可用，再准备内容
#             if not poetry_data:
#                 poetry_data.append({"title": "默认标题", "content": "默认内容"})

#             selected = random.choice(poetry_data)
            
#             # 🆕 修复标题：清理符号，只取逗号前的内容
#             raw_title = selected["title"].split("，")[0]  # 只取逗号前的部分
#             # 清理其他可能的中英文标点
#             import re
#             raw_title = re.sub(r'[，。！？；："“”‘’\'\.,!?;]', '', raw_title)  # 移除常见标点
#             final_title = raw_title[:30] if len(raw_title) > 30 else raw_title
#             if len(final_title) < 5:
#                 final_title = f"{final_title}，{final_title}"
            
#             # 🆕 修复内容：清理多余的句号
#             raw_content = selected["content"]
#             # 清理内容中的多余标点
#             # raw_content = re.sub(r'[。！？；："“”‘’\'\.,!?;]', '', raw_content)  # 移除结尾标点
#              # 只清理可能影响 HTML 的特殊字符，保留中文标点（，。！？等）
#             raw_content = raw_content.replace('"', '').replace("'", '').replace('<', '').replace('>', '')
            
#             # 🆕 第三步：填写标题
#             title_inp = WebDriverWait(driver, 10).until(
#                 EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='请输入帖子标题']"))
#             )
#             title_inp.clear()
#             for ch in final_title:
#                 title_inp.send_keys(ch)
#                 time.sleep(random.uniform(0.05, 0.15))

#             # 🆕 第四步：填写内容（编辑器已经确认可用）
#             driver.switch_to.frame(iframe)
#             body = WebDriverWait(driver, 8).until(
#                 EC.presence_of_element_located((By.CSS_SELECTOR, "body[contenteditable='true']"))
#             )
#             body.clear()
            
#             # for part in raw_content.split("，"):
#             #     body.send_keys(part + " ")
#             #     time.sleep(random.uniform(0.2, 0.5))
            
#             # 5. 30%~40%概率插入图片
#             if random.random() < IMAGE_PROBABILITY:
#                 img_path = get_random_image_path()
#                 if img_path:
#                     print(f"🔍 尝试通过JS插入图片: {img_path}")
                    
#                     # 方法1：将图片转为base64，用JS插入
#                     import base64
#                     with open(img_path, "rb") as img_file:
#                         img_data = img_file.read()
#                         img_base64 = base64.b64encode(img_data).decode('utf-8')
                    
#                     # 获取图片扩展名
#                     img_ext = os.path.splitext(img_path)[1].lower()
#                     mime_type = {
#                         '.jpg': 'image/jpeg',
#                         '.jpeg': 'image/jpeg',
#                         '.png': 'image/png',
#                         '.gif': 'image/gif',
#                         '.bmp': 'image/bmp'
#                     }.get(img_ext, 'image/jpeg')
                    
#                     # 方法A：通过JavaScript直接创建img元素
#                     try:
#                         js_script = f"""
#                         var editor = document.querySelector('body[contenteditable="true"]');
#                         var img = document.createElement('img');
#                         img.src = 'data:{mime_type};base64,{img_base64}';
#                         img.style.maxWidth = '100%';
#                         img.style.maxHeight = '300px';
#                         img.style.margin = '10px 0';
#                         editor.appendChild(img);
                        
#                         // 添加换行
#                         var br = document.createElement('br');
#                         editor.appendChild(br);
#                         """
#                         driver.execute_script(js_script)
#                         print("✅ 通过JS直接插入图片成功")
                        
#                         # 插入后添加一些文字
#                         body.send_keys("\n\n")  # 添加空行
                        
#                     except Exception as js_e:
#                         print(f"❌ JS插入失败: {js_e}")
                        
#                         # 方法B：尝试用paste事件模拟
#                         try:
#                             # 模拟粘贴事件
#                             paste_script = f"""
#                             var editor = document.querySelector('body[contenteditable="true"]');
#                             editor.focus();
                            
#                             // 创建图片
#                             var img = new Image();
#                             img.onload = function() {{
#                                 // 将图片插入编辑器
#                                 var range = document.createRange();
#                                 var selection = window.getSelection();
#                                 range.selectNodeContents(editor);
#                                 range.collapse(false);
#                                 selection.removeAllRanges();
#                                 selection.addRange(range);
                                
#                                 // 插入图片
#                                 editor.appendChild(img);
#                             }};
#                             img.src = 'data:{mime_type};base64,{img_base64}';
#                             img.style.maxWidth = '100%';
#                             """
#                             driver.execute_script(paste_script)
#                             print("✅ 通过paste事件模拟成功")
#                         except Exception as paste_e:
#                             print(f"❌ Paste模拟也失败: {paste_e}")
            
#             # 6. 继续填写文字内容
#             for part in raw_content.split("，"):
#                 body.send_keys(part + " ")
#                 time.sleep(random.uniform(0.2, 0.5))
            
#             # 如果插入了图片，在图片后面添加文字
#             if random.random() < IMAGE_PROBABILITY and img_path:
#                 body.send_keys("\n\n")  # 图片后面加空行
            
#             driver.switch_to.default_content()
#             print("✅ 内容填写完成")
#             return
            
#         except Exception as e:
#             driver.refresh()
#             time.sleep(1)

def fill_title_and_content(driver):
    """修复执行顺序 - 先检查编辑器再填写"""
    max_retries = 1
    
    for retry_count in range(max_retries + 1):
        try:
            # 🆕 第一步：先检查富文本编辑器是否可用
            print("检查富文本编辑器...")
            iframe = WebDriverWait(driver, 4).until(
                EC.presence_of_element_located((By.ID, "ueditor_0"))
            )
            
            # 🆕 第二步：编辑器可用，再准备内容
            if not poetry_data:
                poetry_data.append({"title": "默认标题", "content": "默认内容"})

            selected = random.choice(poetry_data)
            
            # 🆕 修复标题：清理符号，只取逗号前的内容
            raw_title = selected["title"].split("，")[0]  # 只取逗号前的部分
            # 清理其他可能的中英文标点
            import re
            raw_title = re.sub(r'[，。！？；：""\'",!?;]', '', raw_title)  # 移除常见标点
            final_title = raw_title[:30] if len(raw_title) > 30 else raw_title
            if len(final_title) < 5:
                final_title = f"{final_title}，{final_title}"
            
            # 🆕 修复内容：保留中文标点符号
            raw_content = selected["content"]
            # 只清理可能影响 HTML 的特殊字符，保留中文标点（，。！？等）
            raw_content = raw_content.replace('"', '').replace("'", '').replace('<', '').replace('>', '')
            
            # 🆕 第三步：填写标题
            title_inp = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='请输入帖子标题']"))
            )
            title_inp.clear()
            for ch in final_title:
                title_inp.send_keys(ch)
                time.sleep(random.uniform(0.05, 0.15))

            # 🆕 第四步：填写内容（编辑器已经确认可用）
            driver.switch_to.frame(iframe)
            body = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "body[contenteditable='true']"))
            )
            body.clear()
            
            # 5. 30%~40%概率插入图片
            if random.random() < IMAGE_PROBABILITY:
                img_path = get_random_image_path()
                if img_path:
                    print(f"🔍 尝试通过JS插入图片: {img_path}")
                    
                    # 方法1：将图片转为base64，用JS插入
                    import base64
                    with open(img_path, "rb") as img_file:
                        img_data = img_file.read()
                        img_base64 = base64.b64encode(img_data).decode('utf-8')
                    
                    # 获取图片扩展名
                    img_ext = os.path.splitext(img_path)[1].lower()
                    mime_type = {
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.png': 'image/png',
                        '.gif': 'image/gif',
                        '.bmp': 'image/bmp'
                    }.get(img_ext, 'image/jpeg')
                    
                    # 方法A：通过JavaScript直接创建img元素
                    try:
                        js_script = f"""
                        var editor = document.querySelector('body[contenteditable="true"]');
                        var img = document.createElement('img');
                        img.src = 'data:{mime_type};base64,{img_base64}';
                        img.style.maxWidth = '100%';
                        img.style.maxHeight = '300px';
                        img.style.margin = '10px 0';
                        editor.appendChild(img);
                        
                        // 添加换行
                        var br = document.createElement('br');
                        editor.appendChild(br);
                        """
                        driver.execute_script(js_script)
                        print("✅ 通过JS直接插入图片成功")
                        
                        # 插入后添加一些文字
                        body.send_keys("\n\n")  # 添加空行
                        
                    except Exception as js_e:
                        print(f"❌ JS插入失败: {js_e}")
            
            # 🆕 关键修改：智能处理标点符号的分割
            # 6. 继续填写文字内容
            # print(f"原始内容: {raw_content}")
            
            # 方法1：如果内容包含中文标点，按标点分割
            if "，" in raw_content or "。" in raw_content or "！" in raw_content or "？" in raw_content:
                # 使用正则表达式按中文标点分割，但保留标点
                import re
                parts = re.split(r'([，。！？])', raw_content)
                
                # 重组内容，确保标点跟在文字后面
                for i in range(0, len(parts), 2):
                    if i < len(parts):
                        text = parts[i]
                        if text.strip():  # 非空文本
                            body.send_keys(text)
                            time.sleep(random.uniform(0.2, 0.5))
                    
                    if i+1 < len(parts):
                        punc = parts[i+1]
                        if punc.strip():  # 非空标点
                            body.send_keys(punc)
                            time.sleep(random.uniform(0.1, 0.2))
            else:
                # 方法2：没有标点，直接发送整个内容
                body.send_keys(raw_content)
                time.sleep(random.uniform(0.2, 0.5))
            
            # 如果插入了图片，在图片后面添加文字
            if random.random() < IMAGE_PROBABILITY and img_path:
                body.send_keys("\n\n")  # 图片后面加空行
            
            driver.switch_to.default_content()
            print("✅ 内容填写完成")
            return
            
        except Exception as e:
            # print(f"❌ 填充内容异常: {e}")
            import traceback
            # traceback.print_exc()
            driver.refresh()
            time.sleep(1)        
            
def wait_for_page_fully_loaded(driver, timeout=15):
    """等待页面完全加载，包括关键元素"""
    print("等待页面完全加载...")
    
    # 等待标题输入框（基本元素）
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='请输入帖子标题']"))
    )
    
    # 额外等待2秒让其他资源加载
    time.sleep(2)
    
    # 检查富文本编辑器是否可用（但不阻塞）
    try:
        iframe = WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.ID, "ueditor_0"))
        )
        print("✅ 富文本编辑器已加载")
    except TimeoutException:
        print("⚠️ 富文本编辑器加载较慢，继续流程")

def click_publish(driver):
    """点击发布按钮"""
    pub_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'mdc-button') and .//span[text()='发布']]"))
    )
    pub_btn.click()

def select_board(board_counts, all_boards):
    """选择未达上限的板块"""
    available_boards = [board for board in all_boards if board_counts[board] < MAX_POSTS_PER_BOARD]
    if not available_boards:
        print("所有板块已达发布上限，流程终止")
        sys.exit()
    return random.choice(available_boards)

# 保留独立运行入口（方便单独测试）
if __name__ == "__main__":
    # 仅用于单独测试时初始化浏览器（整合到主流程时不会执行）
    from selenium import webdriver
    from selenium.webdriver.edge.service import Service
    from selenium.webdriver.edge.options import Options

    edge_options = Options()
    edge_options.add_argument("--start-maximized")
    driver_path = os.path.join("yiban", "msedgedriver.exe")
    service = Service(driver_path)
    driver = webdriver.Edge(service=service, options=edge_options)
    driver.get("https://www.yiban.cn")  # 单独测试时需先手动登录
    input("请手动登录后按回车继续...")  # 等待手动登录
    publish_tiezi(driver)  # 调用发布函数
    input("按回车关闭浏览器...")
    driver.quit()
    
   