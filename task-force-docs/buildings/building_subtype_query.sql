CASE
    -- Agricultural
    WHEN tags['building'] IN (
            'agricultural',
            'barn',
            'cowshed',
            'farm',
            'farm_auxiliary',
            'glasshouse',
            'greenhouse',
            'silo',
            'stable',
            'sty'
        ) THEN 'agricultural'

    -- Civic
    WHEN tags['building'] IN (
            'civic',
            'fire_station',
            'government',
            'government_office',
            'public'
    ) OR tags['amenity'] IN (
            'animal_shelter',
            'community_centre',
            'courthouse',
            'fire_station',
            'library',
            'police',
            'post_office',
            'public_bath',
            'public_building',
            'ranger_station',
            'shelter',
            'social_centre',
            'townhall',
            'veterinary'
        ) THEN 'civic'

    --Commercial
    WHEN tags['building'] IN (
            'commercial',
            'hotel',
            'kiosk',
            'marketplace',
            'office',
            'restaurant',
            'retail',
            'shop',
            'supermarket',
            'warehouse'
        ) OR tags['amenity'] IN (
            'bar',
            'cafe',
            'fast_food',
            'food_court',
            'fuel',
            'ice_cream',
            'pub',
            'restaurant'
        ) THEN 'commercial'

    --Education
    WHEN tags['building'] IN (
            'college',
            'kindergarten',
            'school',
            'university'
        ) OR tags['amenity'] IN (
            'college',
            'driving_school',
            'kindergarten',
            'music_school',
            'school',
            'university'
        ) THEN 'education'

    --Entertainment
    WHEN tags['building'] IN (
            'grandstand',
            'pavilion',
            'sports_centre',
            'sports_hall',
            'stadium'
        ) OR tags['amenity'] IN (
            'casino',
            'conference_centre',
            'events_venue',
            'cinema',
            'theatre',
            'arts_centre',
            'nightclub'
        ) OR tags['tourism'] IN (
            'aquarium',
            'attraction',
            'gallery',
            'museum'
        ) THEN 'entertainment'

    --Industrial
    WHEN tags['building'] IN (
            'factory',
            'industrial',
            'manufacture'
        ) THEN 'industrial'

    --Medical
    WHEN tags['building'] IN (
            'clinic',
            'hospital'
        ) OR tags['amenity'] IN (
            'clinic',
            'dentist',
            'doctors',
            'hospital',
            'pharmacy'
        ) THEN 'medical'

    --Military
    WHEN tags['building'] IN (
            'bunker',
            'military'
        ) THEN 'military'

    --Outbuilding
    WHEN tags['building'] IN (
            'allotment_house',
            'carport',
            'outbuilding',
            'shed'
        ) THEN 'outbuilding'

    --Religious
    WHEN tags['building'] IN (
            'cathedral',
            'chapel',
            'church',
            'monastery',
            'mosque',
            'presbytery',
            'religious',
            'shrine',
            'synagogue',
            'temple',
            'wayside_shrine'
        ) OR tags['amenity'] = 'place_of_worship'
        THEN 'religious'

    --Residential
    WHEN tags['building'] IN (
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
            'trullo'
        ) OR tags['amenity'] IN (
            'nursing_home'
        ) THEN 'residential'

    --Service
    WHEN tags['building'] IN (
            'beach_hut',
            'boathouse',
            'digester',
            'guardhouse',
            'service',
            'slurry_tank',
            'storage_tank',
            'toilets',
            'transformer_tower'
        ) THEN 'service'

    -- Transportation
    WHEN tags['building'] IN (
            'hangar',
            'parking',
            'train_station',
            'transportation'
        ) OR tags['amenity'] IN (
            'bus_station',
            'parking'
        ) THEN 'transportation'
    ELSE NULL
END
