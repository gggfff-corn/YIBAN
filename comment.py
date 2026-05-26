import requests
import random
import time
import json
import uuid
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException
from yanzheng import get_captcha_elements, ocr_prompt_text, find_smallest_target  # 你的验证码模块
import re
import importlib
import os
from tieziID import POST_ID_LIST  # 导入保存的帖子ID列表

# 评论配置
MAX_COMMENTS_PER_DAY = 30  # 每日最多评论数30
# COMMENT_INTERVAL = 60     # 评论间隔（秒）
COMMENT_INTERVAL = random.randint(60, 61)  # 60-120秒随机间隔
CURRENT_USER_ID = "72216696"  # 你自己的用户ID（替换为实际ID）

# 评论内容池
COMMENT_POOL = [
    "写得太好了！", "受益匪浅嗯！", "感谢分享哈！", "很有启发哦！", "赞一个一个！",
    "帖子学习了！", "非常支持楼主！", "这篇内容很棒！", "下次继续加油！", "期待更多分享！",
    "观点独特哦！", "分析到位哈！", "可以实用性强！", "我已经收藏了！", "推荐给大家！",
    "说得太好了","不能同意更多","mark了很有用","收藏感谢分享","是我心里话",
    "楼主继续加油","抱抱你会好的","支持一下","你很棒别灰心","我们支持你",
    "蹲一个后续","这是在哪里呀","等楼主更新","然后呢然后呢","求更多细节",
    "学到了谢谢","原来是这样","围观打卡","有用的知识增加了","给你赞一个",
    "赞赞赞赞赞",
]

def load_post_ids():
    """动态加载帖子ID列表，文件不存在时返回空列表"""
    POST_ID_FILE = "e:/yiban/yiban/tieziID.py"
    if not os.path.exists(POST_ID_FILE):
        print(f"⚠️  未找到 {POST_ID_FILE}，请先运行点赞功能生成")
        return []
    try:
        # 动态导入模块，避免直接import报错
        spec = importlib.util.spec_from_file_location("tieziID", POST_ID_FILE)
        tiezi_id_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tiezi_id_module)
        return tiezi_id_module.POST_ID_LIST if hasattr(tiezi_id_module, "POST_ID_LIST") else []
    except Exception as e:
        print(f"❌ 加载 {POST_ID_FILE} 失败，返回空列表: {e}")
        return []

POST_ID_LIST = load_post_ids()

# class YibanCommentFromSavedIds:
    
#     def __init__(self, cookies_dict: dict, driver):
#         self.session = requests.Session()
#         self.cookies_dict = cookies_dict
#         self.driver = driver
#         self.update_cookies()
#         # 移除 captcha_base_url 相关代码
#         # 初始化关键参数
#         self.csrf_token = self.get_csrf_token()
#         self.ybticket = self.get_ybticket()
#         self.current_user_id = CURRENT_USER_ID
        
#         # 加载保存的帖子ID列表（从 tieziId.py 导入）
#         self.saved_posts = POST_ID_LIST
#         if not self.saved_posts:
#             print("⚠️  暂无可用的帖子ID，评论任务无法执行")
#             # 不抛出异常，避免程序崩溃
#             self.can_run = False
#         else:
#             self.can_run = True
        
#         # 请求头
#         self.headers = {
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0',
#             'Referer': 'https://s.yiban.cn/',
#             'Origin': 'https://s.yiban.cn',
#             'Content-Type': 'application/json',
#             'Accept': 'application/json, text/plain, */*',
#             'platform': 'yiban_web',
#             'X-Requested-With': 'XMLHttpRequest',
#             'Cookie': '; '.join([f"{k}={v}" for k, v in self.cookies_dict.items()])
#         }
        
#         print(f"✅ 评论模块初始化完成")

