[English](./README.md)

# Gemini API 唯一性代理

一个简单的、可自行部署的 Google Gemini API 代理服务，旨在解决一个特定问题：当连续发送完全相同的提示（Prompt）时，Gemini API 有时会拒绝响应。

## 问题背景

在短时间内向 Gemini API 发送多次完全相同的请求时，您可能会遇到 API 返回空内容或不完整响应的情况。这很可能是由于服务端存在某种机制，用于防止重复处理或过滤潜在的垃圾请求。然而，对于某些需要合法地多次发送相同提示的应用场景（例如，在无状态环境中进行测试或重试），这会成为一个棘手的问题。

## 解决方案

该代理服务会拦截您发送给 Gemini API 的请求，并透明地向您的提示（Prompt）添加唯一内容。默认情况下，它会在提示的末尾追加一个高精度的时间戳，但这个行为是完全可配置的。

**原始提示:**
`"法国的首都是哪里？"`

**修改后发送给 Gemini 的提示（默认 SUFFIX + TIMESTAMP 模式）:**
`"法国的首都是哪里？\n\n(Current time: 2023-10-27 10:30:00.123. This is an automated injection by the proxy. Please disregard.)"`

**使用 PREFIX + UUID 模式的替代方案:**
`"(Random ID: a4b7. This is an automated injection by the proxy. Please disregard.)\n\n法国的首都是哪里？"`

这个微小的改动使得从 Gemini API 的角度来看，每个请求都变得独一无二，从而有效地绕过了其重复请求过滤器，确保您能获得稳定的响应。我们添加的文本前缀经过精心设计，会被模型忽略，不影响生成结果的质量。

## 功能特性

- **可配置的提示唯一性**: 为每个请求注入时间戳或UUID，解决重复提示问题。
- **灵活的注入位置**: 可选择在提示的开头（PREFIX）或结尾（SUFFIX）注入内容。
- **多种注入模式**: 支持时间戳注入（默认）或基于UUID的唯一性。
- **完全 API 兼容**: 完美镜像 Gemini API 的接口结构，您可以将其作为官方 API 端点的直接替代品。
- **支持流式响应**: 完全支持流式（Streaming）响应，提供实时交互体验。
- **灵活的身份验证**: 同时支持从 `Authorization: Bearer <key>` 请求头和 `?key=<key>` URL参数中获取 API 密钥。
- **易于部署**: 单个 Python 文件，依赖项极少。

## 安装与使用

### 使用 Docker Compose (推荐)

最简单的部署方式是使用 Docker Compose。

1.  **环境要求**: 请确保您已安装 Docker 和 Docker Compose。
2.  **克隆本仓库。**
3.  **启动服务**:
    ```bash
    docker-compose up -d
    ```
代理服务现在将运行在 `http://localhost:8000`。您可以像下面描述的那样发送请求。

### 手动安装

#### 1. 环境要求

- Python 3.8+
- `pip`

#### 2. 安装

1.  克隆本仓库或下载 `main.py` 文件。

2.  创建一个名为 `requirements.txt` 的文件（或使用已提供的），并填入以下内容：
    ```
    fastapi
    uvicorn
    httpx
    python-dotenv
    ```

3.  安装依赖：
    ```bash
    pip install -r requirements.txt
    ```

4.  （可选）在项目根目录下创建一个 `.env` 文件，用于配置代理行为。如果未提供，将使用默认的上游端点 `https://generativelanguage.googleapis.com`，采用 SUFFIX 注入 TIMESTAMP 的方式。
    ```
    # .env
    UPSTREAM_GEMINI_ENDPOINT="https://generativelanguage.googleapis.com"
    
    # 注入位置: "SUFFIX" (默认) 或 "PREFIX"
    INJECTION_POSITION=SUFFIX
    
    # 注入模式: "TIMESTAMP" (默认) 或 "UUID"
    INJECTION_MODE=TIMESTAMP
    ```

#### 3. 运行代理

使用 Uvicorn 启动代理服务器：

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

现在，代理服务已在 `http://localhost:8000` 上运行。

## 发送请求

将您的应用程序或客户端请求的目标地址从官方 Gemini API 端点修改为代理服务器的地址（`http://localhost:8000`）。请确保请求中包含了您的 Gemini API 密钥。

**`curl` 使用示例:**

```bash
curl http://localhost:8000/v1beta/models/gemini-pro:generateContent?key=你的API密钥 \
    -H 'Content-Type: application/json' \
    -d '{
      "contents": [{
        "parts":[{
          "text": "写一个关于魔法背包的故事。"
        }]
      }]
    }'
```

代理服务会自动为您的请求添加唯一内容（时间戳或UUID），然后将其转发给 Gemini，并将收到的响应流式传输回给您。

## 配置选项

代理支持多个环境变量来自定义其行为：

- **`UPSTREAM_GEMINI_ENDPOINT`**: 上游 Gemini API 端点（默认：`https://generativelanguage.googleapis.com`）
- **`INJECTION_POSITION`**: 唯一内容注入位置
  - `SUFFIX`（默认）：追加到提示末尾
  - `PREFIX`：添加到提示开头
- **`INJECTION_MODE`**: 注入的唯一内容类型
  - `TIMESTAMP`（默认）：高精度时间戳
  - `UUID`：4位随机UUID

### 不同配置的示例

**默认配置（SUFFIX + TIMESTAMP）：**
```
原始提示: "你好，世界！"
修改后: "你好，世界！\n\n(Current time: 2023-10-27 10:30:00.123. This is an automated injection by the proxy. Please disregard.)"
```

**PREFIX + UUID 配置：**
```
原始提示: "你好，世界！"
修改后: "(Random ID: a4b7. This is an automated injection by the proxy. Please disregard.)\n\n你好，世界！"
```