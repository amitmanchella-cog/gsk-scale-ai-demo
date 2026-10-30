"""Builds the two 'before' notebooks with nbformat. Run once; the .ipynb files are committed."""
from pathlib import Path

import nbformat as nbf

HERE = Path(__file__).parent

# ---------------------------------------------------------------- territory_kpis (messy, mixed pandas/PySpark)
tk = nbf.v4.new_notebook()
tk.cells = [
    nbf.v4.new_markdown_cell("# Territory KPIs (weekly)\n\nQuick analysis notebook - started in pandas, moved some bits to Spark when it got slow. "
                              "Run top to bottom. TODO: clean up before handing to data eng."),
    nbf.v4.new_code_cell(
        "import pandas as pd\n"
        "import numpy as np\n"
        "from pyspark.sql import SparkSession\n"
        "from pyspark.sql import functions as F\n"
        "spark = SparkSession.builder.appName('territory_kpis_adhoc').master('local[*]').getOrCreate()\n"
        "spark.sparkContext.setLogLevel('ERROR')\n"
        "DATA = '../data'  # TODO parametrise"),
    nbf.v4.new_code_cell(
        "# load everything - some in pandas, some in spark, whatever was quicker at the time\n"
        "visits = pd.read_parquet(DATA + '/visits.parquet')\n"
        "fu = pd.read_parquet(DATA + '/follow_ups.parquet')\n"
        "sales_sdf = spark.read.parquet(DATA + '/weekly_sales.parquet')\n"
        "reps = pd.read_parquet(DATA + '/reps.parquet')\n"
        "terr = pd.read_parquet(DATA + '/territories.parquet')\n"
        "print(len(visits), len(fu), sales_sdf.count())"),
    nbf.v4.new_code_cell(
        "# week = monday of the visit week\n"
        "visits['visit_date'] = pd.to_datetime(visits['visit_date'])\n"
        "visits['week'] = (visits['visit_date'] - pd.to_timedelta(visits['visit_date'].dt.weekday, unit='D')).dt.date\n"
        "visits['f2f'] = (visits['channel'] == 'face_to_face').astype(int)\n"
        "v = visits.groupby(['territory_id', 'week']).agg(\n"
        "    visits=('visit_id', 'count'),\n"
        "    unique_hcps=('hcp_id', 'nunique'),\n"
        "    f2f_visits=('f2f', 'sum'),\n"
        "    avg_duration_min=('duration_min', 'mean'),\n"
        ").reset_index()\n"
        "v['f2f_share'] = (v['f2f_visits'] / v['visits']).round(4)\n"
        "v['avg_duration_min'] = v['avg_duration_min'].round(2)\n"
        "v.head()"),
    nbf.v4.new_code_cell(
        "# open follow ups due in week -> need territory, join via reps (follow_ups has no territory col!)\n"
        "fu['due_date'] = pd.to_datetime(fu['due_date'])\n"
        "fu['week'] = (fu['due_date'] - pd.to_timedelta(fu['due_date'].dt.weekday, unit='D')).dt.date\n"
        "fu2 = fu.merge(reps[['rep_id', 'territory_id']], on='rep_id', how='left')\n"
        "open_fu = fu2[fu2['status'] == 'open'].groupby(['territory_id', 'week']).size().reset_index(name='open_follow_ups')"),
    nbf.v4.new_code_cell(
        "# sales in spark because the file was big in prod\n"
        "sales = (sales_sdf.groupBy('territory_id', 'week')\n"
        "         .agg(F.sum('units').alias('units'), F.round(F.sum('revenue_gbp'), 2).alias('revenue_gbp'))\n"
        "         .toPandas())\n"
        "sales['week'] = pd.to_datetime(sales['week']).dt.date"),
    nbf.v4.new_code_cell(
        "# reps per territory for visits_per_rep\n"
        "rep_cnt = reps.groupby('territory_id').size().reset_index(name='rep_count')"),
    nbf.v4.new_code_cell(
        "kpis = sales.merge(v, on=['territory_id', 'week'], how='left') \\\n"
        "            .merge(open_fu, on=['territory_id', 'week'], how='left') \\\n"
        "            .merge(rep_cnt, on='territory_id', how='left') \\\n"
        "            .merge(terr[['territory_id', 'region']], on='territory_id', how='left')\n"
        "for c in ['visits', 'unique_hcps', 'f2f_visits', 'open_follow_ups']:\n"
        "    kpis[c] = kpis[c].fillna(0).astype(int)\n"
        "kpis['f2f_share'] = kpis['f2f_share'].fillna(0.0)\n"
        "kpis['avg_duration_min'] = kpis['avg_duration_min'].fillna(0.0)\n"
        "kpis['visits_per_rep'] = (kpis['visits'] / kpis['rep_count']).round(2)\n"
        "kpis['revenue_per_visit'] = np.where(kpis['visits'] > 0, (kpis['revenue_gbp'] / kpis['visits']).round(2), 0.0)\n"
        "kpis = kpis[['territory_id', 'region', 'week', 'visits', 'unique_hcps', 'f2f_visits', 'f2f_share', 'avg_duration_min',\n"
        "             'open_follow_ups', 'rep_count', 'visits_per_rep', 'units', 'revenue_gbp', 'revenue_per_visit']]\n"
        "kpis = kpis.sort_values(['territory_id', 'week']).reset_index(drop=True)\n"
        "print(kpis.shape)\n"
        "kpis.head(10)"),
    nbf.v4.new_code_cell(
        "# save for the dashboard team\n"
        "kpis['week'] = pd.to_datetime(kpis['week'])\n"
        "kpis.to_parquet('expected_output/territory_kpis.parquet', index=False)\n"
        "kpis.to_csv('expected_output/territory_kpis.csv', index=False)"),
]
nbf.write(tk, HERE / "territory_kpis.ipynb")

