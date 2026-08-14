# herdr-collab

在同一台機器用 [herdr](https://herdr.dev) 開 2-3 個 peer coding agent session，
互相挑錯、分工「實作 vs 獨立驗證」的協作 skill。核心理念：**peer session 沒有共享錨定，
能真正挑錯；subagent 繼承派工者的 frame，挑不了。**

Run 2-3 peer coding-agent sessions in [herdr](https://herdr.dev) panes on one machine,
splitting work into implementer vs. adversarial verifier who redo each other's analysis
with independent methods. Peers hold no shared anchoring, so they can genuinely
challenge each other — subagents inherit the dispatcher's frame and cannot.

## 安裝 Install

```bash
git clone <this-repo> ~/dev/herdr-collab
# Claude Code
ln -s ~/dev/herdr-collab ~/.claude/skills/herdr-collab
# pi（尊重 PI_CODING_AGENT_DIR，未設則預設 ~/.pi/agent）
ln -s ~/dev/herdr-collab "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/skills/herdr-collab"
```

裝完**重開 session 最可靠**；Claude Code 亦可試 `/reload-plugins`。

## 需求 Requirements

- herdr（session 需在 herdr 內執行，`HERDR_ENV=1`）
- 一個 coding agent CLI（預設 `claude`；`codex`、`pi` 皆可）
- Python 3（bootstrap 腳本，stdlib only）
- 注意：pi 若慣用 `--no-skills`/`-ns` 啟動，skill 不會載入

## 客製化 Configuration

| env | default | 說明 |
|---|---|---|
| `HERDR_COLLAB_DIR` | `~/.claude/collab` | 共用工作目錄根（briefing、findings 檔都放這） |
| `HERDR_COLLAB_AGENT_CLI` | `claude` | 在新 pane 起 peer 的指令 |

skill 本身不含任何個人路徑；briefing 骨架的任務內容、檔案所有權、
額度/鎖規則都在啟動時由發起 session 填入。

## 使用 Usage

對你的 agent 說：**「開 herdr 協作：<任務描述>」**（可加人數／角色，例如
「三個，第三個當意圖守門人」）。agent 會照 `SKILL.md` 走七步流程：
判準 → bootstrap（腳本建目錄＋briefing 骨架）→ 開 pane → 迭代（換口徑複驗）→
意圖 gate → 一支筆收尾 → 互評。

方法論與五種已知失效模式（含「共識≠用戶意圖」——這套模式特有的最大陷阱）：
`references/playbook.md`。

## License

MIT
