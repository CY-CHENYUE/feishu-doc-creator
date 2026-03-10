# 飞书文档创建技能

通过飞书 API 创建文档，**自动转移所有权给用户**，并保留机器人的编辑权限。

> 解决飞书应用创建文档后用户无权编辑的问题。

## 核心流程

```
创建文档 → 转移所有权给用户 → 机器人保留编辑权限
```

## 安装

### OpenClaw 安装

```
在 OpenClaw 中搜索 feishu-doc-creator 并安装
```

### 手动安装

```bash
git clone https://github.com/CY-CHENYUE/feishu-doc-creator.git
```

将 `SKILL.md` 和 `scripts/` 目录放入你的 Claude Code 技能目录。

## 配置

### 1. 设置环境变量

```bash
export FEISHU_APP_ID="cli_xxxxx"
export FEISHU_APP_SECRET="xxxxx"
export FEISHU_USER_OPEN_ID="ou_xxxxx"
```

| 变量 | 说明 | 获取方式 |
|------|------|----------|
| `FEISHU_APP_ID` | 飞书应用 App ID | [飞书开放平台](https://open.feishu.cn/app) > 凭证与基础信息 |
| `FEISHU_APP_SECRET` | 飞书应用 App Secret | 同上 |
| `FEISHU_USER_OPEN_ID` | 你的 open_id | 通过 feishu-meeting-call 的 `lookup` 查找 |

### 2. 开通飞书权限

在 [飞书开放平台](https://open.feishu.cn/app) > 权限管理中搜索并开通：

| 权限 | 说明 |
|------|------|
| `docs:permission.member:create` | 添加云文档协作者 |
| `docs:permission.member:transfer` | 转移云文档的所有权 |

开通后需要在「版本管理与发布」中创建新版本并发布。

## 使用

### 创建文档（推荐）

```bash
python3 scripts/feishu_doc.py create --title "项目周报"
```

创建文档并自动完成：
1. 创建飞书文档
2. 转移所有权给你
3. 保留机器人编辑权限

### 创建到指定文件夹

```bash
python3 scripts/feishu_doc.py create --title "会议纪要" --folder "fldcnXXXXXXXX"
```

### 转移已有文档的所有权

```bash
python3 scripts/feishu_doc.py transfer --doc-token "doxcnXXXXXXXX"
```

### 添加协作者

```bash
python3 scripts/feishu_doc.py share --doc-token "doxcnXXXXXXXX" --user-id "ou_xxx" --perm edit
```

权限级别：`view`（只读）、`edit`（编辑）、`full_access`（完全控制）

## 输出示例

```
🔐 正在获取访问令牌...
✅ 令牌获取成功

📄 正在创建飞书文档...
   标题: 项目周报 2026-03-02

① 创建文档...
   ✅ 文档已创建
   文档链接: https://xxx.feishu.cn/docx/xxxxx

② 转移所有权...
   ✅ 已转移给用户 (ou_b73cc0e7...)

③ 确保机器人保留编辑权限...
   ✅ 权限设置完成

================================================
📄 文档创建完成！
   标题: 项目周报 2026-03-02
   文档链接: https://xxx.feishu.cn/docx/xxxxx
   所有者: 用户
   耗时: 2.3 秒
================================================
```

## 常见问题

| 错误 | 原因 | 解决 |
|------|------|------|
| 创建失败 (99991672) | 权限不足 | 检查应用权限配置 |
| 转移失败 (99991672) | 缺少转移权限 | 开通 `docs:permission.member:transfer` |
| 添加协作者失败 | 缺少协作者权限 | 开通 `docs:permission.member:create` |
| 认证失败 | 凭证错误 | 检查 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET` |

## 依赖

- Python 3.6+（无第三方依赖，仅使用标准库）
- 飞书应用凭证

## 相关技能

- [feishu-meeting-call](https://github.com/CY-CHENYUE/feishu-meeting-call) — 飞书紧急提醒（创建会议 + 电话/应用内加急）

## License

MIT

---

<div align="center">
  <h3>联系作者</h3>
  <p>扫码加微信，交流反馈</p>
  <img src="assets/wechat-qr.jpg" alt="WeChat QR Code" width="200">
</div>