# ---------------------------------------------------------------- hcp_engagement (smaller, messy, stays unconverted for the live run)
he = nbf.v4.new_notebook()
he.cells = [
    nbf.v4.new_markdown_cell("# HCP engagement\n\nPer-HCP engagement snapshot: last visit, visits in last 90 days, open follow-ups, engagement tier. Pandas + a bit of Spark."),
    nbf.v4.new_code_cell(
        "import pandas as pd\n"
        "from pyspark.sql import SparkSession, functions as F\n"
        "spark = SparkSession.builder.master('local[*]').getOrCreate()\n"
        "DATA = '../data'\n"
        "AS_OF = pd.Timestamp('2025-09-29')"),
    nbf.v4.new_code_cell(
        "hcps = spark.read.parquet(DATA + '/hcps.parquet')\n"
        "visits = spark.read.parquet(DATA + '/visits.parquet')\n"
        "fu = pd.read_parquet(DATA + '/follow_ups.parquet')"),
    nbf.v4.new_code_cell(
        "last = visits.groupBy('hcp_id').agg(F.max('visit_date').alias('last_visit'), F.count('*').alias('total_visits')).toPandas()\n"
        "v = visits.toPandas()\n"
        "v['visit_date'] = pd.to_datetime(v['visit_date'])\n"
        "recent = v[v['visit_date'] >= AS_OF - pd.Timedelta(days=90)].groupby('hcp_id').size().reset_index(name='visits_90d')\n"
        "open_fu = fu[fu['status'] == 'open'].groupby('hcp_id').size().reset_index(name='open_follow_ups')"),
    nbf.v4.new_code_cell(
        "df = hcps.toPandas().merge(last, on='hcp_id', how='left').merge(recent, on='hcp_id', how='left').merge(open_fu, on='hcp_id', how='left')\n"
        "df['last_visit'] = pd.to_datetime(df['last_visit'])\n"
        "df['days_since_last_visit'] = (AS_OF - df['last_visit']).dt.days\n"
        "for c in ['total_visits', 'visits_90d', 'open_follow_ups']:\n"
        "    df[c] = df[c].fillna(0).astype(int)\n"
        "def tier(r):\n"
        "    if r['visits_90d'] >= 3: return 'high'\n"
        "    if r['visits_90d'] >= 1: return 'medium'\n"
        "    return 'low'\n"
        "df['engagement_tier'] = df.apply(tier, axis=1)\n"
        "df = df.sort_values('hcp_id').reset_index(drop=True)\n"
        "df.head()"),
    nbf.v4.new_code_cell(
        "df.to_parquet('expected_output/hcp_engagement.parquet', index=False)"),
]
nbf.write(he, HERE / "hcp_engagement.ipynb")
print("notebooks written")
