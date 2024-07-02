-- This file contains the logic for transforming OpenStreetMap features into Overture features
-- for the `land_use` type within the `base` theme.

-- The order of the WHEN clauses in the following CASE statement is very specific. It is the same
-- as saying "WHEN this tag is present AND ignore any of the other tags below this line"
WITH classified_osm AS (
    SELECT CAST(
        CASE
            -- Polygons
            WHEN SUBSTR(wkt,1,7) = 'POLYGON' OR SUBSTR(wkt,1,12) = 'MULTIPOLYGON' THEN CASE
                -- Military
                WHEN tags['military'] IN (
                    'airfield',
                    'barracks',
                    'base',
                    'danger_area',
                    'naval_base',
                    'nuclear_explosion_site',
                    'obstacle_course',
                    'range',
                    'training_area',
                    'trench'
                ) THEN ROW('military', tags['military'])

                -- Other general military landuse
                WHEN tags['military'] <> 'no' OR tags['landuse'] = 'military' THEN ROW('military', 'military')

                -- Residential
                WHEN tags['landuse'] IN ('residential', 'static_caravan', 'garages') THEN ROW('residential', tags['landuse'])

                -- Entertainment
                WHEN tags['tourism'] IN (
                    'zoo',
                    'theme_park'
                ) THEN ROW('entertainment', tags['tourism'])
                WHEN tags['leisure'] IN (
                    'water_park'
                ) THEN ROW('entertainment', tags['leisure'])

                -- Give National Parks top priority since it might have other tags.
                WHEN tags['boundary'] = 'national_park' THEN ROW('protected','national_park')

                -- Aboriginal Lands & Reservations
                WHEN tags['boundary'] IN ('aboriginal_lands') OR (
                    tags['boundary'] = 'protected_area' AND tags['protect_class'] = '24'
                ) THEN ROW('protected', 'aboriginal_land')

                -- Pedestrian land use, such as plazas
                WHEN tags['place'] = 'square' THEN ROW('pedestrian', 'plaza')
                WHEN tags['highway'] = 'pedestrian' THEN ROW('pedestrian', 'pedestrian')

                -- Is there is an official Protect Class Designation (wiki.openstreetmap.org/wiki/Key:protect_class)?
                WHEN tags['protect_class'] IN ('1a', '1b', '1', '2', '3', '4', '5', '6') THEN CASE
                    WHEN tags['protect_class'] = '1a' THEN ROW('protected', 'strict_nature_reserve')
                    WHEN tags['protect_class'] IN ('1b', '1') THEN ROW('protected', 'wilderness_area')
                    WHEN tags['protect_class'] = '2' THEN ROW('protected', 'national_park')
                    WHEN tags['protect_class'] = '3' THEN ROW('protected', 'natural_monument')
                    WHEN tags['protect_class'] = '4' THEN ROW('protected', 'species_management_area')
                    WHEN tags['protect_class'] = '5' THEN ROW('protected', 'protected_landscape_seascape')
                    WHEN tags['protect_class'] = '6' THEN ROW('protected', 'nature_reserve')
                END

                WHEN tags['boundary'] = 'protected_area' THEN CASE
                    WHEN LOWER(tags['protection_title']) IN ('national forest', 'state forest')
                        THEN ROW('protected', 'forest')
                    WHEN LOWER(tags['protection_title']) IN ('national park', 'parque nacional', 'national_park')
                        THEN ROW('protected', 'national_park')
                    WHEN LOWER(tags['protection_title']) IN ('state park') THEN ROW('protected','state_park')
                    WHEN LOWER(tags['protection_title']) IN (
                        'wilderness area',
                        'wilderness study area'
                    ) THEN ROW('protected', 'wilderness_area')
                    WHEN LOWER(tags['protection_title']) IN ('nature reserve', 'nature refuge', 'reserva nacional')
                        THEN ROW('protected', 'nature_reserve')
                    WHEN LOWER(tags['protection_title']) IN ('environmental use')
                        THEN ROW('protected', 'environmental')
                    WHEN tags['leisure'] IN ('nature_reserve')
                        THEN ROW('protected', tags['leisure'])
                    WHEN tags['landuse'] IS NOT NULL
                        THEN ROW('protected', 'protected')
                END

                WHEN tags['leisure'] IN ('nature_reserve') THEN ROW('protected','nature_reserve')

                -- National & State Parks (US)
                WHEN STRPOS(LOWER(tags['name']), 'national park') > 0
                    OR tags['boundary'] = 'national_park'
                    OR LOWER(tags['protection_title']) = 'national park'
                        THEN ROW('protected', 'national_park')

                WHEN STRPOS(LOWER(tags['name']), 'state park') > 0
                    OR LOWER(tags['protection_title']) = 'state park'
                        THEN ROW('protected', 'state_park')

                WHEN tags['protected_area'] = 'national_park' THEN ROW('protected', 'national_park')

                -- Golf
                WHEN tags['golf'] IN (
                    'bunker',
                    'driving_range',
                    'fairway',
                    'green',
                    'lateral_water_hazard',
                    'rough',
                    'tee',
                    'water_hazard'
                )
                    THEN ROW('golf', tags['golf'])
                WHEN tags['leisure'] IN (
                    'golf_course'
                ) THEN ROW('golf','golf_course')

                -- Winter Sports
                WHEN tags['landuse'] IN ('winter_sports') THEN ROW('winter_sports','winter_sports')

                -- Horticulture
                WHEN tags['landuse'] IN (
                    'allotments',
                    'greenhouse_horticulture',
                    'flowerbed',
                    'plant_nursery',
                    'orchard',
                    'vineyard'
                ) THEN ROW('horticulture', tags['landuse'])
                WHEN tags['leisure'] IN (
                    'garden'
                ) THEN ROW('horticulture', tags['leisure'])

                -- Aquaculture
                WHEN tags['landuse'] IN ('aquaculture') THEN ROW('aquaculture', 'aquaculture')

                -- Education / Schoolyards
                WHEN tags['amenity'] IN (
                    'college',
                    'university',
                    'school'
                ) THEN ROW('education', tags['amenity'])
                WHEN tags['landuse'] IN (
                    'education'
                ) THEN ROW('education', tags['landuse'])
                WHEN tags['leisure'] IN ('schoolyard')
                    THEN ROW('education', tags['leisure'])

                -- Medical
                WHEN tags['amenity'] IN (
                    'clinic',
                    'doctors',
                    'hospital'
                ) THEN ROW('medical', tags['amenity'])

                -- Park
                WHEN tags['leisure'] IN (
                    'dog_park',
                    'park'
                ) THEN ROW('park', tags['leisure'])
                WHEN tags['landuse'] IN ('village_green') THEN ROW('park', tags['landuse'])

                -- Agriculture
                WHEN tags['landuse'] IN ('animal_keeping', 'farmland', 'farmyard', 'meadow')
                    THEN ROW('agriculture', tags['landuse'])
                -- Meadows can also be tagged this way:
                WHEN tags['meadow'] IN ('agricultural', 'agriculture', 'pasture')
                    THEN ROW('agriculture', 'meadow')

                -- Resource extraction
                WHEN tags['landuse'] IN (
                    'logging',
                    'peat_cutting',
                    'quarry',
                    'salt_pond'
                ) THEN ROW('resource_extraction', tags['landuse'])

                -- Campgrounds
                WHEN tags['tourism'] = 'camp_site' AND tags['refugee'] IS NULL
                    THEN ROW('campground', 'camp_site')

                -- Cemetery
                WHEN tags['amenity'] IN ('grave_yard') THEN ROW('cemetery', 'grave_yard')
                WHEN tags['landuse'] IN ('cemetery') THEN ROW('cemetery', 'cemetery')
                WHEN tags['landuse'] IN ('grave_yard') THEN ROW('cemetery','grave_yard')

                -- Religious
                WHEN tags['landuse'] IN ('religious') THEN ROW('religious', tags['landuse'])

                -- Recreation
                WHEN tags['leisure'] IN (
                    'beach_resort',
                    'marina',
                    'pitch',
                    'playground',
                    'recreation_ground',
                    'stadium',
                    'track'
                ) THEN ROW('recreation', tags['leisure'])
                WHEN tags['landuse'] IN ('recreation_ground') THEN ROW('recreation',tags['landuse'])
                WHEN tags['leisure'] IN ('track', 'recreation_ground') THEN ROW('recreation', tags['leisure'])

                -- Landfill
                WHEN tags['landuse'] IN ('landfill') THEN ROW('landfill', 'landfill')

                -- General "developed"
                WHEN tags['landuse'] IN (
                    'brownfield',
                    'commercial',
                    'industrial',
                    'institutional',
                    'retail'
                ) THEN ROW('developed', tags['landuse'])
                WHEN tags['man_made'] = 'works' THEN ROW('developed', 'works')

                -- Construction
                WHEN tags['landuse'] IN ('construction', 'greenfield') THEN ROW('construction',tags['landuse'])

                -- Other managed / maintained
                WHEN tags['natural'] IS NULL AND tags['landuse'] IN (
                    'grass'
                ) THEN ROW('managed', tags['landuse'])

                -- Other Landuse
                WHEN tags['landuse'] IN ('highway', 'traffic_island') THEN ROW('transportation',tags['landuse'])
                ELSE ROW(NULL,NULL)
            END
            -- Linestrings
            WHEN SUBSTR(wkt,1,10) = 'LINESTRING' THEN CASE
                WHEN tags['leisure'] IN ('track') THEN ROW('recreation', tags['leisure'])
                ELSE ROW(NULL,NULL)
            END

        -- No Points allowed in landuse
        ELSE ROW(NULL,NULL)
        END AS ROW(subtype varchar, class varchar)
        ) AS overture,

        -- Transform the surface tag
        CASE
            --Sports related surface tags:
            WHEN tags['leisure'] IN ('pitch', 'playground', 'track', 'stadium') OR tags['sport'] IS NOT NULL THEN CASE
                WHEN tags['natural'] = 'sand' OR tags['surface'] IN (
                    'dirt',
                    'earth',
                    'fine_gravel',
                    'gravel',
                    'ground',
                    'unpaved',
                    'sand'
                ) OR tags['golf'] IN ('bunker') THEN 'recreation_sand'

                WHEN tags['surface'] IN ('artificial_turf', 'grass', 'grass_paver')
                    THEN 'recreation_grass'

                WHEN tags['surface'] IN (
                    'acrylic',
                    'asphalt',
                    'clay',
                    'compacted',
                    'concrete',
                    'hard',
                    'paved'
                ) THEN 'recreation_paved'
                WHEN tags['surface'] IS NULL AND tags['sport'] IN ('basketball')
                    THEN 'recreation_paved'

                WHEN tags['surface'] IS NULL AND tags['sport'] IN ('soccer', 'football')
                    THEN 'recreation_grass'
            END
            -- Golf bunkers are recreation sand, even if not tagged as such
            WHEN tags['golf'] = 'bunker' THEN 'recreation_sand'

            -- Only these tags are allowed through:
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
            -- Turn concrete:plates into concrete_plates
            WHEN tags['surface'] = 'concrete:plates'
                THEN 'concrete_plates'
            ELSE NULL
        END AS surface,
        *
    FROM
        -- These two lines get injected.
        {daylight_table}
    WHERE release = '{daylight_version}'
        AND (
            ARRAYS_OVERLAP(
                MAP_KEYS(tags),
                ARRAY[
                    'aeroway',
                    'amenity',
                    'boundary',
                    'golf',
                    'highway',
                    'landuse',
                    'leisure',
                    'man_made',
                    'meadow',
                    'military',
                    'place',
                    'protect_class',
                    'protection_title',
                    'tourism',
                    'waterway'
                ]
            ) = TRUE
            -- OR STRPOS(LOWER(tags['name']), 'national park') > 0
            -- OR STRPOS(LOWER(tags['name']), 'state park') > 0
        )

        AND (
            tags['building'] IS NULL
            OR tags['building'] = 'no'
        )
)

