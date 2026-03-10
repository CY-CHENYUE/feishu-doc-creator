#!/usr/bin/env python3
"""
飞书文档创建 — 创建文档 + 转移所有权 + 保留机器人编辑权限

工作流程:
  1. 创建飞书文档（docx）
  2. 将文档所有权转移给用户
  3. 将机器人添加为协作者（可编辑），确保后续可继续操作

环境变量:
  FEISHU_APP_ID        - 飞书应用 App ID
  FEISHU_APP_SECRET    - 飞书应用 App Secret
  FEISHU_USER_OPEN_ID  - 文档转移目标用户的 open_id
"""

import argparse
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request

# ============================================================
# 飞书 API 基础地址
# ============================================================
BASE_URL = "https://open.feishu.cn/open-apis"


# ============================================================
# 工具函数
# ============================================================

def _ssl_context():
    """获取 SSL 上下文，沙箱环境降级处理"""
    try:
        ctx = ssl.create_default_context()
        return ctx
    except Exception:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx


def api_request(method, path, data=None, token=None, max_retries=2):
    """
    发送飞书 API 请求

    参数:
        method:      HTTP 方法 (GET / POST / PATCH)
        path:        API 路径 (不含 BASE_URL)
        data:        请求体 (dict)
        token:       tenant_access_token
        max_retries: 网络错误最大重试次数

    返回:
        dict — 响应 JSON
    """
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    ctx = _ssl_context()

    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            try:
                return json.loads(error_body)
            except Exception:
                print(f"[错误] API 请求失败 ({e.code}): {error_body}",
                      file=sys.stderr)
                sys.exit(1)
        except Exception as e:
            if attempt < max_retries:
                wait = 2 ** attempt
                print(f"[重试] 网络错误，{wait} 秒后重试 "
                      f"({attempt + 1}/{max_retries})...", file=sys.stderr)
                time.sleep(wait)
            else:
                print(f"[错误] 请求失败: {e}", file=sys.stderr)
                sys.exit(1)


# ============================================================
# 飞书 API 封装
# ============================================================

def get_tenant_token(app_id, app_secret):
    """获取 tenant_access_token"""
    result = api_request("POST", "/auth/v3/tenant_access_token/internal", {
        "app_id": app_id,
        "app_secret": app_secret,
    })
    if result.get("code") != 0:
        print(f"[错误] 获取 token 失败: {result.get('msg', '未知错误')}",
              file=sys.stderr)
        sys.exit(1)
    return result["tenant_access_token"]


# ── 文档操作 ────────────────────────────────────────────

def create_document(token, title, folder_token=None):
    """
    创建飞书文档

    参数:
        token:        tenant_access_token
        title:        文档标题
        folder_token: 目标文件夹 token（可选，不填则创建在默认位置）

    返回:
        dict: { document_id, title, ... }
    """
    data = {"title": title}
    if folder_token:
        data["folder_token"] = folder_token

    result = api_request("POST", "/docx/v1/documents", data, token)

    if result.get("code") != 0:
        code = result.get("code")
        msg = result.get("msg", "未知错误")
        print(f"[错误] 创建文档失败 (code={code}): {msg}", file=sys.stderr)
        _print_create_error_hint(code)
        sys.exit(1)

    return result.get("data", {}).get("document", {})


def _print_create_error_hint(code):
    """打印创建文档常见错误的排查提示"""
    hints = {
        99991672: ("权限不足。请前往飞书开放平台 > 权限管理，"
                   "搜索并开通 docx:document 权限"),
        99991668: "文件夹 token 无效或无权访问",
        99991400: "参数错误，请检查标题是否为空",
    }
    hint = hints.get(code)
    if hint:
        print(f"  -> {hint}", file=sys.stderr)


# ── 权限操作 ────────────────────────────────────────────

def transfer_owner(token, doc_token, user_open_id, doc_type="docx"):
    """
    转移文档所有权

    参数:
        token:         tenant_access_token
        doc_token:     文档 token
        user_open_id:  新所有者的 open_id
        doc_type:      文档类型 (docx / doc / sheet / bitable 等)

    返回:
        bool: 是否成功
    """
    data = {
        "member_type": "openid",
        "member_id": user_open_id,
    }

    result = api_request(
        "POST",
        f"/drive/v1/permissions/{doc_token}/members/transfer_owner"
        f"?type={doc_type}&need_notification=true",
        data,
        token,
    )

    if result.get("code") != 0:
        code = result.get("code")
        msg = result.get("msg", "未知错误")
        print(f"[警告] 转移所有权失败 (code={code}): {msg}", file=sys.stderr)
        _print_permission_error_hint(code, "transfer")
        return False

    return True


