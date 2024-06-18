Global Entity Reference System (GERS)
====


## What is GERS?
Overture's Global Entity Reference System (GERS) is a system of structuring, encoding, and referencing map data to a shared universal reference. This will provide a mechanism to easily conflate datasets from different providers based on a specific GERS ID assigned to each feature.

For example, two geospatial datasets that contain a footprint representing the Empire State Building can be easily conflated because both footprints will contain the same GERS ID, referring to the entity: "A Polygonal represention of the footprint of New York's Empire State Building"

A GERS entity is defined by a GERS ID. These IDs are useful to anyone looking to match their data with Overture data. These IDs are stable (within reason) and unique.

## The main components of GERS are:

1. An ever-growing set of _entities_ that are a shared reference for a `thing` in the world, where a `thing` could be a segment of road, a city, a store, a building, etc. Multiple _features_ in the Overture corpus can and will share the same GERS ID if they are representing the same `thing`.

2.  GERS IDs are stable (with a reasonable tolerance of error). Across multiple versions of Overture data, efforts will be taken to ensure the mapping of a real world `thing` to a GERS ID remains consistent. When stability is not possible, traceability will be provided. Examples:
    - A single road segment is bisected by a new road and becomes 2 road segments: 1 GERS ID -> 2 New GERS IDs
    - 1 large building footprint on the map is determined to be 4 smaller buildings when a higher resolution dataset becomes available: 1 GERS ID -> 4 new GERS IDs
    - A building is shifted 10m west when higher resolution imagery is made available: GERS ID is preserved for that feature.

### Obtaining a GERS ID
There are two ways to obtain an associated GERS identifier for one's data:

1. Join Overture, in which case we will generate new GERS IDs or associate existing IDs for your dataset as it relates to the current Overture corpus (of which your data is now a part).
2. Conflate your data against the current Overture map, identifying matches between existing map objects with a GERS ID and your own data.

In option 2, new GERS IDs cannot be obtained for entities in one's data that do not already exist in the map. Only features in the Overture data corpus can be assigned a new GERS ID. See the _Scenarios_ below for more detailed examples of how and when these sitautions arise.


## Why do we need GERS?

Conflation is hard, expensive, and messy. Each provider has different ways to model and store data, particularly across layers, and consumers have to develop their own tools and approaches to try to identify where each dataset is describing different attributes of the same thing. GERS enables providers to register their data and add GERS-IDs to unambiguously say what `thing` in the world they are adding attributes for.

One of the biggest challenges to map data commoditization is the cost and effort of integrating semantic map data into a consolidated data product. There is a growing ecosystem of data collectors through sensors carried by individuals and integrated into cars that collect observations of the world, and the Intelligent Edge converting those signals into semantic data. However, combining that semantic data into a single product used to power market and global scale services does not have an industry solution at this time.

This means that for today, building a dataset from different providers requires expensive manual work and custom solutions. Which increases the minimum cost of acquiring data, adds a significant amount of time between acquiring data and using it to improve services, and locks in provider-consumer relationships due to the expense of replacing data and developing a new custom solution.

By building a process and tools for a Global Entity Reference System, providers and consumers of data can be sure that the data they are exchanging is compatible with and/or can augment other referenced datasets. For example, this will allow providers of traffic data to not have to collect road data, they can just register their traffic to the GERS for road features, so anyone who has GERS road features can consume their traffic data. In a ‘Divisions’ example, a producer of detailed demographic data does not also need to collect a set of States/Counties/Cities, they can ‘register’ their demographic elements to the State/County/City feature, so that anyone who purchases/acquires their dataset can join on GERS registered States/Counties/City features.

## GERS Use-Case Scenarios:

### Live Traffic Data Provider

A company providing live traffic data operates by ingesting sensor data and then conflating, cleaning, and calculating traffic density for a variety of locations through proprietary methods. Ultimately, they provide a data feed of live traffic conditions that customers subscribe to for a monthly access fee.

**Before GERS + Overture**: This company maintains a version of the OpenStretMap road network to which they associate their traffic density information. The data-feed product is made of GeoJSON features, each with a LineString geometry representing a segment of road (from OSM) and properties including a timestamp and traffic information along that section of road. Using OSM is preferred because the geometries in the data feed will match road segment geometries for any customer using OSM. However, a more computationally expensive geospatial match operation is required to associate the traffic information with the road network.

