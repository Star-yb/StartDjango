# StarDjango

Django 项目脚手架。选定 API 栈后，一键生成带认证、文档和公共工具的可运行项目。

提供两套彼此独立的生成器：

| 目录 | 栈 | 适合 |
|------|-----|------|
| `drf版本/` | Django REST Framework + SimpleJWT + Spectacular | 需要 Swagger / ReDoc 的 REST API |
| `ninja版本/` | Django Ninja Extra + Ninja JWT | Schema 驱动、内置文档的 Ninja API |

## 环境要求

使用本生成器前，本机必须已安装 **Python**，版本要求：

- **Python >= 3.12**

强烈建议同时安装 **[uv](https://docs.astral.sh/uv/)**。生成器默认用 uv 创建虚拟环境并同步依赖，速度更快，也更稳定。没有 uv 时会回退到 pip。

### 安装 uv（推荐）

Windows（PowerShell）：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

macOS / Linux：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

安装后确认：

```bash
python --version    # 应为 3.12 或更高
uv --version
```

## 快速开始

克隆后进入对应栈目录再运行，不要在仓库根目录启动。

```bash
git clone https://github.com/Star-yb/StarDjango.git
cd StarDjango
```

**DRF：**

```bash
cd drf版本
python start.py
```

**Ninja：**

```bash
cd ninja版本
python start.py
```

Windows 也可以运行对应目录下的 `start.bat`。

按提示填写项目名称、路径、是否创建虚拟环境即可。命令行示例：

```bash
python start.py myproject
python start.py myproject D:\projects
python start.py myproject --no-venv
```

## 生成流程

1. `django-creator.py` 创建 Django 项目、`.venv`，并用 uv（或 pip）安装依赖
2. `django-helper.py` 按 `templates/` 写入 apps、settings、urls

各栈的模板、端点和启动方式见：

- [drf版本/README.md](drf版本/README.md)
- [ninja版本/README.md](ninja版本/README.md)

## 项目名称

生成时会校验名称：不能是 Python 关键字、不能与内置模块同名、只能包含字母数字和下划线/连字符、不能以数字开头。推荐如 `my_project`、`api_server`。

## License

MIT
