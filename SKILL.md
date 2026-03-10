---
name: feishu-doc-creator
description: 通过飞书 API 创建文档，自动转移所有权给用户，机器人保留编辑权限。支持创建文档、转移所有权、添加协作者。
version: 1.0.0
tools: Bash, Read
metadata: {"clawdbot":{"emoji":"📄","primaryEnv":"FEISHU_APP_ID","requires":{"bins":["python3"],"env":["FEISHU_APP_ID","FEISHU_APP_SECRET","FEISHU_USER_OPEN_ID"]}}}
---

# 飞书文档创建

通过飞书 API 创建文档，自动将所有权转移给用户，并保留机器人的编辑权限。解决飞书应用创建文档后用户无权编辑的问题。

## 首次使用配置（最高优先级）

**每次执行技能前，必须先检查环境变量。** 缺哪项补哪项，不要全量重配。

### 检查步骤

```bash
echo "APP_ID=${FEISHU_APP_ID:-(未设置)}" && echo "APP_SECRET=${FEISHU_APP_SECRET:-(未设置)}" && echo "USER_OPEN_ID=${FEISHU_USER_OPEN_ID:-(未设置)}"
```

- 三项都存在 → 跳过本节，直接执行用户请求
- 任何一项显示「未设置」→ 只针对缺失项执行下方对应步骤

> **提示**：如果用户已安装并配置过 feishu-meeting-call 技能，`~/.feishu.env` 中通常已有这三个变量，无需重复配置。

### 补全缺失的 FEISHU_APP_ID / FEISHU_APP_SECRET

仅当 APP_ID 或 APP_SECRET 缺失时执行。

