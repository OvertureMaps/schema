-- This file contains the logic for transforming OpenStreetMap features into Overture features
-- for the `water` type within the `base` theme.

-- The order of the WHEN clauses in the following CASE statement is very specific. It is the same
-- as saying "WHEN this tag is present AND ignore any of the other tags below this line"
WITH classified_OSM AS (
    SELECT CAST(
        CASE
            -- Streams
            WHEN tags['waterway'] IN ('stream') THEN ROW('stream', tags['waterway'])
            WHEN tags['water'] IN ('stream') THEN ROW('stream', tags['water'])

            -- Rivers
            WHEN tags['waterway'] IN ('river') THEN ROW('river', tags['waterway'])
            WHEN tags['water'] IN ('river') THEN ROW('river', tags['water'])

            -- Canals
            WHEN tags['water'] IN ('canal', 'ditch', 'moat') THEN ROW('canal', tags['water'])
            WHEN tags['waterway'] IN ('canal', 'ditch', 'moat') THEN ROW('canal', tags['waterway'])
            WHEN tags['water'] IN ('drain') THEN ROW('canal', 'drain')
            WHEN tags['waterway'] IN ('drain') THEN ROW('canal', 'drain')

            -- Ponds
            WHEN tags['water'] IN ('fishpond', 'pond') THEN ROW('pond', tags['water'])
            WHEN tags['water'] IN ('lake', 'reservoir', 'pond')
                    AND ST_GeometryType(ST_GeometryFromText(wkt)) IN ('ST_Polygon', 'ST_MultiPolygon')
                    AND ST_AREA(TO_SPHERICAL_GEOGRAPHY(ST_GeometryFromText(wkt))) < 4000
                    THEN ROW('pond','pond')

            -- Lakes
            WHEN tags['water'] IN ('lake', 'oxbow','lagoon') THEN ROW('lake', tags['water'])

            -- Springs
            WHEN tags['natural'] IN ('spring','hot_spring','geyser','blowhole') THEN ROW('spring', tags['natural'])

            -- Tidal Channels / Fairways
            WHEN tags['waterway'] IN ('tidal_channel', 'fairway') THEN ROW('water', tags['waterway'])

            -- Wastewater
            WHEN tags['water'] IN ('wastewater') THEN ROW('water', 'wastewater')
            WHEN tags['reservoir_type'] IN ('sewage') THEN ROW('wastewater', 'sewage')

            -- Reservoirs
            WHEN tags['water'] IN ('reservoir', 'basin') THEN ROW('reservoir', tags['water'])
            WHEN tags['landuse'] IN ('reservoir', 'basin') THEN
                CASE
                    WHEN tags['basin'] IN (
                        'evaporation',
                        'detention',
                        'retention',
                        'infiltration',
                        'cooling'
                    ) THEN ROW('reservoir', 'basin')
                    WHEN tags['reservoir_type'] IN ('water_storage') THEN ROW('reservoir', 'water_storage')
                    ELSE ROW('reservoir', 'reservoir')
                END

            -- Physical
            WHEN tags['natural'] IN ('bay','cape','shoal','strait') THEN ROW('physical', tags['natural'])
            WHEN tags['waterway'] IN ('waterfall') THEN ROW('physical', tags['waterway'])

            -- Swimming Pools
            WHEN tags['leisure'] = 'swimming_pool' AND tags['location'] IS NULL
                OR tags['location'] IN ('','roof','outdoor','overground','surface')
                    THEN ROW('human_made', 'swimming_pool')

            -- Reflecting Pools
            WHEN tags['water'] IN ('reflecting_pool') THEN ROW('human_made', 'reflecting_pool')

            -- Salt Ponds
            WHEN tags['landuse'] IN ('salt_pond') THEN ROW('human_made', 'salt_pond')

            -- Fish pass
            WHEN tags['waterway'] IN ('fish_pass') THEN ROW('human_made', 'fish_pass')

            -- Dock
            WHEN tags['waterway'] = 'dock' AND tags['dock'] <> 'drydock' THEN ROW('water', 'dock')

            -- Oceans / Seas
            WHEN tags['place'] IN ('ocean','sea') THEN ROW('physical', tags['place'])

            -- Default "water"
            WHEN tags['natural'] = 'water' THEN ('water', 'water')

            ELSE ROW(NULL,NULL)
        END AS ROW(subtype varchar, class varchar)) AS overture,
        ST_GeometryFromText(wkt) as geom,
        TRY_CAST(tags['ele'] AS integer) AS elevation,
        *
    FROM
        {daylight_table}
    WHERE
        release = '{daylight_version}'

        -- Some buildings are tagged as having running water
        AND tags['building'] IS NULL

        AND (
            -- Consider anything with a water tag
            tags['water'] IS NOT NULL

            -- The OSM key/values for water features considered 'natural'
            OR tags['natural'] IN (
                'bay',
                'cape',
                'geyser',
                'hot_spring',
                'shoal',
                'spring',
                'straight',
                'water'
            )

            -- Reservoirs and basins are tagged this way
            OR tags['basin'] IS NOT NULL
            OR tags['landuse'] IN ('basin', 'reservoir', 'salt_pond')

            OR tags['leisure'] = 'swimming_pool'

            -- Mostly for labeling:
            OR tags['seamark:type'] = 'fairway'
            OR tags['place'] IN ('sea','ocean')

            -- Filter IN for waterway features to avoid dams, locks, etc.
            OR (
                tags['waterway'] IN (
                    'canal',
                    'ditch',
                    'dock',
                    'drain',
                    'fairway',
                    'fish_pass',
                    'river',
                    'riverbank',
                    'stream',
                    'tidal_channel',
                    'waterfall'
                )
            )
        )
)
SELECT
    -- Needed to compute GERS ID and satisfy Overture requirements.
    type,
    id,
    version,
    min_lon,
    max_lon,
    min_lat,
    max_lat,

    -- Use the OSM timestamp as update_time
    TO_ISO8601(created_at AT TIME ZONE 'UTC') AS update_time,

    -- The complex logic that builds the Overture names object will be injected
    '__OVERTURE_NAMES_QUERY' AS names,

    -- The overture struct is defined below
    overture.subtype as subtype,
    overture.class AS class,

    -- Relevant OSM tags for water type
    MAP_FILTER(tags, (k,v) -> k IN (
            'basin',
            'building',
            'dock',
            'intermittent',
            'landuse',
            'leisure',
            'location',
            'man_made',
            'natural',
            'reservoir_type',
            'salt',
            'seamark:type',
            'water',
            'waterway'
        )
    ) as source_tags,

    -- Temporary for debugging
    tags AS osm_tags,

    -- Sources are an array of structs.
    ARRAY [ CAST(
        ROW(
            '',
            'OpenStreetMap',
            SUBSTR(type, 1, 1) || CAST(id AS varchar) || '@' || CAST(version AS varchar),
            NULL,
            TO_ISO8601(created_at AT TIME ZONE 'UTC')
        )
        AS ROW(
            property varchar,
            dataset varchar,
            record_id varchar,
            confidence double,
            update_time varchar
        )
    ) ] AS sources,

    -- Wikidata is a top-level property in the OSM Container
    tags['wikidata'] as wikidata,

    -- Overture's concept of `layer` is called level
    TRY_CAST(tags['layer'] AS integer) AS level,

    -- Elevation is common on some ponds / lakes.
    IF(elevation < 9000, elevation, NULL) as elevation,

    -- Other type=water top-level attributes
    (tags['salt'] = 'yes') AS is_salt,
    (tags['intermittent'] = 'yes') AS is_intermittent,

    -- Cast geometry as WKB after cleaning up any improperly filled polygons
    ST_AsBinary(
        CASE
            WHEN ST_GeometryType(geom) = 'ST_Polygon' AND tags['waterway'] IN ('canal', 'drain', 'ditch')
                THEN ST_ExteriorRing(geom)
            ELSE
                geom
        END
    ) AS geometry
