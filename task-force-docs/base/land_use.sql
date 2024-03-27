SELECT
    type,
    id,
    version,
    min_lon,
    max_lon,
    min_lat,
    max_lat,
    update_time,
    subtype,
    class,
    names,
    source_tags,
    osm_tags,
    sources,
    wikidata,
    surface,
    elevation,
    wkt_geometry
FROM (
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

        -- Determine subtype from class or tags
        CASE
            -- Agriculture
            WHEN class IN (
                'animal_keeping',
                'farmland',
                'farmyard',
                'meadow'
            ) THEN 'agriculture'

            -- Airports
            WHEN class IN (
                'aerodrome',
                'helipad',
                'heliport'
            ) THEN 'airport'

            -- Aquaculture
            WHEN class IN ('aquaculture') THEN 'aquaculture'

            -- Campground
            WHEN class IN ('camp_site') THEN 'campground'

            -- Cemetery
            WHEN class IN ('cemetery') THEN 'cemetery'

            -- Conservation
            WHEN class IN ('conservation') THEN 'conservation'

            -- Construction
            WHEN class IN (
                'construction',
                'greenfield'
            ) THEN 'construction'

            -- Developed
            WHEN class IN (
                'commercial',
                'retail',
                'industrial',
                'institutional',
                'brownfield'
            ) THEN 'developed'

            -- Education
            WHEN class IN (
                'college',
                'education',
                'school',
                'schoolyard',
                'university'
            ) THEN 'education'

            -- Entertainment
            WHEN class IN (
                'theme_park',
                'water_park',
                'zoo'
            ) THEN 'entertainment'

            -- Golf
            WHEN class IN (
                'bunker',
                'driving_range',
                'fairway',
                'golf_course',
                'green',
                'lateral_water_hazard',
                'rough',
                'tee',
                'water_hazard'
            ) THEN 'golf'

            -- Horticulture
            WHEN class IN (
                'allotments',
                'garden',
                'greenhouse_horticulture',
                'flowerbed',
                'plant_nursery',
                'orchard',
                'vineyard'
            ) THEN 'horticulture'

            -- Landfill
            WHEN class IN ('landfill') THEN 'landfill'

            -- Medical
            WHEN class IN (
                'clinic',
                'doctors',
                'hospital'
            ) THEN 'medical'

            -- Military
            WHEN class IN (
                'airfield',
                'barracks',
                'base',
                'danger_area',
                'military',
                'military_other',
                'naval_base',
                'nuclear_explosion_site',
                'obstacle_course',
                'range',
                'training_area',
                'trench'
            ) THEN 'military'

            -- Parks / Greenspace
            WHEN class IN (
                'common',
                'dog_park',
                'park',
                'village_green'
            ) THEN 'park'

            -- Pedestrian Infrastructure
            WHEN class IN (
                'pedestrian',
                'plaza'
            ) THEN 'pedestrian'

            -- Public
            WHEN class IN (
                'civic_admin',
                'public'
            ) THEN 'public'

            -- Protected
            WHEN class IN (
                'aboriginal_land',
                'environmental',
                'forest',
                'state_park',
                'national_park',
                'natural_monument',
                'nature_reserve',
                'protected_landscape_seascape',
                'species_management_area',
                'strict_nature_reserve',
                'wilderness_area',
                'wilderness'
            ) THEN 'protected'

            -- Recreation
            WHEN class IN (
                'recreation_grass',
                'recreation_paved',
                'pitch',
                'playground',
                'track',
                'recreation_ground',
                'recreation_sand',

                -- Add more leisure= tags here if necessary
                'marina',
                'stadium'
            ) THEN 'recreation'

            -- Religious
            WHEN class IN ('religious', 'churchyard') THEN 'religious'

            -- Residential
            WHEN class IN ('residential', 'static_caravan', 'garages')
                THEN 'residential'

            -- Resource
            WHEN class IN (
                'logging',
                'peat_cutting',
                'quarry',
                'salt_pond'
            ) THEN 'resource_extraction'

            -- Structure
            WHEN class IN ('pier', 'dam', 'bridge') THEN 'structure'

            -- Transportation
            WHEN class IN ('depot', 'traffic_island', 'highway')
                THEN 'transportation'

            -- Winter Sports
            WHEN class IN ('winter_sports') THEN 'winter_sports'

        END AS subtype,
        class,

        '__OVERTURE_NAMES_QUERY' AS names,

        -- Relevant OSM tags for Landuse type
        MAP_FILTER(tags, (k,v) -> k IN (
                'access',
                'aeroway',
                'amenity',
                'area',
                'boundary',
                'golf',
                'highway',
                'layer',
                'leisure',
                'level',
                'man_made',
                'meadow',
                'military',
                'natural',
                'place',
                'protect_class',
                'protection_title',
                'sport',
                'surface',
                'tourism'
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

        -- Wikidata is a top-level property in the OSM Container
        tags['wikidata'] as wikidata,

        -- Elevation as integer (meters above sea level)
        TRY_CAST(tags['ele'] AS integer) AS elevation,

        -- Other type=landuse top-level attributes
        surface,

        wkt_geometry
    FROM (
        SELECT
            *,
            IF(
                --Polygons
                wkt_geometry like '%POLYGON%',
                CASE

                    --logic for piers / dams
                    WHEN tags['man_made'] IN ('pier') AND tags['highway'] = NULL THEN tags['man_made']
                    WHEN tags['waterway'] = 'dam' THEN 'dam'

                    -- Check for Military specific tags
                    WHEN tags['military'] <> 'no' THEN
                        IF(tags['military'] IN (
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
                        ), tags['military'],
                        'military_other')

                    -- Priority landuse tags to pass to class logic:
                    WHEN tags['landuse'] IN ('military') THEN tags['landuse']

                    -- Use these secondary more descriptive tags first:
                    WHEN tags['tourism'] IN ('zoo','theme_park') THEN tags['tourism']

                    -- Aboriginal Lands & Reservations
                    WHEN tags['boundary'] IN ('aboriginal_lands') OR (
                        tags['boundary'] = 'protected_area' AND tags['protect_class'] = '24'
                    ) THEN 'aboriginal_land'

                    -- Pedestrian land use, such as plazas
                    WHEN tags['place'] = 'square' THEN 'plaza'
                    WHEN tags['highway'] = 'pedestrian' THEN 'pedestrian'

                    -- Is there is an official Protect Class Designation (wiki.openstreetmap.org/wiki/Key:protect_class)?
                    WHEN tags['protect_class'] IN ('1a', '1', '2', '3', '4', '5') THEN CASE
                        WHEN tags['protect_class'] = '1a' THEN 'strict_nature_reserve'
                        WHEN tags['protect_class'] IN ('1b', '1') THEN 'wilderness_area'
                        WHEN tags['protect_class'] = '2' THEN 'national_park'
                        WHEN tags['protect_class'] = '3' THEN 'natural_monument'
                        WHEN tags['protect_class'] = '4' THEN 'species_management_area'
                        WHEN tags['protect_class'] = '5' THEN 'protected_landscape_seascape'
                    END

                    -- protect_class >= 6 or null:
                    WHEN tags['boundary'] = 'protected_area' THEN CASE
                        WHEN LOWER(tags['protection_title']) IN ('national forest', 'state forest')
                            THEN 'forest'
                        WHEN LOWER(tags['protection_title']) IN ('national park') THEN 'national_park'
                        WHEN LOWER(tags['protection_title']) IN ('state park') THEN 'state_park'
                        WHEN LOWER(tags['protection_title']) IN (
                            'wilderness area',
                            'wilderness study area'
                        ) THEN 'wilderness_area'
                        WHEN LOWER(tags['protection_title']) IN ('nature reserve', 'nature refuge')
                            THEN 'nature_reserve'
                        WHEN LOWER(tags['protection_title']) IN ('environmental use')
                            THEN 'environmental'
                        -- Fall through to landuse if it's protected
                        WHEN tags['landuse'] IS NOT NULL THEN tags['landuse']
                        -- Last resort, a leisure= tag (such as nature_reserve):
                        WHEN tags['leisure'] IS NOT NULL THEN tags['leisure']
                    END

                    -- National & State Parks (US)
                    WHEN STRPOS(LOWER(tags['name']), 'national park') > 0 OR tags['boundary']
                        = 'national_park' OR LOWER(tags['protection_title']) = 'national park'
                        THEN 'national_park'

                    WHEN STRPOS(LOWER(tags['name']), 'state park') > 0 OR LOWER(tags['protection_title'])
                        = 'state park' THEN 'state_park'

                    -- Pull out golf before going into sport-specific logic
                    WHEN tags['golf'] IN (
                        'bunker',
                        'driving_range',
                        'fairway',
                        'golf_course',
                        'green',
                        'lateral_water_hazard',
                        'rough',
                        'tee',
                        'water_hazard'
                    ) THEN tags['golf']

                    -- Specific sport surfaces
                    WHEN tags['leisure'] IN ('pitch', 'playground', 'track', 'stadium')
                        THEN tags['leisure']

                    -- Meadows are tagged this way
                    WHEN tags['meadow'] IN ('agricultural', 'agriculture', 'pasture')
                        THEN 'meadow'

                    -- Amenity (Campuses)
                    WHEN tags['amenity'] IN (
                        'college',
                        'university',
                        'school',
                        'hospital',
                        'clinic',
                        'doctors'
                    ) THEN tags['amenity']

                    -- Campgrounds
                    WHEN tags['tourism'] = 'camp_site' AND tags['refugee'] IS NULL
                        THEN 'camp_site'

                    -- Leisure values that become classes:
                    WHEN tags['leisure'] IN (
                        'common',
                        'garden',
                        'golf_course',
                        'marina',
                        'nature_reserve',
                        'park',
                        'schoolyard',
                        'stadium',
                        'water_park'
                    ) THEN tags['leisure']

                    WHEN tags['aeroway'] IN ('aerodrome', 'helipad', 'heliport') THEN tags['aeroway']

                    -- Else use the landuse tag and assign it to a class above
                    -- (refer aginfo.osm.org/keys/landuse#values for top landuse values)
                    WHEN tags['landuse'] NOT IN ('meadow','forest') THEN tags['landuse']
                END,
                -- Linestrings / Points
                CASE
                    WHEN tags['man_made'] IN ('pier') THEN tags['man_made']

                    -- Some tracks are linestrings and they are not included elsewhere
                    WHEN tags['leisure'] IN ('track') THEN tags['leisure']
                END
            ) AS class,

            -- Transform tags to ROW(k,v) for names conversion
            TRANSFORM(
                MAP_ENTRIES(tags),
                r->CAST(r AS ROW(k VARCHAR, v VARCHAR))
            ) AS kv,

            -- Transform the surface tag
            IF(
                tags['leisure'] IN ('pitch', 'playground', 'track', 'stadium') OR tags['sport'] IS NOT NULL,
                CASE
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
                    ELSE tags['surface']
                END,
                CASE
                    WHEN tags['golf'] IN ('bunker') THEN 'recreation_sand'
                    ELSE tags['surface']
                END
            ) AS surface
        FROM (
            SELECT
                id,
                type,
                version,
                created_at,
                tags,
                -- ST_GeometryFromText(wkt) AS geom,
                wkt AS wkt_geometry,
                min_lon, max_lon, min_lat, max_lat
            FROM
                 -- These two lines get injected.
                {daylight_table}
                WHERE release = '{daylight_version}'
                --
                AND ARRAYS_OVERLAP(
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
                        'military',
                        'place',
                        'tourism',
                        'waterway'
                    ]
                ) = TRUE
                AND (
                    tags['building'] IS NULL
                    OR tags['building'] = 'no'
                )
            )
        )
    WHERE
        class IS NOT NULL
    )
WHERE
    subtype IS NOT NULL
