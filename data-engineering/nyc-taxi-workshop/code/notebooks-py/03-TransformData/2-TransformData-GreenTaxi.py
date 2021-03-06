# Databricks notebook source
# MAGIC %md
# MAGIC # What's in this exercise?
# MAGIC 
# MAGIC 1) Read raw data, augment with derived attributes, augment with reference data & persist<BR> 
# MAGIC 2) Create external unmanaged Hive tables<BR>
# MAGIC 3) Create statistics for tables                          

# COMMAND ----------

from pyspark.sql.functions import *
from pyspark.sql.types import StructType, StructField, StringType, IntegerType,LongType,FloatType,DoubleType, TimestampType

# COMMAND ----------

#Destination directory
destDataDirRoot = "/mnt/<userid>/data/nyctaxi/curatedDir/<userid>/green-taxi" 

#Delete any residual data from prior executions for an idempotent run
dbutils.fs.rm(destDataDirRoot,recurse=True)

# COMMAND ----------

# MAGIC %md
# MAGIC ### 1.  Execute notebook with common/reusable functions 

# COMMAND ----------

# MAGIC %run "../01-General/3-CommonFunctions"

# COMMAND ----------

# MAGIC %md
# MAGIC ### 2.  Read raw, augment, persist as parquet 

# COMMAND ----------

curatedDF = sql("""
  select 
      t.taxi_type,
      t.vendor_id,
      t.pickup_datetime,
      t.dropoff_datetime,
      t.store_and_fwd_flag,
      t.rate_code_id,
      t.pickup_location_id,
      t.dropoff_location_id,
      t.pickup_longitude,
      t.pickup_latitude,
      t.dropoff_longitude,
      t.dropoff_latitude,
      t.passenger_count,
      t.trip_distance,
      t.fare_amount,
      t.extra,
      t.mta_tax,
      t.tip_amount,
      t.tolls_amount,
      t.ehail_fee,
      t.improvement_surcharge,
      t.total_amount,
      t.payment_type,
      t.trip_type,
      t.trip_year,
      t.trip_month,
      v.abbreviation as vendor_abbreviation,
      v.description as vendor_description,
      tt.description as trip_type_description,
      tm.month_name_short,
      tm.month_name_full,
      pt.description as payment_type_description,
      rc.description as rate_code_description,
      tzpu.borough as pickup_borough,
      tzpu.zone as pickup_zone,
      tzpu.service_zone as pickup_service_zone,
      tzdo.borough as dropoff_borough,
      tzdo.zone as dropoff_zone,
      tzdo.service_zone as dropoff_service_zone,
      year(t.pickup_datetime) as pickup_year,
      month(t.pickup_datetime) as pickup_month,
      day(t.pickup_datetime) as pickup_day,
      hour(t.pickup_datetime) as pickup_hour,
      minute(t.pickup_datetime) as pickup_minute,
      second(t.pickup_datetime) as pickup_second,
      year(t.dropoff_datetime) as dropoff_year,
      month(t.dropoff_datetime) as dropoff_month,
      day(t.dropoff_datetime) as dropoff_day,
      hour(t.dropoff_datetime) as dropoff_hour,
      minute(t.dropoff_datetime) as dropoff_minute,
      second(t.dropoff_datetime) as dropoff_second
  from 
    <userid>_taxi_db.green_taxi_trips t
    left outer join <userid>_taxi_db.vendor_lookup v 
      on (t.vendor_id = v.vendor_id)
    left outer join <userid>_taxi_db.trip_type_lookup tt 
      on (t.trip_type = tt.trip_type)
    left outer join <userid>_taxi_db.trip_month_lookup tm 
      on (t.trip_month = tm.trip_month)
    left outer join <userid>_taxi_db.payment_type_lookup pt 
      on (t.payment_type = pt.payment_type)
    left outer join <userid>_taxi_db.rate_code_lookup rc 
      on (t.rate_code_id = rc.rate_code_id)
    left outer join <userid>_taxi_db.taxi_zone_lookup tzpu 
      on (t.pickup_location_id = tzpu.location_id)
    left join <userid>_taxi_db.taxi_zone_lookup tzdo 
      on (t.dropoff_location_id = tzdo.location_id)
  """)

