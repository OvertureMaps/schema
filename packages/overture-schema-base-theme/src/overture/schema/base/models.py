from pydantic import BaseModel

from overture.schema.base.types import SourceTags
from overture.schema.core.types import WikidataId


class SourcedFromOpenStreetMap(BaseModel):
    source_tags: SourceTags | None = None
    wikidata: WikidataId | None = None
