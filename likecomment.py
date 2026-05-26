import requests
import random
import time
import json
from typing import List, Dict
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from yanzheng import get_captcha_elements, ocr_prompt_text, find_smallest_target
import re

# 仅保留点赞配置
MAX_LIKES_PER_DAY =30  # 每日最多点赞数30
LIKE_INTERVAL = 3       # 点赞间隔（秒）
import os
# 获取当前脚本所在目录
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
POST_ID_FILE = os.path.join(CURRENT_DIR, "tieziID.py")
# POST_ID_FILE = "./tieziID.py"  # 保存帖子ID的文件

# 板块配置
BOARD_CONFIG = [
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
    {"value": "3aJTZ1XZAlDge3k", "name": "2025考研祝福"}
]

# class YibanLikeComment:
#     def __init__(self, cookies_dict: dict, driver):
#         self.session = requests.Session()
#         self.cookies_dict = cookies_dict
#         self.driver = driver
#         self.update_cookies()  # 初始化Cookie
        
#         # 提取当前登录用户ID（用于验证）
#         self.current_user_id = self.extract_current_user_id()
#         self.csrf_token = self.get_csrf_token()
#         self.ybticket = self.get_ybticket()

#         # 请求头（模拟浏览器）
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
        
#         # 初始化帖子ID列表（从文件读取已有ID）
#         self.post_ids = self.load_post_ids_from_file()
#         print(f"✅ 已加载历史帖子ID数量：{len(self.post_ids)}")