SELECT
    -- Needed to compute ID and satisfy Overture requirements.
    type,
    id,
    version,
    min_lon,
    max_lon,
    min_lat,
    max_lat,
    TO_ISO8601(created_at AT TIME ZONE 'UTC') AS update_time,

    '__OVERTURE_NAMES_QUERY' AS names,

    -- Subtype and class determined by logic below
    overture.subtype AS subtype,
    overture.class AS class,

    -- Relevant OSM tags for Landuse type
    MAP_FILTER(tags, (k,v) -> k IN (
            'access',
            'aeroway',
            'amenity',
            'area',
            'boundary',
            'building',
            'crop',
            'golf',
            'highway',
            'landuse',
            'layer',
            'leisure',
            'level',
            'man_made',
            'meadow',
            'military',
            'natural',
            'place',
            'produce',
            'protect_class',
            'protection_title',
            'refugee',
            'sport',
            'surface',
            'tourism',
            'trees',
            'waterway'
        )
    ) as source_tags,

    tags as osm_tags,

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

    -- Overture's concept of `layer` is called level
    TRY_CAST(tags['layer'] AS int) AS level,

    -- Wikidata is a top-level property in the OSM Container
    tags['wikidata'] as wikidata,

    -- Elevation as integer (meters above sea level)
    TRY_CAST(tags['ele'] AS integer) AS elevation,

    -- Other type=land_use top-level attributes
    surface,

    wkt AS wkt_geometry
FROM classified_osm
WHERE
    overture.subtype IS NOT NULL
