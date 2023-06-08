/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docs: [
    'index',
    {
      type: 'category',
      label: 'Core Concepts',
      link: {
        type: 'generated-index',
        slug: '/concepts',
      },
      collapsed: false,
      items: [
          'concepts/feature',
          'concepts/theme',
          'concepts/gers',
      ]
    },
    {
      type: 'category',
      label: 'Theme Concepts',
      link: {
        type: 'generated-index',
        slug: '/themes',
      },
      collapsed: true,
      items: [
        'themes/admins/admins',
        'themes/buildings/building',
        'themes/places/place',
        {
          type: 'category',
          label: 'Transportation',
          link: {
            type: 'doc',
            id: 'themes/transportation/index',
          },
          collapsed: true,
          items: [
            //'themes/transportation/topology',
            //'themes/transportation/scoped-properties',
            //'themes/transportation/travel-modes',
            /*{
              type: 'category',
              label: 'Roads',
              link: {
                type: 'doc',
                id: 'themes/transportation/roads/index'
              },
              collapsed: true,
              items: [
                'themes/transportation/roads/lanes'
              ],
            }*/
          ]
        }
      ]
    },
    {
      type: 'category',
      label: 'Schema Reference',
      link: {
        type: 'generated-index',
        slug: '/reference',
      },
      collapsed: true,
      items: [
        {
          type: 'category',
          label: 'admins',
          link: {
            type: 'generated-index',
          },
          collapsed: false,
          items: [
              'reference/admins/administrativeBoundary',
              'reference/admins/administrativeLocality',
              'reference/admins/namedLocality',
          ]
        },
        {
          type: 'category',
          label: 'buildings',
          link: {
            type: 'generated-index',
          },
          collapsed: false,
          items: [
            'reference/buildings/building',
          ]
        },
        {
          type: 'category',
          label: 'places',
          link: {
            type: 'generated-index',
          },
          collapsed: false,
          items: [
            'reference/places/place',
          ]
        },
        {
          type: 'category',
          label: 'transportation',
          link: {
            type: 'generated-index',
          },
          collapsed: false,
          items: [
            'reference/transportation/connector',
            'reference/transportation/segment',
          ]
        },
      ]
    }
  ],
};

module.exports = sidebars;
