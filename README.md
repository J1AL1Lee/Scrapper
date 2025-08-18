# 课程信息爬虫

一个基于 Playwright 的智能课程信息爬虫，支持自动点击验证码识别和登录。

## ✨ 功能特性

- 🔐 **智能登录**: 支持自动点击验证码识别，无需手动操作
- 🤖 **多种验证码识别**: 计算机视觉识别 + 若快在线服务
- 📚 **课程数据抓取**: 自动抓取课程标题、教师、代码等信息
- 💾 **会话管理**: 自动保存和恢复登录状态
- 🚀 **高性能**: 异步处理，支持并发抓取

## 🚀 快速开始

### 1. 安装依赖

```bash
# 自动安装所有依赖
python install_deps.py

# 或手动安装
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置账号

在 `config.py` 中配置你的登录信息：

```python
username: str = "你的用户名"
password: str = "你的密码"
```

### 3. 运行爬虫

```bash
# 使用计算机视觉自动识别点击验证码（推荐）
python main.py

# 明确使用计算机视觉
python main.py --use-solver ocr

# 使用若快在线服务（需配置账号）
python main.py --use-solver ruokuai

# 手动登录（备用方案）
python main.py --login-manual
```

## 🔧 配置说明

### 验证码识别服务

#### 计算机视觉识别（默认）

- 无需额外配置
- 支持点击验证码（如"请依次点击【加,书,话】"）
- 识别准确率约 60-80%

#### 若快在线服务

- 识别准确率更高（90%+）
- 需要配置账号信息

```bash
# 设置环境变量
export SOLVER_USERNAME="你的若快用户名"
export SOLVER_PASSWORD="你的若快密码"
export SOLVER_SOFT_ID="软件ID"
```

### 其他配置

在 `config.py` 中可以调整：

- 页面加载超时时间
- 请求间隔
- 并发数量
- 浏览器设置

## 📊 输出格式

抓取的数据将保存为 `courses.csv` 文件，包含以下字段：

- `title`: 课程标题
- `teacher`: 教师姓名
- `code`: 课程代码
- `link`: 课程链接

## 🛠️ 故障排除

### 验证码识别失败

1. 确保已安装 OpenCV、NumPy、Pillow
2. 尝试使用若快在线服务
3. 检查验证码图片是否清晰
4. 验证码指令是否清晰可读

### 登录失败

1. 检查账号密码是否正确
2. 确认网络连接正常
3. 尝试手动登录模式

### 依赖安装问题

1. 运行 `python install_deps.py` 自动安装
2. 检查 Python 版本（建议 3.8+）
3. 确保 pip 是最新版本

## 📝 开发说明

### 项目结构

```
├── main.py              # 主程序入口
├── crawler.py           # 核心爬虫逻辑
├── config.py            # 配置文件
├── selectors.py         # 页面元素选择器
├── utils.py             # 工具函数
├── captcha/             # 验证码识别模块
├── install_deps.py      # 依赖安装脚本
└── requirements.txt     # 依赖列表
```

### 扩展验证码识别器

继承 `ClickCaptchaSolver` 类并实现 `solve_captcha` 方法：

```python
class CustomSolver(ClickCaptchaSolver):
    async def solve_captcha(self, image_bytes: bytes, instruction: str = "") -> dict:
        # 你的点击验证码识别逻辑
        return {"success": True, "result": [(x1, y1), (x2, y2), ...]}
```

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！
