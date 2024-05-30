# Overture Schema Documentation

Official Overture Maps documentation pages are maintained at github.com/overturemaps/docs and publishes to [docs.overturemaps.org](https://docs.overturemaps.org)

This repo (schema/docusaurus) contains the contents of what gets published at docs.overturemaps.org/**schema**.

This page is built using [Docusaurus 3](https://docusaurus.io/) with the [JSON Schema Plugin](https://github.com/jy95/docusaurus-json-schema-plugin).


## Editing
To update any of the documentation available at `docs.overturemaps.org/schema`, you can edit the files here in `docs/schema`.


## Local Development

### nvm, node.js, and npm
Project uses Node.js which is prerequisite to run the next instructions.

For Windows and/or WSL users on Windows (Ubuntu) here is a [link](https://learn.microsoft.com/en-us/windows/dev-environment/javascript/nodejs-on-wsl) to working instructions set.

### First, install the dependencies:

```
$ npm install
```
Then, start the local server:
```
$ npm run start
```
This command does 2 things: First, it copies the contents of `schema/` into `docusaurus/docs/_schema`, and `examples/` into `docusaurus/docs/_examples`, then it runs the docusaurus server which builds the documentation.

This command should also launch a browser window to `http://localhost:3000` where any changes to the source `.mdx` files are reflected live.

_Note: each time you run `npm run start`, the official YAML schema files from `/schema` are copied to the `docusaurus/docs/_schema_` directory, where docusaurus parses them._
