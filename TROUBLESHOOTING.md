# Troubleshooting

Symptom-first. Find the error you actually saw, read that entry, and skip the rest.
**Nothing on this page is setup you need to perform.** If your commands run cleanly,
you do not need this page at all.

The page has two halves. Most of it is **errors** — something failed and printed a
message you can search for. The last section is **gotchas**: cases where nothing fails,
and you get wrong output instead of an error. Those are worth reading once before you
trust a round-trip.

| Symptom | Section |
|---|---|
| `ModuleNotFoundError: No module named 'overture'` | [Wrong interpreter](#modulenotfounderror-no-module-named-overture) |
| `command not found: overture-schema` | [Missing `uv run`](#command-not-found-overture-schema) |
| A wall of `exclude-newer` warning text, and a dirty `uv.lock` | [uv is out of date](#uv-warns-about-exclude-newer--and-quietly-rewrites-your-lockfile) |
| `FileNotFoundError: ... spark-submit` | [Stale `SPARK_HOME`](#filenotfounderror-on-spark-submit) |
| `model_names()` returns `[]`, or `KeyError` on a feature type | [PySpark expressions not generated](#model_names-returns--or-keyerror-on-a-feature-type) |
| `wc: #: open: No such file or directory` when pasting | [zsh and `#`](#-is-not-a-comment-in-interactive-zsh) |
| A pasted command turns into something from your shell history | [zsh and `!`](#-runs-a-command-out-of-your-history) |
| `ValidationError` you didn't expect from a model | [Model gotchas](#model-gotchas) |

---

## Install and environment

### `ModuleNotFoundError: No module named 'overture'`

You started Python without `uv run`, so you're in your system or `pyenv` interpreter
rather than the project's `.venv`. Use `uv run python` instead of `python`. See
[Running Python against the models](SCHEMA_GUIDE.md#21-running-python-against-the-models).

### `command not found: overture-schema`

You're missing the `uv run` prefix, or you're not in the repo root. Every command in this
guide is `uv run overture-schema …`, run from the directory containing `pyproject.toml`.

### uv warns about `exclude-newer` — and quietly rewrites your lockfile

```
warning: Failed to parse `pyproject.toml` during settings discovery:
  TOML parse error at line 10, column 17
     |
  10 | exclude-newer = "1 week"
     |                 ^^^^^^^^
  failed to parse year in date "1 week": failed to parse "1 we" as year ...
```

> **Do you actually have this problem?** Only if that banner appears when you run a
> command. If your commands print their output cleanly, skip this entire subsection —
> there is nothing to fix, and the four steps below are not maintenance you need to
> perform. Confirm in one line:
>
> ```bash
> uv run overture-schema --version
> ```
>
> A single line of output means you're fine. A wall of warning text above it means read on.

**If you do see it: this is not cosmetic. Fix it before you do anything else.**

The root `pyproject.toml` writes `exclude-newer` as a relative duration (`"1 week"`),
which caps how new a package `uv` will consider during dependency resolution. Only
reasonably recent `uv` versions parse that form.

An older `uv` fails to read the whole `[tool.uv]` block, says so, **and carries on
without the cap** — then, because its resolution no longer matches the committed
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

> **Both commands printing nothing is the healthy result.** `git status --short` and
> `git diff --stat` say nothing about a file that hasn't changed. Empty output here means
> your lockfile is untouched and there is nothing to fix. If you'd rather have an explicit
> answer than read silence:
>
> ```bash
> git diff --quiet uv.lock && echo "uv.lock: unmodified" || echo "uv.lock: MODIFIED"
> ```

It drops the `[options]` block that records the resolution settings, and pulls in
dependency versions past the cutoff the repo intended. Nothing breaks immediately — the
install works fine — but you're now building against a different dependency set than the
project pinned, and `git status` is dirty.

**Step 1 — check your version:**

```bash
uv --version
brew outdated uv
```

**Step 2 — upgrade:**

```bash
brew upgrade uv
```

**Step 3 — restore the lockfile if the old `uv` already rewrote it:**

```bash
git checkout uv.lock
```

**Step 4 — confirm:**

```bash
uv sync --all-packages --locked
```

```
Resolved 64 packages in 12ms
Audited 60 packages in 0.81ms
```

`--locked` fails outright if the lockfile isn't authoritative, so a clean pass means your
`uv`, the lockfile, and your `.venv` all agree. Run `git status --short uv.lock` once more
too — it should print nothing, which means the file is unmodified.

> **If you see `error: The lockfile at uv.lock needs to be updated, but --locked was
> provided`,** you're at step 3, not step 4. A previous `uv sync` under the old `uv`
> already modified the lock. `git checkout uv.lock` and re-run.

Once you're on a current `uv`, ordinary use leaves the lockfile alone — including the
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
print('SUCCESS — spark', s.version)
s.stop()"
```

```
SUCCESS — spark 4.2.0
```

**Fix it permanently.** The variable is set in *two* files — fixing only one won't help,
because `.zprofile` runs for login shells and `.zshrc` for interactive ones:

```
~/.zshrc:8      export SPARK_HOME=/opt/homebrew/Cellar/apache-spark/3.5.3/libexec
~/.zshrc:9      export PATH="$SPARK_HOME/bin/:$PATH"
~/.zprofile:5   export SPARK_HOME=/opt/homebrew/Cellar/apache-spark/3.5.3/libexec
~/.zprofile:6   export PATH="$SPARK_HOME/bin/:$PATH"
```

Pick one:

- **Simplest — delete all four lines.** If you only use Spark through Python projects
  like this one, you don't need `SPARK_HOME` at all; each venv's `pyspark` brings its
  own.
- **Keep Homebrew Spark for other work — stop hardcoding the version.** Replace the two
  `SPARK_HOME` lines with the version-independent symlink Homebrew maintains:

  ```bash
  export SPARK_HOME=/opt/homebrew/opt/apache-spark/libexec
  ```

  This survives upgrades. But note it points at Spark **4.0.0** while this project's
  `pyspark` is **4.2.0** — mismatched versions cause their own confusing failures, so
  prefer the first option while working in this repo.

Then open a new terminal, or `exec zsh`, and re-run the check above.

> **Per-shell workaround** if you don't want to touch your profile right now:
> `unset SPARK_HOME` in the terminal you're working in. It lasts until you close it.

### `model_names()` returns `[]`, or `KeyError` on a feature type

The PySpark validation expressions are generated code that is **not committed to git** —
they're in `.gitignore`, and `uv sync` alone cannot produce them. Skipping that step
doesn't raise an error; it leaves you with an empty registry, which is why this is easy
to miss.

```bash
make generate-pyspark
```

Then confirm — don't infer it from the output, which is silent by design:

```bash
uv run python -c "from overture.schema.pyspark import model_names; print(model_names())"
```

Before, an empty list. After, 30 entries — 15 feature types, each reachable by two names:

```
['address', 'bathymetry', 'building', 'building_part', 'connector', 'division', ...]
```

Only people working from a git clone ever need this. Published wheels ship the generated
expressions already; see
[Why generated code is gitignored](CONCEPTS.md#why-generated-code-is-gitignored).

---

## Pasting commands into zsh

macOS defaults to **zsh**, and two of its interactive behaviors mangle commands copied
out of documentation. Neither affects scripts or non-interactive shells.

### `#` is not a comment in interactive zsh

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

A line that *starts* with `#` fails more obviously — `command not found: #`.

This guide keeps `#` comments only as standalone label lines inside multi-command blocks,
never trailing after a command. To paste those blocks whole, enable comments once:

```bash
setopt interactive_comments
```

Add it to `~/.zshrc` to make it permanent. Otherwise, skip the `#` lines when copying —
they are labels, not commands. Scripts and non-interactive shells are unaffected; this is
purely an interactive-zsh behavior.

### `!` runs a command out of your history

This one is worth understanding because it can do real damage. In an interactive shell,
`!` triggers **history expansion**, and it fires *inside double quotes*. `!r` means "the
most recent command starting with `r`" — the shell splices that command's text into your
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
produced a syntax error — Python never ran and nothing was deleted. But the same mechanism
can land text somewhere the shell *will* execute.

**The fix used throughout this guide:** multi-line Python is passed via a heredoc with a
**quoted** delimiter, not `-c "..."`.

```python
from overture.schema.buildings import Building
print(f"{Building.__name__!r} is safe here")
```

Quoting the delimiter (`<<'""" + D + """'` rather than `<<""" + D + """`) disables every
form of expansion in the body — history, variables, command substitution. The text reaches
Python exactly as written.

Verified rather than assumed:

```
double-quoted -c   ->  !r expanded into a command from history
quoted heredoc     ->  !r left alone
```

Single quotes also block history expansion, but the Python in this guide uses single
quotes internally, so heredocs are the practical choice. If you hit this in your own
one-liners, `{value!r}` can always be written `{repr(value)}` instead — no `!` at all.

---

---

## Model gotchas

Things that cost time if you don't know them. Every one of these is a consequence of
[the two representations](SCHEMA_GUIDE.md#32-the-one-thing-to-understand-two-representations).

| Gotcha | What happens | Fix |
|---|---|---|
| `model_validate(geojson_dict)` | `ValidationError`: missing `theme`/`version`, `type` is `'Feature'` | Use `model_validate_json()`. Python mode expects flat data, JSON mode expects GeoJSON. |
| `model_dump()` without `by_alias` | Emits `class_`, not `class`; output won't re-validate | Always `by_alias=True` |
| `Segment.model_validate(...)` | `AttributeError` — it's a union alias, not a class | `TypeAdapter(Segment).validate_json(...)` |
| `model_names()` returns `[]` | PySpark expressions are generated, not committed | `make generate-pyspark` (or `make install`) |
| Dumps full of `null` | Unset optionals serialize explicitly | `exclude_none=True` |
| Absent list → `[]` → won't re-validate | An omitted optional list defaults to `[]` on the model, dumps as `[]`, then fails a `min_length` check on the way back in | `exclude_defaults=True`, or drop empty lists before re-validating |

Asymmetric round-trip, worth knowing about: an optional list that is simply *absent*
from the input becomes an empty list on the model, and an empty list is not the same as
absent on the way back out.

```python
segments = TypeAdapter(Segment)
seg = segments.validate_json(
    open("road-indoors.yaml-as-json").read()
)  # no `connectors` key
seg.connectors  # []      ← not None

flat = seg.model_dump(mode="python", by_alias=True, exclude_none=True)
flat["connectors"]  # []      ← exclude_none doesn't drop it
segments.validate_python(flat)
# ValidationError: road.connectors
#   List should have at least 2 items after validation, not 0
```

The same document validates fine on the way in (the CLI accepts it) and fails on the way
back. `exclude_defaults=True` avoids it, as does pruning empty lists before re-validating.

## Docs in the repo that are currently wrong

- **`pip install overture-schema`** — in every package README. Nothing is on PyPI yet;
  see [7.3](SCHEMA_GUIDE.md#73-what-changes-once-these-packages-are-published). Every other item that
  stood here has been fixed, and `tests/test_documented_imports.py` now imports every
  `overture.*` statement in every tracked Markdown file, so a broken one fails the suite
  rather than accumulating here.
