"""
Releasing examples in YAML format is better than JSON because YAML allows for commenting.

JSON, however, is a more common format. This script helps maintains the `examples_json` directory
remain in sync with the `examples` directory.

The `examples_json` directory will contain JSON versions of all of the YAML examples. Any JSON examples
that do not exist as YAML in the `examples` directory will be created.

Features in the `examples_json` directory will always be overwritten by their YAML versions.

Usage: python3 utils/sync_yaml_and_json_examples.py

"""

import json, yaml, glob, datetime
from os import makedirs, path

class YAML_to_JSON():

    def load_yaml_examples(self):
        self.yaml_examples = yaml_examples = glob.glob('examples/**/*.yaml', recursive=True)


    def load_json_examples(self):
        self.json_examples = glob.glob('examples_json/**/*.json', recursive=True)


    def ensure_json_mirrors_yaml(self):
        """
            For each YAML example, ensure there is a corresponding JSON version.
            This will always over-write the JSON example from the YAML.
        """
        for example in self.yaml_examples:
            parts = example.split("/")
            json_path = ['examples_json'] + parts[1:-1] + [parts[-1].replace(".yaml",".json")]

            # Ensure path exists
            makedirs("/".join(json_path[:-1]), exist_ok=True)

            # Read YAML
            feature = yaml.safe_load(open(example,'r'))

            # Progress
            print(f"\t{parts[-1]} --> {json_path[-1]}")

            json.dump(feature, open("/".join(json_path),'w'), indent=4, cls=DateTimeEncoder)


    def add_extra_json_samples_to_yaml(self):
        """
            If any extra JSON examples exist that are not in the YAML, this creates a YAML version.
            Future JSON examples will be created from this YAML version when the previous function runs.
        """
        for example in self.json_examples:
            parts = example.split("/")
            yaml_path = ['examples'] + parts[1:-1] + [parts[-1].replace(".json",".yaml")]

            if path.exists("/".join(yaml_path)):
                print(f"Found YAML version of {parts[-1]}")
            else:
                print(f"{parts[-1]} has no corresponding YAML entry, will make it now")

                # Ensure path exists
                makedirs("/".join(yaml_path[:-1]), exist_ok=True)

                # Load JSON
                feature = json.load(open(example,'r'))

                # Write YAML
                with open("/".join(yaml_path),'w') as outFile:
                    outFile.write(yaml.dump(feature))

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()



if __name__=='__main__':

    runner = YAML_to_JSON()

    # Load all examples
    runner.load_yaml_examples()
    runner.load_json_examples()

    # Ensure JSON mirrors YAML
    runner.ensure_json_mirrors_yaml()

    # Add extra JSON samples to YAML
    runner.add_extra_json_samples_to_yaml()