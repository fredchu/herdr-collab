from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from scripts.lint_wait_claim import find_violations
DEFAULT_CORPUS = SKILL_ROOT / "references" / "lint-wait-claim-corpus.tsv"
SCRIPT = SKILL_ROOT / "scripts" / "lint_wait_claim.py"


def _rows() -> list[tuple[str, str]]:
    path = Path(os.environ.get("LINT_WAIT_CLAIM_CORPUS", DEFAULT_CORPUS)).expanduser()
    assert path.exists(), f"Corpus file not found: {path}"
    return [
        (label, text.replace(r"\n", "\n"))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
        for label, text in [line.split("\t", 1)]
    ]


def test_corpus_has_no_block_misses_and_only_known_meta_false_positives() -> None:
    misses = [text for label, text in _rows() if label == "BLOCK" and not find_violations(text)]
    false_positives = {text for label, text in _rows() if label == "PASS" and find_violations(text)}
    assert misses == []
    assert false_positives == {
        "上等、中等、等級都不是等待",
        "等待器 timeout 比任務久（memory 那條），這是引用不是在等",
    }


def test_waiting_is_a_wait_verb() -> None:
    text = "等待 pi 的授權"
    assert find_violations(text) == [(1, text)]


def test_schedule_wakeup_needs_no_id() -> None:
    assert find_violations("等 13:33 額度重置，ScheduleWakeup 已排") == []


def test_previous_sentence_handle_does_not_cover_later_wait() -> None:
    text = "監看 be59l03eh 還在跑。另外我等 pi 的授權"
    assert find_violations(text) == [(1, text)]


def test_handle_in_next_sentence_is_valid() -> None:
    assert find_violations("我等 pi。Monitor be59l03eh 已掛") == []


def test_bare_mechanism_words_are_invalid() -> None:
    for text in ("背景說明一下，我在等 pi", "監看一下就好，我等他", "until 迴圈我沒掛，等 Fable"):
        assert find_violations(text) == [(1, text)]


def test_real_task_ids_are_valid() -> None:
    assert find_violations("等 pi 交件（監看 be59l03eh）") == []
    assert find_violations("等 pi 的 SKILL.md，task id bpy9t5lpj 盯著") == []


def test_herdr_agent_wait_requires_a_pane_id() -> None:
    assert find_violations("等 pi 交件，herdr agent wait w4K:p2 --timeout 600000 掛著") == []
    text = "等 pi 交件，herdr agent wait 掛著"
    assert find_violations(text) == [(1, text)]
    lowercase_pane = "等 pi 交件，herdr agent wait w4k:p2 --timeout 600000 掛著"
    assert find_violations(lowercase_pane) == [(1, lowercase_pane)]
    wait_output = r"等 pi 交件，herdr pane wait-output w4K:p2 --regex '\[blocked\]' 掛著"
    assert find_violations(wait_output) == [(1, wait_output)]


def test_herdr_agent_wait_until_idle_is_not_a_handle() -> None:
    for text in (
        "等 pi 交件，herdr agent wait w4K:p2 --until idle 掛著",
        "等 pi 交件，herdr agent wait w4K:p2 --until idle --timeout 600000 掛著",
        "等 pi 交件，herdr agent wait w4K:p2 --until=idle 掛著",
        '等 pi 交件，herdr agent wait w4K:p2 --until "idle" --timeout 600000 掛著',
        "等 pi 交件，背景掛 herdr agent wait w4K:p2 --until idle 盯著 boiq2qno3",
    ):
        assert find_violations(text) == [(1, text)]
    assert find_violations(
        "等 pi 交件，herdr agent wait w4K:p2 --until working --timeout 5000 "
        "再掛 herdr agent wait w4K:p2 --timeout 600000"
    ) == []


def test_prefix_rule_excludes_bound_words() -> None:
    assert find_violations("上等、中等、高等、初等、優等、劣等、同等、相等、平均等") == []
    assert find_violations("我等 pi 交件") == [(1, "我等 pi 交件")]
    assert find_violations("等待 pi 的授權") == [(1, "等待 pi 的授權")]


