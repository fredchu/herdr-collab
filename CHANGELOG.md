# Changelog

## 0.3.0 - 2026-09-20

把 Orca（stablyai/orca）編排層值得學的做法整合進來。Fable 對抗審查砍掉不適合對等結構的部分，
再由 Orca 三席協作（Opus orchestrator、pi implementer、Fable verifier）實作與實測。

### 新功能
- SKILL.md §3.5 判活：`herdr agent get` 五態（idle／working／blocked／done／unknown）對照表；沒消息＝不知道，不是死；判死要正面證據
- 等待規則補三條：連兩次空叫醒強制盤點（agent get＋pane read＋查上則 exit code）；把手正確用法是先 `--until working` 5 秒確認對方起了回合，再掛不帶 `--until` 的 `herdr agent wait`；正在做事的席位收訊息只在下一個工具邊界併入，長實驗要能中止得靠 kill 檔
- bootstrap 啟動訊息：peer 要回 session id＋模型＋「不是 briefing 作者」；禁用 AskUserQuestion；需要對方動作的訊息以 `[blocked]` 開頭；briefing 骨架新增「驗收」段，分實作產物（可重跑指令）與複驗產物（指名不同口徑，不得寫成指令）
- 收尾：commit 前 `git status --porcelain` 逐檔對所有權表；逐席三選一處置（關閉／保留登 OPEN-ITEMS／交棒須重發 briefing 並明送角色作廢）
- playbook 失效模式 6：沒消息當死掉

### 修正
- `say.sh` exit 2 改叫「送達未確認」（含 20 秒逾時，訊息可能已進 pane）；先讀對方 pane 確認不在才重送
- lint 認 `herdr agent wait <pane id>` 當把手，pane id 大小寫敏感（herdr 對 `w4k:p2` 回 agent_not_found）
- lint 把 `--until idle` 視同沒把手（對 peer pane 永不醒，實測 review-01）

測試 33 → 38；語料回歸 24 條無翻面。

### 不採納
- 每席一個 worktree：與「互驗同一份產物」衝突，且前提事故查無出處
- 訊息型別 lint 強制：只讀者是 LLM，強制標籤會被套用交差

## 0.2.0 - 2026-08-30（追記，當時未打 tag）

### 新功能
- 兩條協作 hard rule：說「等」之前先做完不需要對方的事，真要等必掛叫醒把手；動手前一行宣告
- `scripts/lint_wait_claim.py` 可執行 lint＋`references/lint-wait-claim-corpus.tsv` 語料，接到 `say.sh` 送出點；use–mention 排除

## 0.1.0 - 2026-08-14（追記，當時未打 tag）

### 新功能
- 初版：三判準、2–3 席角色、bootstrap 腳本建目錄與 briefing 骨架、`--clis` 每席模型、peer 預設 bypass permission、意圖 gate、一支筆收尾、互評
- 可移植性：topic slug 化防路徑穿越、pi 路徑 env 化
