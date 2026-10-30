import pytest

from pipelines.territory_kpis.config import DEFAULT_INPUT_DIR
from pipelines.territory_kpis.extract import INPUT_TABLES, read_inputs, read_table
from pipelines.territory_kpis.load import write_output


def test_read_inputs_loads_all_tables(spark):
    frames = read_inputs(spark, DEFAULT_INPUT_DIR)
    assert set(frames) == set(INPUT_TABLES)
    assert "territory_id" not in frames["follow_ups"].columns  # the reason we join via reps
    assert frames["visits"].schema["visit_date"].dataType.simpleString() == "date"
    assert frames["weekly_sales"].count() == 2080


def test_read_table_missing_file_raises(spark, tmp_path):
    with pytest.raises(FileNotFoundError, match="nope"):
        read_table(spark, tmp_path, "nope")


def test_write_output_creates_dirs_and_overwrites(spark, tmp_path):
    target = tmp_path / "nested" / "dir" / "out.parquet"
    df = spark.createDataFrame([("T001", 1), ("T002", 2)], "territory_id string, n long")
    assert write_output(df, target) == target
    assert spark.read.parquet(str(target)).count() == 2
    write_output(df.limit(1), target)
    assert spark.read.parquet(str(target)).count() == 1
