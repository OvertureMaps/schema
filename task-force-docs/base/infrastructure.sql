-- This file contains the logic for transforming OpenStreetMap features into Overture features
-- for the `infrastructure` type within the `base` theme.

-- The order of the WHEN clauses in the following CASE statement is very specific. It is the same
-- as saying "WHEN this tag is present AND ignore any of the other tags below this line"

WITH classified_osm AS (
    SELECT CAST(
        CASE
            -- Transit
            WHEN element_at(tags,'railway') IN ('station','halt') THEN ROW('transit', 'railway_' || element_at(tags,'railway'))

            WHEN element_at(tags,'highway') = 'bus_stop' THEN ROW('transit', 'bus_stop')
            WHEN element_at(tags,'route') = 'bus' THEN ROW('transit', 'bus_route')
            WHEN element_at(tags,'amenity') = 'bus_station' THEN ROW('transit', 'bus_station')

            WHEN element_at(tags,'amenity') = 'ferry_terminal' THEN ROW('transit','ferry_terminal')

            WHEN element_at(tags,'amenity') IN ('parking','parking_space','bicycle_parking') THEN ROW('transit', element_at(tags,'amenity'))

            WHEN element_at(tags,'public_transport') IN ('stop_position', 'platform') THEN ROW('transit', element_at(tags,'public_transport'))

            -- Aerialways
            WHEN element_at(tags,'aerialway') IN (
                'cable_car',
                'gondola',
                'mixed_lift',
                'chair_lift',
                'drag_lift',
                't-bar',
                'pylon'
            ) THEN ROW('aerialway', element_at(tags,'aerialway'))

            WHEN element_at(tags,'aerialway') = 'station' THEN ROW('aerialway', 'aerialway_station')

            -- Airports
            WHEN element_at(tags,'aeroway') IN ('runway', 'taxiway', 'airstrip', 'helipad') THEN ROW('airport', element_at(tags,'aeroway'))

            WHEN element_at(tags,'aeroway') = 'gate' THEN ROW('airport', 'airport_gate')

            WHEN element_at(tags,'aeroway') = 'aerodrome' THEN CASE
                WHEN element_at(tags,'aerodrome:type') = 'military' OR element_at(tags,'landuse') = 'military' OR element_at(tags,'military') IN (
                    'airfield'
                ) THEN ROW('airport','military_airport')
                WHEN element_at(tags,'access') IN ('emergency', 'no', 'permissive', 'private')
                    OR element_at(tags,'aerodrome:type') = 'private' THEN ROW('airport','private_airport')
                WHEN lower(element_at(tags,'name')) LIKE '%international%' OR element_at(tags,'aerodrome:type') = 'international'
                    OR element_at(tags,'aerodrome') = 'international' THEN ROW('airport','international_airport')
                WHEN lower(element_at(tags,'name')) LIKE '%regional%' OR element_at(tags,'aerodrome:type') = 'regional'
                    THEN ROW('airport','regional_airport')
                WHEN lower(element_at(tags,'name')) LIKE '%municipal%' THEN ROW('airport','municipal_airport')
                WHEN lower(element_at(tags,'name')) LIKE '%seaplane%' THEN ROW('airport','seaplane_airport')
                WHEN lower(element_at(tags,'name')) LIKE '%heli%' THEN ROW('airport','heliport')
                ELSE ROW('airport','airport')
            END

            -- Bridges
            WHEN element_at(tags,'bridge') IN (
                'aqueduct',
                'boardwalk',
                'cantilever',
                'covered',
                'movable',
                'trestle',
                'viaduct'
            ) THEN ROW('bridge', element_at(tags,'bridge'))
            WHEN element_at(tags,'bridge:support') IS NOT NULL THEN
                ROW('bridge', 'bridge_support')

            -- Communication
            WHEN element_at(tags,'communication:mobile_phone') <> 'no' THEN ROW('communication','mobile_phone_tower')
            WHEN element_at(tags,'communication') IN ('line','pole') THEN ROW('communication','communication_' || element_at(tags,'communication'))
            WHEN element_at(tags,'tower:type') = 'communication' THEN ROW('communication','communication_tower')

            -- Pedestrian
            WHEN element_at(tags,'highway') IS NULL AND element_at(tags,'footway') IN ('crossing') AND (wkt LIKE 'MULTIPOLYGON%' OR wkt LIKE 'POLYGON%') THEN ROW('pedestrian','pedestrian_crossing')
            WHEN element_at(tags,'tourism') IN ('information', 'viewpoint') THEN ROW('pedestrian', element_at(tags,'tourism'))
            WHEN element_at(tags,'amenity') IN (
                'atm',
                'bench',
                'picnic_table',
                'post_box',
                'toilets',
                'vending_machine'
            ) THEN ROW('pedestrian', element_at(tags,'amenity'))

            -- Manholes
            WHEN element_at(tags,'manhole') IN ('drain', 'sewer') THEN ROW('manhole', element_at(tags,'manhole'))
            WHEN element_at(tags,'manhole') IS NOT NULL THEN ROW('manhole','manhole')

            -- Power
            WHEN element_at(tags,'power') IN (
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
            ) THEN ROW('power', element_at(tags,'power'))

            WHEN element_at(tags,'power') IN ('line', 'pole', 'tower') THEN ROW('power','power_' || element_at(tags,'power'))

            -- Recreation
            WHEN element_at(tags,'tourism') = ('camp_site') AND wkt LIKE 'POINT%' THEN ROW('recreation','camp_site')

            -- Towers
            WHEN element_at(tags,'tower:type') IN (
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
            ) THEN ROW('tower', element_at(tags,'tower:type'))

            -- Utility
            WHEN element_at(tags,'man_made') IN ('silo','utility_pole','storage_tank', 'pipeline', 'water_tower') THEN ROW('utility',element_at(tags,'man_made'))

            -- Waste Management
            WHEN element_at(tags,'amenity') IN(
                'recycling',
                'waste_basket',
                'waste_disposal'
            ) THEN ROW('waste_management',element_at(tags,'amenity'))

            --Water
            WHEN element_at(tags,'man_made') IN ('dam') THEN ROW('water',element_at(tags,'man_made'))
            WHEN element_at(tags,'waterway') IN ('dam','weir') THEN ROW('water', element_at(tags,'waterway'))
            WHEN element_at(tags,'amenity') = ('drinking_water') AND
                (element_at(tags,'drinking_water') IS NULL OR element_at(tags,'drinking_water') <> 'no') AND
                (element_at(tags,'access') IS NULL OR element_at(tags,'access') <> 'private')
                THEN ROW('water', 'drinking_water')


            -- Standalone piers
            WHEN element_at(tags,'man_made') IN ('pier') THEN ROW('pier','pier')


            -- Barrier tags are often secondary on other features, so put them last.
            -- Barrier tags that are not allowed on points:
            WHEN wkt NOT LIKE 'POINT%' AND element_at(tags,'barrier') IN (
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
            ) THEN ROW('barrier', element_at(tags,'barrier'))

            -- Points allowed on these types of barriers:
            WHEN element_at(tags,'barrier') IN (
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
            ) THEN ROW('barrier', element_at(tags,'barrier'))
            WHEN element_at(tags,'man_made') IN ('cutline') THEN ROW('barrier','cutline')

            -- If there remains a barrier tag but it's not in the above list:
            WHEN element_at(tags,'barrier') IS NOT NULL THEN ROW('barrier','barrier')

            -- Lower priority generic `bridge` tags
            WHEN element_at(tags,'man_made') = 'bridge' THEN ROW('bridge','bridge')
            WHEN element_at(tags,'bridge') = 'yes' THEN ROW('bridge','bridge')

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

    -- Convert to Overture format
    TO_ISO8601(created_at AT TIME ZONE 'UTC') AS update_time,

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
            NULL
        )
        AS ROW(
            property varchar,
            dataset varchar,
            record_id varchar,
            confidence double
        )
    ) ] AS sources,

    -- Values of surface are restricted
    CASE
        WHEN element_at(tags,'surface') IN (
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
        )   THEN element_at(tags,'surface')
        WHEN element_at(tags,'surface') = 'concrete:plates'
            THEN 'concrete_plates'
        ELSE NULL
    END AS surface,

    -- Overture's concept of `layer` is called level
    TRY_CAST(element_at(tags,'layer') AS int) AS level,

    -- Wikidata is a top-level property in the OSM Container
    element_at(tags,'wikidata') as wikidata,

    -- Store geometries as WKT
    wkt AS wkt_geometry
FROM
    classified_osm
WHERE
    overture.subtype IS NOT NULL
