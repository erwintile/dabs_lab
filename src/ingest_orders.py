# Databricks notebook source
# Ingest demo orders into the bronze schema.
# catalog and schema come from job parameters (set per bundle target).

dbutils.widgets.text("catalog", "dev")
dbutils.widgets.text("schema", "bronze")

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
target_table = f"{catalog}.{schema}.orders"

print("Hello World")
print(f"Writing to {target_table}")

# COMMAND ----------

from pyspark.sql import functions as F

rows = [
    (1, "C001", "2026-11-01", 120.50),
    (2, "C002", "2026-11-02", 75.00),
    (3, "C001", "2026-11-03", 210.25),
    (4, "C003", "2026-11-03", 42.90),
]

df = (
    spark.createDataFrame(rows, "order_id INT, customer_id STRING, order_date STRING, amount DOUBLE")
    .withColumn("order_date", F.to_date("order_date"))
    .withColumn("_ingested_at", F.current_timestamp())
)

# Managed Delta table: no path option, files go to the catalog storage root.
df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(target_table)

# COMMAND ----------

display(spark.table(target_table))
