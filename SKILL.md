---
name: herdr-collab
description: 啟動 herdr 多 session 對抗協作——在同一台機器開 2-3 個 peer coding agent session 互相挑錯、分工實作與驗證。當用戶說「開 herdr 協作」「herdr 多 session」「開一個 pane 一起做」「找另一個 session 協作/驗證」「雙 session 對抗」時使用。也適用於用戶描述了一個爆炸半徑大、有可驗證 ground truth、需要「實作者＋獨立驗證者」結構的任務並暗示要多顆腦。不適用於：平行 fan-out 苦力（用 subagent/多 agent 編排——它們繼承派工者的 frame 挑不了錯，peer 才能）、例行任務、單檔修改、探索式研究（context 該集中一顆腦）。
---

# herdr-collab — 多 session 對抗協作

> 方法論與失效模式詳見本 skill 的 `references/playbook.md`（先讀）。
> 前置：在 herdr 內執行（`HERDR_ENV=1`）、有可用的 coding agent CLI。
> 本質：peer session 沒有共享錨定，能真正挑錯；subagent 繼承派工者的 prompt，挑不了。

## 環境變數（客製化點，都有預設值）

| 變數 | 預設 | 用途 |
|---|---|---|
| `HERDR_COLLAB_DIR` | `~/.claude/collab` | 共用工作目錄的根 |
| `HERDR_COLLAB_AGENT_CLI` | `claude --dangerously-skip-permissions` | 在新 pane 起 peer 的預設指令。peer pane 沒人盯著，權限確認框＝假死，故預設 bypass；換 `codex`/`pi` 請自帶等效旗標 |

## 0. 適用判準（三個都要成立，否則回報用戶不適用）

1. 有 ground truth 能裁決分歧（log／語料／測試）
2. 爆炸半徑大（infra 預設、事故調查、改日常行為）或研究＋實作＋驗證全鏈
3. 檔案所有權能切乾淨

## 1. 決定人數、角色與模型

- **預設 2**：實作者＋對抗驗證者（角色按組件互換）
- **3 的條件**（任一命中才開第三席）：需要**意圖守門人**（不進實作共識圈，只拿產出對照
  原始 brief 與用戶偏好）或**長實驗跑者**（≥30 分鐘背景實驗，跑者與分析者分離）
- **不要 4+**：通道數平方成長，需要更多平行度＝任務其實是 fan-out 型
- **每席同時決定模型檔位**（開 pane 前決定，不是開完再想）：驗證者／意圖守門人的檔位
  **≥** 實作者——把關比實作重要；不確定就全席同檔位。決定透過 bootstrap 的 `--clis`
  傳入，briefing 會留下每席啟動指令的紀錄，方便事後歸因
- 用戶指定人數／角色／模型時照用戶的

## 2. Bootstrap（確定性部分走腳本）

```bash
python3 <本 skill 目錄>/scripts/bootstrap.py \
  --topic <kebab-slug> --sessions 2 --roles "implementer,adversarial-verifier" \
  "--clis=-,claude --dangerously-skip-permissions --model opus"
```

腳本會：建共用工作目錄、產 briefing 骨架（含挑錯授權條款與意圖 gate 清單的固定文字）、
印出每席帶各自 CLI／模型的開 pane 指令序列。`--clis` 首位=發起 session（已在跑，填 `-`）、
須用 `--clis=` 等號形式；省略則全 peer 用 `HERDR_COLLAB_AGENT_CLI` 預設值。
注意 bypass 模式下 peer 不會再問權限——briefing 的檔案所有權表與意圖 gate 就是唯一防線，
所有權表不可留空泛描述。

然後你（發起 session）：
1. **把 briefing 骨架的 `<待填>` 全部填完**——任務、硬約束、檔案所有權表、
   本任務特有的意圖 gate 項目。briefing 品質決定協作品質，不要留空泛描述。
2. 開 pane（先 `herdr pane split --help` 確認旗標再執行，不要憑記憶猜 CLI）：
   split → 在新 pane run 該席的啟動指令（bootstrap 已按 `--clis` 印出）→ `herdr agent prompt <pane>
   "任務開始。先完整讀 briefing 再動手：<briefing 絕對路徑>。讀完回我一句確認＋
   你對角色分工的異議（若有）。"`
3. 等每個 peer 回覆確認後才進入迭代。

## 3. 迭代規則（hard rules）

- 長內容一律落檔（findings-*.md / review-*.md），herdr 訊息只帶結論＋證據指標
- 每輪「一方產出 → 另一方**換口徑重做**複驗」：不抄對方指令、不只讀結論。
  只互讀結論說「看起來沒問題」＝假對抗，成本全付收益歸零
- 分歧直說，用 ground truth 裁決；跨 session 狀態只從共同事實檔讀，不從現況推論
- 兩 session 不同時改同一 repo；外部資源（API 額度、鎖）照你環境既有的規則過 gate
- 一、說「等」之前，先做完所有不需要對方的事。剩下真的要等的，掛一個會叫醒你的東西——三選一，沒有掛就不准說「等」。
  - 三選一：背景 `until` 迴圈、Monitor、`ScheduleWakeup`。
  - 背景 `until` 與 Monitor 必須附可回查的 ≥6 字元識別碼；只有關鍵字不算掛上。
  - `ScheduleWakeup` 單獨出現即視為有效（可不帶識別碼）；把手必須在等待主張的同句或下一句，前一句與訊息其他位置不算。
  - 「等」這個字只准跟一個會叫醒你的東西一起出現。
  - 聲稱要等待之前強制先回答：「我手上哪一行需要對方的輸出？」答不出具體哪一行＝不需要等。
- 二、動手前一行宣告「我來跑 X」。
  - 十秒宣告換掉整個共用待辦清單：規則一會讓兩席同時做同一件事，不先宣告就會造成雙倍成本。
  - 完成也要宣告完整句：「X 做完了，產物在 Y」。
- 任何人能做的事沒有主人：交接不可以寫「等某某有額度」，要寫「這件事任何人有額度都能做：指令是 X、預期是 Y」。

## 4. 意圖 gate（無論 session 間共識多強，命中就停下問用戶）

- 改變日常行為的預設（工具選型、模型配置、排程、routing）
- 刪除或覆蓋非本次協作產生的東西
- 對外動作（發布、PR、通知）
- briefing 裡用戶追加的項目

## 5. 收尾（一支筆）

- 由 context 最低的 session 單獨執行收尾寫入（session 交接紀錄、知識庫、memory——
  依你環境的制度；多個 session 若共用同一份交接檔，多人寫＝互相覆蓋）
- 殘留項寫共用目錄 `OPEN-ITEMS.md`
- 互評一句：各自指出對方本輪最大的錯（方法層優先），值得的寫進你的教訓庫
