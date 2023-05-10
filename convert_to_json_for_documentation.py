# Read the YAML docs, replace .yaml files with .json and then write out json

import yaml, sys, json, glob
import re

ref_line = re.compile(""".*"\$ref": """)

def replace_refs(file):

	resolves = [
		('defs.yaml', 'defs.json'),
		('schema.yaml', 'schema.json'),
		('footprint.yaml', 'footprint.json'),
		('segment.yaml', 'segment.json'),
		('connector.yaml', 'connector.json'),
		('administrativeBoundary.yaml', 'administrativeBoundary.json')

	]

	line_by_line = ""

	for line in open(file,'r'):

		# We have a reference
		if re.match(ref_line, line):
			for ref_resolve in resolves:
				if ref_resolve[0] in line:
					line = line.replace(ref_resolve[0], ref_resolve[1])

		line_by_line += line

	schema = yaml.safe_load(line_by_line)

	filename = file.split("/")[-1].replace('.yaml','.json')
	new_file = "/".join(file.split("/")[:-1] + [filename])

	print(new_file)

	json.dump(schema, open("documentation_website/static/" + new_file,'w'), indent=2)


if __name__ == '__main__':

	for file in glob.glob('schema/*.yaml') + glob.glob('schema/**/*.yaml'):
		replace_refs(file)
