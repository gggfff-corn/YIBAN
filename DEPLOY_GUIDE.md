# 阿里云服务器部署指南

## 1. 环境准备

### 1.1 安装依赖

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Python3 和 pip
sudo apt install python3 python3-pip -y

# 安装 Chrome 浏览器
sudo apt install chromium-browser -y

# 安装 ChromeDriver（版本需与 Chrome 对应）
# 查看 Chrome 版本
chromium-browser --version

# 下载对应版本的 ChromeDriver（示例，根据实际版本调整）
wget https://storage.googleapis.com/chrome-for-testing-public/120.0.6099.109/linux64/chromedriver-linux64.zip
unzip chromedriver-linux64.zip
sudo cp chromedriver-linux64/chromedriver /usr/local/bin/
chmod +x /usr/local/bin/chromedriver

# 安装 Python 依赖
pip3 install opencv-python numpy pillow paddleocr selenium
```

### 1.2 安装 PaddleOCR 模型

```bash
# PaddleOCR 首次运行会自动下载模型，也可手动下载
mkdir -p ~/.paddleocr/whl
```

## 2. 上传代码

将以下文件上传到服务器：
- `wangxin1.py` - 主脚本
- `config.ini` - 配置文件（需修改账号密码）
- `tiezi.py` - 帖子发布模块
- `chromedriver` - Linux 版本的 ChromeDriver（如果不在系统路径）

## 3. 配置修改

### 3.1 修改 config.ini

```ini
[account]
username = 你的易班账号
password = 你的易班密码
```

### 3.2 权限设置

```bash
chmod +x wangxin1.py
chmod +x chromedriver
```

## 4. 测试运行

```bash
cd /path/to/your/scripts
python3 wangxin1.py
```

## 5. 设置定时任务

### 5.1 使用 crontab

```bash
# 编辑定时任务
crontab -e

# 添加以下内容（每天早上8点执行）
0 8 * * * /usr/bin/python3 /path/to/your/scripts/wangxin1.py >> /path/to/logs/yiban.log 2>&1

# 查看定时任务
crontab -l
```

### 5.2 定时任务说明

- `0 8 * * *` - 每天早上8点执行
- `/usr/bin/python3` - Python 路径（使用 `which python3` 查看）
- `/path/to/your/scripts/wangxin1.py` - 脚本路径
- `/path/to/logs/yiban.log` - 日志文件路径

### 5.3 常用定时表达式

| 表达式 | 含义 |
|--------|------|
| `0 8 * * *` | 每天早上8点 |
| `0 8,12,18 * * *` | 每天8点、12点、18点 |
| `*/30 * * * *` | 每30分钟 |
| `0 8 * * 1-5` | 工作日早上8点 |

## 6. 日志管理

```bash
# 创建日志目录
mkdir -p /path/to/logs

# 查看日志
tail -f /path/to/logs/yiban.log

# 查看最近100行日志
tail -n 100 /path/to/logs/yiban.log
```

## 7. 注意事项

1. **ChromeDriver 版本**：确保 ChromeDriver 版本与 Chrome 浏览器版本一致
2. **网络问题**：确保服务器网络可以访问易班网站
3. **权限问题**：确保脚本和配置文件有正确的读写权限
4. **验证码问题**：脚本使用 OCR 识别验证码，可能存在识别失败情况
5. **账号安全**：配置文件包含敏感信息，建议设置权限为 `600`

```bash
chmod 600 config.ini
```

## 8. 故障排除

### 常见错误

1. **ChromeDriver 版本不匹配**
   - 重新下载对应版本的 ChromeDriver

2. **缺少依赖**
   - 检查并安装缺少的 Python 包

3. **权限不足**
   - 确保有执行权限
   - 考虑使用 `sudo` 运行

4. **验证码识别失败**
   - 检查网络连接
   - 考虑增加重试次数