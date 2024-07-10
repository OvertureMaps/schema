-- This file contains the logic for transforming OpenStreetMap features into Overture features
-- for the `infrastructure` type within the `base` theme.

-- The order of the WHEN clauses in the following CASE statement is very specific. It is the same
-- as saying "WHEN this tag is present AND ignore any of the other tags below this line"

WITH classified_osm AS (
    SELECT CAST(
        CASE
            -- Transit
            WHEN tags['railway'] IN ('station','halt') THEN ROW('transit', 'railway_' || tags['railway'])

            WHEN tags['highway'] = 'bus_stop' THEN ROW('transit', 'bus_stop')
            WHEN tags['route'] = 'bus' THEN ROW('transit', 'bus_route')
            WHEN tags['amenity'] = 'bus_station' THEN ROW('transit', 'bus_station')

            WHEN tags['amenity'] = 'ferry_terminal' THEN ROW('transit','ferry_terminal')

            WHEN tags['amenity'] IN ('parking','parking_space','bicycle_parking') THEN ROW('transit', tags['amenity'])

            WHEN tags['public_transport'] IN ('stop_position', 'platform') THEN ROW('transit', tags['public_transport'])

            -- Aerialways
            WHEN tags['aerialway'] IN (
                'cable_car',
                'gondola',
                'mixed_lift',
                'chair_lift',
                'drag_lift',
                't-bar',
                'pylon'
            ) THEN ROW('aerialway', tags['aerialway'])

            WHEN tags['aerialway'] = 'station' THEN ROW('aerialway', 'aerialway_station')

            -- Airports
            WHEN tags['aeroway'] IN ('runway', 'taxiway', 'airstrip', 'helipad') THEN ROW('airport', tags['aeroway'])

            WHEN tags['aeroway'] = 'gate' THEN ROW('airport', 'airport_gate')

            WHEN tags['aeroway'] = 'aerodrome' THEN CASE
                WHEN tags['aerodrome:type'] = 'military' OR tags['landuse'] = 'military' OR tags['military'] IN (
                    'airfield'
                ) THEN ROW('airport','military_airport')
                WHEN tags['access'] IN ('emergency', 'no', 'permissive', 'private')
                    OR tags['aerodrome:type'] = 'private' THEN ROW('airport','private_airport')
                WHEN lower(tags['name']) LIKE '%international%' OR tags['aerodrome:type'] = 'international'
                    OR tags['aerodrome'] = 'international' THEN ROW('airport','international_airport')
                WHEN lower(tags['name']) LIKE '%regional%' OR tags['aerodrome:type'] = 'regional'
                    THEN ROW('airport','regional_airport')
                WHEN lower(tags['name']) LIKE '%municipal%' THEN ROW('airport','municipal_airport')
                WHEN lower(tags['name']) LIKE '%seaplane%' THEN ROW('airport','seaplane_airport')
                WHEN lower(tags['name']) LIKE '%heli%' THEN ROW('airport','heliport')
                ELSE ROW('airport','airport')
            END

            -- Bridges
            WHEN tags['bridge'] IN (
                'aqueduct',
                'boardwalk',
                'cantilever',
                'covered',
                'movable',
                'trestle',
                'viaduct'
            ) THEN ROW('bridge', tags['bridge'])
            WHEN tags['bridge:support'] IS NOT NULL THEN
                ROW('bridge', 'bridge_support')

            -- Communication
            WHEN tags['communication:mobile_phone'] <> 'no' THEN ROW('communication','mobile_phone_tower')
            WHEN tags['communication'] IN ('line','pole') THEN ROW('communication','communication_' || tags['communication'])
            WHEN tags['tower:type'] = 'communication' THEN ROW('communication','communication_tower')

            -- Pedestrian
            WHEN tags['highway'] IS NULL AND tags['footway'] IN ('crossing') AND (wkt LIKE 'MULTIPOLYGON%' OR wkt LIKE 'POLYGON%') THEN ROW('pedestrian','pedestrian_crossing')
            WHEN tags['tourism'] IN ('information', 'viewpoint') THEN ROW('pedestrian', tags['tourism'])
            WHEN tags['amenity'] IN (
                'atm',
                'bench',
                'picnic_table',
                'post_box',
                'toilets',
                'vending_machine'
            ) THEN ROW('pedestrian', tags['amenity'])

            -- Manholes
            WHEN tags['manhole'] IN ('drain', 'sewer') THEN ROW('manhole', tags['manhole'])
            WHEN tags['manhole'] IS NOT NULL THEN ROW('manhole','manhole')

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
            ) THEN ROW('power', tags['power'])

            WHEN tags['power'] IN ('line', 'pole', 'tower') THEN ROW('power','power_' || tags['power'])

            -- Recreation
            WHEN tags['tourism'] = ('camp_site') AND wkt LIKE 'POINT%' THEN ROW('recreation','camp_site')

            -- Towers
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
            ) THEN ROW('tower', tags['tower:type'])

            -- Utility
            WHEN tags['man_made'] IN ('silo','utility_pole','storage_tank', 'pipeline', 'water_tower') THEN ROW('utility',tags['man_made'])

            -- Waste Management
            WHEN tags['amenity'] IN(
                'recycling',
                'waste_basket',
                'waste_disposal'
            ) THEN ROW('waste_management',tags['amenity'])

            --Water
            WHEN tags['man_made'] IN ('dam') THEN ROW('water',tags['man_made'])
            WHEN tags['waterway'] IN ('dam','weir') THEN ROW('water', tags['waterway'])
            WHEN tags['amenity'] = ('drinking_water') AND
                (tags['drinking_water'] IS NULL OR tags['drinking_water'] <> 'no') AND
                (tags['access'] IS NULL OR tags['access'] <> 'private')
                THEN ROW('water', 'drinking_water')


            -- Standalone piers
            WHEN tags['man_made'] IN ('pier') THEN ROW('pier','pier')


            -- Barrier tags are often secondary on other features, so put them last.
            -- Barrier tags that are not allowed on points:
            WHEN wkt NOT LIKE 'POINT%' AND tags['barrier'] IN (
                'cable_barrier',
                'city_wall',
                'chain',
                'ditch',
                'fence',
                'guard_rail',
                'handrail',
                'hedge',
                'jersey_barrier',
                'kerb',
                'retaining_wall',
                'wall'
            ) THEN ROW('barrier', tags['barrier'])

            -- Points allowed on these types of barriers:
            WHEN tags['barrier'] IN (
                'block',
                'bollard',
                'border_control',
                'bump_gate',
                'bus_trap',
                'cattle_grid',
                'cycle_barrier',
                'chain',
                'entrance',
                'full-height_turnstile',
                'gate',
                'hampshire_gate',
                'height_restrictor',
                'jersey_barrier',
                'kerb',
                'kissing_gate',
                'lift_gate',
                'planter',
                'sally_port',
                'stile',
                'swing_gate',
                'toll_booth'
            ) THEN ROW('barrier', tags['barrier'])
            WHEN tags['man_made'] IN ('cutline') THEN ROW('barrier','cutline')

            -- If there remains a barrier tag but it's not in the above list:
            WHEN tags['barrier'] IS NOT NULL THEN ROW('barrier','barrier')

            -- Lower priority generic `bridge` tags
            WHEN tags['man_made'] = 'bridge' THEN ROW('bridge','bridge')
            WHEN tags['bridge'] = 'yes' THEN ROW('bridge','bridge')

        END AS ROW(subtype varchar, class varchar)) AS overture,
        *
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
                'bridge:support',
                'bridge:structure',
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
                'footway',
                'highway',
                'icao',
                'public_transport',
                'railway',
                'route'
            ]
        )
)

