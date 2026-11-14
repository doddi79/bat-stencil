# batstencil Public API Index

- Distribution: `batstencil` (PyPI) — Import: `batstencil` — Console script: `bat-stencil` (also `python -m batstencil`)
- Covers: version **1.0.0**
- Depends on: `batutils >=2.2,<3`, `allconf >=4.0.2,<5` (see its [API index](https://github.com/doddi79/allconf/blob/main/docs/api-index.md)), `jinja2 >=3.1,<4`. Optional extra `batstencil[fidelius]` for `${__FID__:...}` secrets.
- Python 3.10+

`batstencil` renders Jinja2 templates (a string, a file or a whole directory
tree) with a context that can come from an AllConf YAML/JSON file, a dict,
kwargs or command line arguments. Typical uses: project scaffolding /
bootstrapping, CI/CD and Kubernetes manifests.

**Preferred import:** `from batstencil.stencils import *` — it re-exports every
context, template and renderer class and `render_stencil`. Errors live in
`batstencil.structs` (`from batstencil.structs import StencilError, ...`).

## Find it by task

| I want to… | Use | Section |
|------------|-----|---------|
| Render a template string/file to a `str` in one call | `render_stencil(template, context)` | [Shortcut](#shortcut) |
| Use a YAML/JSON (AllConf) file as the variables | `AllConfContext(path)` | [Contexts](#contexts) |
| Use a dict or kwargs as the variables | `DictContext(d)`, `KeyWordArgumentContext(**kw)` | [Contexts](#contexts) |
| Override/add a (nested) variable, e.g. `app.name=x` | `ctx.nested_update('app.name', 'x')`, CLI `-a app.name=x` | [Contexts](#contexts) |
| Render to a file / print to stdout | `FileRenderer`, `StdOutRenderer` | [Renderers](#renderers) |
| Scaffold / generate a whole project from a template folder | `DirectoryTemplate` + `DirectoryRenderer`, CLI `-d` | [Directory rendering](#directory-rendering) |
| Name the output file (or folder) dynamically | `{% setfilename %}...{% endsetfilename %}` | [Template tags](#template-tags-and-filters) |
| Skip a file or folder conditionally | `{% skip_if cond %}` | [Template tags](#template-tags-and-filters) |
| Generate one folder/file per list item (loop, foreach, "for each gateway") | `{% repeat_for item in items %}` | [Template tags](#template-tags-and-filters) |
| Paste a file's contents verbatim (e.g. a config into a ConfigMap) | `{% embed 'file', indent=4 %}` | [Template tags](#template-tags-and-filters) |
| Base64 encode a value (Kubernetes Secrets) | `{{ value\|base64 }}` | [Template tags](#template-tags-and-filters) |
| Know the current template's name/path/loop index inside a template | `__stencil__` variable | [`__stencil__`](#the-__stencil__-variable) |
| Use `{% include %}` / `{% extends %}` / find templates by name | search paths, `STENCIL_TEMPLATE_PATH` | [Search paths](#search-paths) |
| Run it from the shell | `bat-stencil -i ctx.yaml -t tpl -o out` | [CLI](#cli) |
| Catch errors / find which template failed | `StencilError`, `TemplateRenderError` | [Errors](#errors) |

---

## Shortcut

```python
from batstencil.stencils import render_stencil
render_stencil('Hi {{ name }}', {'name': 'Bob'})          # 'Hi Bob'
render_stencil(Path('tpl.txt'), 'context.yaml')          # file template, AllConf context
```

| Signature | Result / behavior |
|-----------|-------------------|
| `render_stencil(template: str \| Path \| ITemplate, context: None \| dict \| str \| Path \| IContext = None) -> Optional[str]` | Renders with a `StringRenderer`. Returns `None` if the template hit `{% skip_if %}`. |
| `guess_template_by_argument(template, renderer=None) -> ITemplate` (`batstencil.utils`) | `ITemplate` → as-is; `Path` → `FileTemplate`; multi-line `str` → `StringTemplate`; single-line `str` → `FileTemplate` if it's a template name loadable from the [search paths](#search-paths) or an existing file path, else `StringTemplate`. |
| `guess_context_by_argument(context) -> IContext` (`batstencil.utils`) | `IContext` → as-is; `None` → empty `DictContext`; `Mapping` → `DictContext` (shallow copy); `str`/`Path` → `AllConfContext`. |

Caveat: a single-line string that happens to match an existing file name is
treated as a file path. Pass `StringTemplate(...)` explicitly to avoid guessing.

## Contexts

Import from `batstencil.stencils` (defined in `batstencil.context`). All implement `IContext`.

| Signature | Notes |
|-----------|-------|
| `DictContext(context_map: dict = None)` | Wraps (does **not** copy) the dict; updates mutate it. |
| `KeyWordArgumentContext(**kwargs)` | `DictContext` from kwargs. |
| `AllConfContext(file_name: str \| Path)` | Loads with `allconf.quickloader.autoload` (includes, `__extends__`, `${...}` refs, `${__ENV__:X}`, `${__PY__:mod.attr}` are resolved at load). `.file_name` property. |
| `AlvissContext` | **Deprecated** alias of `AllConfContext`. |
| `ctx.update(key, value)` | Sets a top-level key. |
| `ctx.nested_update(key: str \| Sequence[str], value)` | Dotted string (`'a.b.c'`) or key sequence; creates missing intermediate dicts. |
| `ctx.as_dict() -> dict` | The variables (unmasked for AllConf, i.e. secrets included). |

Source: [batstencil/context](../batstencil/context).

## Templates

| Signature | Notes |
|-----------|-------|
| `StringTemplate(template_string: str)` | |
| `FileTemplate(file_path: str \| Path)` | A `str` is first tried as a template name in the [search paths](#search-paths), then as a path; a `Path` is always a path. Read as UTF-8; compiled with its file name (so errors/tracebacks name the file and `{% embed %}` looks next to it). `.file_name`, `.get_file_path()`. Raises `TemplateNotFoundError` on render if missing. |
| `DirectoryTemplate(dir_path: str \| Path)` | Crawls the tree at construction (sorted). Raises `TemplateNotFoundError` if missing/not a dir and `TemplateError` if the root contains `__stencil_meta__`. `.files`, `.directories`, `.meta_file`, `.source_path`, `.absolute_source_path`, `.dump()`. Only usable with `DirectoryRenderer`. |

## Renderers

All take `(context=None, template=None, ...)` and can also have `.context` /
`.template` assigned later; call `.render()`. Setting an incompatible template
raises `InvalidTemplateTypeForRendererError`; rendering with no template raises
`NoTemplateSetError`. No context = empty variables.

| Signature | `render()` returns |
|-----------|--------------------|
| `StringRenderer(context=None, template=None)` | The rendered `str`, or `None` if skipped. |
| `StdOutRenderer(context=None, template=None)` | `None`; prints the result (nothing if skipped). |
| `FileRenderer(output_path: str \| Path, context=None, template=None, overwrite=True, new_line_char='\n')` | Absolute path `str` of the written file, or `None` if skipped. |
| `DirectoryRenderer(output_path: str \| Path, context=None, template=None, overwrite=True, purge=True, new_line_char='\n')` | `List[str]` of absolute paths written. See [Directory rendering](#directory-rendering). |

`FileRenderer` details:
- `output_path` ending with `/` or `\`, or an existing directory → output
  directory; the file name is the `{% setfilename %}` value, else the template's file name.
- Otherwise `output_path` is the file; `{% setfilename %}` still overrides the name
  (same directory). An empty `setfilename` result logs a warning and is ignored.
- `overwrite=False` → `OutputFileExistsError` if the file exists. Parent
  directories are created. Output is UTF-8 with `new_line_char` line endings.

Other renderer members: `.jinja_environment` (the `jinja2.Environment`),
`.search_paths`, `.output_file_name`, `.get_render_context()`,
`.is_template_loadable(name)`. Jinja settings: `trim_blocks`, `lstrip_blocks`,
`keep_trailing_newline`, `undefined=ChainableUndefined` (missing and missing-nested
values render as empty instead of raising).

Source: [batstencil/renderer](../batstencil/renderer).

## Directory rendering

```python
from batstencil.stencils import *
r = DirectoryRenderer('build/', context=AllConfContext('ctx.yaml'),
                      template=DirectoryTemplate('templates/'))
written = r.render()
```

- Every file in the tree is rendered as a template into the same relative place.
- A `__stencil_meta__` file in a sub-directory (not the root) is rendered to
  decide that directory's fate: `{% setfilename %}` renames it, `{% skip_if %}`
  skips it and everything in it, `{% repeat_for %}` makes one copy per item
  (loop variables are visible to everything inside, including nested dirs).
  The meta file itself is not written.
- `purge=True` (default) deletes `output_path` first. It raises
  `OutputFileExistsError` if it exists and `overwrite=False`, and
  `UnsafePurgeError` if `output_path` is a file system root, the home dir, the
  current working directory or one of its parents, or contains the template
  directory. Use `purge=False` to render into an existing directory.
- A file name / dir name that resolves outside `output_path` (e.g. `../x`)
  raises `TemplateRenderError`.
- Any failure while rendering a template is raised as `TemplateRenderError`
  (message has the template path and line; `.template_path`; original
  exception as `__cause__`). `StencilError`s pass through unchanged.
- `repeat_for` copies with duplicate names raise `TemplateRenderError`.

Example (`templates/gateways/__stencil_meta__`):

```jinja
{% repeat_for gw in gateways %}
{% setfilename %}{{ gw.name }}_gateway{% endsetfilename %}
```

Tests: [tests](../tests) (directory and repeat tests).

## Template tags and filters

Available in every renderer (registered from `batstencil.jinjaext`).

| Syntax | Behavior |
|--------|----------|
| `{% skip_if <expr> %}` | If truthy, the template (or directory in `__stencil_meta__`) is not rendered: `render()` returns `None` / no file is written. |
| `{% setfilename %}<template code>{% endsetfilename %}` | Sets the output file (or directory) name to the stripped body. Empty → warning, default name used. Ignored by `StringRenderer`/`StdOutRenderer` output. |
| `{% repeat_for x in <expr> %}` / `{% repeat_for k, v in d.items() %}` | **`DirectoryRenderer` only** (elsewhere raises `RenderError`). Renders the file or (in `__stencil_meta__`) directory once per item with `x` (or `k`, `v`) added to the context. Empty/undefined iterable → nothing rendered. Combine with `setfilename`. |
| `{% embed <path>[, indent=N][, allconf=True][, env=True][, fidelius=True][, py=True] %}` | Inserts the file's contents verbatim (not a template). Relative paths are looked up next to the embedding template first, then in the search paths; `EmbedFileNotFound` if missing. `indent` prefixes every line with N spaces. `allconf=True` first renders the file through `allconf.quickloader.render_load` (`env`/`fidelius`/`py` enable `${__ENV__}`/`${__FID__}`/`${__PY__}`). `alviss=True` is a **deprecated** alias of `allconf=True`. The path may be a variable. |
| `{{ value\|base64 }}` | Base64 of the UTF-8 value (or `bytes`) as a single line. |

## The `__stencil__` variable

Every render gets a `__stencil__` dict (a context key of that name is overwritten):

| Key | Value |
|-----|-------|
| `version` | batstencil version |
| `template_name`, `template_path` | File name / absolute path of a `FileTemplate` (`None` for strings) |
| `template_root` | *(directory rendering)* absolute template root |
| `template_relative_path` | *(dir)* posix path of the template relative to the root, e.g. `gateways/impl.py` |
| `source_dir` | *(dir)* posix source directory relative to the root (`.` for root) |
| `output_root` | *(dir)* absolute output directory |
| `output_dir` | *(dir)* posix target directory relative to `output_root` (after renames) |
| `loop` | *(dir)* innermost `repeat_for` info: `index`, `index0`, `first`, `last`, `length`, `item`; `None` outside loops |
| `loops` | *(dir)* list of all enclosing loop infos, outermost first |

## Search paths

Used by `FileTemplate` name lookup, `{% include %}`/`{% extends %}`/`{% import %}`
and `{% embed %}`: the current working directory, the directory of `sys.argv[0]`,
then each entry of the `STENCIL_TEMPLATE_PATH` environment variable (separated by
`;` or `os.pathsep`). Read when the renderer is created.

## CLI

`bat-stencil [-i CONTEXT_FILE] [-a key=value ...] (-t FILE | -s STRING | -d DIR) [-o OUTPUT] [--no-overwrite] [--no-purge] [-v] [--version]`

- `-i` AllConf context file; `-a` adds/overrides variables (dotted keys nest; values are strings).
- No `-o` → print to stdout; `-o path/` (trailing slash) → directory; `-d` requires `-o`.
- Prints `Wrote file: <path>` per file written. Errors print to stderr and exit with code 3.
- The current directory is added to `sys.path` (for `${__PY__:...}` in context files).

Source: [batstencil/cli/bat_stencil](../batstencil/cli/bat_stencil); programmatic equivalent: `batstencil.cli.bat_stencil._runner.StencilRunner`.

## Errors

From `batstencil.structs`:

- `StencilError`
  - `TemplateError` → `TemplateNotFoundError` (also `FileNotFoundError`)
  - `ContextError` (e.g. bad `-a` argument)
  - `RenderError` → `NoTemplateSetError`, `InvalidContextTypeForRendererError`,
    `InvalidTemplateTypeForRendererError`, `OutputFileExistsError` (also
    `FileExistsError`), `NoOutputFileNameError`, `EmbedFileNotFound`,
    `TemplateRenderError`, `UnsafePurgeError`
- `CancelRendering` / `RepeatRendering`: internal control flow of `skip_if` /
  `repeat_for`, caught by the renderers (not `StencilError`s).
- Jinja2 errors (`jinja2.TemplateSyntaxError`, `UndefinedError`, ...) propagate
  as-is from the string/file renderers; the `DirectoryRenderer` wraps them in
  `TemplateRenderError`.

## Extending

Interfaces in `batstencil.structs.interfaces`: `IContext` (implement
`update`, `nested_update`, `as_dict`), `ITemplate` (`get_jinja_template`),
`IRenderer`. New tags/filters are discovered from `batstencil.jinjaext.extensions`
/ `batstencil.jinjaext.filters` (public names only); there is no plugin hook for
third-party extensions — add them via `renderer.jinja_environment` instead.