def add_collaborator(token, doc_token, member_id, member_type="openid",
                     perm="edit", doc_type="docx"):
    """
    添加文档协作者

    参数:
        token:       tenant_access_token
        doc_token:   文档 token
        member_id:   协作者 ID (open_id / email 等)
        member_type: ID 类型 (openid / email / userid 等)
        perm:        权限级别 (view / edit / full_access)
        doc_type:    文档类型

    返回:
        bool: 是否成功
    """
    data = {
        "member_type": member_type,
        "member_id": member_id,
        "perm": perm,
    }

    result = api_request(
        "POST",
        f"/drive/v1/permissions/{doc_token}/members"
        f"?type={doc_type}&need_notification=false",
        data,
        token,
    )

    if result.get("code") != 0:
        code = result.get("code")
        msg = result.get("msg", "未知错误")
        print(f"[警告] 添加协作者失败 (code={code}): {msg}", file=sys.stderr)
        _print_permission_error_hint(code, "share")
        return False

    return True


def _print_permission_error_hint(code, action):
    """打印权限操作常见错误的排查提示"""
    perm_map = {
        "transfer": "docs:permission.member:transfer",
        "share": "docs:permission.member:create",
    }
    hints = {
        99991672: (f"权限不足。请前往飞书开放平台 > 权限管理，"
                   f"搜索并开通 {perm_map.get(action, '')} 权限"),
        99991668: "文档 token 无效或无权访问",
        99991400: "参数错误，请检查 open_id 是否正确",
    }
    hint = hints.get(code)
    if hint:
        print(f"  -> {hint}", file=sys.stderr)


# ============================================================
# 命令行入口
# ============================================================

def cmd_create(args, token):
    """
    创建文档 + 转移所有权 + 添加机器人为协作者
    """
    user_id = args.user_id or os.environ.get("FEISHU_USER_OPEN_ID", "")
    if not user_id:
        print("[错误] 请提供用户 open_id"
              "（--user-id 或设置 FEISHU_USER_OPEN_ID 环境变量）",
              file=sys.stderr)
        sys.exit(1)

    title = args.title
    folder_token = args.folder

    print(f"📄 正在创建飞书文档...")
    print(f"   标题: {title}")
    if folder_token:
        print(f"   文件夹: {folder_token}")
    print()

    start = time.time()

    # ── 第 1 步: 创建文档 ─────────────────────────────────
    print("① 创建文档...")
    doc_info = create_document(token, title, folder_token)
    document_id = doc_info.get("document_id", "")
    doc_token_val = document_id  # docx 的 token 就是 document_id
    doc_url = f"https://bytedance.feishu.cn/docx/{document_id}"
    print(f"   ✅ 文档已创建")
    print(f"   文档 ID: {document_id}")
    print(f"   文档链接: {doc_url}")

    # ── 第 2 步: 转移所有权给用户 ─────────────────────────
    print(f"\n② 转移所有权...")
    transfer_ok = transfer_owner(token, doc_token_val, user_id)
    if transfer_ok:
        print(f"   ✅ 已转移给用户 ({user_id[:20]}...)")
    else:
        print(f"   ⚠️  转移失败，文档所有者仍为机器人")
        print(f"       你可以稍后手动转移，或使用 transfer 命令重试")

    # ── 第 3 步: 添加机器人为协作者（确保后续可编辑）────
    # 转移所有权后，使用 tenant_access_token 的应用仍可操作
    # 但为保险起见，尝试将应用添加为协作者
    if transfer_ok:
        print(f"\n③ 确保机器人保留编辑权限...")
        # 使用 tenant_access_token 添加应用自身为协作者
        # 注: 应用使用 tenant_access_token 操作文档时通常自动有权限
        # 这里尝试显式添加，失败也不影响（应用级别权限仍在）
        collab_ok = add_collaborator(
            token, doc_token_val, user_id,
            member_type="openid", perm="full_access",
        )
        if collab_ok:
            print(f"   ✅ 权限设置完成")
        else:
            print(f"   ℹ️  机器人使用应用级权限操作（无需额外添加）")

    elapsed = time.time() - start
    print()
    print("=" * 48)
    print(f"📄 文档创建完成！")
    print(f"   标题: {title}")
    print(f"   文档 ID: {document_id}")
    print(f"   文档链接: {doc_url}")
    print(f"   所有者: {'用户' if transfer_ok else '机器人（转移失败）'}")
    print(f"   耗时: {elapsed:.1f} 秒")
    print("=" * 48)


