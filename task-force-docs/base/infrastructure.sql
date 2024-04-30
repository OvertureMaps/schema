SELECT
    -- Needed to compute ID and satisfy Overture requirements:
    type,
    id,
    version,
    min_lon,
    max_lon,
    min_lat,
    max_lat,
    TO_ISO8601(created_at AT TIME ZONE 'UTC') AS update_time,
    -- Determine class from subclass or tags
    CASE
        -- Bus / Ferry / Railway Infrastructure (Transit)
        WHEN class IN (
            'bus_route',
            'bus_stop',
            'bus_station',
            -- 'ferry_route',
            'ferry_terminal',
            'railway_halt',
            'railway_station',
            -- Parking
            'parking',
            'parking_space',

            -- Public transport / cycle
            'stop_position',

            -- cycle
            'bicycle_parking'

        ) THEN 'transit'

        -- Aerialways
        WHEN class IN (
            'aerialway_station',
            'cable_car',
            'gondola',
            'mixed_lift',
            'chair_lift',
            'drag_lift',
            't-bar'
        ) THEN 'aerialway'

        -- Airports
        WHEN class IN (
            'airport',
            'airstrip',
            'helipad',
            'heliport',
            'international_airport',
            'military_airport',
            'municipal_airport',
            'private_airport',
            'regional_airport',
            'runway',
            'seaplane_airport',
            'taxiway'
        ) THEN 'airport'

        -- Barriers / Fences
        WHEN class IN (
            'barrier',
            'block',
            'bollard',
            'cattle_grid',
            'chain',
            'city_wall',
            'cycle_barrier',
            'ditch',
            'entrance',
            'guard_rail',
            'hedge',
            'height_restrictor',
            'jersey_barrier',
            'kerb',
            'kissing_gate',
            'lift_gate',
            'retaining_wall',
            'stile',
            'swing_gate',
            'toll_booth',
            'wall'
        ) THEN 'barrier'

        -- Bridges
        WHEN class IN (
            'bridge',
            'viaduct',
            'boardwalk',
            'aqueduct',
            'movable',
            'covered',
            'cantilever',
            'trestle'
        ) THEN 'bridge'

        -- Communication
        WHEN class IN (
            'communication_line',
            'communication_pole',
            'communication_tower',
            'mobile_phone_tower'
        ) THEN 'communication'

        -- Generic Towers
        WHEN class IN (
            'bell_tower',
            'cooling',
            'defensive',
            'diving',
            'hose',
            'lighting',
            'lightning_protection',
            'minaret',
            'monitoring',
            'observation',
            'radar',
            'siren',
            'suspension',
            'watchtower'
        ) THEN 'tower'

        -- Power
        WHEN class IN (
            'cable_distribution',
            'cable',
            'catenary_mast',
            'connection',
            'generator',
            'heliostat',
            'insulator',
            'minor_line',
            'plant',
            'power_pole',
            'portal',
            'power_line',
            'power_tower',
            'sub_station',
            'substation',
            'switch',
            'terminal',
            'transformer'
        ) THEN 'power'

        -- Pedestrian
        WHEN class IN ('bench','information','waste_basket') THEN 'pedestrian'

        -- Manholes
        WHEN class IN ('manhole', 'drain', 'sewer') THEN 'manhole'

        -- Piers & Dams are their own subtypes
        WHEN class IN ('pier', 'dam') THEN class

    END AS subtype,
    class,
    '__OVERTURE_NAMES_QUERY' AS names,

    -- Relevant OSM tags for land type
    MAP_FILTER(tags, (k,v) -> k IN (
            'access',
            'aerodrome:type',
            'aerodrome',
            'amenity',
            'barrier',
            'icao',
            'landuse',
            'military',
            'parking',
            'ref',
            'route',
            'tower',
            'tourism'
        )
    ) AS source_tags,

    -- Add all OSM Tags for debugging
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

    tags['surface'] AS surface,

    tags['level'] AS level,

    -- Wikidata is a top-level property in the OSM Container
    tags['wikidata'] as wikidata,

    -- Apparently there are corrupt geometries that are breaking Athena, so write WKT for now:
    wkt AS wkt_geometry