FROM classified_osm
WHERE
    overture.subtype IS NOT NULL

UNION ALL
-- Water derived from the OSM Coastline tool delivered via Daylight Earth Table
SELECT
    -- Needed to compute ID and satisfy Overture requirements.
    'area' AS type,
    NULL AS id,
    0 version,
    ST_XMIN(ST_GeometryFromText(wkt)) as min_lon,
    ST_XMAX(ST_GeometryFromText(wkt)) as max_lon,
    ST_YMIN(ST_GeometryFromText(wkt)) AS min_lat,
    ST_YMAX(ST_GeometryFromText(wkt)) AS max_lat,
    -- Stub with today's date for now
    TO_ISO8601(cast(now() as timestamp) AT TIME ZONE 'UTC') AS update_time,
    NULL AS names,
    class as subtype,
    subclass as class,
    MAP() AS source_tags,
    MAP() AS osm_tags,
    -- Source is OSM
    ARRAY [ CAST(
        ROW(
            '',
            'OpenStreetMap',
            NULL,
            NULL,
            NULL
        ) AS ROW(
            property varchar,
            dataset varchar,
            record_id varchar,
            confidence double,
            update_time varchar
        )
    ) ] as sources,
    -- Wikidata is a top-level property in the OSM Container
    NULL as wikidata,
    0 AS level,
    -- Other type=water top-level attributes
    0 AS elevation,
    TRUE AS is_salt,
    FALSE AS is_intermittent,
    ST_AsBinary(ST_GeometryFromText(wkt)) as geometry
FROM {daylight_earth_table}
WHERE release = '{daylight_version}'
    AND theme = 'water'
    AND class = 'ocean'
    AND subclass = 'ocean'
