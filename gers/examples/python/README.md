# GERS Sidecar Match Example

## Context

Consumers of geospatial data sets usually need to solve a complex and costly process of matching them.
A data set that also has GERS IDs can be easily used to augment the Overture data set itself, or other data sets that also have GERS IDs via simple join by id.

Because Overture data sets are modeled and produced with prioritizing for stability of its identifiers (GERS IDs) over time, and the cost of matching being offset to the owner of the data sets, the consumers of data sets with GERS IDs can conflate, evaluate and onboard such feeds much cheaper and faster.

## Purpose

Matching a geospatial data set with overture (or any other) data set is a common problem and many solutions exist for this, from generic to highly specialized for particular data types. 

Depending on the match requirements, this can be achieved with a open source or commercial tools or services, with a few click or couple of lines of code or with large scale distributed system with complex match logic. 

Main purpose is to provide an example of how to start exploring a data set's compatibility with overture data set and to find GERS IDs that correspond to its features.

## Example
[Snap GPS traces to overture roads](MATCH_TRACES.md)

