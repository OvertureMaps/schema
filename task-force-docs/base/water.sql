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
    created_at AS update_time,

    -- Determine class from subclass
    CASE
        WHEN subclass IN ('stream') THEN 'stream'
        WHEN subclass IN ('river') THEN 'river'
        WHEN subclass IN ('pond', 'fishpond') THEN 'pond'
        WHEN subclass IN ('lake', 'oxbow', 'lagoon') THEN 'lake'
        WHEN subclass IN ('reservoir', 'basin', 'water_storage') THEN 'reservoir'
        WHEN subclass IN ('canal', 'ditch', 'moat') THEN 'canal'
        WHEN subclass IN (
            'drain',
            'fish_pass',
            'fish_ladder',
            'reflecting_pool',
            'swimming_pool'
        ) THEN 'human_made'
        WHEN subclass IN (
            'bay',
            'cape',
            'fairway',
            'ocean',
            'shoal',
            'strait'
        ) THEN 'physical'
        WHEN subclass IN ('spring','hot_spring','geyser') THEN 'spring'
        -- Default to just 'water'
        ELSE 'water'
    END AS subtype,
    subclass as class,

    -- The complex logic that builds the Overture names object will be injected
    '__OVERTURE_NAMES_QUERY' AS names,

    -- Relevant OSM tags for water type
    MAP_FILTER(tags, (k,v) -> k IN (
            'basin',
            'intermittent',
            'landuse',
            'leisure',
            'natural',
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
        -- Determine subclass
        CASE
            -- Waterway values that become subclasses
            WHEN tags['waterway'] IN (
                'canal',
                'ditch',
                'dock',
                'drain',
                'fish_pass',
                'river',
                'stream',
                'tidal_channel',
                'waterfall'
            ) THEN tags['waterway']

            WHEN tags['waterway'] = 'riverbank' THEN 'river'

            -- Water tags that become subclasses, independent of surface area
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

            WHEN tags['natural'] IN ('spring','hot_spring','geyser','blowhole') THEN tags['natural']

            -- Check size of still water to reclassify as pond:
            WHEN tags['water'] IN ('lake', 'oxbow', 'reservoir', 'pond')
                THEN IF(surface_area_sq_m < 4000, 'pond', tags['water'])

            -- Basins and Reservoirs are classified in landuse
            WHEN tags['landuse'] IN ('reservoir', 'basin') THEN CASE
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

            -- Add some new feature/label types for points only
            WHEN tags['natural'] IN ('cape', 'shoal', 'strait') THEN IF(
                ST_GEOMETRYTYPE(geom) IN (
                    'ST_Point',
                    'ST_LineString',
                    'ST_MultiLineString'
                ),
                tags['natural'],
                NULL -- null trap to throw out polygons
            )

            WHEN tags['seamark:type'] IN ('fairway') THEN IF(
                ST_GEOMETRYTYPE(geom) IN (
                    'ST_Point',
                    'ST_LineString',
                    'ST_MultiLineString'
                ),
                tags['seamark:type'],
                NULL -- null trap to throw out polygons
            )
            -- Default subclass is just 'water'
            ELSE 'water'
        END AS subclass
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
                AND (
                    -- Consider anything with a water tag
                    tags['water'] IS NOT NULL

                    -- The OSM key/values for water features considered 'natural'
                    OR tags['natural'] IN (
                        'bay',
                        'cape',
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
                            'river',
                            'riverbank',
                            'stream',
                            'tidal_channel'
                        )
                    )
                )
            )
        )
    )
WHERE
    subclass IS NOT NULL
