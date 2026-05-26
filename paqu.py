import requests
from bs4 import BeautifulSoup
import time
import random
import os
import json
import re
# 目标URL
base_url = "https://www.gushiwen.cn"
# tangshi_url = "https://www.gushiwen.cn/gushi/tangshi.aspx"#换你想要爬取的值songsan
tangshi_url = "https://www.gushiwen.cn/gushi/gaozhong.aspx"#换你想要爬取的值

def get_poetry_links():
    """获取所有唐诗的链接"""
    try:
        response = requests.get(tangshi_url, timeout=10)
        response.raise_for_status()
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'lxml')
        
        # 定位唐诗列表区域
        sons_div = soup.find('div', class_='sons')
        if not sons_div:
            print("未找到唐诗列表区域")
            return []
        
        # 提取所有古诗链接
        poetry_links = []
        for a in sons_div.find_all('a', href=True):
            relative_href = a['href']
            # 拼接完整URL
            full_url = base_url + relative_href
            poetry_links.append(full_url)
        
        return poetry_links
    except Exception as e:
        print(f"获取唐诗列表失败: {e}")
        return []

def get_poetry_content(url):
    """获取单首诗的内容"""
    try:
        # 随机延迟，避免请求过于频繁
        time.sleep(random.uniform(0.01, 0.05))
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'lxml')
        
        # 提取meta description中的诗句
        meta = soup.find('meta', attrs={'name': 'description'})
        if not meta or not meta.get('content'):
            print(f"在页面 {url} 中未找到description内容")
            return None, None
        
        content = meta['content'].strip()
        # 按第一个句号分割标题和内容
        if "。" in content:
            title, body = content.split("。", 1)
            # 补全句号
            title += "。"
            return title, body
        else:
            return content, ""
    except Exception as e:
        print(f"获取诗内容失败 ({url}): {e}")
        return None, None

def save_to_file(poetry_list, is_append=True):
    """
    保存诗句数据到指定目录，支持追加模式（彻底解决数据覆盖问题） 
    is_append: 是否追加模式（True=追加，False=覆盖）
    """
    target_dir = r"E:\NJTC-script1\yiban"
    target_file = os.path.join(target_dir, "wenan.py")
    os.makedirs(target_dir, exist_ok=True)  # 确保目录存在

    existing_data = []
    if is_append and os.path.exists(target_file):
        try:
            # 读取文件内容
            with open(target_file, 'r', encoding='utf-8') as f:
                content = f.read()
            # 正则提取已有poetry_data
            match = re.search(r'poetry_data = \[(.*?)\]', content, re.DOTALL)
            if match:
                data_str = match.group(1).strip()
                if data_str:
                    # 处理每一行的字典，转换为列表
                    items = re.findall(r'\{\s*"title":\s*"(.*?)",\s*"content":\s*"(.*?)"\s*\},?', data_str)
                    existing_data = [{"title": title, "content": content} for title, content in items]
                print(f"成功读取已有数据，共{len(existing_data)}条")
        except Exception as e:
            print(f"读取已有数据失败（{e}），将覆盖写入")
            is_append = False

    # 合并新旧数据
    # all_data = existing_data + poetry_list if is_append else poetry_list
    all_data = existing_data + [{"title": t, "content": c} for t, c in poetry_list] if is_append else [{"title": t, "content": c} for t, c in poetry_list]
    # 写入文件（格式化输出，确保语法正确）
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write("poetry_data = [\n")
        for i, item in enumerate(all_data):
            line = f'    {json.dumps(item, ensure_ascii=False)},\n'
            # 最后一行去掉逗号
            if i == len(all_data) - 1:
                line = line.rstrip(',\n') + '\n'
            f.write(line)
        f.write("]\n")

    print(f"已{'追加' if is_append else '保存'}到 {target_file}，共{len(all_data)}条数据")

def main():
    print("开始爬取...")
    poetry_links = get_poetry_links()
    if not poetry_links:
        print("未获取到链接，程序结束")
        return
    
    poetry_list = []
    for i, url in enumerate(poetry_links, 1):
        print(f"正在爬取第 {i}/{len(poetry_links)} 首诗: {url}")
        title, body = get_poetry_content(url)
        if title:
            poetry_list.append((title, body))
        print("-" * 50)
    
    target_path = r'E:\NJTC-script1\yiban\wenan.py'
    save_to_file(poetry_list, target_path)
    print(f"共爬取 {len(poetry_list)} 首诗")

if __name__ == "__main__":
    main()