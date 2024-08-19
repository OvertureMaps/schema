CASE
    WHEN lower(trim(element_at(tags, 'roof:material'))) IN (
        'asphalt_shingle',
        'asphalt',
        'concrete slab',
        'concrete',
        'rcc'
    ) THEN 'concrete'
    WHEN lower(trim(element_at(tags, 'roof:material'))) IN (
        'copper'
    ) THEN 'copper'
    WHEN lower(trim(element_at(tags, 'roof:material'))) IN (
        'a/c sheets',
        'asbestos',
        'eternit'
    ) THEN 'eternit'
    WHEN lower(trim(element_at(tags, 'roof:material'))) IN (
        'glass',
        'acrylic_glass'
    ) THEN 'glass'
    WHEN lower(trim(element_at(tags, 'roof:material'))) IN (
        'grass',
        'plants',
        'roof_greening'
    ) THEN 'grass'
    WHEN lower(trim(element_at(tags, 'roof:material'))) IN (
        'gravel'
    ) THEN 'gravel'
    WHEN lower(trim(element_at(tags, 'roof:material'))) IN (
        'corrugated_iron_sheets',
        'corrugated_iron',
        'corrugated',
        'iron_sheet',
        'metal_sheet',
        'metal:sheet',
        'metal',
        'tin',
        'zinc',
        'zink'
    ) THEN 'metal'
    WHEN lower(trim(element_at(tags, 'roof:material'))) IN (
        'plastic',
        'composite'
    ) THEN 'plastic'
    WHEN lower(trim(element_at(tags, 'roof:material'))) IN (
        'roof_tiles',
        'tile',
        'tiles',
        'roof-tiles',
        'clay_tiles'
    ) THEN 'roof_tiles'
    WHEN lower(trim(element_at(tags, 'roof:material'))) IN (
        'brick',
        'marble',
        'sandstone',
        'slate',
        'stone'
    ) THEN 'slate'
    WHEN lower(trim(element_at(tags, 'roof:material'))) IN (
        'solar_panels'
    ) THEN 'solar_panels'
    WHEN lower(trim(element_at(tags, 'roof:material'))) IN (
        'tar_paper'
    ) THEN 'tar_paper'
    WHEN lower(trim(element_at(tags, 'roof:material'))) IN (
        'cadjan_palmyrah_straw',
        'thatch'
    ) THEN 'thatch'
    WHEN lower(trim(element_at(tags, 'roof:material'))) IN (
        'wood',
        'wooden'
    ) THEN 'wood'
    ELSE NULL
END