class YibanLikeComment:
    def __init__(self, cookies_dict: dict, driver, account_name: str):
        self.session = requests.Session()
        self.cookies_dict = cookies_dict
        self.driver = driver
        self.account_name = account_name  # 新增：账号名
        self.update_cookies()
        self.current_user_id = self.extract_current_user_id()
        self.csrf_token = self.get_csrf_token()
        self.ybticket = self.get_ybticket()

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
        
        self.post_ids = self.load_post_ids_from_file()
        print(f"✅ {self.account_name} 已加载历史帖子ID数量：{len(self.post_ids)}")

    def extract_current_user_id(self):
        """从浏览器Cookie提取当前用户ID（确保会话正确）"""
        try:
            for cookie in self.driver.get_cookies():
                if cookie["name"] == "yiban_user_token":
                    return cookie["value"].split("_")[-1] if "_" in cookie["value"] else "unknown"
            return "unknown"
        except Exception as e:
            print(f"提取用户ID失败: {e}")
            return "unknown"

    def get_csrf_token(self):
        """从页面实时提取CSRF token（关键：避免固定值失效）"""
        try:
            self.driver.get("https://s.yiban.cn/")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "html"))
            )
            # 从页面源码匹配token
            page_source = self.driver.page_source
            csrf_match = re.search(r'csrfToken\s*:\s*"([^"]+)"', page_source)
            if csrf_match:
                return csrf_match.group(1)
            # 备选：从Cookie提取
            for cookie in self.driver.get_cookies():
                if cookie["name"] == "csrfToken":
                    return cookie["value"]
            return ""
        except Exception as e:
            print(f"获取CSRF token失败: {e}")
            return ""

    def get_ybticket(self):
        """从页面实时提取ybticket（关键：避免固定值失效）"""
        try:
            page_source = self.driver.page_source
            ticket_match = re.search(r'ybticket\s*:\s*(\{[^}]+\})', page_source)
            return ticket_match.group(1) if ticket_match else ""
        except Exception as e:
            print(f"获取ybticket失败: {e}")
            return ""

    def update_cookies(self):
        """实时同步浏览器最新Cookie（解决会话过期问题）"""
        try:
            driver_cookies = self.driver.get_cookies()
            new_cookies_dict = {cookie["name"]: cookie["value"] for cookie in driver_cookies}
            self.session.cookies.clear()
            self.session.cookies.update(new_cookies_dict)
            self.cookies_dict = new_cookies_dict
            print("✅ 已同步最新Cookie")
        except Exception as e:
            print(f"同步Cookie失败: {e}")

    def refresh_tokens(self):
        """刷新Token和Cookie（确保请求有效）"""
        print("🔄 刷新Token和Cookie...")
        self.update_cookies()
        self.csrf_token = self.get_csrf_token()
        self.ybticket = self.get_ybticket()
        if self.ybticket:
            self.headers['ybticket'] = self.ybticket
        print("✅ Token和Cookie刷新完成")

    def get_posts_from_board(self, board_id: str, count: int = 10) -> List[Dict]:
        """获取指定板块的帖子列表"""
        url = "https://s.yiban.cn/api/forum/getListByBoard"
        random_offset = random.randint(0, 100)
        params = {
            'offset': random_offset,
            'count': count,
            'boardId': board_id,
            'orgId': '2004882',
            'order': ''
        }
        
        try:
            response = self.session.get(url, params=params, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') and data.get('data'):
                    posts = data['data'].get('list', [])
                    print(f"✅ 从板块获取到 {len(posts)} 个帖子")
                    return posts
                else:
                    print(f"❌ 获取帖子失败: {data.get('message')}")
            else:
                print(f"❌ 请求失败: {response.status_code}")
        except Exception as e:
            print(f"获取帖子异常: {e}")
        return []

    def save_post_id_to_file(self, post_id: str, post_user_id: str):
        """将点赞成功的帖子ID和作者ID保存到 tieziID.py（格式：列表+字典）"""
        # 构建帖子信息字典（包含帖子ID和作者ID，评论时需要）
        post_info = {
            "post_id": post_id,
            "post_user_id": post_user_id
        }
        
        # 去重：避免重复保存同一个帖子
        if post_info not in self.post_ids:
            self.post_ids.append(post_info)
            # 写入文件（Python格式，每行一个帖子信息）
            try:
                with open(POST_ID_FILE, "w", encoding="utf-8") as f:
                    f.write("# 点赞成功的帖子ID列表（自动生成）\n")
                    f.write("# 格式：[{post_id:'帖子ID', post_user_id:'作者ID'}, ...]\n")
                    f.write("POST_ID_LIST = [\n")
                    for post in self.post_ids:
                        f.write(f"    {{'post_id': '{post['post_id']}', 'post_user_id': '{post['post_user_id']}'}},\n")
                    f.write("]\n")
                print(f"📥 已保存帖子ID: {post_id}（作者ID: {post_user_id}）")
            except IOError as e:
                print(f"❌ 文件写入失败: {e}")
        else:
            print(f"⚠️  帖子ID {post_id} 已存在，跳过重复保存")

    def load_post_ids_from_file(self):
        """从 tieziID.py 加载已保存的帖子ID列表"""
        if not os.path.exists(POST_ID_FILE):
            print(f"⚠️  未找到 {POST_ID_FILE}，将创建新文件")
            return []
        try:
            # 动态导入文件中的 POST_ID_LIST
            import importlib.util
            spec = importlib.util.spec_from_file_location("tieziID", POST_ID_FILE)
            tiezi_id_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(tiezi_id_module)
            return tiezi_id_module.POST_ID_LIST if hasattr(tiezi_id_module, "POST_ID_LIST") else []
        except Exception as e:
            print(f"❌ 加载 {POST_ID_FILE} 失败，重置为空列表: {e}")
            return []

    def like_post(self, post_id: str, post_user_id: str) -> bool:
        """点赞单个帖子"""
        like_url = "https://s.yiban.cn/api/post/thumb"
        data = {
            'action': 'up',
            'postId': post_id,
            'userId': post_user_id  # 帖子作者ID（必须正确）
        }
        
        try:
            response = self.session.post(like_url, json=data, headers=self.headers)
            if response.status_code == 200:
                result = response.json()
                if result.get('status'):
                    # 点赞成功后保存帖子ID
                    self.save_post_id_to_file(post_id, post_user_id)
                    return True
                else:
                    print(f"❌ 点赞失败: {result.get('message')}")
                    # 若Token失效，自动刷新并重试
                    if "token" in result.get('message', '').lower():
                        self.refresh_tokens()
            else:
                print(f"❌ 点赞请求失败: {response.status_code}")
        except Exception as e:
            print(f"点赞异常: {e}")
        return False



    def run_like_task(self):
        """执行纯点赞任务"""
        like_count = 0
        last_like_time = 0
        
        print(f"🎯 [{self.account_name}] 开始点赞任务...")
        print(f"目标: 点赞 {MAX_LIKES_PER_DAY} 次")

        while like_count < MAX_LIKES_PER_DAY:
            board = random.choice(BOARD_CONFIG)
            print(f"\n===== [{self.account_name}] 处理板块: {board['name']} =====")
            
            posts = self.get_posts_from_board(board['value'], count=10)
            if not posts:
                print(f"❌ [{self.account_name}] 该板块无有效帖子，跳过")
                continue
            
            random.shuffle(posts)
            
            for post in posts:
                if like_count >= MAX_LIKES_PER_DAY:
                    print(f"\n🎉 [{self.account_name}] 已完成所有点赞目标！")
                    return
                
                post_id = post.get('id')
                post_user = post.get('user', {})
                post_user_id = post_user.get('id')
                post_subject = post.get('subject', '未知标题')[:20]

                if not post_id or not post_user_id:
                    print(f"⏭️  [{self.account_name}] 帖子信息不完整，跳过: {post_subject}")
                    continue

                current_time = time.time()
                if current_time - last_like_time < LIKE_INTERVAL:
                    wait_time = LIKE_INTERVAL - (current_time - last_like_time)
                    time.sleep(wait_time)

                if self.like_post(post_id, post_user_id):
                    like_count += 1
                    last_like_time = time.time()
                    print(f"✅ [{self.account_name}] 今日已点赞: {like_count}/{MAX_LIKES_PER_DAY}")
                else:
                    last_like_time = time.time()

                time.sleep(random.uniform(1, 2))

            if like_count < MAX_LIKES_PER_DAY:
                wait_time = random.randint(1, 2)
                print(f"🔄 [{self.account_name}] 板块处理完成，等待 {wait_time} 秒后继续...")
                time.sleep(wait_time)

        print(f"\n🎉 [{self.account_name}] 点赞任务完成！总点赞数: {like_count}")

# 使用示例（供单独测试用）
def main():
    # 注意：实际使用时需从登录后的driver获取cookies
    from selenium import webdriver
    driver = webdriver.Chrome()
    driver.get("https://www.yiban.cn")
    input("请手动登录后按回车继续...")  # 等待手动登录
    cookies_dict = {cookie["name"]: cookie["value"] for cookie in driver.get_cookies()}
    
    # 初始化点赞器并执行任务
    like_bot = YibanLikeComment(cookies_dict, driver)
    like_bot.run_like_task()
    
    input("按回车关闭浏览器...")
    driver.quit()

if __name__ == "__main__":
    main()

