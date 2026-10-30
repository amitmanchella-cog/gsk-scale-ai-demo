from pathlib import Path

from pipelines.territory_kpis.config import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_PATH, REPO_ROOT, JobConfig


def test_defaults_are_repo_relative():
    cfg = JobConfig.from_args([], env={})
    assert cfg.input_dir == DEFAULT_INPUT_DIR == REPO_ROOT / "data"
    assert cfg.output_path == DEFAULT_OUTPUT_PATH
    assert DEFAULT_OUTPUT_PATH.is_relative_to(REPO_ROOT)
    assert (REPO_ROOT / "pyproject.toml").exists()
    assert (cfg.spark_master, cfg.min_rows, cfg.max_rows) == ("local[*]", 100, 5000)


def test_cli_overrides(tmp_path):
    cfg = JobConfig.from_args(
        ["--input-dir", str(tmp_path), "--output", "some/relative.parquet", "--master", "local[1]", "--min-rows", "1",
         "--max-rows", "2", "--shuffle-partitions", "3"],
        env={},
    )
    assert cfg.input_dir == tmp_path
    assert cfg.output_path == REPO_ROOT / "some" / "relative.parquet"
    assert (cfg.spark_master, cfg.min_rows, cfg.max_rows, cfg.shuffle_partitions) == ("local[1]", 1, 2, 3)


def test_env_overrides_and_cli_wins(tmp_path):
    env = {
        "TERRITORY_KPIS_INPUT_DIR": str(tmp_path / "in"),
        "TERRITORY_KPIS_OUTPUT": str(tmp_path / "out.parquet"),
        "TERRITORY_KPIS_SPARK_MASTER": "local[3]",
        "TERRITORY_KPIS_MAX_ROWS": "42",
    }
    cfg = JobConfig.from_args([], env=env)
    assert (cfg.input_dir, cfg.output_path, cfg.spark_master, cfg.max_rows) == (
        tmp_path / "in", tmp_path / "out.parquet", "local[3]", 42)
    assert JobConfig.from_args(["--master", "local[1]"], env=env).spark_master == "local[1]"


def test_config_is_immutable():
    cfg = JobConfig()
    try:
        cfg.min_rows = 1  # type: ignore[misc]
    except Exception as exc:  # FrozenInstanceError
        assert isinstance(cfg.input_dir, Path) and "frozen" in type(exc).__name__.lower()
    else:
        raise AssertionError("JobConfig should be frozen")
