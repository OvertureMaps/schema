/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docs: [
    'index',
    // {
    //   type: 'category',
    //   label: 'Core Concepts',
    //   link: {
    //     type: 'generated-index',
    //     slug: '/concepts',
    //   },
    //   collapsed: false,
    //   items: [
    //       'concepts/feature',
    //       'concepts/theme',
    //       'concepts/gers',
    //   ]
    // },
    /*
      GERS
    {
      type: 'category',
      label: 'Global Entity Reference System',
      // link: {
      //   type: 'doc',
      //   id: 'gers/gers'
      // },
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
    // */
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
          // link: {
          //   type: 'generated-index',
          // },
          collapsed: false,
          items: [
              'reference/admins/administrativeBoundary',
              'reference/admins/locality',
          ]
        },
        {
          type: 'category',
          label: 'buildings',
          // link: {
          //   type: 'generated-index',
          // },
          collapsed: false,
          items: [
            'reference/buildings/building',
          ]
        },
        {
          type: 'category',
          label: 'places',
          // link: {
          //   type: 'generated-index',
          // },
          collapsed: false,
          items: [
            'reference/places/place',
          ]
        },
        {
          type: 'category',
          label: 'transportation',
          // link: {
          //   type: 'generated-index',
          // },
          collapsed: false,
          items: [
            'reference/transportation/connector',
            'reference/transportation/segment',
          ]
        },
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