def test_suffix_rule_excludes_bound_words_but_not_waiting() -> None:
    assert find_violations("等價、等同、等於、等級、等號、等式、等比、等分、等距、等差、等溫、等高、等長、等量、等效、等閒、等候室、等待器") == []
    assert find_violations("等待回覆") == [(1, "等待回覆")]


def test_idiom_rule_excludes_non_wait_claims() -> None:
    assert find_violations("不用等；別等；不等；免等；等一下我先講；等我一下；等下；等等我補；等等我再說；等等我看看") == []


def test_rule_h_adversarial_cases() -> None:
    for text in ("等等 pi 的結果", "等等看 Fable", "我等 pi 交件", "等待 pi 的授權"):
        assert find_violations(text) == [(1, text)]
    for text in ("等等再說", "Breeze、VV、large-v3 等等", "三席各做一次，等等我補", "兩側的等價性"):
        assert find_violations(text) == []


def test_terminal_anchor_does_not_exempt_wait_with_trailing_words() -> None:
    text = "先等等，pi 還沒交件"
    assert find_violations(text) == [(1, text)]


def test_corpus_literal_newlines_are_semantic(monkeypatch, tmp_path: Path) -> None:
    corpus = tmp_path / "corpus.tsv"
    corpus.write_text(
        "BLOCK\t我等 pi\\n這件事先擱著\\n背景 until 已掛 bf9df30it\n"
        "BLOCK\t我等 Fable 的清單\\n中間隔一句\\n監看 be59l03eh 掛著\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LINT_WAIT_CLAIM_CORPUS", str(corpus))
    rows = _rows()
    assert all("\n" in text and r"\n" not in text for _, text in rows)
    assert all(find_violations(text) for _, text in rows)
    # Without decoding, each handle would appear in the same sentence and fail open.
    assert all(find_violations(text.replace("\n", r"\n")) == [] for _, text in rows)


def test_cli_stdin_and_file(tmp_path: Path) -> None:
    bad = subprocess.run([sys.executable, str(SCRIPT)], input="現在等 B\n", text=True, capture_output=True)
    assert bad.returncode == 1
    assert bad.stdout == "line 1: 現在等 B\n"
    message = tmp_path / "message.txt"
    message.write_text("等一下我先講另一件事\n", encoding="utf-8")
    good = subprocess.run([sys.executable, str(SCRIPT), str(message)], text=True, capture_output=True)
    assert good.returncode == 0


def _fake_herdr(tmp_path: Path, behavior: str) -> Path:
    script = tmp_path / "herdr"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import os, pathlib, sys, time\n"
        f"behavior = {behavior!r}\n"
        "capture = os.environ.get('HERDR_CAPTURE')\n"
        "if capture and len(sys.argv) > 4:\n"
        "    pathlib.Path(capture).write_bytes(sys.argv[4].encode('utf-8'))\n"
        "if behavior == 'sleep': time.sleep(60)\n"
        "if behavior == 'success': print('{\"type\":\"agent_prompted\"}')\n"
        "else: print('{\"error\":{\"code\":\"agent_not_found\"}}')\n"
        "raise SystemExit(0 if behavior == 'success' else 1)\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


def _say_env(tmp_path: Path, capture: Path | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}:{env.get('PATH', '')}"
    if capture:
        env["HERDR_CAPTURE"] = str(capture)
    return env


def test_say_blocks_four_real_wait_claims_and_prints_copyable_exits(tmp_path: Path) -> None:
    _fake_herdr(tmp_path, "success")
    capture = tmp_path / "sent.bin"
    for message in (
        "我在等 pi 的額度重置",
        "等 Fable 的量測數字出來再說",
        "我在等 pi 的授權",
        "等 pi 有額度再說",
    ):
        run = subprocess.run([str(SCRIPT.parent / "say.sh"), "w3T:p1", message], text=True,
                             capture_output=True, env=_say_env(tmp_path, capture))
        assert run.returncode == 1
        assert not capture.exists()
        for expected in ("背景 until 已掛 bf9df30it", "Monitor be59l03eh", "ScheduleWakeup 已排",
                         "我手上哪一行需要對方的輸出？", "任何人有額度都能做",
                         "X 做完了，產物在 Y", "提字只用引號包「等」"):
            assert expected in run.stdout