SELECT
    -- Needed to compute pseudo-stable ID:
    type,
    id,
    version,
    min_lon,
    max_lon,
    min_lat,
    max_lat,

    -- Names query gets injected
    '__OVERTURE_NAMES_QUERY' AS names,

    -- The overture struct is defined below
    overture.subtype as subtype,
    overture.class AS class,

    -- Relevant OSM tags for infrastructure
    MAP_FILTER(tags,
        (k,v) -> k IN (
            'access',
            'aerodrome:type',
            'aerodrome',
            'amenity',
            'barrier',
            'bridge:structure',
            'bridge:support',
            'frequency',
            'icao',
            'landuse',
            'location',
            'military',
            'parking',
            'ref',
            'route',
            'substation',
            'surface',
            'tourism',
            'tower',
            'voltage'
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

    -- Values of surface are restricted
    CASE
        WHEN tags['surface'] IN (
            'asphalt',
            'cobblestone',
            'compacted',
            'concrete',
            'dirt',
            'earth',
            'fine_gravel',
            'grass',
            'gravel',
            'ground',
            'paved',
            'paving_stones',
            'pebblestone',
            'recreation_grass',
            'recreation_paved',
            'recreation_sand',
            'rubber',
            'sand',
            'sett',
            'tartan',
            'unpaved',
            'wood',
            'woodchips'
        )   THEN tags['surface']
        WHEN tags['surface'] = 'concrete:plates'
            THEN 'concrete_plates'
        ELSE NULL
    END AS surface,

    -- Overture's concept of `layer` is called level
    TRY_CAST(tags['layer'] AS int) AS level,

    -- Wikidata is a top-level property in the OSM Container
    tags['wikidata'] as wikidata,

    -- Store geometries as WKT
    wkt AS wkt_geometry
FROM
    classified_osm
WHERE
    overture.subtype IS NOT NULL
