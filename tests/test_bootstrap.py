import subprocess
import sys
from datetime import date
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "bootstrap.py"


def run(tmp_path, *args, cli=None):
    env = {"HERDR_COLLAB_DIR": str(tmp_path / "collab"), "PATH": "/usr/bin:/bin"}
    if cli:
        env["HERDR_COLLAB_AGENT_CLI"] = cli
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True, env=env)


def today():
    return f"{date.today():%Y%m%d}"


def test_normal_topic(tmp_path):
    p = run(tmp_path, "--topic", "fix-parser")
    assert p.returncode == 0, p.stderr
    briefing = tmp_path / "collab" / f"{today()}-fix-parser" / "briefing.md"
    assert briefing.is_file()
    body = briefing.read_text()
    assert "挑錯授權" in body and "意圖 gate" in body
    assert "quota gate" not in body  # MAJOR-3：briefing 骨架不得含內部術語


def test_briefing_marks_messages_requiring_action(tmp_path):
    p = run(tmp_path, "--topic", "blocked-message")
    assert p.returncode == 0, p.stderr
    body = (tmp_path / "collab" / f"{today()}-blocked-message" / "briefing.md").read_text()
    assert "[blocked]" in body


def test_briefing_defines_independent_acceptance(tmp_path):
    p = run(tmp_path, "--topic", "acceptance")
    assert p.returncode == 0, p.stderr
    body = (tmp_path / "collab" / f"{today()}-acceptance" / "briefing.md").read_text()
    assert "## 驗收" in body
    assert "不得寫成指令" in body


def test_bootstrap_stdout_requests_peer_identity(tmp_path):
    p = run(tmp_path, "--topic", "identity")
    assert p.returncode == 0, p.stderr
    assert "session id" in p.stdout


def test_chinese_topic_preserved(tmp_path):
    p = run(tmp_path, "--topic", "字幕修正")
    assert p.returncode == 0, p.stderr
    assert (tmp_path / "collab" / f"{today()}-字幕修正").is_dir()


# BLOCKER 回歸：對抗 review 的四發攻擊輸入（2026-08-14）
def test_path_traversal_neutralized(tmp_path):
    p = run(tmp_path, "--topic", "../../etc/passwd")
    assert p.returncode == 0
    dirs = list((tmp_path / "collab").iterdir())
    assert [d.name for d in dirs] == [f"{today()}-passwd"]
    assert not (tmp_path / "etc").exists()


def test_nested_topic_flattened(tmp_path):
    p = run(tmp_path, "--topic", "a/b/c")
    assert p.returncode == 0
    assert (tmp_path / "collab" / f"{today()}-c").is_dir()


def test_whitespace_topics_rejected(tmp_path):
    for bad in ("  ", "x\ty///", "---", "/"):
        p = run(tmp_path, f"--topic={bad}")
        if p.returncode == 0:
            # tab 案例會 slug 化成 x-y，允許；純空白/純符號必須拒絕
            name = [d.name for d in (tmp_path / "collab").iterdir()]
            assert all("\t" not in n and " " not in n for n in name), (bad, name)
        else:
            assert "至少一個文字字元" in p.stderr, (bad, p.stderr)


def test_agent_cli_env(tmp_path):
    p = run(tmp_path, "--topic", "t1", cli="pi")
    assert "run `pi`" in p.stdout


def test_roles_mismatch_rejected(tmp_path):
    p = run(tmp_path, "--topic", "t2", "--sessions", "3")
    assert p.returncode != 0
    assert "--roles 數量" in p.stderr


# 2026-08-14：每席模型規劃（--clis）＋預設 bypass permission
def test_default_cli_has_bypass(tmp_path):
    p = run(tmp_path, "--topic", "t3")
    assert "claude --dangerously-skip-permissions" in p.stdout


def test_clis_count_mismatch_rejected(tmp_path):
    p = run(tmp_path, "--topic", "t4", "--clis=-,a,b")
    assert p.returncode != 0
    assert "--clis 數量" in p.stderr


def test_clis_in_briefing_and_stdout(tmp_path):
    p = run(tmp_path, "--topic", "t5",
            "--clis=-,claude --dangerously-skip-permissions --model opus")
    assert p.returncode == 0, p.stderr
    body = (tmp_path / "collab" / f"{today()}-t5" / "briefing.md").read_text()
    assert "--model opus" in body                     # 每席模型留紀錄
    assert "--model opus" in p.stdout                  # 開 pane 指令帶對的 CLI
