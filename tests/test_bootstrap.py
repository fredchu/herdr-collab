import os
import subprocess
import sys
from datetime import date
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "bootstrap.py"


def run(tmp_path, *args, cli=None):
    env = {"HERDR_COLLAB_DIR": str(tmp_path / "collab"), "PATH": "/usr/bin:/bin"}
    if os.name == "nt":
        # Windows: CPython cannot initialize without SYSTEMROOT in the env
        # (_Py_HashRandomization_Init fails to get random numbers).
        env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
    if cli:
        env["HERDR_COLLAB_AGENT_CLI"] = cli
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True, encoding="utf-8", env=env)


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