class YibanCommentFromSavedIds:
    def __init__(self, cookies_dict: dict, driver, account_name: str):
        self.session = requests.Session()
        self.cookies_dict = cookies_dict
        self.driver = driver
        self.account_name = account_name  # 新增
        self.update_cookies()
        self.csrf_token = self.get_csrf_token()
        self.ybticket = self.get_ybticket()
        self.current_user_id = CURRENT_USER_ID
        
        self.saved_posts = POST_ID_LIST
        self.can_run = True if self.saved_posts else False
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0',
            'Referer': 'https://s.yiban.cn/',
            'Origin': 'https://s.yiban.cn',
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/plain, */*',
            'platform': 'yiban_web',
            'X-Requested-With': 'XMLHttpRequest',
            'Cookie': '; '.join([f"{k}={v}" for k, v in self.cookies_dict.items()])
        }
        
        print(f"✅ [{self.account_name}] 评论模块初始化完成")
     # 添加缺失的 update_cookies 方法
    def update_cookies(self):
        """实时同步浏览器Cookie"""
        try:
            driver_cookies = self.driver.get_cookies()
            new_cookies_dict = {cookie["name"]: cookie["value"] for cookie in driver_cookies}
            self.session.cookies.clear()
            self.session.cookies.update(new_cookies_dict)
            self.cookies_dict = new_cookies_dict
            print("✅ 已同步最新Cookie")
        except Exception as e:
            print(f"❌ 同步Cookie失败: {e}")
    # 添加 get_csrf_token 方法
    def get_csrf_token(self):
        """通过API接口获取CSRF token"""
        try:
            # 使用专门的API接口获取token
            url = 'https://s.yiban.cn/api/security/getToken'
            headers = {
                'platform': 'yiban_web',
                'origin': 'https://s.yiban.cn',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # 使用当前session的cookies发送请求
            response = self.session.post(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # 从响应中提取csrfToken
            csrf_token = response.json()['data']['csrfToken']
            return csrf_token
        except Exception as e:
            print(f"❌ 通过API接口获取CSRF token失败: {e}")
            return ""

    # 添加 get_ybticket 方法
    def get_ybticket(self):
        """从页面实时提取ybticket"""
        try:
            page_source = self.driver.page_source
            ticket_match = re.search(r'ybticket\s*:\s*(\{[^}]+\})', page_source)
            return ticket_match.group(1) if ticket_match else ""
        except Exception as e:
            print(f"❌ 获取ybticket失败: {e}")
            return ""
    # 移除以下与验证码请求相关的方法:
    # send_captcha_request
    # init_captcha
    # load_captcha_resource
    # register_captcha
    # verify_captcha
    # extract_captcha_uuid
    # get_captcha_image_url

    # 保留并优化验证码处理相关方法，参照 tiezi.py 的实现方式
    def safe_click_captcha(self, captcha_img, target_center):
        """安全点击验证码，使用多种点击方式确保成功"""
        abs_x, abs_y = self.calculate_absolute_coords(captcha_img, target_center[0], target_center[1])
        print(f"尝试点击验证码坐标: ({abs_x}, {abs_y})")
        
        try:
            actions = ActionChains(self.driver)
            actions.move_to_element(captcha_img)
            actions.move_by_offset(
                target_center[0] - captcha_img.size['width']/2,
                target_center[1] - captcha_img.size['height']/2
            )
            actions.pause(0.3)
            actions.click()
            actions.perform()
            print("✅ 验证码点击完成")
            return True
        except Exception as e:
            print(f"❌ 验证码点击失败: {e}")
            return False

    def calculate_absolute_coords(self, captcha_img, relative_x, relative_y):
        """计算验证码绝对坐标"""
        location = captcha_img.location
        size = captcha_img.size
        center_x = location['x'] + size['width'] / 2
        center_y = location['y'] + size['height'] / 2
        abs_x = center_x + (relative_x - size['width'] / 2)
        abs_y = center_y + (relative_y - size['height'] / 2)
        return (abs_x, abs_y)

    def is_captcha_success(self, timeout=5):
        """检查验证码是否成功"""
        try:
            # 方式1: 检查成功文本
            success_elem = WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "div.shumei_captcha_slide_tips"))
            )
            if "验证成功" in success_elem.text:
                return True
        except:
            pass
        
        try:
            # 方式2: 检查弹窗是否消失
            WebDriverWait(self.driver, 2).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, "div.shumei_captcha_popup_wrapper"))
            )
            return True
        except:
            pass
            
        return False

    def is_captcha_visible(self):
        """检查验证码弹窗是否可见"""
        try:
            popup = self.driver.find_element(By.CSS_SELECTOR, "div.shumei_captcha_popup_wrapper")
            return popup.is_displayed()
        except:
            return False

    def safe_refresh_captcha(self):
        """刷新验证码"""
        try:
            refresh_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.shumei_captcha_footer_refresh_btn"))
            )
            refresh_btn.click()
            print("🔄 验证码已刷新")
            time.sleep(2)
            return True
        except:
            print("❌ 无法刷新验证码")
            return False

    # def handle_captcha_smart(self, max_attempts=3):
    #     """
    #     优化版：验证码处理后等待真正的验证结果
    #     """
    #     # 首先检查是否出现验证码弹窗
    #     try:
    #         WebDriverWait(self.driver, 5).until(
    #             EC.visibility_of_element_located((By.CSS_SELECTOR, "div.shumei_captcha_popup_wrapper"))
    #         )
    #         print("🛡️ 检测到验证码弹窗，开始处理...")
    #     except TimeoutException:
    #         print("❌ 未检测到验证码弹窗，跳过处理")
    #         return False
        
    #     # 处理验证码
    #     for attempt in range(max_attempts):
    #         try:
    #             print(f"第 {attempt + 1} 次尝试处理验证码...")
                
    #             if not self.is_captcha_visible():
    #                 print("✅ 验证码已消失，验证通过")
    #                 return True
                    
    #             # 获取验证码元素并处理
    #             captcha_img, prompt_elem = get_captcha_elements(self.driver)
                
    #             # 截图识别
    #             captcha_img.screenshot(f"comment_captcha_{attempt}.png")
    #             prompt_elem.screenshot(f"comment_prompt_{attempt}.png")
                
    #             target_color, target_shape = ocr_prompt_text(f"comment_prompt_{attempt}.png")
    #             if not target_color or not target_shape:
    #                 print("❌ 识别目标失败，刷新验证码")
    #                 self.safe_refresh_captcha()
    #                 continue
                
    #             print(f"🎯 识别到目标: {target_color} {target_shape}")
                
    #             target_center = find_smallest_target(f"comment_captcha_{attempt}.png", target_color, target_shape)
    #             if not target_center:
    #                 print("❌ 未找到目标位置，刷新验证码")
    #                 self.safe_refresh_captcha()
    #                 continue
                
    #             print(f"✅ 找到目标位置: {target_center}")
                
    #             # 安全点击
    #             if self.safe_click_captcha(captcha_img, target_center):
    #                 print("✅ 点击完成，等待验证结果...")
                    
    #                 # 关键：等待验证码处理完成
    #                 time.sleep(3)
                    
    #                 # 检查验证码是否成功消失
    #                 if not self.is_captcha_visible():
    #                     print("✅ 验证码验证成功")
    #                     time.sleep(2)  # 给服务器处理时间
    #                     return True  # 确保在这里就返回
    #                 else:
    #                     print("❌ 验证未成功，继续尝试")
    #                     self.safe_refresh_captcha()
    #             else:
    #                 print("❌ 点击失败，刷新重试")
    #                 self.safe_refresh_captcha()
                    
    #         except Exception as e:
    #             print(f"❌ 验证码处理异常: {e}")
    #             if not self.is_captcha_visible():
    #                 print("✅ 验证码已消失，验证通过")
    #                 return True
    #             self.safe_refresh_captcha()
        
    #     print("❌ 验证码自动处理失败，需要手动处理")
    #     input("请手动完成验证码后按回车继续...")
    #     return self.is_captcha_success()
    
    def handle_captcha_smart(self, max_refresh_rounds=5, max_retry_per_img=3):
            """
            优化版：验证码处理逻辑
            - 外层循环 max_refresh_rounds (5次)：控制整体重试轮数
            - 内层循环 max_retry_per_img (3次)：针对单张图片的识别/点击重试
            - 刷新策略：除第1轮外，每轮开始前刷新整个网页
            """
            
            # 首先检查是否出现验证码弹窗
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "div.shumei_captcha_popup_wrapper"))
                )
                print("🛡️ 检测到验证码弹窗，开始自动处理...")
            except TimeoutException:
                print("❌ 未检测到验证码弹窗，跳过处理")
                return False
            
            # --- 外层循环：控制刷新轮数 ---
            for refresh_idx in range(max_refresh_rounds):
                print(f"\n🔄 [第 {refresh_idx + 1}/{max_refresh_rounds} 轮] 开始处理验证码...")
                
                # 【关键逻辑】除了第一次，每次进入新轮次都刷新网页
                if refresh_idx > 0:
                    print("⚠️ 上一轮失败，正在刷新整个网页以重置状态...")
                    try:
                        self.driver.refresh()
                        time.sleep(3) # 等待页面完全加载
                        
                        # 刷新后重新等待验证码弹窗出现
                        WebDriverWait(self.driver, 10).until(
                            EC.visibility_of_element_located((By.CSS_SELECTOR, "div.shumei_captcha_popup_wrapper"))
                        )
                        print("✅ 网页刷新完成，验证码弹窗已重新加载")
                    except Exception as e:
                        print(f"❌ 刷新网页或等待弹窗失败: {e}")
                        continue

                try:
                    if not self.is_captcha_visible():
                        print("✅ 验证码已消失，验证通过")
                        return True
                        
                    # 获取验证码元素并处理
                    captcha_img, prompt_elem = get_captcha_elements(self.driver)
                    
                    # 截图识别 (文件名带上轮次标识，方便调试)
                    captcha_file = f"comment_captcha_r{refresh_idx}.png"
                    prompt_file = f"comment_prompt_r{refresh_idx}.png"
                    
                    captcha_img.screenshot(captcha_file)
                    prompt_elem.screenshot(prompt_file)
                    
                    success_this_round = False
                    
                    # --- 内层循环：针对当前图片多次尝试 ---
                    for retry_idx in range(max_retry_per_img):
                        print(f"  ↪ [内层] 第 {retry_idx + 1}/{max_retry_per_img} 次尝试识别/点击...")
                        
                        try:
                            target_color, target_shape = ocr_prompt_text(prompt_file)
                            if not target_color or not target_shape:
                                print("  ⚠️ 识别目标失败，短暂等待后重试...")
                                time.sleep(0.5)
                                continue
                            
                            print(f"  🎯 识别到目标: {target_color} {target_shape}")
                            
                            target_center = find_smallest_target(captcha_file, target_color, target_shape)
                            if not target_center:
                                print("  ⚠️ 未找到目标位置，短暂等待后重试...")
                                time.sleep(0.5)
                                continue
                            
                            print(f"  ✅ 找到目标位置: {target_center}")
                            
                            # 安全点击
                            if self.safe_click_captcha(captcha_img, target_center):
                                print("  ✅ 点击完成，等待验证结果...")
                                
                                # 关键：等待验证码处理完成
                                time.sleep(2)
                                
                                # 检查验证码是否成功消失
                                if not self.is_captcha_visible():
                                    print("  ✅ 验证码验证成功")
                                    time.sleep(1)  # 给服务器一点缓冲时间
                                    success_this_round = True
                                    break # 跳出内层循环
                                else:
                                    print("  ❌ 验证未成功，继续尝试点击/识别...")
                            else:
                                print("  ❌ 点击失败，继续尝试...")
                                
                        except Exception as e:
                            print(f"  ❌ 内层尝试异常: {e}")
                            continue
                    
                    # 清理临时文件
                    for f in [captcha_file, prompt_file]:
                        if os.path.exists(f):
                            try:
                                os.remove(f)
                            except:
                                pass

                    if success_this_round:
                        return True
                    
                    # 内层循环结束仍未成功，进入下一轮外层循环（会触发刷新）
                    print(f"  ⚠️ 当前轮次尝试 {max_retry_per_img} 次均失败，准备进入下一轮...")
                    
                except Exception as e:
                    print(f"❌ 验证码处理外层异常: {e}")
                    import traceback
                    traceback.print_exc()
                    # 发生异常也进入下一轮刷新
                    continue
            
            # 所有自动尝试均失败
            # print("\n" + "="*30)
            # print("⚠️ 自动验证连续失败 (5轮 x 3次)，需要人工介入")
            # print("请在浏览器中手动完成验证码验证")
            # print("="*30)
            input("请手动完成验证码后按回车继续...")
            
            # 人工处理后检查
            if not self.is_captcha_visible():
                return True
            return self.is_captcha_success()
    
    
    def check_comment_page_state(self):
        """检测评论页面状态，判断是否在帖子页、是否有验证码"""
        # 检查是否在帖子详情页
        if "post-detail" in self.driver.current_url:
            # 检查是否有评论框
            if len(self.driver.find_elements(By.CSS_SELECTOR, "textarea.comment-input")) > 0:
                return "comment_ready"  # 评论框就绪
            # 检查是否有验证码
            elif self.is_captcha_visible():
                return "captcha"  # 有验证码
            else:
                return "post_page_unknown"  # 帖子页但状态未知
        else:
            return "not_post_page"  # 不在帖子页
    
   
    def comment_post(self, post_id: str, post_user_id: str, comment_content: str) -> bool:
        """修正版：先激活评论框，再输入内容"""
        try:
            print(f"\n📝 开始评论帖子 {post_id[:8]}...")
            
            # 1. 打开帖子详情页
            post_detail_url = f"https://s.yiban.cn/app/2004882/post-detail/{post_id}"
            self.driver.get(post_detail_url)
            print(f"✅ 已打开帖子页：{post_detail_url}")
            
            # 2. 等待评论区根节点加载
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "section.submit"))
                )
                print("✅ 评论区根节点已加载")
            except TimeoutException:
                print("❌ 评论区加载失败，跳过")
                return False
            
            # 3. 第一步：点击触发区域，打开评论框
            try:
                trigger_area = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div.input-trigger"))
                )
                ActionChains(self.driver).move_to_element(trigger_area).pause(0.5).click().perform()
                print("✅ 已点击触发区域，打开评论框")
                time.sleep(1.5)
            except Exception as e:
                print(f"❌ 点击触发区域失败：{e}")
                pass
            
            # 4. 第二步：定位已展开的评论输入框
            try:
                comment_input = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div.input-wrapper input[placeholder='写下评论...']"))
                )
                comment_input.click()
                time.sleep(0.5)
                print("✅ 已定位并激活评论输入框")
            except Exception as e:
                print(f"❌ 定位评论输入框失败：{e}")
                return False
            
            # 5. 输入评论内容（模拟人工打字）
            try:
                for ch in comment_content:
                    comment_input.send_keys(ch)
                    time.sleep(random.uniform(0.05, 0.15))
                print(f"✅ 已输入评论：{comment_content}")
                time.sleep(random.uniform(1, 2))
            except Exception as e:
                print(f"❌ 输入评论内容失败：{e}")
                return False
            
            # 6. 点击提交按钮
            try:
                submit_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div.submit-btn.btn"))
                )
                ActionChains(self.driver).move_to_element(submit_btn).pause(0.3).click().perform()
                print("✅ 已点击提交按钮")
                time.sleep(2)
            except Exception as e:
                print(f"❌ 点击提交按钮失败：{e}")
                return False
            
            # 7. 处理验证码（关键修改：验证成功后立即返回）
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "div.shumei_captcha_popup_wrapper"))
                )
                print("⚠️ 检测到验证码，开始处理...")
                if self.handle_captcha_smart():
                    print("✅ 验证码处理成功，等待评论结果...")
                    # 验证码成功后给服务器处理时间
                    time.sleep(3)
                else:
                    print("❌ 验证码处理失败")
                    return False
            except TimeoutException:
                print("✅ 未触发验证码")
            
            # 8. 检查评论是否成功（优化验证逻辑）
            return self.verify_comment_success(comment_content)
                
        except Exception as e:
            print(f"❌ 评论过程异常：{e}")
            return False

    def verify_comment_success(self, comment_content: str) -> bool:
        """验证评论是否成功发布"""
        max_wait_time = 15  # 最大等待时间
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                # 方式1: 检查评论列表中是否出现我们的评论
                comments_container = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.comment-list"))
                )
                
                # 查找所有评论项
                comment_items = comments_container.find_elements(By.CSS_SELECTOR, "div.comment")
                
                for comment in comment_items:
                    try:
                        content_elem = comment.find_element(By.CSS_SELECTOR, "div.content")
                        if comment_content in content_elem.text:
                            print("✅ 评论成功出现在列表中")
                            return True
                    except:
                        continue
                        
                # 方式2: 检查是否有频率限制提示（关键修改：只在评论未出现时检查）
                if self.check_comment_rate_limit():
                    print("⚠️ 检测到评论频率限制，但评论可能已成功")
                    # 即使有频率限制，也要检查评论是否已经发布成功
                    time.sleep(2)
                    continue
                    
                # 方式3: 检查页面是否有成功提示
                try:
                    success_indicators = [
                        "//div[contains(text(), '评论成功')]",
                        "//div[contains(text(), '发布成功')]",
                        "//div[contains(@class, 'success')]"
                    ]
                    
                    for indicator in success_indicators:
                        try:
                            success_elem = self.driver.find_element(By.XPATH, indicator)
                            if success_elem.is_displayed():
                                print("✅ 检测到成功提示")
                                return True
                        except:
                            continue
                except:
                    pass
                    
                # 等待一段时间后再次检查
                time.sleep(2)
                print("⏳ 等待评论发布确认...")
                
            except Exception as e:
                print(f"⏳ 评论验证中...: {e}")
                time.sleep(2)
        
        print("❌ 评论结果验证超时")
        return False

    def check_comment_rate_limit(self):
        """检查评论频率限制，但不会等待60秒"""
        try:
            # 快速检查是否有频率限制弹窗
            rate_limit_popup = self.driver.find_elements(
                By.XPATH, "//div[contains(text(), '评论的频率过快')]"
            )
            
            if rate_limit_popup and rate_limit_popup[0].is_displayed():
                print("⚠️ 检测到评论频率限制提示")
                
                # 尝试关闭弹窗但不等待60秒
                try:
                    confirm_btn = self.driver.find_element(
                        By.XPATH, "//button[contains(text(), '确定')]"
                    )
                    confirm_btn.click()
                    print("✅ 已关闭频率限制提示")
                except:
                    pass
                    
                return True
        
        except:
            pass
        
        return False
    # 在 comment.py 中添加
    def wait_for_comment_rate_limit(self):
        """等待评论频率限制"""
        try:
            # 检查是否有频率限制弹窗
            rate_limit_popup = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(text(), '评论的频率过快')]"))
            )
            
            if rate_limit_popup:
                print("⚠️ 检测到评论频率限制，等待60秒...")
                time.sleep(60)
                # 点击确定按钮
                confirm_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), '确定')]")
                confirm_btn.click()
                return True
        
        except TimeoutException:
            pass
        
        return False
                
  
    
    def run_comment_task(self):
        comment_count = 0
        last_comment_time = 0
        
        print(f"\n🎯 [{self.account_name}] 开始评论任务...")
        
        while comment_count < MAX_COMMENTS_PER_DAY and len(self.saved_posts) > 0:
            selected_post = random.choice(self.saved_posts)
            post_id = selected_post["post_id"]
            post_user_id = selected_post["post_user_id"]
            
            current_time = time.time()
            if current_time - last_comment_time < COMMENT_INTERVAL:
                wait_time = COMMENT_INTERVAL - (current_time - last_comment_time)
                print(f"⏳ [{self.account_name}] 等待 {wait_time:.1f} 秒后继续...")
                time.sleep(wait_time)
            
            comment_content = random.choice(COMMENT_POOL)
            
            if self.comment_post(post_id, post_user_id, comment_content):
                comment_count += 1
                last_comment_time = time.time()
                print(f"✅ [{self.account_name}] 今日已评论: {comment_count}/{MAX_COMMENTS_PER_DAY}")
                
                next_interval = random.randint(COMMENT_INTERVAL, COMMENT_INTERVAL + 0)
                print(f"⏱️ [{self.account_name}] 下次评论间隔: {next_interval}秒")
            else:
                print(f"❌ [{self.account_name}] 评论失败，跳过该帖子")
                time.sleep(3)
        
        print(f"\n🎉 [{self.account_name}] 评论任务完成！总评论数: {comment_count}")

# 使用示例（供单独测试用）
def main():
    from selenium import webdriver
    driver = webdriver.Chrome()
    driver.get("https://www.yiban.cn")
    input("请手动登录后按回车继续...")
    cookies_dict = {cookie["name"]: cookie["value"] for cookie in driver.get_cookies()}
    
    # 初始化评论器并执行任务
    comment_bot = YibanCommentFromSavedIds(cookies_dict, driver)
    comment_bot.run_comment_task()
    
    input("按回车关闭浏览器...")
    driver.quit()

if __name__ == "__main__":
    main()