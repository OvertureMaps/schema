# Editing the Overture Schema Documentation

[docs.overturemaps.org](https://docs.overturemaps.org) is a docusaurus website that builds from the [github.com/overturemaps/docs](github.com/overturemaps/docs) repo

Everything at `docs.overturemaps.org/schema` comes from here, specifically:
1. Any examples shown on the documentation are pulled from the `examples` folder.
2. The interactive schema blocks are built off the YAML files located in the `schema` folder.
3. The source for the reference pages are the `.mdx` files located here in the `docs/schema` folder.


### Development
Clone this repo, checkout a feature branch, and run the `build_docs.sh` script. This will check out the `OvertureMaps/docs` repo and create symlinks for _examples_, _schema_, and _docs/schema_ into the build.

You can then edit the `.mdx` files here in `docs/schema` (do not worry about the _docusaurus_ folder) and see your changes live at http://localhost:3000
