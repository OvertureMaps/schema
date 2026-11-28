-- Pulls the release records the schema guides use as examples.
-- Run from the guides/examples folder:  duckdb < fetch-records.sql
INSTALL spatial; LOAD spatial;
INSTALL httpfs; LOAD httpfs;
SET s3_region = 'us-west-2';

-- Empire State Building
COPY (
  SELECT * REPLACE (ST_AsText(geometry) AS geometry)
  FROM read_parquet('s3://overturemaps-us-west-2/release/2026-11-18.0/theme=buildings/type=building/*', hive_partitioning = 1)
  WHERE bbox.xmin > -73.990 AND bbox.xmax < -73.982
    AND bbox.ymin > 40.745 AND bbox.ymax < 40.752
    AND id = '0e8abfe5-a7f3-4e8e-b6f0-db1fb0bb5b0c'
) TO 'raw/empire-state-building.json' (FORMAT JSON, ARRAY true);

-- West 34th Street, in front of the Empire State Building
COPY (
  SELECT * REPLACE (ST_AsText(geometry) AS geometry)
  FROM read_parquet('s3://overturemaps-us-west-2/release/2026-11-18.0/theme=transportation/type=segment/*', hive_partitioning = 1)
  WHERE bbox.xmin > -73.995 AND bbox.xmax < -73.975
    AND bbox.ymin > 40.744 AND bbox.ymax < 40.754
    AND id = 'e0fe7f44-2ba6-44bf-ae1e-797e39a04485'
) TO 'raw/west-34th-street.json' (FORMAT JSON, ARRAY true);

-- Starbucks Reserve, in the Empire State Building
COPY (
  SELECT * REPLACE (ST_AsText(geometry) AS geometry)
  FROM read_parquet('s3://overturemaps-us-west-2/release/2026-11-18.0/theme=places/type=place/*', hive_partitioning = 1)
  WHERE bbox.xmin > -73.986 AND bbox.xmax < -73.984
    AND bbox.ymin > 40.748 AND bbox.ymax < 40.749
    AND id = '3e5a04fb-d588-4266-95fe-658f2f324a9b'
) TO 'raw/starbucks-reserve-empire-state-building.json' (FORMAT JSON, ARRAY true);

-- Manhattan, the locality
COPY (
  SELECT * REPLACE (ST_AsText(geometry) AS geometry)
  FROM read_parquet('s3://overturemaps-us-west-2/release/2026-11-18.0/theme=divisions/type=division/*', hive_partitioning = 1)
  WHERE bbox.xmin > -73.986 AND bbox.xmax < -73.985
    AND bbox.ymin > 40.757 AND bbox.ymax < 40.758
    AND id = '84d8a97e-4624-43a4-9c7f-5c853ac90703'
) TO 'raw/manhattan.json' (FORMAT JSON, ARRAY true);