def test_say_delivers_message_byte_for_byte(tmp_path: Path) -> None:
    _fake_herdr(tmp_path, "success")
    capture = tmp_path / "sent.bin"
    message = "等 pi 交件，背景 until 已掛 bf9df30it\nquotes: ' \" ` $(touch /tmp/MUST_NOT_RUN)"
    run = subprocess.run([str(SCRIPT.parent / "say.sh"), "w3T:p1", message], text=True,
                         capture_output=True, env=_say_env(tmp_path, capture))
    assert run.returncode == 0
    assert capture.read_bytes() == message.encode("utf-8")
    assert "sent → w3T:p1" in run.stderr


def test_say_missing_pane_output_is_delivery_failure(tmp_path: Path) -> None:
    _fake_herdr(tmp_path, "failure")
    run = subprocess.run([str(SCRIPT.parent / "say.sh"), "w3T:p9", "訊息"], text=True,
                         capture_output=True, env=_say_env(tmp_path))
    assert run.returncode == 2
    assert "agent_not_found" in run.stderr


def test_say_lint_failure_is_fail_open_with_distinct_status(tmp_path: Path) -> None:
    _fake_herdr(tmp_path, "success")
    capture = tmp_path / "sent.bin"
    isolated = tmp_path / "isolated"
    isolated.mkdir()
    say_copy = isolated / "say.sh"
    shutil.copy2(SCRIPT.parent / "say.sh", say_copy)
    run = subprocess.run([str(say_copy), "w3T:p1", "我在等 pi"], text=True,
                         capture_output=True, env=_say_env(tmp_path, capture))
    assert run.returncode == 3
    assert "lint 故障，本則未檢查" in run.stderr
    assert capture.read_text(encoding="utf-8") == "我在等 pi"


def test_say_times_out_stuck_herdr_within_twenty_two_seconds(tmp_path: Path) -> None:
    _fake_herdr(tmp_path, "sleep")
    started = time.monotonic()
    run = subprocess.run([str(SCRIPT.parent / "say.sh"), "w3T:p1", "訊息"], text=True,
                         capture_output=True, env=_say_env(tmp_path), timeout=25)
    elapsed = time.monotonic() - started
    assert run.returncode == 2
    assert elapsed < 22
    assert "未送出" in run.stderr


def test_say_has_no_lint_bypass() -> None:
    source = (SCRIPT.parent / "say.sh").read_text(encoding="utf-8")
    assert "--force" not in source
    assert "--skip-lint" not in source



def test_equivalence_sentence_is_not_wait() -> None:
    assert find_violations("兩側的等價性主張要降級") == []


def test_use_mention_quotes_are_narrow_and_bidirectional() -> None:
    for text in (
        "「等」這個字只准跟把手一起出現",
        "lint 對『等』的判定",
        '"等等"是慣用句',
        "規則裡的 '等' 不算動詞",
        "`等`這個字",
    ):
        assert find_violations(text) == []
    for text in (
        "「等 pi 的結果」",
        "「等」pi 的結果",
        "「等」Fable 交件",
        "『等』pi 的結果",
        "「等等」pi 的結果",
        "他說「等 pi 交件」",
        "「等」「等」pi 交件",
        "我在等 pi，「等」這個字我知道",
    ):
        assert find_violations(text) == [(1, text)]


def test_bootstrap_briefing_and_stdout_route_messages_through_say(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["HERDR_COLLAB_DIR"] = str(tmp_path / "collab")
    run = subprocess.run(
        [sys.executable, str(SKILL_ROOT / "scripts" / "bootstrap.py"), "--topic", "lint-wire"],
        text=True,
        capture_output=True,
        env=env,
    )
    assert run.returncode == 0, run.stderr
    briefing = next((tmp_path / "collab").glob("*-lint-wire/briefing.md")).read_text(encoding="utf-8")
    assert "say.sh" in briefing and "送出前自動 lint" in briefing
    assert "herdr agent prompt <pane>" not in briefing
    assert "say.sh" in run.stdout
    assert "herdr agent prompt <pane>" not in run.stdout
