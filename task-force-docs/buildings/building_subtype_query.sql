CASE
    -- Prioritize the `building` tag to determine the subtype
    -- Agricultural
    WHEN lower(trim(element_at(tags, 'building'))) IN (
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
    WHEN lower(trim(element_at(tags, 'building'))) IN (
        'civic',
        'fire_station',
        'government',
        'government_office',
        'public'
    ) THEN 'civic'

    -- Commercial
    WHEN lower(trim(element_at(tags, 'building'))) IN (
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
    ) THEN 'commercial'

    -- Education
    WHEN lower(trim(element_at(tags, 'building'))) IN (
        'college',
        'kindergarten',
        'school',
        'university'
    ) THEN 'education'

    -- Entertainment
    WHEN lower(trim(element_at(tags, 'building'))) IN (
        'grandstand',
        'pavilion',
        'sports_centre',
        'sports_hall',
        'stadium'
    ) THEN 'entertainment'

    -- Industrial
    WHEN lower(trim(element_at(tags, 'building'))) IN (
        'factory',
        'industrial',
        'manufacture'
    ) THEN 'industrial'

    -- Medical
    WHEN lower(trim(element_at(tags, 'building'))) IN (
        'clinic',
        'hospital'
    ) THEN 'medical'

    -- Military
    WHEN lower(trim(element_at(tags, 'building'))) IN (
        'bunker',
        'military'
    ) THEN 'military'

    -- Outbuilding
    WHEN lower(trim(element_at(tags, 'building'))) IN (
        'allotment_house',
        'carport',
        'outbuilding',
        'shed'
    ) THEN 'outbuilding'

    -- Religious
    WHEN lower(trim(element_at(tags, 'building'))) IN (
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
    ) THEN 'religious'

    -- Residential
    WHEN lower(trim(element_at(tags, 'building'))) IN (
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
    ) THEN 'residential'

    -- Service
    WHEN lower(trim(element_at(tags, 'building'))) IN (
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
    WHEN lower(trim(element_at(tags, 'building'))) IN (
        'hangar',
        'parking',
        'train_station',
        'transportation'
    ) THEN 'transportation'

    -- Consider any amenity / tourism tags if no other building tag was present
    WHEN lower(trim(element_at(tags, 'amenity'))) IN (
        'nursing_home'
    ) THEN 'residential'

    WHEN lower(trim(element_at(tags, 'amenity'))) IN (
        'bus_station',
        'parking'
    ) THEN 'transportation'

    WHEN lower(trim(element_at(tags, 'amenity'))) IN (
        'place_of_worship'
    ) THEN 'religious'

    WHEN lower(trim(element_at(tags, 'amenity'))) IN (
        'clinic',
        'dentist',
        'doctors',
        'hospital',
        'pharmacy'
    ) THEN 'medical'

    WHEN lower(trim(element_at(tags, 'amenity'))) IN (
        'casino',
        'conference_centre',
        'events_venue',
        'cinema',
        'theatre',
        'arts_centre',
        'nightclub'
    ) THEN 'entertainment'

    WHEN lower(trim(element_at(tags, 'tourism'))) IN (
        'aquarium',
        'attraction',
        'gallery',
        'museum'
    ) THEN 'entertainment'

    WHEN lower(trim(element_at(tags, 'amenity'))) IN (
        'bar',
        'cafe',
        'fast_food',
        'food_court',
        'fuel',
        'ice_cream',
        'pub',
        'restaurant'
    ) THEN 'commercial'

    WHEN lower(trim(element_at(tags, 'amenity'))) IN (
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

     WHEN lower(trim(element_at(tags, 'amenity'))) IN (
        'college',
        'driving_school',
        'kindergarten',
        'music_school',
        'school',
        'university'
    ) THEN 'education'

    -- buildings that are part of bridge structures
    WHEN  lower(trim(element_at(tags, 'bridge:support'))) <> 'no'
    THEN 'bridge_structure'

    WHEN lower(trim(element_at(tags, 'bridge:structure'))) <> 'no'
    THEN 'bridge_structure'

    ELSE NULL
END
