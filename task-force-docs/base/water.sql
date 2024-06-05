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

    -- Determine subtype from class
    CASE
        WHEN class IN ('stream') THEN 'stream'
        WHEN class IN ('river') THEN 'river'
        WHEN class IN ('pond', 'fishpond') THEN 'pond'
        WHEN class IN ('lake', 'oxbow', 'lagoon') THEN 'lake'
        WHEN class IN ('reservoir', 'basin', 'water_storage') THEN 'reservoir'
        WHEN class IN ('canal', 'ditch', 'moat') THEN 'canal'
        WHEN class IN (
            'drain',
            'fish_pass',
            'reflecting_pool',
            'swimming_pool'
        ) THEN 'human_made'
        WHEN class IN (
            'bay',
            'cape',
            'fairway',
            'ocean',
            'sea',
            'shoal',
            'strait'
        ) THEN 'physical'
        WHEN class IN ('spring','hot_spring','geyser') THEN 'spring'
        -- Default to just 'water'
        ELSE 'water'
    END AS subtype,
    class,

    -- The complex logic that builds the Overture names object will be injected
    '__OVERTURE_NAMES_QUERY' AS names,

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
            NULL
        )
        AS ROW(
            property varchar,
            dataset varchar,
            record_id varchar,
            confidence double
        )
    ) ] AS sources,

    -- Wikidata is a top-level property in the OSM Container
    tags['wikidata'] as wikidata,

    -- Overture's concept of `layer` is called level
    TRY_CAST(tags['layer'] AS integer) AS level,

    -- Elevation is common on some ponds / lakes.
    TRY_CAST(tags['ele'] AS integer) AS elevation,

    -- Other type=water top-level attributes
    (tags['salt'] = 'yes') AS is_salt,
    (tags['intermittent'] = 'yes') AS is_intermittent,

    -- Cast geometry as WKB
    ST_AsBinary(geom) AS geometry
FROM (
    SELECT
        *,
        -- Determine class
        CASE
            -- Waterway values that become classes
            WHEN tags['waterway'] IN (
                'canal',
                'ditch',
                'drain',
                'fish_pass',
                'river',
                'stream',
                'tidal_channel',
                'waterfall'
            ) THEN tags['waterway']

            WHEN tags['waterway'] = 'riverbank' THEN 'river'

            -- Water tags that become classes, independent of surface area
            WHEN tags['water'] IN (
                'basin',
                'canal',
                'ditch',
                'drain',
                'fishpond',
                'lagoon',
                'lock',
                'moat',
                'oxbow',
                'reflecting_pool',
                'river',
                'salt_pool',
                'stream',
                'wastewater'
            ) THEN tags['water']

            WHEN tags['natural'] IN (
                'bay',
                'cape',
                'spring',
                'hot_spring',
                'geyser',
                'blowhole',
                'shoal',
                'strait'
            ) THEN tags['natural']

            WHEN tags['place'] IN ('sea','ocean') THEN tags['place']

            -- Check size of still water to reclassify as pond:
            WHEN tags['water'] IN ('lake', 'reservoir', 'pond')
                THEN IF(surface_area_sq_m < 4000, 'pond', tags['water'])

            -- Basins and Reservoirs are classified in landuse
            WHEN tags['landuse'] IN ('reservoir', 'basin') THEN
                CASE
                    WHEN tags['basin'] IN (
                        'evaporation',
                        'detention',
                        'retention',
                        'infiltration',
                        'cooling'
                    ) THEN 'basin'
                    WHEN tags['reservoir_type'] IN ('sewage','water_storage') THEN tags['reservoir_type']
                    ELSE 'reservoir'
                END

            WHEN tags['leisure'] = 'swimming_pool' THEN tags['leisure']

            WHEN tags['waterway'] = 'dock' AND tags['dock'] <> 'drydock' THEN 'dock'

            WHEN tags['natural'] = 'water' AND tags['man_made'] IN (
                'basin',
                'pond',
                'reservoir',
                'yes',
                'waterway'
            ) THEN IF(
                surface_area_sq_m < 4000,
                'pond',
                IF(
                    tags['man_made'] IN ('basin', 'reservoir', 'pond'),
                    tags['man_made'],
                    'water'
                )
            )

            WHEN tags['place'] IN ('sea','ocean') THEN tags['place']
            -- Default class is just 'water'
            ELSE 'water'
        END AS class
    FROM (
        SELECT
            id,
            type,
            version,
            tags,
            geom,
            -- Extra attrs for water-specific logic
            IF(
                ST_GEOMETRYTYPE(geom) IN ('ST_Polygon', 'ST_MultiPolygon'),
                ROUND(ST_AREA(TO_SPHERICAL_GEOGRAPHY(geom)), 2),
                NULL
            ) AS surface_area_sq_m,
            created_at, min_lon, max_lon, min_lat, max_lat
        FROM (
            SELECT
                id,
                version,
                type,
                tags,
                IF(
                    ST_GEOMETRYTYPE(ST_GeometryFromText(wkt)) = 'ST_Polygon'
                        AND tags['waterway'] IN ('canal', 'drain', 'ditch'),
                    ST_EXTERIORRING(ST_GeometryFromText(wkt)),
                    ST_GeometryFromText(wkt)
                ) AS geom,
                created_at, min_lon, max_lon, min_lat, max_lat
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
                    OR tags['landuse'] IN ('basin', 'reservoir')

                    -- Swimming pools are complicated:
                    OR (
                        -- swimming pools are cool
                        -- but not if they are a building/indoor
                        tags['leisure'] = 'swimming_pool'
                        AND (
                            tags['building'] = 'no'
                            OR tags['building'] IS NULL
                        )

                        AND (
                            tags['location'] IS NULL
                            OR tags['location'] IN (
                                'roof',
                                'outdoor',
                                'overground',
                                'surface'
                            )
                        )
                    )
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
        )
    )
WHERE
    class IS NOT NULL

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
    class as subtype,
    subclass as class,
    NULL AS names,
    MAP() AS source_tags,
    MAP() AS osm_tags,
    -- Source is OSM
    ARRAY [ CAST(
        ROW(
            '',
            'OpenStreetMap',
            NULL,
            NULL
        ) AS ROW(
            property varchar,
            dataset varchar,
            record_id varchar,
            confidence double
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
