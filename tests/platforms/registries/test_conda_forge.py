"""Tests for the conda-forge feedstock plugin."""

from __future__ import annotations

import pytest

from release_kit.core.config import PolicyConfig, TargetConfig
from release_kit.core.errors import AuthenticationError, PublishError
from release_kit.core.runner import RunContext
from release_kit.platforms.registries.conda_forge import CondaForge


def _ctx(*, dry_run: bool = True) -> RunContext:
    return RunContext(dry_run=dry_run, policies=PolicyConfig(), target_name="conda-forge")


def _plat(**extras) -> CondaForge:
    target = TargetConfig.model_validate({"enabled": True, "auth": "token", **extras})
    plat = CondaForge.from_target(target)
    plat.__post_init__()
    return plat


def test_authenticate_invalid_feedstock(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _plat(feedstock="just-name").authenticate(_ctx())
    assert exc.value.code == "invalid-feedstock"


def test_authenticate_invalid_fork(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _plat(feedstock="conda-forge/x").authenticate(_ctx())
    assert exc.value.code == "invalid-fork"


def test_authenticate_missing_token(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _plat(
            feedstock="conda-forge/x", fork="user/x"
        ).authenticate(_ctx())
    assert exc.value.code == "token-not-found"


def test_authenticate_ok(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAP_GITHUB_TOKEN", "ghp_x")
    out = _plat(feedstock="conda-forge/x", fork="user/x").authenticate(_ctx())
    assert out.status == "ok"


def test_validate_missing_version(monkeypatch: pytest.MonkeyPatch) -> None:
    plat = _plat(feedstock="conda-forge/x", fork="user/x")
    with pytest.raises(AuthenticationError) as exc:
        plat.validate(_ctx())
    assert exc.value.code == "missing-version"


def test_validate_invalid_sha256() -> None:
    plat = _plat(
        feedstock="conda-forge/x", fork="user/x", version="0.1.0", sha256="short"
    )
    with pytest.raises(AuthenticationError) as exc:
        plat.validate(_ctx())
    assert exc.value.code == "invalid-sha256"


def test_validate_ok() -> None:
    plat = _plat(
        feedstock="conda-forge/x",
        fork="user/x",
        version="0.1.0",
        sha256="a" * 64,
    )
    out = plat.validate(_ctx())
    assert out.status == "ok"
    assert "0.1.0" in out.detail


def test_publish_dry_run() -> None:
    plat = _plat(
        feedstock="conda-forge/x",
        fork="user/x",
        version="0.1.0",
        sha256="a" * 64,
    )
    out = plat.publish(_ctx(dry_run=True))
    assert out.status == "dry-run"
    assert "0.1.0" in out.detail


def test_publish_apply_clones_and_pushes(
    clean_env: None, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """End-to-end mocked: subprocess clones, patches, pushes; API opens PR."""
    import subprocess as _sp
    monkeypatch.setenv("TAP_GITHUB_TOKEN", "ghp_x")

    calls: list[list[str]] = []
    feedstock = tmp_path / "feedstock"
    recipe_dir = feedstock / "recipe"
    recipe_dir.mkdir(parents=True)
    (recipe_dir / "meta.yaml").write_text(
        '{% set version = "0.0.1" %}\n'
        "package:\n  name: x\n  version: {{ version }}\n"
        "source:\n  sha256: " + ("0" * 64) + "\n"
        "build:\n  number: 0\n",
        encoding="utf-8",
    )

    def fake_run(argv, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(list(argv))
        # `git clone <fork-url> <dest>` -> create the dest dir with the
        # prepared feedstock; subsequent git commands run inside it.
        if argv[:2] == ["git", "clone"]:
            dest = argv[-1]
            import shutil
            shutil.copytree(feedstock, dest)
        return _sp.CompletedProcess(args=argv, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    # Mock API: no existing PR + successful pulls POST.
    import httpx
    import respx
    with respx.mock(assert_all_called=False) as router:
        router.get(
            "https://api.github.com/repos/conda-forge/x/pulls"
        ).mock(return_value=httpx.Response(200, json=[]))
        router.post(
            "https://api.github.com/repos/conda-forge/x/pulls"
        ).mock(
            return_value=httpx.Response(
                201,
                json={"html_url": "https://github.com/conda-forge/x/pull/42"},
            )
        )
        plat = _plat(
            feedstock="conda-forge/x",
            fork="user/x",
            version="1.0.0",
            sha256="a" * 64,
        )
        out = plat.publish(_ctx(dry_run=False))

    assert out.status == "ok"
    assert "pull/42" in out.detail
    # Verify the subprocess flow: clone, checkout, add, commit, push.
    cmds = [" ".join(c) for c in calls]
    assert any(c.startswith("git clone") for c in cmds)
    assert any("checkout" in c for c in cmds)
    assert any("commit -m" in c for c in cmds)
    assert any("push" in c for c in cmds)


def test_publish_apply_no_op_patch_raises(
    clean_env: None, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """If recipe/meta.yaml has no version/sha256 to match, raise patch-no-op."""
    import subprocess as _sp
    monkeypatch.setenv("TAP_GITHUB_TOKEN", "ghp_x")

    feedstock = tmp_path / "feedstock"
    (feedstock / "recipe").mkdir(parents=True)
    (feedstock / "recipe" / "meta.yaml").write_text(
        "name: x\n# no version, no sha256\n", encoding="utf-8"
    )

    def fake_run(argv, **kwargs):  # type: ignore[no-untyped-def]
        if argv[:2] == ["git", "clone"]:
            import shutil
            shutil.copytree(feedstock, argv[-1])
        return _sp.CompletedProcess(args=argv, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    plat = _plat(
        feedstock="conda-forge/x",
        fork="user/x",
        version="1.0.0",
        sha256="a" * 64,
    )
    with pytest.raises(PublishError) as exc:
        plat.publish(_ctx(dry_run=False))
    assert exc.value.code == "patch-no-op"
