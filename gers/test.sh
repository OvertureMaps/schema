echo "Testing Registry Schema"
jv registry/registry_schema.yaml registry/examples/*

echo "Testing Bridge File Schema"
jv bridge_file/bridge_file_schema.yaml bridge_file/examples/*
