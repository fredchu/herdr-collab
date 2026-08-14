#!/usr/bin/env python3
"""herdr-collab bootstrap — 建共用工作目錄＋briefing 骨架，印出開 pane 指令序列。

只做確定性部分；任務內容、硬約束、檔案所有權由發起 session 填。
"""
import argparse
import os
import sys
from datetime import date
from pathlib import Path

COLLAB_DIR = Path(os.environ.get("HERDR_COLLAB_DIR", str(Path.home() / ".claude/collab"))).expanduser()
AGENT_CLI = os.environ.get("HERDR_COLLAB_AGENT_CLI", "claude")

BRIEFING = """# briefing — {topic}（herdr 多 session 協作）

> 發起：{initiator_note}
> 共用工作目錄：{workdir}
> 回話方式：`herdr agent prompt <pane> "內容"`；長內容寫檔案再給路徑。

## 任務

<待填：一段話講清楚要解什麼問題、成功長什麼樣>

## 角色與 pane

{roles_block}

## 硬約束

- <待填：quota gate／lock／時限／不可動的東西>
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
    args = ap.parse_args()

    roles = [r.strip() for r in args.roles.split(",") if r.strip()]
    if len(roles) != args.sessions:
        sys.exit(f"ERROR: --roles 數量（{len(roles)}）必須等於 --sessions（{args.sessions}）")
    unknown = [r for r in roles if r not in ROLE_HINTS]
    if unknown:
        print(f"[note] 非標準角色（允許，但 briefing 請自行說明職責）: {unknown}")

    workdir = COLLAB_DIR / f"{date.today():%Y%m%d}-{args.topic}"
    if workdir.exists():
        sys.exit(f"ERROR: 已存在 {workdir}（換 topic 或清掉再跑）")
    workdir.mkdir(parents=True)

    roles_block = "\n".join(
        f"- session {i+1}（{'發起，本 pane' if i == 0 else f'pane <待填 w?:p?>'}）："
        f"**{r}** — {ROLE_HINTS.get(r, '<待填職責>')}"
        for i, r in enumerate(roles))
    briefing = workdir / "briefing.md"
    briefing.write_text(BRIEFING.format(
        topic=args.topic, workdir=workdir,
        initiator_note="<待填：發起 session 的 agent/model 與 pane>",
        roles_block=roles_block), encoding="utf-8")

    print(f"workdir : {workdir}")
    print(f"briefing: {briefing}")
    print(f"""
下一步（發起 session 執行）：
1. 填完 briefing 所有 <待填>（品質決定協作品質）
2. 每個 peer 開一個 pane（先 --help 確認旗標，勿憑記憶猜）：
     herdr pane split --help && herdr pane run --help
     # split 出新 pane → 在新 pane run `{AGENT_CLI}` → 等它就緒
3. 注入啟動訊息：
     herdr agent prompt <pane> "任務開始。先完整讀 briefing 再動手：{briefing}。讀完回我一句確認＋你對角色分工的異議（若有）。"
4. 收到每個 peer 的確認才進迭代（SKILL.md §3）。""")


if __name__ == "__main__":
    main()
