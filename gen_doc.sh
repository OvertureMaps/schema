
#First, convert the YAML to JSON
SCHEMA_DIR="schema"
JSON_PATH="documentation_website/static/jsonschema/"
JSON_PATH_MD="/tmp/jsonschema"

for f in $(find $SCHEMA_DIR -name '*.yaml'); do
    echo $f;

    DIR=$(dirname "${f}")

    FILE=$(basename "${f}")

    # Create .json files that can be ingested direclty by the docusaurus plugin.
    # Issue: the refs don't technically work because the refs in the file are looking for `.yaml` files.
    mkdir -p $JSON_PATH/$DIR;
    yq $f -o json > $JSON_PATH/$DIR/${FILE%.yaml}.json

    # Create JSON-formatted files with the incorrect extension ".yaml" that can be read by jsonschema2md
    # because the `$ref` paths do exist.
    mkdir -p $JSON_PATH_MD/$DIR;
    yq $f -o json > $JSON_PATH_MD/$DIR/$FILE
done

# Use @adobe/jsonschema2md to autogenerate markdown from our schema
jsonschema2md --input=$JSON_PATH_MD/schema \
              --out=documentation_website/docs/jsonschema2md/ \
              --schema-extension=yaml \
              --schema-out=-
