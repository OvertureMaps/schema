/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docs: [
    'index',
    /*
      Themes
    */
    {
      type: 'category',
      label: 'Schema Themes',
      link: {
        type: 'doc',
        id: 'themes/themes'
      },
      collapsed: true,
      items: [
        {
          type: 'doc',
          id: 'themes/admins/admins',
          label: 'Admins'
        },
        'themes/base/index',
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
            'themes/transportation/shape-connectivity',
            'themes/transportation/scoping-rules',
            'themes/transportation/roads',
            'themes/transportation/travel-modes',
          ]
        }
      ]
    },
    /*
      Schema Reference
    */
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
          collapsed: false,
          items: [
              'reference/admins/administrativeBoundary',
              'reference/admins/locality',
          ]
        },
        {
          type: 'category',
          label: 'base',
          collapsed: false,
          items: [
              'reference/base/land',
              'reference/base/landUse',
              'reference/base/water',
          ]
        },
        {
          type: 'category',
          label: 'buildings',
          collapsed: false,
          items: [
            'reference/buildings/building',
          ]
        },
        {
          type: 'category',
          label: 'places',
          collapsed: false,
          items: [
            'reference/places/place',
          ]
        },
        {
          type: 'category',
          label: 'transportation',
          collapsed: false,
          items: [
            'reference/transportation/connector',
            'reference/transportation/segment',
          ]
        }
      ]
    }
  ],

  gers: [
    {
      type: 'category',
      label: 'Global Entity Reference System',
      collapsed: true,
      items: [
        {
          type: 'doc',
          id:'gers/gers',
          label: 'Overview'
        },
        'gers/scenarios',
        'gers/terminology'
      ]
    },
  ]
};

module.exports = sidebars;
