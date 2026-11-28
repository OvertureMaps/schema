# Troubleshooting

Use this page when a command or model gives you an error you don't expect. Find the
message in the table and follow the link. Most entries apply however you installed the
packages. Entries that apply only to a [clone of the repository](../CONTRIBUTING.md#set-up-a-clone)
say so.

| Symptom | Section |
|---|---|
| `ModuleNotFoundError: No module named 'overture'` | [Wrong interpreter](#modulenotfounderror-no-module-named-overture) |
| `command not found: overture-schema` | [Missing `uv run`](#command-not-found-overture-schema) |
| `command not found: overture-codegen` or `overture-validate` | [Package not installed](#command-not-found-overture-codegen-or-overture-validate) |
| A wall of `exclude-newer` warning text, and a dirty `uv.lock` (clone only) | [uv is out of date](#exclude-newer-warning-from-uv) |
| `FileNotFoundError: ... spark-submit` | [Stale `SPARK_HOME`](#filenotfounderror-on-spark-submit) |
| `model_names()` returns `[]`, or `KeyError` on a feature type (clone only) | [PySpark expressions not generated](#model_names-returns--or-keyerror-on-a-feature-type) |
| `wc: #: open: No such file or directory` when pasting | [zsh and `#`](#-in-interactive-zsh) |
| A pasted command turns into something from your shell history | [zsh and `!`](#-history-expansion-in-zsh) |
| `ValidationError` you didn't expect from a model | [Model gotchas](#model-gotchas) |

---

## Install and environment

### `ModuleNotFoundError: No module named 'overture'`

You started Python outside the environment the packages are installed in, so you're in
your system or `pyenv` interpreter rather than your project's `.venv`. With `uv`, use
`uv run python` instead of `python`. With `pip`, activate the venv first
(`source .venv/bin/activate`). See
[Running Python against the models](exploring-the-models.md#running-python-against-the-models).

### `command not found: overture-schema`

You're missing the `uv run` prefix, or you're not in your project directory. Every
command in this guide is `uv run overture-schema …`, run from the directory containing
your `pyproject.toml` (the repo root, for a clone). With `pip`, activate the venv instead.

If you use pyenv, the message reads `pyenv: overture-schema: command not found`, and
pyenv may list other Python environments where it found an `overture-schema` command.
Those are separate installs, not your project's. The fix is the same: use `uv run`, or
activate your project's venv.

### `command not found: overture-codegen` or `overture-validate`

The `overture-schema` metapackage installs only the `overture-schema` command. The other
two come from their own packages:

```bash
uv add overture-schema-codegen
uv add "overture-schema-pyspark[spark]"
```

If you use `pip`:

```bash
pip install overture-schema-codegen
pip install "overture-schema-pyspark[spark]"
```

A clone installs all three. See
[Install from PyPI](getting-started-with-the-schema.md#install-from-pypi).

### `exclude-newer` warning from uv

```
warning: Failed to parse `pyproject.toml` during settings discovery:
  TOML parse error at line 10, column 17
     |
  10 | exclude-newer = "1 week"
     |                 ^^^^^^^^
  failed to parse year in date "1 week": failed to parse "1 we" as year ...
```

**Clone only.** The setting lives in the repo's root `pyproject.toml`, so a PyPI install
never sees it.

> [!NOTE]
> You only have this problem if that banner appears when you run a command. If your commands print their output cleanly, skip this entire subsection.
> There's nothing to fix, and the four steps below are not maintenance you need to
> perform. Confirm in one line:
>
> ```bash
> uv run overture-schema --version
> ```
>
> A single line of output means you're fine. A wall of warning text above it means you have a problem to sort out.

**If you do see it: this is not cosmetic. Fix it before you do anything else.**

The root `pyproject.toml` writes `exclude-newer` as a relative duration (`"1 week"`),
which caps how new a package `uv` will consider during dependency resolution. Only
reasonably recent `uv` versions parse that form.

An older `uv` fails to read the whole `[tool.uv]` block, says so, **and continues
without the cap**. Then, because its resolution no longer matches the committed
lockfile, rewrites `uv.lock` in place. You end up with a modified tracked file you never
asked to change:

```bash
git status --short uv.lock
git diff --stat uv.lock
```

On an affected machine:

```
 M uv.lock
 uv.lock | 807 +++++++++++++++++++-------------------
 1 file changed, 464 insertions(+), 343 deletions(-)
```

> [!NOTE]
> **Both commands printing nothing is the healthy result.** `git status --short` and
> `git diff --stat` say nothing about a file that hasn't changed. Empty output here means
> your lockfile is untouched and there is nothing to fix. If you'd rather have an explicit
> answer than read silence:
>
> ```bash
> git diff --quiet uv.lock && echo "uv.lock: unmodified" || echo "uv.lock: MODIFIED"
> ```

It drops the `[options]` block that records the resolution settings, and pulls in
dependency versions past the cutoff the repo intended. Nothing breaks immediately, and the
install works fine, but you're now building against a different dependency set than the
project pinned, and `git status` is dirty.

**Step 1: check your version.**

```bash
uv --version
brew outdated uv
```

**Step 2: upgrade.**

```bash
brew upgrade uv
```

**Step 3: restore the lockfile if the old `uv` already rewrote it.**

```bash
git checkout uv.lock
```

**Step 4: confirm.**

```bash
uv sync --all-packages --locked
```

```
Resolved 64 packages in 12ms
Audited 60 packages in 0.81ms
```

`--locked` fails outright if the lockfile isn't authoritative, so a clean pass means your
`uv`, the lockfile, and your `.venv` all agree. Run `git status --short uv.lock` once more
too. It should print nothing, which means the file is unmodified.

> [!TIP]
> **If you see `error: The lockfile at uv.lock needs to be updated, but --locked was
> provided`,** you're at step 3, not step 4. A previous `uv sync` under the old `uv`
> already modified the lock. `git checkout uv.lock` and re-run.

Once you're on a current `uv`, ordinary use leaves the lockfile alone, including the
`uv sync --all-packages --all-extras` that `make install`, `make check`, and
`make generate-pyspark` all run internally.

---

### `FileNotFoundError` on `spark-submit`

```
FileNotFoundError: [Errno 2] No such file or directory:
'/opt/homebrew/Cellar/apache-spark/3.5.3/libexec/./bin/spark-submit'
```

**This has nothing to do with the generation step in "Do you need PySpark?".** It's a stale `SPARK_HOME`
environment variable, and it will happen whether or not you ran `make generate-pyspark`.

What's going on: you have a `SPARK_HOME` exported in your shell profile pointing at a
**version-specific Homebrew path**. Homebrew has since upgraded Spark, so that exact
directory no longer exists:

```bash
echo $SPARK_HOME
ls /opt/homebrew/Cellar/apache-spark/
```

```
/opt/homebrew/Cellar/apache-spark/3.5.3/libexec
4.0.0
```

The variable names `3.5.3`; the only version present is `4.0.0`. It points at nothing.

Meanwhile the `pyspark` in your venv (4.2.0) **ships its own copy of Spark** and doesn't
need the Homebrew one at all. But when `SPARK_HOME` is set, PySpark obeys it and looks
for `spark-submit` at that dead path.

**Confirm that's your problem:**

```bash
env -u SPARK_HOME uv run python -c "
from pyspark.sql import SparkSession
s = SparkSession.builder.master('local[1]').getOrCreate()
print('SUCCESS: spark', s.version)
s.stop()"
```

```
SUCCESS: spark 4.2.0
```

**Fix it permanently.** The variable is set in *two* files, and fixing only one won't help,
because `.zprofile` runs for login shells and `.zshrc` for interactive ones:

```
~/.zshrc:8      export SPARK_HOME=/opt/homebrew/Cellar/apache-spark/3.5.3/libexec
~/.zshrc:9      export PATH="$SPARK_HOME/bin/:$PATH"
~/.zprofile:5   export SPARK_HOME=/opt/homebrew/Cellar/apache-spark/3.5.3/libexec
~/.zprofile:6   export PATH="$SPARK_HOME/bin/:$PATH"
```

Pick one:

- **Simplest: delete all four lines.** If you only use Spark through Python projects
  like this one, you don't need `SPARK_HOME` at all; each venv's `pyspark` brings its
  own.
- **Keep Homebrew Spark for other work: stop hardcoding the version.** Replace the two
  `SPARK_HOME` lines with the version-independent symlink Homebrew maintains:

  ```bash
  export SPARK_HOME=/opt/homebrew/opt/apache-spark/libexec
  ```

  This survives upgrades. But note it points at Spark **4.0.0** while this project's
  `pyspark` is **4.2.0**. Mismatched versions cause their own confusing failures, so
  prefer the first option while working in this repo.

Then open a new terminal, or `exec zsh`, and re-run the check above.

> [!TIP]
> **Per-shell workaround** if you don't want to touch your profile right now:
> `unset SPARK_HOME` in the terminal you're working in. It lasts until you close it.

### `model_names()` returns `[]`, or `KeyError` on a feature type

**Clone only.** The PySpark validation expressions are generated code that is **not committed to git**.
They're in `.gitignore`, and `uv sync` alone cannot produce them. Skipping that step
doesn't raise an error; it leaves you with an empty registry, which is why this is easy
to miss.

```bash
make generate-pyspark
```

Then confirm. Don't infer it from the output, which is silent by design:

```bash
uv run python -c "from overture.schema.pyspark import model_names; print(model_names())"
```

Before, an empty list. After, 30 entries: 15 feature types, each reachable by two names:

```
['address', 'bathymetry', 'building', 'building_part', 'connector', 'division', ...]
```

Only people working from a git clone ever need this. Published wheels ship the generated
expressions already; see
[Generated code and git](concepts.md#generated-code-and-git).

---

## Pasting commands into zsh

macOS defaults to **zsh**, and two of its interactive behaviors mangle commands copied
out of documentation. Neither affects scripts or non-interactive shells.

### `#` in interactive zsh

macOS defaults to **zsh**, and interactive zsh does *not* treat `#` as a comment unless
you turn that on. Paste a line like this and zsh hands `#`, `→`, and `15` to `wc` as
filenames:

```
find ... | wc -l      # → 15
wc: #: open: No such file or directory
wc: →: open: No such file or directory
wc: 15: open: No such file or directory
       0 total
```

A line that *starts* with `#` fails more obviously, with `command not found: #`.

This guide keeps `#` comments only as standalone label lines inside multi-command blocks,
never trailing after a command. To paste those blocks whole, enable comments once:

```bash
setopt interactive_comments
```

Add it to `~/.zshrc` to make it permanent. Otherwise, skip the `#` lines when copying.
They are labels, not commands. Scripts and non-interactive shells are unaffected; this is
purely an interactive-zsh behavior.

### `!` history expansion in zsh

This one can do real damage. In an interactive shell,
`!` triggers **history expansion**, and it fires *inside double quotes*. `!r` means "the
most recent command starting with `r`." The shell splices that command's text into your
line before running it.

So a Python one-liner containing `{value!r}`, pasted into zsh as

```
uv run python -c "... f'default={f.default!r}' ..."
```

becomes something else entirely. What you get depends on your own shell history:

```
SyntaxError: f-string: invalid syntax
    (f.defaultrm -rf schema)
```

That is a past command of yours, pasted into the middle of a Python f-string. Here it only
produced a syntax error. Python never ran and nothing was deleted. But the same mechanism
can land text somewhere the shell *will* execute.

**The fix used throughout this guide:** multi-line Python is passed via a heredoc with a
**quoted** delimiter, not `-c "..."`.

```python
from overture.schema.buildings import Building

print(f"{Building.__name__!r} is safe here")
```

Quoting the delimiter (`<<'""" + D + """'` rather than `<<""" + D + """`) disables every
form of expansion in the body: history, variables, and command substitution. The text reaches
Python exactly as written.

Here's the result of testing both:

```
double-quoted -c   ->  !r expanded into a command from history
quoted heredoc     ->  !r left alone
```

Single quotes also block history expansion, but the Python in this guide uses single
quotes internally, so heredocs are the practical choice. If you hit this in your own
one-liners, `{value!r}` can always be written `{repr(value)}` instead, with no `!` at all.

---

---

## Model gotchas

Navigating [the two representations](working-with-features.md#two-representations) of the models can be challenging.

| Gotcha | What happens | Fix |
|---|---|---|
| `model_validate(geojson_dict)` | `ValidationError`: missing `theme`/`version`, `type` is `'Feature'` | Use `model_validate_json()`. Python mode expects flat data, JSON mode expects GeoJSON. |
| `model_dump()` without `by_alias` | Emits `class_`, not `class`; output won't re-validate | Always `by_alias=True` |
| `Segment.model_validate(...)` | `AttributeError`: it's a union alias, not a class | `TypeAdapter(Segment).validate_json(...)` |
| `model_names()` returns `[]` | From a clone: PySpark expressions are generated, not committed | `make generate-pyspark` (or `make install`) |
| Dumps full of `null` | Unset optionals serialize explicitly | `exclude_none=True` |

---

## Next steps

If your error isn't on this page, read the `README.md` for the package whose command or
function you ran, under `packages/`. Then search the
[schema repository's issues](https://github.com/OvertureMaps/schema/issues), or ask in
[GitHub Discussions](https://github.com/orgs/OvertureMaps/discussions). When you report a problem, include the command you ran, the full error message,
and the output of `uv run overture-schema --version`.
