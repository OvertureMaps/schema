using Microsoft.Geospatial.Data.Cosmos.GeoSerializer;
using YamlDotNet.Serialization.NamingConventions;

namespace Overture.Schema
{
    public class OvertureSchema
    {
        public List<EntityType> EntityTypes { get; set; }
        public List<EntityNameType> EntityNameTypes { get; set; }
        public List<Language> Languages { get; set; }
        public List<DataType> DataTypes { get; set; }
        public List<Property> EntityProperties { get; set; }
        public List<PolygonType> PolygonTypes { get; set; }
        public List<LineType> LineTypes { get; set; }
        public List<NodeType> NodeTypes { get; set; }
        public List<RelationshipType> TopologyRelationships { get; set; }
        public List<RelationshipType> EntityRelationships { get; set; }
        public List<RelationshipType> EntityNameTypeRelationships { get; set; }
        public List<RelationshipType> EntityPropertyRelationships { get; set; }
        public List<RelationshipType> EntityGeometryRelationships { get; set; }
        
        public string ToJson(bool indented = false)
        {
            return SerializeUtils.ToJson(this, indented);
        }

        public string ToXml(bool indented = false)
        {
            return SerializeUtils.ToXml(this, indented);
        }

        public string ToYaml(bool inlineStyleLists = false)
        {
            return SerializeUtils.ToYaml(this, inlineStyleLists: inlineStyleLists, namingConvention: PascalCaseNamingConvention.Instance);
        }
    }

    public class EntityType
    {
        public string Name { get; set; }
        public string Description { get; set; }
        public string ParentEntityType { get; set; }
    }

    public class EntityNameType
    {
        public string Type { get; set; }
        public string Description { get; set; }
    }

    public class Language
    {
        public string LanguageCode { get; set; }
        public string LanguageName { get; set; }
        public string Script { get; set; }
    }

    public class PolygonType
    {
        public string Name { get; set; }
        public string Description { get; set; }
        public string ParentPolygonType { get; set; }
    }

    public class LineType
    {
        public string Name { get; set; }
        public string Description { get; set; }
        public string ParentLineType { get; set; }
    }

    public class NodeType
    {
        public string Name { get; set; }
        public string Description { get; set; }
        public string ParentNodeType { get; set; }
    }

    public class RelationshipKey
    {
        public string FromClass { get; set; }
        public string FromName { get; set; }
        public string ToClass { get; set; }
        public string ToName { get; set; }
    }

    public class Cardinality
    {
        public string Name { get; set; }
        public uint Min { get; set; }
        public uint Max { get; set; }
    }

    public class RelationshipType
    {
        public string Name { get; set; }
        public string Description { get; set; }
        public Dictionary<RelationshipKey, Cardinality> Relationships { get; set; }
    }

    public class Property
    {
        public string Name { get; set; }
        public string Description { get; set; }
        public DataType DataType { get; set; }
        public List<EnumValue> EnumValues { get; set; }
    }

    public class DataType
    {
        public string Name { get; set; }
        public string Description { get; set; }
    }

    public class EnumValue
    {
        public string Name { get; set; }
        public string Description { get; set; }
    }
}
