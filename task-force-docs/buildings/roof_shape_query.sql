
    WHEN lower(trim(element_at(tags, 'roof:shape'))) IN (
        'dome'
    ) THEN 'dome'
    WHEN lower(trim(element_at(tags, 'roof:shape'))) IN (
        'flat'
    ) THEN 'flat'
    WHEN lower(trim(element_at(tags, 'roof:shape'))) IN (
        'gambrel'
    ) THEN 'gambrel'
    WHEN lower(trim(element_at(tags, 'roof:shape'))) IN (
        'gabled',
        'pitched',
        'crosspiched',
        'double_pitch',
        'gabled_height_moved',
        'hip-and-gabled',
        'gable',
        'gabled_row',
        'round_gabled',
        'dutch_gabled',
        'monopitch',
        '2 faces (pitched)',
        'gabeled',
        'gabed',
        'gambled',
        'double_gabled',
        'gabred',
        'cross_gabled'
    ) THEN 'gabled'
    WHEN lower(trim(element_at(tags, 'roof:shape'))) IN (
        'half-hipped'
    ) THEN 'half_hipped'
    WHEN lower(trim(element_at(tags, 'roof:shape'))) IN (
        'hipped',
        'side_hipped',
        'hyped',
        'equal_hipped',
        '4 faces (hipped)',
        'side_half-hipped',
        'side_half_hipped'
    ) THEN 'hipped'
    WHEN lower(trim(element_at(tags, 'roof:shape'))) IN (
        'mansard'
    ) THEN 'mansard'
    WHEN lower(trim(element_at(tags, 'roof:shape'))) IN (
        'onion',
        'cone',
        'conical'
    ) THEN 'onion'
    WHEN lower(trim(element_at(tags, 'roof:shape'))) IN (
        'pyramidal'
    ) THEN 'pyramidal'
    WHEN lower(trim(element_at(tags, 'roof:shape'))) IN (
        'round'
    ) THEN 'round'
    WHEN lower(trim(element_at(tags, 'roof:shape'))) IN (
        'saltbox',
        'double_saltbox',
        'quadruple_saltbox'
    ) THEN 'saltbox'
    WHEN lower(trim(element_at(tags, 'roof:shape'))) IN (
        'sawtooth'
    ) THEN 'sawtooth'
    WHEN lower(trim(element_at(tags, 'roof:shape'))) IN (
        'skillion',
        'lean_to',
        'triple_skillion'
    ) THEN 'skillion'
    WHEN lower(trim(element_at(tags, 'roof:shape'))) IN (
        'spherical'
    ) THEN 'spherical'
    ELSE NULL
END
