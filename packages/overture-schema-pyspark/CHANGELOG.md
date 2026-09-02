## [2.0.0] - 2026-09-02

### Bug Fixes

- Fixed published wheels and sdists shipping without the generated validation expressions, which left an installed `validate_model()` unable to discover any models. ([#625](https://github.com/OvertureMaps/schema/issues/625))
- Moved `pyspark` from a hard dependency to the `spark` optional extra, so installing `overture-schema-pyspark` no longer resolves `pyspark` on runtimes (Glue, EMR) that already bundle their own. Standalone environments need `pip install overture-schema-pyspark[spark]`. Importing the package without PySpark installed now raises an actionable `ModuleNotFoundError` pointing at that extra, instead of a bare "No module named 'pyspark'". Importing it with a PySpark older than the declared floor raises an `ImportError` naming both versions, so the floor still applies on installs that skip the extra and bring their own PySpark. ([#659](https://github.com/OvertureMaps/schema/issues/659))
- Fixed the validation registry coming back empty when `overture-schema-pyspark` is loaded from a wheel on `sys.path` (zipimport) rather than installed to a real directory, as happens on AWS Glue via `--extra-py-files`. The generated tree is now read through `importlib.resources`, which resolves a namespace portion inside an archive as well as one on disk. ([#661](https://github.com/OvertureMaps/schema/issues/661))

### Documentation

- Updated the README's S3 examples to a release the bucket still retains, and documented how to read the current release identifier from the STAC catalog. ([#668](https://github.com/OvertureMaps/schema/issues/668))

### Miscellaneous

- Declared explicit version floors for workspace dependencies. ([#557](https://github.com/OvertureMaps/schema/issues/557))
- Migrated the build backend to uv_build and PEP 420; the runtime registry now walks the namespace roots as files so it discovers generated modules that no longer ship `__init__.py`. ([#618](https://github.com/OvertureMaps/schema/issues/618))
- Moved expression-generation from the shared prebuild step into the package's own `scripts/prebuild.sh`, run by `release-publish.yaml` before `uv build`. CI-only change: no runtime code, dependencies, or wheel contents affected. ([#638](https://github.com/OvertureMaps/schema/issues/638))
