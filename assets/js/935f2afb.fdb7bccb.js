"use strict";(self.webpackChunkoverture_schema=self.webpackChunkoverture_schema||[]).push([[581],{5610:e=>{e.exports=JSON.parse('{"pluginId":"default","version":"current","label":"Next","banner":null,"badge":false,"noIndex":false,"className":"docs-version-current","isLast":true,"docsSidebars":{"docs":[{"type":"category","label":"Overview","collapsed":false,"items":[{"type":"link","label":"Introduction","href":"/","docId":"overview/index","unlisted":false},{"type":"category","label":"Feature Model","collapsed":false,"items":[{"type":"link","label":"Names","href":"/overview/feature-model/names","docId":"overview/feature-model/names","unlisted":false},{"type":"link","label":"Scoping Rules","href":"/overview/feature-model/scoping-rules","docId":"overview/feature-model/scoping-rules","unlisted":false}],"collapsible":true,"href":"/overview/feature-model/"}],"collapsible":true},{"type":"category","label":"Schema Themes","collapsed":true,"items":[{"type":"link","label":"Admins","href":"/themes/admins/","docId":"themes/admins/admins","unlisted":false},{"type":"link","label":"Base","href":"/themes/base/","docId":"themes/base/index","unlisted":false},{"type":"link","label":"Buildings","href":"/themes/buildings/building","docId":"themes/buildings/building","unlisted":false},{"type":"link","label":"Places","href":"/themes/places/place","docId":"themes/places/place","unlisted":false},{"type":"category","label":"Transportation","collapsed":true,"items":[{"type":"link","label":"Shape and connectivity","href":"/themes/transportation/shape-connectivity","docId":"themes/transportation/shape-connectivity","unlisted":false},{"type":"link","label":"Roads","href":"/themes/transportation/roads","docId":"themes/transportation/roads","unlisted":false},{"type":"link","label":"Travel modes","href":"/themes/transportation/travel-modes","docId":"themes/transportation/travel-modes","unlisted":false}],"collapsible":true,"href":"/themes/transportation/"}],"collapsible":true,"href":"/themes/"},{"type":"category","label":"Schema Reference","collapsed":true,"items":[{"type":"category","label":"admins","collapsed":false,"items":[{"type":"link","label":"administrative boundary","href":"/reference/admins/administrative-boundary","docId":"reference/admins/administrative-boundary","unlisted":false},{"type":"link","label":"locality","href":"/reference/admins/locality","docId":"reference/admins/locality","unlisted":false},{"type":"link","label":"locality area","href":"/reference/admins/locality-area","docId":"reference/admins/locality-area","unlisted":false}],"collapsible":true},{"type":"category","label":"base","collapsed":false,"items":[{"type":"link","label":"land","href":"/reference/base/land","docId":"reference/base/land","unlisted":false},{"type":"link","label":"land use","href":"/reference/base/land-use","docId":"reference/base/land-use","unlisted":false},{"type":"link","label":"water","href":"/reference/base/water","docId":"reference/base/water","unlisted":false}],"collapsible":true},{"type":"category","label":"buildings","collapsed":false,"items":[{"type":"link","label":"building","href":"/reference/buildings/building","docId":"reference/buildings/building","unlisted":false},{"type":"link","label":"part","href":"/reference/buildings/part","docId":"reference/buildings/part","unlisted":false}],"collapsible":true},{"type":"category","label":"places","collapsed":false,"items":[{"type":"link","label":"place","href":"/reference/places/place","docId":"reference/places/place","unlisted":false}],"collapsible":true},{"type":"category","label":"transportation","collapsed":false,"items":[{"type":"link","label":"connector","href":"/reference/transportation/connector","docId":"reference/transportation/connector","unlisted":false},{"type":"link","label":"segment","href":"/reference/transportation/segment","docId":"reference/transportation/segment","unlisted":false}],"collapsible":true}],"collapsible":true,"href":"/reference"}]},"docs":{"gers/gers":{"id":"gers/gers","title":"Global Entity Reference System","description":"Overview of GERS"},"gers/scenarios":{"id":"gers/scenarios","title":"Scenarios","description":"Live Traffic Data"},"gers/terminology":{"id":"gers/terminology","title":"Terminology","description":"|  Term | Description |"},"overview/feature-model/geojson":{"id":"overview/feature-model/geojson","title":"GeoJSON mental model","description":"Coming Soon"},"overview/feature-model/index":{"id":"overview/feature-model/index","title":"Feature Model","description":"Key Concepts","sidebar":"docs"},"overview/feature-model/names":{"id":"overview/feature-model/names","title":"Names","description":"Common Names Schema","sidebar":"docs"},"overview/feature-model/scoping-rules":{"id":"overview/feature-model/scoping-rules","title":"Scoping Rules","description":"In the real-world, many facts and rules affecting transportation have","sidebar":"docs"},"overview/index":{"id":"overview/index","title":"Introduction","description":"Introduction to the Overture Map Foundation\'s documentation","sidebar":"docs"},"reference/admins/administrative-boundary":{"id":"reference/admins/administrative-boundary","title":"administrative boundary","description":"Administrative boundaries are borders surrounding administrative localities.","sidebar":"docs"},"reference/admins/locality":{"id":"reference/admins/locality","title":"locality","description":"Localities are populated areas that are named.","sidebar":"docs"},"reference/admins/locality-area":{"id":"reference/admins/locality-area","title":"locality area","description":"Adds land or maritime area polygon to locality.","sidebar":"docs"},"reference/base/land":{"id":"reference/base/land","title":"land","description":"Features in the land theme come from OpenStreetMap features with the natural tag.","sidebar":"docs"},"reference/base/land-use":{"id":"reference/base/land-use","title":"land use","description":"Features in the land use theme come primarily from OpenStreetMap features containing the landuse tag.","sidebar":"docs"},"reference/base/water":{"id":"reference/base/water","title":"water","description":"Features in the water theme are from OpenStreetMap features with the natural=water tag.","sidebar":"docs"},"reference/buildings/building":{"id":"reference/buildings/building","title":"building","description":"Buildings are human-made structures with roofs or interior spaces that are permanently or semi-permanently in one place (OSM building definition).","sidebar":"docs"},"reference/buildings/part":{"id":"reference/buildings/part","title":"part","description":"Geometry Type","sidebar":"docs"},"reference/places/place":{"id":"reference/places/place","title":"place","description":"A place is point of interest in the real world.","sidebar":"docs"},"reference/transportation/connector":{"id":"reference/transportation/connector","title":"connector","description":"Connectors create physical connections between segments.","sidebar":"docs"},"reference/transportation/segment":{"id":"reference/transportation/segment","title":"segment","description":"Segments are paths which can be traveled by people or objects.","sidebar":"docs"},"themes/admins/admins":{"id":"themes/admins/admins","title":"Admins","description":"The Overture admins theme includes entities that describe named localities in the real world including settlements, cities, regions, provinces and countries. The current version of the schema does not support the modeling of multiple geo-political views. In future schema versions, Overture will have support for:","sidebar":"docs"},"themes/base/index":{"id":"themes/base/index","title":"Base","description":"The Overture base theme provides the land and water features that are necessary to render a complete basemap. These features are currently derived from the Daylight Earth Tables schema and include the Daylight Coastlines.","sidebar":"docs"},"themes/buildings/building":{"id":"themes/buildings/building","title":"Buildings","description":"The Overture buildings theme describes human-made structures with roofs or interior spaces that are permanently or semi-permanently in one place (source: OSM building definition).","sidebar":"docs"},"themes/places/place":{"id":"themes/places/place","title":"Places","description":"The places theme contains datasets with point representations of real-world facilities, services, businesses or amenities.","sidebar":"docs"},"themes/themes":{"id":"themes/themes","title":"Schema Themes","description":"","sidebar":"docs"},"themes/transportation/index":{"id":"themes/transportation/index","title":"Transportation","description":"Overture\'s transportation layer is the collection of features and attributes that describe the infrastructure and conventions of how people and objects travel around the world. Transportation data includes highways, footways, cycleways, railways, ferry routes and public transportation.","sidebar":"docs"},"themes/transportation/roads":{"id":"themes/transportation/roads","title":"Roads","description":"In the Overture transportation theme, a road is any kind of road,","sidebar":"docs"},"themes/transportation/shape-connectivity":{"id":"themes/transportation/shape-connectivity","title":"Shape and connectivity","description":"The Overture transportation theme captures the physical shape and connectivity","sidebar":"docs"},"themes/transportation/travel-modes":{"id":"themes/transportation/travel-modes","title":"Travel modes","description":"In the real world, a travel mode can be thought of intuitively as a way","sidebar":"docs"}}}')}}]);