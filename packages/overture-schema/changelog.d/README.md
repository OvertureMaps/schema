# Changelog fragments

[towncrier](https://towncrier.readthedocs.io) news fragments for this package.
One file per change to this package (including patch-level fixes and internal
work):

```
changelog.d/<issue-or-pr>.<type>.md
```

Types, body format, the preview command, and when a fragment is required are
documented once in
[docs/versioning.md -> Add a changelog fragment](../../../docs/versioning.md#add-a-changelog-fragment).

> [!NOTE]
> This README also keeps `changelog.d/` tracked in git, so no `.gitkeep` is
> needed. Leave it in place even when the directory holds no fragments.