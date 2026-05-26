import os
import sys
import json
import zipfile
import requests
import subprocess
import platform
from pathlib import Path

# ================= 配置区域 =================
TARGET_DIR = r"E:\yiban\yiban"  # 驱动存放根目录
DRIVER_NAME = "msedgedriver.exe"
# ===========================================

def get_edge_version_via_cmd():
    """
    通过 CMD reg query 命令获取 Edge 完整版本号
    """
    try:
        # 执行命令
        result = subprocess.run(
            ['reg', 'query', r'HKCU\Software\Microsoft\Edge\BLBeacon', '/v', 'version'],
            capture_output=True,
            text=True,
            shell=True 
        )
        
        if result.returncode != 0:
            # 如果 HKCU 失败，尝试 HKLM (系统级安装)
            result = subprocess.run(
                ['reg', 'query', r'HKLM\Software\Microsoft\Edge\BLBeacon', '/v', 'version'],
                capture_output=True,
                text=True,
                shell=True
            )
            
        if result.returncode == 0:
            output = result.stdout
            lines = output.strip().split('\n')
            for line in lines:
                if 'REG_SZ' in line:
                    version = line.split('REG_SZ')[-1].strip()
                    print(f"✅ 通过 CMD 检测到 Edge 版本: {version}")
                    return version
        
        raise Exception("无法通过 reg query 获取版本")

    except Exception as e:
        print(f"❌ 获取 Edge 版本失败: {e}")
        return None

def build_download_url(edge_version):
    """
    根据完整版号构建微软官方下载链接
    """
    base_url = "https://msedgedriver.microsoft.com"
    clean_version = edge_version.strip()
    download_url = f"{base_url}/{clean_version}/edgedriver_win64.zip"
    print(f"🔗 构建下载链接: {download_url}")
    return download_url

def download_and_extract(driver_url, target_dir):
    """仅下载并解压，不进行任何覆盖、移动或清理操作"""
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        
    zip_path = os.path.join(target_dir, "edgedriver_temp.zip")
    
    print(f"⬇️ 正在下载驱动...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(driver_url, stream=True, timeout=60, headers=headers)
        
        if response.status_code == 404:
            print(f"❌ 下载失败: 404 Not Found。版本号 {driver_url.split('/')[3]} 可能不存在。")
            return False
            
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    sys.stdout.write(f"\r进度: {percent:.2f}%")
                    sys.stdout.flush()
        print("\n✅ 下载完成")
        
        # 解压
        print(f"📦 正在解压到: {target_dir} ...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(target_dir)
            
        # 清理临时 zip (通常建议删除压缩包，只保留解压后的文件)
        if os.path.exists(zip_path):
            os.remove(zip_path)
            print("🗑️ 已删除临时压缩包")
            
        print(f"✅ 解压完成！请手动检查 {target_dir} 目录下的文件结构。")
        print("⚠️ 注意：由于未进行覆盖和移动操作，如果驱动在子文件夹中，你可能需要手动将其移动到根目录或修改 Selenium 配置。")
        return True
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求失败: {e}")
        if os.path.exists(zip_path):
            os.remove(zip_path)
        return False
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        if os.path.exists(zip_path):
            os.remove(zip_path)
        return False

def main():
    print("="*40)
    print("🚀 EdgeDriver 自动下载工具 (纯净版)")
    print("="*40)
    
    # 1. 获取 Edge 版本
    edge_ver = get_edge_version_via_cmd()
    if not edge_ver:
        print("❌ 无法获取 Edge 版本，程序退出")
        return

    # 2. 构建下载链接
    driver_url = build_download_url(edge_ver)

    # 3. 下载并解压
    success = download_and_extract(driver_url, TARGET_DIR)
    
    if success:
        print("\n🎉 操作完成！")
    else:
        print("\n💥 操作失败。")

if __name__ == "__main__":
    main()