**With GERS + Overture**: The company uses the Overture road network internally. When they associate their traffic information to a road segment, they can publish the data feed with a GERS ID that represents the given road segment. Consumers that are also using Overture can then match this data by GERS ID to the Overture road segment, not needing to perform any geospatial computation. Additionally, even the geometry of the road segment could be omitted from the feed, since the ID will match for any customer also using the Overture road network.

**What if the company has proprietary (better) road segment data extracted from their sensor network that they do not / cannot share?**

Because these road segments are not shared with Overture, they cannot be assigned GERS-IDs. A GERS-ID is of little value to these segments because they do not exist in other datasets, so conflating or matching them is meaningless.

However, by sharing _just the new road segment_ geometries with Overture (not the entire proprietary traffic feed), Overture will add it to the Overture corpus and generate GERS IDs accordingly. The Overture road network will be improved and 100% of the company's data feed can become GERS-enabled.

### Place Enrichment
Venues – both private and public – are often an atomic unit in data environments. For example:

- Businesses organize customer records based on home addresses.
- Municipalities map property information and status by parcel identifiers.
- Insurance companies use various building identifiers to organize policy information.
- Retailers organize analyze market opportunities and challenges by their own and competitive retail outlets.
- Delivery companies optimize services by destination address.

Despite these common use cases, location is under-utilized as an organizing mechanism for data, applications, and analytics. Addresses are often inconsistent, messy, or simply wrong. Coordinate pairs are precise but often inaccurate and can be difficult to cluster correctly. GIS infrastructure on the whole is often out of reach for many teams or is maintained by a small, specialty group at the fringes of the organization.

If location data can be associated with easy-to-use standard identifiers, data owners and consumers can use locations as a common denominator data element that facilitates joins, enrichment, and data sharing. GERS has the opportunity to make location a connector as valuable as phone numbers or email addresses, unlocking the incredible value of complex GIS data that is currently beyond the reach of most teams.

#### Scenario
A data analyst at a pet-focused retail company is evaluating a metropolitan area in order to understand supply and demand, relative to their offerings, in the region. In their environment they have 1st party customer data organized by delivery address, addresses for their own retail locations, and a list of potential store locations provided by their real estate team. Their data infrastructure team has staged an Overture dataset in their environment, which they use as a foundational ground truth for the region. The company's executive team has asked the data analyst to review the potential store locations, recommend the most valuable sites for new stores, and model the expected market impact if they opened a new store at each site.

The data analyst plans on using Overture's GERS to quickly onboard necessary external data for their analysis.

- They match customer residences and store locations to GERS by conflating street addresses with venues in their local Overture basemap.
- They request retail foot traffic data and residential demographic data from external vendors, specifying the data should be organized by GERS ID.
- The external data vendors maintain a version of their data products keyed off GERS ID (matched via a conflation pipeline that accounts for street address, business name, and coordinate pair), which they provide to the requesting analyst.
- The analyst is able to quickly ingest and join the external datasets in their own environment, without relying on their data infrastructure team, thanks to the simplicity of joining using consistent GERS identifiers.
- The analyst performs their work, taking into account their current customer base, market potential, competitive footprint, and more.

This is ad-hoc enrichment; enrichment that occurs within the confines of a single project. However, there are many datasets this company may choose to continually subscribe to which will be managed by the data ops or infrastructure teams. GERS has significant benefits in this scenario as well as it reduces the time to usage, allows for easy updates (vendors simply ship diff files keyed to GERS ID), and facilitates the sharing of data both internally and externally.



---

## Terminology
|  Term | Description |
| - | - |
| GERS ID| A unique ID representing a real-world entity, such as a building, road segment, parking lot, or even a park bench. |
| Contributed Dataset | A dataset maintained by Overture that a foundation member has contributed to Overture. These datasets are converted to the appropriate Overture schema for their type. For GERS-enabled layers (buildings, transportation, etc.), data is given a GERS ID. These data are now forever part of the Overture Corpus|
| Overture Dataset | An open dataset that is registered with Overture and thereby is included in GERS, but not maintained by Overture. |
| Outside Dataset / Proprietary Data | A dataset outside of Overture is proprietary data that a company or individual does not want to make fully open, but desires to associate with Overture data. <br><br>The dataset owner can conflate their data against the current Overture map to identify any existing GERS IDs that map to their own data, but they cannot generate new GERS IDs for entities that do not already exist in the Overture corpus. |
