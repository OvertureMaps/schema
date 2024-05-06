CASE
    -- Certain building tags become the class value to further describe the building subtype
    WHEN tags['building'] IN (

        -- Agricultural
        'agricultural',
        'barn',
        'cowshed',
        'farm',
        'farm_auxiliary',
        'glasshouse',
        'greenhouse',
        'silo',
        'stable',
        'sty',

        -- Civic
        'civic',
        'fire_station',
        'government',
        'government_office',
        'public',

        --Commercial
        'commercial',
        'hotel',
        'kiosk',
        'marketplace',
        'office',
        'restaurant',
        'retail',
        'shop',
        'supermarket',
        'warehouse',

        --Education
        'college',
        'kindergarten',
        'school',
        'university',

        --Entertainment
        'grandstand',
        'pavillion',
        'sports_centre',
        'sports_hall',
        'stadium',

        --Industrial
        'factory',
        'industrial',
        'manufacture',

        --Medical
        'clinic',
        'hospital',

        --Military
        'bunker',
        'military',

        --Outbuilding
        'allotment_house',
        'carport',
        'outbuilding',
        'shed',

        --Religious
        'cathedral',
        'chapel',
        'church',
        'monastary',
        'mosque',
        'presbytery',
        'religious',
        'shrine',
        'synagogue',
        'temple',
        'wayside_shrine',

        --Residential
        'apartments',
        'bungalow',
        'cabin',
        'detached',
        'dormitory',
        'duplex',
        'dwelling_house',
        'garage',
        'garages',
        'ger',
        'house',
        'houseboat',
        'hut',
        'residential',
        'semi',
        'semidetached_house',
        'static_caravan',
        'stilt_house',
        'terrace',
        'townhouse',
        'trullo',

        --Service
        'beach_hut',
        'boathouse',
        'digester',
        'guardhouse',
        'service',
        'slurry_tank',
        'storage_tank',
        'toilets',
        'transformer_tower',

        -- Transportation
        'hangar',
        'parking',
        'train_station',
        'transportation'
    ) THEN tags['building']
    ELSE NULL
END
