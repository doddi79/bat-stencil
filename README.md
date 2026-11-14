# BatStencil

[![PyPI](https://img.shields.io/pypi/v/batstencil)](https://pypi.org/project/batstencil/)

An [AllConf](https://github.com/doddi79/allconf) and Jinja2 powered template
renderer where the context can come from config files and entire directory
trees can be rendered.

- Context from AllConf files (YAML/JSON with includes, `${__ENV__:...}`,
  `${__PY__:...}` etc.), plain dicts, keyword arguments or command line
  arguments
- Render a string, a file or a whole directory tree of templates
- Extra Jinja2 tags for embedding files, skipping output, naming output files
  and repeating files/directories once per item in a list
- Use it from the command line (`bat-stencil`) or from Python

The main use cases are project scaffolding (render a "template project" into a
new project) and rendering CI/CD manifests (Kubernetes, pipelines etc.) on
demand.

See the **[Public API index](docs/api-index.md)** for a task-oriented reference
of everything batstencil offers, and the [CHANGELOG](CHANGELOG.md) for what
changed between versions.

## Note

This is a fork of [`ccp-stencil`](https://github.com/ccpgames/ccp-stencil)
(PyPI: `ccpstencil` 0.8.0) by CCP Games, made in order to continue its
development and maintenance. The package _and_ module are now called
`batstencil` (starting at version 1.0.0) so it can live side-by-side with the
original, and the command line tool is `bat-stencil`.

The dependencies moved along with it: `ccptools` became
[`batutils`](https://github.com/doddi79/batutils) and `alviss` became
[`allconf`](https://github.com/doddi79/allconf) (both also forks of CCP
packages). Names that carried the old name have deprecated aliases
(`AlvissContext`, `{% embed ..., alviss=True %}`).

## Install

Requires Python 3.10+.

```bash
pip install batstencil
pip install batstencil[fidelius]   # optional, for secret lookup via AllConf/Fidelius
```

## Command line

```
bat-stencil [-i INPUT] [-a KEY=VALUE ...] (-t FILE | -s STRING | -d DIR) [-o OUTPUT]
            [--no-overwrite] [--no-purge] [-v] [--version]
```

(`python -m batstencil` works the same way.)

| Flag | Meaning |
|------|---------|
| `-i`, `--input` | AllConf file (YAML or JSON) to use as the context |
| `-a`, `--arg` | Extra context value as `key=value`, can be repeated. Dots nest: `-a app.name=foo` sets `app: {name: foo}`. Applied on top of `-i` |
| `-t`, `--template` | A template file to render |
| `-s`, `--string-template` | A template given directly on the command line |
| `-d`, `--directory-template` | A directory of templates to render (requires `-o`) |
| `-o`, `--output` | Where to write. A path ending in `/` is a directory (the file keeps the template's name, or the one from `{% setfilename %}`), otherwise it's the output file. Without `-o` results go to stdout. For `-d` it's the output directory |
| `--no-overwrite` | Fail instead of overwriting existing output files (also fails when purging an existing output directory) |
| `--no-purge` | Don't delete the output directory first when rendering a directory |
| `-v`, `--verbose` | DEBUG logging (and full tracebacks on errors) |
| `--version` | Print the version |

Exactly one of `-t`, `-s` and `-d` is required. On errors the command prints
the message to stderr and exits with code 3.

Given this `config.yaml`:

```yaml
app:
  name: demo
  replicas: 3
services: [api, worker]
```

**Render a file** (to a directory, keeping the file name):

```bash
bat-stencil -i config.yaml -a app.name=shop -t deploy.yaml.j2 -o out/
# Wrote file: /.../out/deploy.yaml.j2
```

**Render a string to stdout:**

```bash
bat-stencil -a who=world -a a.b=c -s 'Hello {{ who }} {{ a.b }}!'
# Hello world c!
```

**Render a directory** (see [Directory rendering](#directory-rendering)):

```bash
bat-stencil -i config.yaml -d my_template_project -o generated/
# Wrote file: /.../generated/README.md
# ...
```

## Python

```python
from batstencil.stencils import *
```

### `render_stencil`

The shortcut for the common case; it returns the rendered `str` (or `None` if
the template skipped itself with `{% skip_if %}`):

```python
render_stencil('Hello {{ who }}!', {'who': 'world'})      # 'Hello world!'
render_stencil('deploy.yaml.j2', 'config.yaml')           # file template, AllConf file context
```

The **template** argument is guessed as follows:

- An `ITemplate` object is used as-is
- A `Path` is a file template
- A multi-line string is a string template
- A single-line string is a file template if it names a template that can be
  loaded from the [search paths](#template-search-paths) or is a path to an
  existing file, otherwise it's a string template

The **context** argument is guessed as follows:

- An `IContext` object is used as-is
- `None` is an empty context
- A `dict` (any `Mapping`) is a `DictContext`
- A `str` or `Path` is an `AllConfContext` (the path of a YAML/JSON file)

### Contexts, templates and renderers

For anything else (writing to files, rendering directories) combine the
classes explicitly:

```python
from batstencil.stencils import *

renderer = FileRenderer('out/')
renderer.context = AllConfContext('config.yaml')
renderer.template = FileTemplate('deploy.yaml.j2')
path = renderer.render()      # absolute path of the file written (None if skipped)

# Or all in the constructor
DirectoryRenderer('generated/',
                  context=DictContext({'app': {'name': 'shop'}, 'services': ['api']}),
                  template=DirectoryTemplate('my_template_project')).render()
```

| Contexts | |
|----------|--|
| `DictContext(dict)` | A plain dict (`update()` and dotted `nested_update('a.b', v)` to modify) |
| `KeyWordArgumentContext(**kwargs)` | Same, from keyword arguments |
| `AllConfContext(file)` | Loaded with AllConf. `AlvissContext` is a deprecated alias |

| Templates | |
|-----------|--|
| `StringTemplate(str)` | A template in a string |
| `FileTemplate(path)` | A template file. A `str` is first looked up as a template name in the search paths, then as a path |
| `DirectoryTemplate(dir)` | A directory tree of templates (only for `DirectoryRenderer`) |

| Renderers | `render()` returns |
|-----------|--------------------|
| `StringRenderer()` | The rendered `str` (or `None` if skipped) |
| `StdOutRenderer()` | Prints the result, returns `None` |
| `FileRenderer(output_path, overwrite=True)` | The absolute path written (or `None` if skipped). A path ending in `/` or an existing directory is a directory |
| `DirectoryRenderer(output_path, overwrite=True, purge=True)` | A list of the absolute paths written |

Output files are always written as UTF-8 with `\n` line endings.

### Jinja2 environment

Templates are rendered in a Jinja2 environment with `trim_blocks`,
`lstrip_blocks` and `keep_trailing_newline` turned on, and `ChainableUndefined`
so that missing (even deeply nested) values render as empty strings instead of
raising errors:

```jinja
{{ nothing.here.at_all }}   {# renders as an empty string #}
```

The context is available as top level variables, plus the
[`__stencil__`](#the-__stencil__-variable) variable.

Note that only the context _file_ is processed by AllConf. Templates are plain
Jinja2, so `${__ENV__:...}` and friends are not resolved in them (except in
files pulled in with `{% embed ..., allconf=True %}`).

## Template search paths

`{% include %}`, `{% extends %}`, `{% import %}`, file template names and
`{% embed %}` look for files in:

1. The current working directory
2. The directory of the running script (`sys.argv[0]`)
3. Every path in the `STENCIL_TEMPLATE_PATH` environment variable, separated
   by `;` or the OS path separator (`:` on Linux/macOS)

The list is available as `renderer.search_paths`.

## Custom tags and filters

### `{% embed 'file' %}`

Inserts a file "as-is" (it is _not_ rendered as a template). The file is looked
up relative to the template doing the embedding first, then in the
[search paths](#template-search-paths); an absolute path is used directly. A
missing file raises `EmbedFileNotFound`. A newline is added after the embedded
content.

```jinja
{% embed 'fragment.yaml' %}
{% embed 'fragment.yaml', indent=4 %}
{% embed 'fragment.yaml', allconf=True, env=True %}
```

| Argument | Effect |
|----------|--------|
| `indent=N` | Indent every line by N spaces (handy for YAML) |
| `allconf=True` | Render the file with AllConf first (`alviss=True` is a deprecated alias) |
| `env=True` | With `allconf`: resolve `${__ENV__:...}` |
| `py=True` | With `allconf`: resolve `${__PY__:...}` |
| `fidelius=True` | With `allconf`: resolve `${__FID__:...}` (needs `batstencil[fidelius]`) |

### `{% skip_if condition %}`

Skips the template if the condition is true: nothing is written (the CLI prints
`Skipped rendering (skip_if)`, `render_stencil` returns `None`). In a
`__stencil_meta__` file it skips the whole directory.

```jinja
{% skip_if not app.use_docker %}
FROM python:3.12
```

### `{% setfilename %}...{% endsetfilename %}`

Sets the name of the output file (or directory, in `__stencil_meta__`) to the
stripped result of its body. This takes precedence over the template's own name
and over a file name given in the output path. An empty result logs a warning
and the default name is used.

```jinja
{% setfilename %}{{ app.name }}.yaml{% endsetfilename %}
```

### `{% repeat_for item in items %}`

Directory rendering only (using it elsewhere raises `RenderError`). Renders the
file (or, in a `__stencil_meta__` file, the whole directory) once per item, with
`item` available in the template. Several names unpack each item, e.g.
`{% repeat_for k, v in some_dict.items() %}`. A missing or empty list renders
nothing. Every copy needs a unique name, so combine it with `setfilename`
(otherwise you get a `TemplateRenderError`):

```jinja
{% repeat_for svc in services %}
{% setfilename %}{{ svc }}.yaml{% endsetfilename %}
name: {{ svc }}
```

### `base64` filter

Base64 encodes a string (or bytes) to a single line, e.g. for Kubernetes
Secrets: `password: {{ db.password | base64 }}`.

## Directory rendering

`DirectoryRenderer` (and `bat-stencil -d`) walks a template directory and
renders it into the output directory:

- Every file is a template, rendered with the same context, and written with the
  same name (unless `{% setfilename %}` says otherwise). `{% skip_if %}` and
  `{% repeat_for %}` work in them too.
- A file named `__stencil_meta__` inside a **subdirectory** (not allowed in the
  root) is rendered to control that directory: `{% setfilename %}` for its name,
  `{% skip_if %}` to skip it and everything in it, and `{% repeat_for %}` to
  render it once per item. Its text output is ignored and it is never copied.
- Directories inside a repeated directory inherit its loop variables.
- Errors in a template raise `TemplateRenderError` naming the failing template
  file (and line).
- Output paths that would escape the output directory are refused.

Example template tree:

```
my_template_project/
  README.md                  # "# {{ app.name }}"
  docs/
    __stencil_meta__         # {% skip_if not app.docs %}
    index.md
  services/
    svc/
      __stencil_meta__       # {% repeat_for svc in services %}
                             # {% setfilename %}{{ svc }}{% endsetfilename %}
      main.py                # "# {{ svc }} ({{ __stencil__.loop.index }}/{{ __stencil__.loop.length }})"
```

With `services: [api, worker]` and no `app.docs` this renders:

```
generated/README.md
generated/services/api/main.py
generated/services/worker/main.py
```

### Purging

By default the output directory is **deleted before rendering** so it only
contains what the template produces. Use `--no-purge` / `purge=False` to render
into an existing directory and keep what's there. With `--no-overwrite` /
`overwrite=False`, rendering fails if the output directory exists (when
purging) or if any file to be written exists (when not purging).

As a safety guard the renderer refuses to purge (raising `UnsafePurgeError`)
the current working directory or any of its parents, the home directory, a file
system root or a directory containing the template directory.

## The `__stencil__` variable

Every render has a `__stencil__` variable with info about the rendering:

| Key | Value |
|-----|-------|
| `version` | The batstencil version |
| `template_name` | File name of the template (`None` for string templates) |
| `template_path` | Absolute path of the template file (`None` for string templates) |

Directory rendering adds:

| Key | Value |
|-----|-------|
| `template_root` | Absolute path of the template directory |
| `template_relative_path` | Path of the current template relative to the root (posix style) |
| `source_dir` | The current template's directory, relative to the root (`.` for the root) |
| `output_root` | Absolute path of the output directory |
| `output_dir` | Current output directory, relative to the output root (posix style) |
| `loop` | Info on the innermost `repeat_for` loop (or `None`): `index` (from 1), `index0`, `first`, `last`, `length` and `item` |
| `loops` | A list of all enclosing loops, outermost first |

## Errors

All batstencil errors derive from `StencilError`:

- `TemplateError` / `TemplateNotFoundError` (also a `FileNotFoundError`)
- `ContextError` (e.g. a malformed `-a` argument)
- `RenderError`
  - `NoTemplateSetError`, `InvalidContextTypeForRendererError`,
    `InvalidTemplateTypeForRendererError`, `NoOutputFileNameError`
  - `OutputFileExistsError` (also a `FileExistsError`)
  - `EmbedFileNotFound` (also a `FileNotFoundError`)
  - `TemplateRenderError` (has `template_path`; the original error is chained
    as `__cause__`)
  - `UnsafePurgeError`

Plain Jinja2 errors (e.g. syntax errors) outside of directory rendering are
raised as `jinja2.TemplateError`s; the CLI reports both kinds and exits with
code 3.

## License

MIT, see [LICENSE](LICENSE).