FROM (
    SELECT
        *,
        CASE
            -- Transit Infrastructure
            -- Air
            WHEN tags['aeroway'] IN ('runway', 'taxiway', 'airstrip', 'helipad') THEN tags['aeroway']

            -- Specific airport classing
            WHEN tags['aeroway'] = 'aerodrome' THEN CASE
                WHEN tags['aerodrome:type'] = 'military' OR tags['landuse'] = 'military' OR tags['military'] IN (
                    'airfield'
                ) THEN 'military_airport'
                WHEN tags['access'] IN ('emergency', 'no', 'permissive', 'private')
                    OR tags['aerodrome:type'] = 'private' THEN 'private_airport'
                WHEN tags['name'] LIKE '%international%' OR tags['aerodrome:type'] = 'international'
                    OR tags['aerodrome'] = 'international' THEN 'international_airport'
                WHEN tags['name'] LIKE '%regional%' OR tags['aerodrome:type'] = 'regional'
                    THEN 'regional_airport'
                WHEN tags['name'] LIKE '%municipal%' THEN 'municipal_airport'
                WHEN tags['name'] LIKE '%seaplane%' THEN 'seaplane_airport'
                WHEN tags['name'] LIKE '%heli%' THEN 'heliport'
                ELSE 'airport'
            END

            --Aerialways
            WHEN tags['aerialway'] IN (
                'cable_car',
                'gondola',
                'mixed_lift',
                'chair_lift',
                'drag_lift',
                't-bar'
            ) THEN tags['aerialway']

            WHEN tags['aerialway'] = 'station' THEN 'aerialway_station'

            --Barriers
            WHEN tags['barrier'] IS NOT NULL AND tags['barrier'] <> 'no' THEN
                IF(tags['barrier'] IN (
                    'block',
                    'bollard',
                    'cattle_grid',
                    'chain',
                    'city_wall',
                    'cycle_barrier',
                    'ditch',
                    'entrance',
                    'guard_rail',
                    'hedge',
                    'height_restrictor',
                    'jersey_barrier',
                    'kerb',
                    'kissing_gate',
                    'lift_gate',
                    'retaining_wall',
                    'stile',
                    'swing_gate',
                    'toll_booth',
                    'wall'
                ), tags['barrier'],
                'barrier'
            )

            -- Bus
            WHEN tags['highway'] = 'bus_stop' THEN 'bus_stop'
            WHEN tags['route'] = 'bus' THEN 'bus_route'
            WHEN tags['amenity'] = 'bus_station' THEN 'bus_station'

            -- Public Transport
            WHEN tags['public_transport'] = 'stop_position' THEN 'stop_position'

            -- Ferry
            -- WHEN tags['route'] = 'ferry' THEN 'ferry_route'
            WHEN tags['amenity'] = 'ferry_terminal' THEN 'ferry_terminal'

            -- Parking
            WHEN tags['amenity'] IN ('parking','parking_space') THEN tags['amenity']

            -- Pedestrian
            WHEN tags['amenity'] IN ('bench','bicycle_parking','waste_basket') THEN tags['amenity']
            WHEN tags['tourism'] IN ('information') THEN tags['tourism']

            -- Rail
            WHEN tags['railway'] = 'station' THEN 'railway_station'
            WHEN tags['railway'] = 'halt' THEN 'railway_halt'


            -- Communication
            WHEN tags['communication:mobile_phone'] <> 'no' THEN 'mobile_phone_tower'
            WHEN tags['communication'] = 'line' THEN 'communication_line'
            WHEN tags['communication'] = 'pole' THEN 'communication_pole'
            WHEN tags['tower:type'] = 'communication' THEN 'communication_tower'

            -- Manhole
            WHEN tags['manhole'] IN ('drain', 'sewer') THEN tags['manhole']
            WHEN tags['manhole'] IS NOT NULL THEN 'manhole'

            -- Power
            WHEN tags['power'] IN (
                'cable_distribution',
                'cable',
                'catenary_mast',
                'connection',
                'generator',
                'heliostat',
                'insulator',
                'minor_line',
                'plant',
                'portal',
                'sub_station',
                'substation',
                'switch',
                'terminal',
                'transformer'
            ) THEN tags['power']

            WHEN tags['power'] = 'line' THEN 'power_line'
            WHEN tags['power'] = 'pole' THEN 'power_pole'
            WHEN tags['power'] = 'tower' THEN 'power_tower'

            -- Other towers
            WHEN tags['tower:type'] IN (
                'bell_tower',
                'cooling',
                'defensive',
                'diving',
                'hose',
                'lighting',
                'lightning_protection',
                'minaret',
                'monitoring',
                'observation',
                'radar',
                'siren',
                'watchtower'
            ) THEN tags['tower:type']

            -- TODO: bridges, dams?
            WHEN tags['bridge'] = 'yes' THEN 'bridge'
            WHEN tags['bridge'] IN (
                'aqueduct',
                'boardwalk',
                'cantilever',
                'covered',
                'movable',
                'trestle',
                'viaduct'
            ) THEN tags['bridge']

            WHEN tags['man_made'] IN ('bridge', 'pier') THEN tags['man_made']

            WHEN tags['waterway'] IN ('dam') THEN 'dam'

        END AS class
    FROM
        -- These two lines get injected.
        {daylight_table}
        WHERE release = '{daylight_version}'
        --
        AND ARRAYS_OVERLAP(
            MAP_KEYS(tags),
            ARRAY[
                'barrier',
                'bridge',
                'communication:mobile_phone',
                'communication',
                'man_made',
                'manhole',
                'power',
                'tower:type',
                'tower',
                'tourism',
                'waterway',
                -- Transit
                'aerialway',
                'aeroway',
                'amenity',
                'highway',
                'icao',
                'public_transport',
                'railway',
                'route'
            ]
        ) = TRUE
    )
WHERE
    class IS NOT NULL
