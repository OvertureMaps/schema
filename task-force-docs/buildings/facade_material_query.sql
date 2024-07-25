CASE
    WHEN lower(trim(element_at(tags, 'building:facade'))) IN (
        'brick',
        'slate',
        'ladrillos',
        'masonry',
        'silicate brick',
        'bricks',
        'unburnt brick',
        'silicate_brick',
        'brick_block',
        'muddy_brick'
    ) THEN 'brick'
    WHEN lower(trim(element_at(tags, 'building:facade'))) IN (
        'cement_block',
        'block',
        'cement block',
        'cement_blocks',
        'cement blocks'
    ) THEN 'cement_block'
    WHEN lower(trim(element_at(tags, 'building:facade'))) IN (
        'clay',
        'mud',
        'rammed_earth',
        'loam',
        'earth',
        'grass',
        'pressed_soil_blocks'
    ) THEN 'clay'
    WHEN lower(trim(element_at(tags, 'building:facade'))) IN (
        'concrete',
        'concrete masonry unit',
        'cement',
        'concrete_reinforced',
        'reinforced_concrete'
    ) THEN 'concrete'
    WHEN lower(trim(element_at(tags, 'building:facade'))) IN (
        'glass',
        'mirror'
    ) THEN 'glass'
    WHEN lower(trim(element_at(tags, 'building:facade'))) IN (
        'metal',
        'steel',
        'metal_plates',
        'tin',
        'iron_sheet',
        'copper',
        'metal_sheet',
        'ironsheets',
        'panel',
        'aluminium'
    ) THEN 'metal'
    WHEN lower(trim(element_at(tags, 'building:facade'))) IN (
        'plaster',
        'plastered',
        'hard'
    ) THEN 'plaster'
    WHEN lower(trim(element_at(tags, 'building:facade'))) IN (
        'plastic',
        'vinyl',
        'plastic_sheeting',
        'composite',
        'vinyl_siding'
    ) THEN 'plastic'
    WHEN lower(trim(element_at(tags, 'building:facade'))) IN (
        'stone',
        'limestone',
        'sandstone',
        'granite',
        'marble',
        'tiles'
    ) THEN 'stone'
    WHEN lower(trim(element_at(tags, 'building:facade'))) IN (
        'timber_framing',
        'traditional'
    ) THEN 'timber_framing'
    WHEN lower(trim(element_at(tags, 'building:facade'))) IN (
        'wood',
        'reed',
        'wattle_and_daub',
        'timber_planks',
        'wood/masonry',
        'wood/bamboo',
        'bamboo'
    ) THEN 'wood'

    -- when building:facade isn't usable then try building:facade:material

    WHEN lower(trim(element_at(tags, 'building:facade:material'))) IN (
        'brick',
        'slate',
        'ladrillos',
        'masonry',
        'silicate brick',
        'bricks',
        'unburnt brick',
        'silicate_brick',
        'brick_block',
        'muddy_brick'
    ) THEN 'brick'
    WHEN lower(trim(element_at(tags, 'building:facade:material'))) IN (
        'cement_block',
        'block',
        'cement block',
        'cement_blocks',
        'cement blocks'
    ) THEN 'cement_block'
    WHEN lower(trim(element_at(tags, 'building:facade:material'))) IN (
        'clay',
        'mud',
        'rammed_earth',
        'loam',
        'earth',
        'grass',
        'pressed_soil_blocks'
    ) THEN 'clay'
    WHEN lower(trim(element_at(tags, 'building:facade:material'))) IN (
        'concrete',
        'concrete masonry unit',
        'cement',
        'concrete_reinforced',
        'reinforced_concrete'
    ) THEN 'concrete'
    WHEN lower(trim(element_at(tags, 'building:facade:material'))) IN (
        'glass',
        'mirror'
    ) THEN 'glass'
    WHEN lower(trim(element_at(tags, 'building:facade:material'))) IN (
        'metal',
        'steel',
        'metal_plates',
        'tin',
        'iron_sheet',
        'copper',
        'metal_sheet',
        'ironsheets',
        'panel',
        'aluminium'
    ) THEN 'metal'
    WHEN lower(trim(element_at(tags, 'building:facade:material'))) IN (
        'plaster',
        'plastered',
        'hard'
    ) THEN 'plaster'
    WHEN lower(trim(element_at(tags, 'building:facade:material'))) IN (
        'plastic',
        'vinyl',
        'plastic_sheeting',
        'composite',
        'vinyl_siding'
    ) THEN 'plastic'
    WHEN lower(trim(element_at(tags, 'building:facade:material'))) IN (
        'stone',
        'limestone',
        'sandstone',
        'granite',
        'marble',
        'tiles'
    ) THEN 'stone'
    WHEN lower(trim(element_at(tags, 'building:facade:material'))) IN (
        'timber_framing',
        'traditional'
    ) THEN 'timber_framing'
    WHEN lower(trim(element_at(tags, 'building:facade:material'))) IN (
        'wood',
        'reed',
        'wattle_and_daub',
        'timber_planks',
        'wood/masonry',
        'wood/bamboo',
        'bamboo'
    ) THEN 'wood'
    ELSE NULL
END
