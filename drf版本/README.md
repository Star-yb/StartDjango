# StartDjango · DRF

基于 Django REST Framework 的脚手架：生成项目后自动写入 JWT 认证、Swagger 文档、验证码和公共工具。

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
│   ├── accounts/          # JWT 认证
│   └── common/            # 基础模型、响应、分页、中间件、管理命令
├── media/
├── static/
├── templates/
├── logs/
├── myproject/             # Django 配置
├── manage.py
└── requirements.txt / pyproject.toml
```

## 内置功能

- JWT 登录、刷新、校验
- 图片验证码
- 统一响应格式与分页
- Swagger / ReDoc 文档
- SimpleUI 后台
- CORS、软删除基础模型
- `python manage.py server`（uvicorn ASGI，替代同步 `runserver`）

### API 端点

- `POST /accounts/token/` 登录
- `POST /accounts/token/refresh/` 刷新 Token
- `POST /accounts/token/verify/` 校验 Token
- `GET /accounts/captcha/` 验证码
- `GET /admin/` 管理后台
- `GET /doc/swagger/` Swagger
- `GET /doc/redoc/` ReDoc

## 创建后启动

模板在 `apps/common/management/commands/server.py` 里提供了 uvicorn 的 ASGI 启动命令，开发和部署都用它，不再走同步 `runserver`。默认 `127.0.0.1:8005`。

```bash
cd myproject
source .venv/bin/activate      # Linux / macOS
.venv\Scripts\activate         # Windows

python manage.py migrate
python manage.py createsuperuser
python manage.py server
```

```bash
python manage.py server --host 0.0.0.0 --port 8000 --no-reload --workers 4
```

`--host`、`--port`、`--reload` / `--no-reload`、`--workers`、`--log-level` 等参数说明见仓库根目录 [README.md](../README.md)。

访问：

- 首页：http://127.0.0.1:8005/
- 后台：http://127.0.0.1:8005/admin/
- 文档：http://127.0.0.1:8005/doc/swagger/

## 自定义模板

修改 `templates/` 即可改变生成结果，不必改 Python 脚本。

`templates/config.json` 示例：

```json
{
  "directories": ["media", "static", "templates", "logs"],
  "apps": ["accounts", "common"],
  "settings_template": "project/settings.py",
  "settings_mode": "replace",
  "urls_template": "project/urls.py",
  "env_manager": "uv"
}
```

- **`directories` / `apps`**：要创建的目录和应用
- **`templates/apps/<name>/`**：存在则整目录拷贝到生成项目；不存在则用脚本内置骨架
- **`settings_template`**：`merge` 按变量合并，`replace` 整文件覆盖；可用 `{{ project_name }}`
- **`urls_template`**：覆盖项目 `urls.py`
- **`env_manager`**：`uv` 或 `pip`

## 技术栈

Django 5.2、DRF、SimpleJWT、drf-spectacular、SimpleUI、django-cors-headers、django-simple-captcha、django-model-utils。需要 Python >= 3.12。

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
