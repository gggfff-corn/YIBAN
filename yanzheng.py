import time
import random
import cv2
import os
from paddleocr import PaddleOCR
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
# 创建验证码图片保存目录
PICTURE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "yiban_picture")
if not os.path.exists(PICTURE_DIR):
    os.makedirs(PICTURE_DIR)
    
# ocr = PaddleOCR(use_textline_orientation=True, lang="ch")
_ocr_instance = None
COLOR_HSV_MAP = {
    "红色": [(0, 50, 50), (10, 255, 255), (156, 50, 50), (180, 255, 255)],
    "蓝色": [(80, 40, 40), (130, 255, 255)],
    "绿色": [(35, 50, 50), (77, 255, 255)],
    "黄色": [(20, 50, 50), (34, 255, 255)]
}

# yanzheng.py - 修改前
# ocr = PaddleOCR(use_textline_orientation=True, lang="ch")  # ❌ 模块级初始化

# yanzheng.py - 修改后
# _ocr_instance = None  # ✅ 全局缓存

def get_ocr_instance():
    """延迟加载 OCR 实例，避免导入时加载模型"""
    global _ocr_instance
    if _ocr_instance is None:
        print("⏳ 首次加载 OCR 模型，请耐心等待...")
        _ocr_instance = PaddleOCR(use_textline_orientation=True, lang="ch")
        print("✅ OCR 模型加载完成")
    return _ocr_instance

#     return captcha_img, prompt_element
def get_captcha_elements(driver):
    wait = WebDriverWait(driver, 15)
    
    # 步骤1：检查是否在iframe中，若存在则切换（核心修正）
    # try:
    #     # 查找数美验证码的iframe（通过src包含数美域名判断）
    #     # iframe = wait.until(EC.presence_of_element_located(
    #     #     (By.CSS_SELECTOR, "iframe[src*='fengkongcloud.cn'], iframe[src*='shumei']")
    #     # ))
    #     # driver.switch_to.frame(iframe)
    #     print("✅ 已切换到验证码iframe")
    # except:
    #     print("⚠️ 未找到验证码iframe，尝试在当前页面查找")
    
    # 步骤2：定位验证码图片（确保可见）
    captcha_img = wait.until(EC.visibility_of_element_located(
        (By.CLASS_NAME, "shumei_captcha_loaded_img_bg")  # 你的原类名，有效
    ))
    
    # 步骤3：定位提示文本（确保可见）
    prompt_element = wait.until(EC.visibility_of_element_located(
        (By.CLASS_NAME, "shumei_captcha_slide_tips")  # 你的原类名，有效
    ))
    
    return captcha_img, prompt_element

def ocr_prompt_text(prompt_img_path, max_attempts=1):
    """增加多次识别机制，通过投票选择最优结果，提高颜色/形状提取成功率"""
    ocr = get_ocr_instance()
    try:
        # 检查图片是否存在
        if not os.path.exists(prompt_img_path):
            print(f"提示文字图片不存在：{prompt_img_path}")
            # 返回默认值而不是要求手动输入
            return "红色", "球体"
        
        # 定义颜色和形状列表（用于匹配）
        colors = ["红色", "蓝色", "黄色", "绿色"]
        shapes = ["三棱柱", "圆柱体", "球体", "三棱锥", "圆锥", "六棱柱", "长方体"]
        
        # 存储多次识别的结果（用于投票）
        color_candidates = []
        shape_candidates = []
        
        # 多次识别循环
        for attempt in range(max_attempts):
            try:
                print(f"\n第{attempt+1}次识别：")
                # 执行OCR识别
                result = ocr.ocr(prompt_img_path)
                
                # 提取并清洗文本
                raw_text = ""
                if result and len(result) > 0:
                    for page in result:
                        if isinstance(page, dict) and "rec_texts" in page:
                            raw_text += "".join(page["rec_texts"])
                        elif isinstance(page, list):
                            for line in page:
                                if line and len(line) >= 2:
                                    raw_text += line[1][0]
                
                # 清洗文本（保留中文和数字）
                clean_text = "".join([c for c in raw_text if c.isdigit() or '\u4e00' <= c <= '\u9fff'])
                print(f"清洗后文本：{clean_text}")
                
                # 提取当前次的颜色和形状
                curr_color = None
                curr_shape = None
                # 优先匹配"颜色+形状"组合（如"黄色三棱柱"）
                for color in colors:
                    for shape in shapes:
                        if f"{color}{shape}" in clean_text:
                            curr_color = color
                            curr_shape = shape
                            break
                    if curr_color:
                        break
                # 单独匹配颜色和形状（容错）
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
                
                # 记录当前次的候选结果
                color_candidates.append(curr_color)
                shape_candidates.append(curr_shape)
                print(f"第{attempt+1}次提取：颜色={curr_color}，形状={curr_shape}")
                
                # 每次识别间隔短暂时间（避免频繁操作）
                time.sleep(0.5)
            except Exception as e:
                print(f"第{attempt+1}次OCR识别出错：{e}")
                continue
        
        # 投票选择最优结果（取出现次数最多的颜色和形状）
        from collections import Counter
        # 统计颜色出现次数（过滤None）
        valid_colors = [c for c in color_candidates if c is not None]
        # 统计形状出现次数（过滤None）
        valid_shapes = [s for s in shape_candidates if s is not None]
        
        # 确定最终颜色和形状
        final_color = None
        final_shape = None
        if valid_colors:
            final_color = Counter(valid_colors).most_common(1)[0][0]
        if valid_shapes:
            final_shape = Counter(valid_shapes).most_common(1)[0][0]
        
        print(f"\n多次识别投票结果：颜色={final_color}，形状={final_shape}")
        
        # 如果仍提取失败，使用默认值而不是要求手动输入
        if not final_color or not final_shape:
            print("多次识别仍失败，使用默认值")
            final_color = "红色"
            final_shape = "球体"
        
        return final_color, final_shape
    
    except Exception as e:
        print(f"OCR识别过程出错：{str(e)}")
        import traceback
        traceback.print_exc()
        # 出错时使用默认值
        return "红色", "球体"

def find_smallest_target(captcha_img_path, target_color, target_shape,thread_id=0):
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
        # print(f"颜色筛选后找到轮廓数量：{len(contours)}")
        
        valid_contours = []
        for i, cnt in enumerate(contours):
            area = cv2.contourArea(cnt)
            # 修复：正确缩进，只有面积过小的才跳过
            if area < 50:
                # print(f"轮廓{i}面积过小（{area}），跳过")
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
            # print(f"轮廓{i}有效：面积{area}，中心({cX},{cY})")
        
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
   