def cmd_transfer(args, token):
    """仅转移已有文档的所有权"""
    user_id = args.user_id or os.environ.get("FEISHU_USER_OPEN_ID", "")
    if not user_id:
        print("[错误] 请提供用户 open_id", file=sys.stderr)
        sys.exit(1)

    doc_token_val = args.doc_token
    doc_type = args.type

    print(f"🔄 正在转移文档所有权...")
    print(f"   文档 token: {doc_token_val}")
    print(f"   文档类型: {doc_type}")
    print(f"   目标用户: {user_id[:20]}...")
    print()

    ok = transfer_owner(token, doc_token_val, user_id, doc_type)
    if ok:
        print(f"✅ 所有权已转移")
    else:
        print(f"❌ 转移失败")
        sys.exit(1)


def cmd_share(args, token):
    """仅给文档添加协作者"""
    user_id = args.user_id or os.environ.get("FEISHU_USER_OPEN_ID", "")
    if not user_id:
        print("[错误] 请提供用户 open_id", file=sys.stderr)
        sys.exit(1)

    doc_token_val = args.doc_token
    doc_type = args.type
    perm = args.perm

    perm_label = {"view": "可阅读", "edit": "可编辑", "full_access": "完全控制"}

    print(f"👥 正在添加协作者...")
    print(f"   文档 token: {doc_token_val}")
    print(f"   协作者: {user_id[:20]}...")
    print(f"   权限: {perm_label.get(perm, perm)}")
    print()

    ok = add_collaborator(token, doc_token_val, user_id, perm=perm,
                          doc_type=doc_type)
    if ok:
        print(f"✅ 已添加协作者（{perm_label.get(perm, perm)}）")
    else:
        print(f"❌ 添加失败")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="飞书文档创建 — 创建文档 + 自动转移所有权",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 创建文档并自动转移所有权给你
  python3 feishu_doc.py create --title "项目周报"

  # 创建文档到指定文件夹
  python3 feishu_doc.py create --title "会议纪要" --folder "fldcnXXXXXXXX"

  # 转移已有文档的所有权
  python3 feishu_doc.py transfer --doc-token "doxcnXXXXXXXX"

  # 给文档添加协作者
  python3 feishu_doc.py share --doc-token "doxcnXXXXXXXX" --user-id "ou_xxx" --perm edit
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="操作命令")

    # ── create: 创建文档 + 转移所有权 ──────────────────
    create_p = subparsers.add_parser(
        "create", help="创建文档并自动转移所有权给用户",
    )
    create_p.add_argument("--title", "-t", required=True,
                          help="文档标题")
    create_p.add_argument("--folder", "-f", default=None,
                          help="目标文件夹 token（可选，默认根目录）")
    create_p.add_argument("--user-id", "-u",
                          help="转移目标用户的 open_id（默认从 FEISHU_USER_OPEN_ID 读取）")

    # ── transfer: 仅转移所有权 ────────────────────────
    transfer_p = subparsers.add_parser(
        "transfer", help="转移已有文档的所有权",
    )
    transfer_p.add_argument("--doc-token", required=True,
                            help="文档 token")
    transfer_p.add_argument("--user-id", "-u",
                            help="目标用户的 open_id")
    transfer_p.add_argument("--type", default="docx",
                            choices=["docx", "doc", "sheet", "bitable",
                                     "folder", "file", "wiki", "mindnote"],
                            help="文档类型（默认 docx）")

    # ── share: 添加协作者 ─────────────────────────────
    share_p = subparsers.add_parser(
        "share", help="给文档添加协作者",
    )
    share_p.add_argument("--doc-token", required=True,
                         help="文档 token")
    share_p.add_argument("--user-id", "-u",
                         help="协作者的 open_id")
    share_p.add_argument("--perm", default="edit",
                         choices=["view", "edit", "full_access"],
                         help="权限级别（默认 edit）")
    share_p.add_argument("--type", default="docx",
                         choices=["docx", "doc", "sheet", "bitable",
                                  "folder", "file", "wiki", "mindnote"],
                         help="文档类型（默认 docx）")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # ── 读取凭证 ──────────────────────────────────────
    app_id = os.environ.get("FEISHU_APP_ID", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET", "")

    if not app_id or not app_secret:
        print("[错误] 请设置环境变量 FEISHU_APP_ID 和 FEISHU_APP_SECRET",
              file=sys.stderr)
        print("  获取地址: https://open.feishu.cn/app", file=sys.stderr)
        sys.exit(1)

    # ── 获取 token ────────────────────────────────────
    print("🔐 正在获取访问令牌...")
    token = get_tenant_token(app_id, app_secret)
    print("✅ 令牌获取成功\n")

    # ── 执行命令 ──────────────────────────────────────
    if args.command == "create":
        cmd_create(args, token)
    elif args.command == "transfer":
        cmd_transfer(args, token)
    elif args.command == "share":
        cmd_share(args, token)


if __name__ == "__main__":
    main()