#Write parquet output, calling function to calculate number of partition files
curatedDF.coalesce(15).write.partitionBy("trip_year", "trip_month").parquet(destDataDirRoot)

# COMMAND ----------

# MAGIC %scala
# MAGIC //setting variable in scala to run some scala commands on file system
# MAGIC val destDataDirRoot = "/mnt/<userid>/data/nyctaxi/curatedDir/<userid>/green-taxi" 
# MAGIC //Delete residual files from job operation (_SUCCESS, _start*, _committed*)
# MAGIC recursivelyDeleteSparkJobFlagFiles(destDataDirRoot)

# COMMAND ----------

# MAGIC %md
# MAGIC ### 3.  Define Hive external table

# COMMAND ----------

# MAGIC %sql
# MAGIC use <userid>_taxi_db;
# MAGIC 
# MAGIC DROP TABLE IF EXISTS green_taxi_trips_curated;
# MAGIC CREATE TABLE green_taxi_trips_curated(
# MAGIC taxi_type STRING,
# MAGIC vendor_id INT,
# MAGIC pickup_datetime TIMESTAMP,
# MAGIC dropoff_datetime TIMESTAMP,
# MAGIC store_and_fwd_flag STRING,
# MAGIC rate_code_id INT,
# MAGIC pickup_location_id INT,
# MAGIC dropoff_location_id INT,
# MAGIC pickup_longitude STRING,
# MAGIC pickup_latitude STRING,
# MAGIC dropoff_longitude STRING,
# MAGIC dropoff_latitude STRING,
# MAGIC passenger_count INT,
# MAGIC trip_distance DOUBLE,
# MAGIC fare_amount DOUBLE,
# MAGIC extra DOUBLE,
# MAGIC mta_tax DOUBLE,
# MAGIC tip_amount DOUBLE,
# MAGIC tolls_amount DOUBLE,
# MAGIC ehail_fee DOUBLE,
# MAGIC improvement_surcharge DOUBLE,
# MAGIC total_amount DOUBLE,
# MAGIC payment_type INT,
# MAGIC trip_type INT,
# MAGIC trip_year STRING,
# MAGIC trip_month STRING,
# MAGIC vendor_abbreviation STRING,
# MAGIC vendor_description STRING,
# MAGIC trip_type_description STRING,
# MAGIC month_name_short STRING,
# MAGIC month_name_full STRING,
# MAGIC payment_type_description STRING,
# MAGIC rate_code_description STRING,
# MAGIC pickup_borough STRING,
# MAGIC pickup_zone STRING,
# MAGIC pickup_service_zone STRING,
# MAGIC dropoff_borough STRING,
# MAGIC dropoff_zone STRING,
# MAGIC dropoff_service_zone STRING,
# MAGIC pickup_year INT,
# MAGIC pickup_month INT,
# MAGIC pickup_day INT,
# MAGIC pickup_hour INT,
# MAGIC pickup_minute INT,
# MAGIC pickup_second INT,
# MAGIC dropoff_year INT,
# MAGIC dropoff_month INT,
# MAGIC dropoff_day INT,
# MAGIC dropoff_hour INT,
# MAGIC dropoff_minute INT,
# MAGIC dropoff_second INT)
# MAGIC USING parquet
# MAGIC partitioned by (trip_year,trip_month)
# MAGIC LOCATION '/mnt/<userid>/data/nyctaxi/curatedDir/<userid>/green-taxi/';

# COMMAND ----------

# MAGIC %md
# MAGIC ### 4.  Create Hive table partitions

# COMMAND ----------

#Register Hive partitions for the transformed table
sql("MSCK REPAIR TABLE <userid>_taxi_db.green_taxi_trips_curated")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 5.  Compute Hive table statistics

# COMMAND ----------

sql("REFRESH TABLE <userid>_taxi_db.green_taxi_trips_curated")
sql("ANALYZE TABLE <userid>_taxi_db.green_taxi_trips_curated COMPUTE STATISTICS")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 6.  Explore

# COMMAND ----------

# MAGIC %sql
# MAGIC select trip_year,trip_month, count(*) as trip_count from <userid>_taxi_db.green_taxi_trips_curated group by trip_year,trip_month