**向用户索取凭证：**
> 需要配置飞书应用凭证才能使用。请提供：
> - **App ID** 和 **App Secret** — 在 [飞书开放平台](https://open.feishu.cn/app) → 应用详情 → 凭证与基础信息 中获取
>
> 如果还没有飞书应用，请参考下方「飞书应用创建指南」创建。

**用户提供后，写入专用配置文件（幂等）：**

```bash
# 创建或更新 ~/.feishu.env（专用配置文件，避免污染 ~/.zshrc）
touch ~/.feishu.env && chmod 600 ~/.feishu.env
# 幂等写入：已存在则替换，不存在则追加
grep -q '^export FEISHU_APP_ID=' ~/.feishu.env \
  && sed -i '' 's|^export FEISHU_APP_ID=.*|export FEISHU_APP_ID="用户提供的AppID"|' ~/.feishu.env \
  || echo 'export FEISHU_APP_ID="用户提供的AppID"' >> ~/.feishu.env
grep -q '^export FEISHU_APP_SECRET=' ~/.feishu.env \
  && sed -i '' 's|^export FEISHU_APP_SECRET=.*|export FEISHU_APP_SECRET="用户提供的AppSecret"|' ~/.feishu.env \
  || echo 'export FEISHU_APP_SECRET="用户提供的AppSecret"' >> ~/.feishu.env
# 确保 ~/.zshrc 会加载此文件（幂等，只加一次）
grep -q 'source ~/.feishu.env' ~/.zshrc || echo '[ -f ~/.feishu.env ] && source ~/.feishu.env' >> ~/.zshrc
# 当前会话立即生效
source ~/.feishu.env
```

> **安全提醒**：写入完成后，**不要在聊天中回显 App Secret 明文**。只需告诉用户「凭证已保存」。

### 补全缺失的 FEISHU_USER_OPEN_ID

仅当 FEISHU_USER_OPEN_ID 缺失时执行。需要 APP_ID/SECRET 已就绪。

**向用户索取手机号或邮箱，然后 lookup：**

> 如果已安装 feishu-meeting-call 技能，可以用它的 lookup 命令；否则需要用户在飞书开放平台的 API 调试台查找自己的 open_id。

```bash
# 当前命令显式注入环境变量（确保子进程可用），同时执行 lookup
source ~/.feishu.env && python3 {baseDir}/../feishu-meeting-call/scripts/feishu_meeting.py lookup --phone "用户的手机号"
```

**查到 open_id 后，写入配置文件（幂等）：**

```bash
grep -q '^export FEISHU_USER_OPEN_ID=' ~/.feishu.env \
  && sed -i '' 's|^export FEISHU_USER_OPEN_ID=.*|export FEISHU_USER_OPEN_ID="查到的open_id"|' ~/.feishu.env \
  || echo 'export FEISHU_USER_OPEN_ID="查到的open_id"' >> ~/.feishu.env
source ~/.feishu.env
```

### 配置完成

补全所有缺失项后告诉用户：
> 飞书配置已保存到 `~/.feishu.env`，后续使用无需再次配置。

然后**继续执行用户原本的请求**（创建文档等），执行命令前先 `source ~/.feishu.env` 确保变量可用：

```bash
source ~/.feishu.env && python3 {baseDir}/scripts/feishu_doc.py create --title "xxx"
```

### 飞书应用创建指南

如果用户还没有飞书应用，引导他们：

1. 打开 [飞书开放平台](https://open.feishu.cn/app)，点击「创建企业自建应用」
2. 填写应用名称和描述，创建应用
3. 记录 **App ID** 和 **App Secret**
4. 左侧「权限管理」→ 搜索并开通以下权限：
   - `docs:permission.member:create`（添加云文档协作者）
   - `docs:permission.member:transfer`（转移云文档的所有权）
5. 左侧「版本管理与发布」→ 可用范围中添加自己 → 创建版本并发布

## 核心流程

```
创建文档 → 转移所有权给用户 → 机器人保留编辑权限
```

1. **创建文档**：机器人通过 API 创建飞书文档
2. **转移所有权**：将文档所有者从机器人转移给用户
3. **保留协作权限**：确保机器人后续仍可编辑文档内容

## 快速开始

```bash
# 创建文档（自动转移所有权给你）
python3 {baseDir}/scripts/feishu_doc.py create --title "项目周报"

# 创建文档到指定文件夹
python3 {baseDir}/scripts/feishu_doc.py create --title "会议纪要" --folder "fldcnXXXXXXXX"

# 转移已有文档的所有权
python3 {baseDir}/scripts/feishu_doc.py transfer --doc-token "doxcnXXXXXXXX"

# 给文档添加协作者
python3 {baseDir}/scripts/feishu_doc.py share --doc-token "doxcnXXXXXXXX" --user-id "ou_xxx" --perm edit
```

## 命令说明

### 1. `create` — 创建文档（推荐）

创建文档 + 自动转移所有权 + 保留机器人编辑权限。**这是最常用的命令。**

```bash
python3 {baseDir}/scripts/feishu_doc.py create --title "文档标题"
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--title` / `-t` | 文档标题（必填） | - |
| `--folder` / `-f` | 目标文件夹 token | 默认位置 |
| `--user-id` / `-u` | 转移给谁的 open_id | 从 `FEISHU_USER_OPEN_ID` 读取 |

### 2. `transfer` — 仅转移所有权

转移已有文档的所有权。适用于之前创建但未转移的文档。

```bash
python3 {baseDir}/scripts/feishu_doc.py transfer --doc-token "文档token"
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--doc-token` | 文档 token（必填） | - |
| `--user-id` / `-u` | 目标用户 open_id | 从 `FEISHU_USER_OPEN_ID` 读取 |
| `--type` | 文档类型 | `docx` |

支持的文档类型：`docx`、`doc`、`sheet`、`bitable`、`folder`、`file`、`wiki`、`mindnote`

### 3. `share` — 添加协作者

给文档添加协作者并指定权限级别。

```bash
python3 {baseDir}/scripts/feishu_doc.py share --doc-token "文档token" --perm edit
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--doc-token` | 文档 token（必填） | - |
| `--user-id` / `-u` | 协作者 open_id | 从 `FEISHU_USER_OPEN_ID` 读取 |
| `--perm` | 权限级别 | `edit` |
| `--type` | 文档类型 | `docx` |

权限级别说明：
- `view` — 可阅读
- `edit` — 可编辑
- `full_access` — 完全控制

## 使用场景

| 场景 | 推荐命令 | 说明 |
|------|---------|------|
| 帮我建个文档 | `create` | 创建文档并自动转移所有权 |
| 写一份周报 | `create` | 创建文档，后续可通过机器人写入内容 |
| 我之前的文档没权限 | `transfer` | 转移已有文档的所有权 |
| 让同事也能编辑 | `share` | 添加协作者 |
| 创建到指定文件夹 | `create --folder` | 指定文件夹 token |

## AI 使用指引

当用户说以下内容时，使用本技能：
- 「帮我创建一个飞书文档」「建个文档」「写个文档」
- 「帮我写一份 XX 报告」「创建会议纪要」「写个周报」
- 「文档没有权限」「帮我转移文档权限」
- 「把文档分享给 XX」「添加协作者」

### 默认行为

1. **始终使用 `create` 命令**创建文档（除非用户明确要求转移或分享）
2. 创建后自动转移所有权给用户（使用 `FEISHU_USER_OPEN_ID`）
3. 机器人保留编辑权限，后续可继续操作文档

### 结果反馈

执行成功后，**必须将以下信息反馈给用户**：

1. **文档标题**
2. **文档链接**（用户点击即可打开）
3. **所有权状态**（是否已转移给用户）

示例反馈：

```
飞书文档已创建：
- 标题：项目周报 2026-03-02
- 链接：https://xxx.feishu.cn/docx/xxxxx
- 所有者：你
- 机器人：可编辑
```

如果部分步骤失败，也要如实反馈：

```
文档已创建但所有权转移失败：
- 标题：项目周报
- 链接：https://xxx.feishu.cn/docx/xxxxx
- 所有者：机器人（转移失败）
- 建议：请在飞书开放平台开通 docs:permission.member:transfer 权限
```

## 所需飞书权限

### 权限列表

| 权限 | 说明 | 用途 | 必需 |
|------|------|------|------|
| `docs:permission.member:create` | 添加云文档协作者 | share 命令、create 后添加机器人协作者 | 是 |
| `docs:permission.member:transfer` | 转移云文档的所有权 | create 和 transfer 命令 | 是 |

> **注意**：创建文档功能使用 `tenant_access_token` 时，应用默认具有创建文档的能力，无需额外的文档创建权限。

### 权限开通步骤

1. 打开 [飞书开放平台](https://open.feishu.cn/app)，进入你的应用
2. 左侧菜单点击 **「权限管理」**
3. 搜索 `docs:permission.member`，分别开通：
   - `docs:permission.member:create` — 添加云文档协作者
   - `docs:permission.member:transfer` — 转移云文档的所有权
4. 进入 **「版本管理与发布」** 创建新版本并发布

## 常见错误排查

| 错误现象 | 原因 | 解决方法 |
|---------|------|---------|
| 创建文档失败 (99991672) | 权限不足 | 检查应用是否有文档创建权限 |
| 创建文档失败 (99991668) | 文件夹 token 无效 | 检查 --folder 参数是否正确 |
| 转移所有权失败 (99991672) | 缺少转移权限 | 开通 `docs:permission.member:transfer` |
| 添加协作者失败 (99991672) | 缺少协作者权限 | 开通 `docs:permission.member:create` |
| 转移失败 (99991400) | open_id 格式错误 | 检查 FEISHU_USER_OPEN_ID 是否正确 |
| 认证失败 | App ID 或 Secret 错误 | 检查 FEISHU_APP_ID 和 FEISHU_APP_SECRET |

## 外部接口说明

本技能会向以下地址发送请求：

| 接口 | 地址 | 发送的数据 |
|------|------|-----------|
| 飞书认证 | `https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal` | App ID、App Secret |
| 创建文档 | `https://open.feishu.cn/open-apis/docx/v1/documents` | 文档标题、文件夹 token |
| 转移所有权 | `https://open.feishu.cn/open-apis/drive/v1/permissions/{token}/members/transfer_owner` | 用户 open_id |
| 添加协作者 | `https://open.feishu.cn/open-apis/drive/v1/permissions/{token}/members` | 协作者 ID、权限级别 |

除上述接口外，不会向任何其他地址发送数据。

## 依赖

- Python 3.6+（无第三方依赖，仅使用标准库）
- 有效的飞书应用凭证
