import yaml, sys, json, glob

import re

ref_line = re.compile(""".*"\$ref": """)

BASE_URL = "http://localhost:3000"

resolves = [
	('../defs.yaml', f'{BASE_URL}/schema/defs.json'),
	('defs.yaml', f'{BASE_URL}/schema/defs.json'),
	('../schema.yaml', f'{BASE_URL}/schema/schema.json'),
	('schema.yaml', f'{BASE_URL}/schema/schema.json')
]

def main(file):
	line_by_line = "";

	for line in open(file,'r'):

		#We have a reference
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
	if len(sys.argv)>1 and '.yaml' in sys.argv[1]:
		main(sys.argv[1])

	else:
		for file in glob.glob('schema/*.yaml') + glob.glob('schema/**/*.yaml'):
			main(file)
