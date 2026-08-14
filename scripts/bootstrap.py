#!/usr/bin/env python3
"""herdr-collab bootstrap — 建共用工作目錄＋briefing 骨架，印出開 pane 指令序列。

只做確定性部分；任務內容、硬約束、檔案所有權由發起 session 填。
"""
import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path

COLLAB_DIR = Path(os.environ.get("HERDR_COLLAB_DIR", str(Path.home() / ".claude/collab"))).expanduser()
# peer pane 沒人盯著，權限確認框＝假死，故預設 bypass；換 codex/pi 請自帶等效旗標
AGENT_CLI = os.environ.get("HERDR_COLLAB_AGENT_CLI", "claude --dangerously-skip-permissions")

BRIEFING = """# briefing — {topic}（herdr 多 session 協作）

> 發起：{initiator_note}
> 共用工作目錄：{workdir}
> 回話方式：`herdr agent prompt <pane> "內容"`；長內容寫檔案再給路徑。

## 任務

<待填：一段話講清楚要解什麼問題、成功長什麼樣>

## 角色與 pane

{roles_block}

## 硬約束

- <待填：API 額度上限／檔案鎖／時間限制／不可動的東西>
- **這一輪先驗證再動手**；實作階段按下方所有權表分工，不同時改同一 repo。

## 檔案所有權

| 檔案/repo | 誰改 |
|---|---|
| <待填> | <待填> |

## 挑錯授權（固定條款，不可刪）

你的判斷若跟我衝突，直接講，不要遷就。複驗必須換口徑重做（不抄我的指令、
不只讀我的結論）。不確定的地方標「不確定」，不要為了完整而填空。

## 意圖 gate（命中任一，無論我們共識多強，停下問用戶；固定＋任務特有）

- 改變日常行為的預設（worker 選型、模型配置、排程、routing）
- 刪除或覆蓋非本次協作產生的東西
- 對外動作（發布、PR、通知）
- <待填：本任務特有的 gate 項目>

## 回報格式

每輪：結論一句話＋支撐證據（檔案路徑或指令輸出）＋你認為我哪裡錯了。
"""

ROLE_HINTS = {
    "implementer": "實作者——動手改，產出後交對方複驗",
    "adversarial-verifier": "對抗驗證者——換口徑重做複驗、跑對抗掃描、挑錯",
    "intent-guardian": "意圖守門人——不進實作共識圈，只拿產出對照原始 brief 與用戶偏好",
    "experiment-runner": "長實驗跑者——跑 ≥30 分鐘背景實驗並回報數據，不參與實作",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", required=True, help="kebab-case slug")
    ap.add_argument("--sessions", type=int, default=2, choices=(2, 3))
    ap.add_argument("--roles", default="implementer,adversarial-verifier",
                    help="逗號分隔，首位=發起 session")
    ap.add_argument("--clis", default=None,
                    help="逗號分隔的每席啟動指令（含模型旗標），數量=sessions；"
                         "首位=發起 session（已在跑，填 -）。省略則全 peer 用預設 CLI。"
                         "須用 --clis=... 等號形式（值以 - 開頭）；指令本身不可含逗號")
    args = ap.parse_args()

    # --topic slug 化：agent 常直接從任務描述生成 topic，可能夾帶路徑成分或空白。
    # 先剝掉所有路徑成分再只留文字/連字號（\w 含中文，保留中文 topic）。
    raw = Path(args.topic).name
    slug = re.sub(r"[^\w-]+", "-", raw, flags=re.U).strip("-")
    if not slug:
        sys.exit("ERROR: --topic 需要至少一個文字字元（收到: %r）" % args.topic)

    roles = [r.strip() for r in args.roles.split(",") if r.strip()]
    if len(roles) != args.sessions:
        sys.exit(f"ERROR: --roles 數量（{len(roles)}）必須等於 --sessions（{args.sessions}）")
    unknown = [r for r in roles if r not in ROLE_HINTS]
    if unknown:
        print(f"[note] 非標準角色（允許，但 briefing 請自行說明職責）: {unknown}")

    if args.clis:
        clis = [c.strip() for c in args.clis.split(",")]
        if len(clis) != args.sessions:
            sys.exit(f"ERROR: --clis 數量（{len(clis)}）必須等於 --sessions（{args.sessions}）")
    else:
        clis = ["-"] + [AGENT_CLI] * (args.sessions - 1)

    if not COLLAB_DIR.parent.exists():
        print(f"[note] HERDR_COLLAB_DIR 的上層目錄不存在，將整路建立: {COLLAB_DIR}（打錯路徑請 Ctrl-C）")
    workdir = COLLAB_DIR / f"{date.today():%Y%m%d}-{slug}"
    if workdir.exists():
        sys.exit(f"ERROR: 已存在 {workdir}（換 topic 或清掉再跑）")
    workdir.mkdir(parents=True)

    roles_block = "\n".join(
        f"- session {i+1}（{'發起，本 pane' if i == 0 else f'pane <待填 w?:p?>'}）："
        f"**{r}** — {ROLE_HINTS.get(r, '<待填職責>')}"
        + ("" if clis[i] == "-" else f"（啟動指令：`{clis[i]}`）")
        for i, r in enumerate(roles))
    briefing = workdir / "briefing.md"
    briefing.write_text(BRIEFING.format(
        topic=slug, workdir=workdir,
        initiator_note="<待填：發起 session 的 agent/model 與 pane>",
        roles_block=roles_block), encoding="utf-8")

    pane_lines = "\n".join(
        f"     # pane {i+1}（{roles[i]}）→ split 出新 pane → run `{clis[i]}` → 等它就緒"
        for i in range(1, args.sessions))
    print(f"workdir : {workdir}")
    print(f"briefing: {briefing}")
    print(f"""
下一步（發起 session 執行）：
1. 填完 briefing 所有 <待填>（品質決定協作品質）
2. 每個 peer 開一個 pane（先 --help 確認旗標，勿憑記憶猜）：
     herdr pane split --help && herdr pane run --help
{pane_lines}
3. 注入啟動訊息：
     herdr agent prompt <pane> "任務開始。先完整讀 briefing 再動手：{briefing}。讀完回我一句確認＋你對角色分工的異議（若有）。"
4. 收到每個 peer 的確認才進迭代（SKILL.md §3）。""")


if __name__ == "__main__":
    main()
