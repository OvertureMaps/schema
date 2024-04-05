/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docs: [
    /*
    Overview
    */
    {
      type: 'category',
      label: 'Overview',
      collapsed: false,
      items: [
        {
          type: 'doc',
          id: 'overview/index'
        },
        {
          type: 'category',
          label: 'Feature Model',
          link: {
            type: 'doc',
            id: 'overview/feature-model/index'
          },
          collapsed: false,
          items: [
            // 'overview/feature-model/geojson',
            'overview/feature-model/names',
            'overview/feature-model/scoping-rules',
          ]
        }

      ]
    },
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
              'reference/admins/administrative-boundary',
              'reference/admins/locality',
              'reference/admins/locality-area',
          ]
        },
        {
          type: 'category',
          label: 'base',
          collapsed: false,
          items: [
              'reference/base/land',
              'reference/base/land-use',
              'reference/base/water',
          ]
        },
        {
          type: 'category',
          label: 'buildings',
          collapsed: false,
          items: [
            'reference/buildings/building',
            'reference/buildings/part'
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
          label: 'divisions',
          collapsed: false,
          items: [
              'reference/divisions/boundary',
              'reference/divisions/division',
              'reference/divisions/division_area',
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
  ]
};

module.exports = sidebars;
