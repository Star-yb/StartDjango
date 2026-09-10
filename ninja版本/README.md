# StartDjango · Ninja

基于 Django Ninja Extra 的脚手架：生成项目后自动写入 JWT 认证、验证码、Schema 驱动 API 和公共工具。

本机需要 **Python >= 3.12**。推荐安装 [uv](https://docs.astral.sh/uv/)，生成器默认用它管理虚拟环境和依赖。环境说明见仓库根目录 [README.md](../README.md)。

## 工具结构

- **`start.py` / `start.bat`**：交互式入口，串联创建流程
- **`django-creator.py`**：创建项目目录、`.venv`、安装依赖、执行 `django startproject`
- **`django-helper.py`**：按 `templates/` 写入 apps、settings、urls
- **`templates/`**：项目骨架与 `config.json` 配置
- **`pyproject.toml`**：uv 依赖（默认）
- **`requirements.txt`**：pip 回退依赖

## 使用方法

进入本目录后运行。

### 交互式创建（推荐）

```bash
python start.py
```

Windows 也可双击 `start.bat`。

按提示输入项目名称、路径、是否创建虚拟环境即可。

### 命令行创建

```bash
python start.py myproject
python start.py myproject D:\projects
python start.py myproject --no-venv
```

仅创建基础项目（不跑结构优化）：

```bash
python django-creator.py myproject
python django-creator.py myproject --path D:\projects
python django-creator.py myproject --no-venv
```

## 项目名称要求

工具会自动校验项目名：

- 不能是 Python 关键字（如 `class`、`for`）
- 不能与内置模块同名（如 `json`、`abc`、`math`）
- 只能包含字母、数字、下划线和连字符
- 不能以数字开头

推荐：`my_project`、`web_app`、`blog_site`、`api_server`

## 生成的项目结构

```
myproject/
├── .venv/                 # 虚拟环境（可选）
├── apps/
│   ├── accounts/          # 认证、验证码、JWT Controller
│   │   └── api/
│   └── common/            # 基础模型、响应、验证码工具、中间件、管理命令
├── media/
├── static/
├── templates/
├── logs/
├── myproject/             # Django 配置
├── manage.py
└── pyproject.toml
```

## 内置功能

- Ninja Extra + Ninja JWT
- 登录 / 刷新 / 校验 Token（`apps.accounts.api.auth`）
- 图片验证码（`/api/auth/captcha`）
- 统一响应 Schema
- 内置 API 文档
- CORS、软删除基础模型
- `python manage.py server`（uvicorn）

### API 端点

Ninja 接口统一挂在 `/api/` 下，文档一般在 `/api/docs`。

- `GET /api/auth/captcha` 获取验证码
- `POST /api/auth/captcha/refresh` 刷新验证码
- `POST /api/auth/captcha/verify` 校验验证码
- `POST /api/auth/login` 登录（需在 `urls.py` 注册 `CustomAuthController`）
- `POST /api/auth/refresh` 刷新 Token
- `POST /api/auth/verify` 校验 Token
- `GET /admin/` 管理后台

## 创建后启动

```bash
cd myproject
source .venv/bin/activate      # Linux / macOS
.venv\Scripts\activate         # Windows

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

访问：

- 首页：http://127.0.0.1:8000/
- 后台：http://127.0.0.1:8000/admin/
- 文档：http://127.0.0.1:8000/api/docs

## 自定义模板

修改 `templates/` 即可改变生成结果，不必改 Python 脚本。

`templates/config.json` 示例：

```json
{
  "directories": ["media", "static", "templates", "logs"],
  "apps": ["accounts", "common"],
  "settings_template": "project/settings.py",
  "urls_template": "project/urls.py",
  "env_manager": "uv"
}
```

- **`directories` / `apps`**：要创建的目录和应用
- **`templates/apps/<name>/`**：存在则整目录拷贝到生成项目
- **`settings_template` / `urls_template`**：覆盖项目配置，可用 `{{ project_name }}`
- **`env_manager`**：`uv` 或 `pip`

当前 Ninja 版已带完整 `templates/apps/accounts` 与 `templates/apps/common`。

## 技术栈

Django 6、django-ninja、django-ninja-extra、django-ninja-jwt、ninja-schema、django-cors-headers、django-simple-captcha、django-model-utils。需要 Python >= 3.12。

## 注意事项

1. 需能访问网络以下载依赖（默认清华 PyPI 镜像）
2. 创建完成后先执行 `migrate`
3. 在本目录运行脚本，不要从仓库根目录直接启动

### 依赖安装失败

```bash
uv sync
# 或
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 虚拟环境失败

```bash
python django-creator.py myproject --no-venv
```
