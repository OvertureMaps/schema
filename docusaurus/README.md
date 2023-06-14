# Overture Schema Documentation Webpage

This documentation page is build using [Docusaurus 2](https://docusaurus.io/) with the [JSON Schema Plugin](https://github.com/jy95/docusaurus-json-schema-plugin).


## Local Development

### nvm, node.js, and npm
Project uses Node.js which is prerequisite to run next instructions.

The minimum required Node.js version is `15.0.0`.

For Windows and/or WSL users on Windows (Ubuntu) here is a [link](https://learn.microsoft.com/en-us/windows/dev-environment/javascript/nodejs-on-wsl) to working instructions set.

### First, install the dependencies:

```
$ npm install
```
Then, start the local server:
```
$ npm run start
```
This command does 2 things: First, it copies the contents of `schema/` into `docusaurus/docs/yaml`, then it runs the docusaurus server which reads the contents of `docs/overture-schema` pages and the `docs/yaml` files to build the page.

This command should also launch a browser window to `http://localhost:3000` where any changes to the source `.mdx` files are reflected live.

### Editing
All of the relevant editable `.mdx` files are here:
```
schema-wg/
  docusaurus/
    docs/
      overture-schema/
        -schema.mdx
        Addresses/
          -address.mdx
        Buildings/
          -footprint.mdx

```
These files may contain the headings, examples, etc. for each schema file, in markdown.

Adding descriptions to the actual schema elements, however, should be done in the schema YAML files directly in the main (`schema-wg/schema/`) directory.

_Note: each time you run `npm run start`, the official YAML schema files from `schema-wg/schema` are copied to the `docusaurus/docs/yaml` directory, where docusaurus parses them._

### Adding a new Schema Page
1. Update the `src/YAML_FILE_TREE.js` file to include the _relative_ path to the YAML file.
2. Add a new `.mdx` file in the `docs/overture-schema` directory.


## Publishing
```
$ npm run build
```
Docusaurus builds a static web page in the `docusaurus/build` directory. There is a Github hook that builds the website and publishes it to the gh-pages branch.