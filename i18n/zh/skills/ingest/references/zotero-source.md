# Zotero 来源路径

当 `source` 是 Zotero 条目引用时使用本路径：

- 8 位 item key：`ABCD1234`
- 带前缀的 key：`zotero:ABCD1234`
- 条目 URL：`https://zotero.org/users/<id>/items/<key>`（群组库同样支持：
  `https://zotero.org/groups/<id>/items/<key>`）

其余任何输入都会在发起网络请求前被拒绝（exit 2）。

## 前置条件

- `.env` 中配置 `ZOTERO_LIBRARY_ID` 与 `ZOTERO_API_KEY`（参见 `.env.example`
  的 Zotero 段；在 https://www.zotero.org/settings/keys 创建）。`ZOTERO_LIBRARY_TYPE`
  默认为 `user`。
- 工具运行时由 `tools/_env.py` 自动加载凭据。凭据缺失 → exit 2 并在 stderr
  打印说明；向用户报告并停止，不要编造元数据。

## 步骤

1. 获取规范化元数据（当不涉及 arXiv ID 时，也可用于 Step 2 的身份字段）：

   ```bash
   "$PYTHON_BIN" tools/zotero_fetch.py item <ref> -o raw/tmp/zotero/<key>.json
   ```

2. 下载 PDF 附件：

   ```bash
   "$PYTHON_BIN" tools/zotero_fetch.py download <ref>
   ```

   成功时 stdout 输出 JSON 记录：

   - `source_path` —— `raw/tmp/zotero/` 下的 PDF
   - `metadata_path` —— 规范化元数据 JSON
   - `record` —— `title`、`creators`（`Family, Given`）、`year`、`doi`、
     `publication_title`、`tags`、`collections` …

3. 把 `source_path` 交给常规的本地 PDF 流程：

   ```bash
   "$PYTHON_BIN" tools/prepare_paper_source.py --raw-root raw --source <source_path>
   ```

   之后与直接丢 `.pdf` 完全一样，继续主流程的 Step 2（身份、enrichment、
   页面撰写）。用 `record` 交叉核对标题/作者/年份；当存在 arXiv ID 或 DOI 时，
   S2/DeepXiv enrichment 照常生效。

## 失败模式

所有失败均 fail-closed：非零退出码、stderr 上的机器可读 JSON、不留半成品
（PDF 先写成 `*.part`，只有完整写入并通过 magic 校验后才改名落位）。

| exit | error | 含义 | 处理方式 |
|---|---|---|---|
| 2 | （纯文本消息，非 JSON） | 引用格式非法或缺少 `ZOTERO_*` 凭据 | 修正引用格式或补全 `.env` 后重试 |
| 3 | `no_pdf_attachment` | 条目没有 PDF 子附件 | 请用户在 Zotero 中挂上 PDF 或提供本地路径 |
| 3 | `file_not_on_server` | 附件记录存在，但字节未同步到 zotero.org（存储同步关闭，或仅导入了元数据） | 提示用户开启文件同步 / 重新挂载附件，改用 `download <ref> --from-attachment-url` 重试，或提供本地路径 |
| 3 | `attachment_url_fetch_failed` | `--from-attachment-url` fallback 未返回 PDF（死链、付费墙/登录 HTML、超出体积上限） | 转报错误消息，向用户索要本地路径 |
| 3 | `zotero_api_error` | 条目不存在（404）、鉴权或限流 | 核对 key/URL 与 `.env` 凭据 |

## 备注

- `--from-attachment-url` 是**显式 opt-in**：只有当存储文件 404 之后才去抓取
  附件记录的 URL，且必须是真正的 PDF magic bytes（`%PDF`），上限 200 MB。
- 产物落在 `raw/tmp/zotero/`（skill 可写）。绝不写入 `raw/{papers,notes,web}`
  —— 那些归用户所有且只读。
- 超出单条目解析的需求（collections、tags、导出、创建/更新条目），使用独立的
  `$pyzotero` skill。
- Sandbox：在 Codex 内该工具会以 126 退出并打印 SANDBOX GATE 横幅；按
  AGENTS.md 表中的 prefix rule 带 escalation 重新运行。
