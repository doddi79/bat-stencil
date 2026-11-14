# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-11-14

Forking and Renaming: this is a continuation fork of CCP Games'
[`ccp-stencil`](https://github.com/ccpgames/ccp-stencil) (`ccpstencil` 0.8.0).

### Changed

- **Renamed**: the package _and_ module are now called `batstencil` and the
  command line tool `bat-stencil` (it can also be run via `python -m batstencil`)
- Now depends on [`batutils`](https://github.com/doddi79/batutils) (instead of
  `ccptools`) and [`allconf`](https://github.com/doddi79/allconf) (instead of
  `alviss`), and requires Python 3.10+ (tested on 3.10-3.14)
- `AlvissContext` is now `AllConfContext` (`AlvissContext` is kept as a
  deprecated alias) and the `{% embed %}` tag's `alviss=True` argument is now
  `allconf=True` (`alviss=True` still works)
- `render()` of the `DirectoryRenderer` (and the command line) now returns/
  prints the paths of the files actually written, i.e. with names set via
  `{% setfilename %}`, not the template names
  ([ccp-stencil#10](https://github.com/ccpgames/ccp-stencil/issues/10))
- Directory templates are crawled in sorted order (so rendering is deterministic)
- Templates, embedded files and rendered output are read/written as UTF-8
- The `FileRenderer` also treats an existing directory as an output directory
  (not only paths ending with a slash)
- `render_stencil()` and `guess_context_by_argument()` accept no context (or
  `None`) as well as `IContext` and `ITemplate` instances
- `DirectoryTemplate.target_name`, `target_path` and `skip_me` were removed
  since the names (and copies) of directories are now decided while rendering
  (see `{% repeat_for %}`)
- Loggers are now named after their modules (`batstencil.*`)
- Modernized packaging (`pyproject.toml` license metadata, `python -m build`)
  and the GitHub workflows (unit tests on Python 3.10-3.14 for pushes to `main`
  and all pull requests and a PyPI release workflow that checks that the
  release tag matches the package version)

### Added

- A `{% repeat_for item in items %}` tag (and `{% repeat_for k, v in d.items() %}`)
  that makes the `DirectoryRenderer` render a directory (when used in its
  `__stencil_meta__` file) or a file once per item, with the loop variables in
  the context of everything inside it (use `{% setfilename %}` to name each
  copy) ([ccp-stencil#11](https://github.com/ccpgames/ccp-stencil/issues/11))
- A `__stencil__` "dynamic context" variable in every template with the
  `version`, `template_name` and `template_path` and, when rendering
  directories, the `template_root`, `template_relative_path`, `source_dir`,
  `output_root`, `output_dir` and `{% repeat_for %}` info (`loop` and `loops`)
  ([ccp-stencil#14](https://github.com/ccpgames/ccp-stencil/issues/14))
- A `TemplateRenderError` raised by the `DirectoryRenderer` naming the template
  (and line) that failed to render, and template file names in Jinja2 errors
  and tracebacks in general (`FileTemplate` now compiles with the file name)
  ([ccp-stencil#12](https://github.com/ccpgames/ccp-stencil/issues/12))
- A warning when `{% setfilename %}` renders an empty name (which is ignored)
  ([ccp-stencil#15](https://github.com/ccpgames/ccp-stencil/issues/15))
- `py=True` for the `{% embed %}` tag (resolving `${__PY__:...}` with `allconf=True`)
- An `UnsafePurgeError`: the `DirectoryRenderer` now refuses to purge (delete)
  the current working directory or any of its parents, the home directory, a
  file system root or a directory containing the template
- `--version` for the command line and nicer command line errors for template
  errors and `-a` arguments without a `=`
- A `fidelius` extra (`pip install batstencil[fidelius]`)
- A task-oriented [Public API index](docs/api-index.md) (for humans and LLMs alike)

### Fixed

- The `base64` filter split values longer than 57 bytes into multiple lines
  (it now always returns a single line, and accepts `bytes`)
- The `FileRenderer` rendered every template twice
- The `{% embed %}` tag ignored `fidelius=True` and didn't look for files
  relative to the template doing the embedding
- `AlvissContext.update()` crashed
- `StringRenderer` (and thus `render_stencil`) crashed when no context was set
- An empty `{% setfilename %}` in a template rendered with a `FileRenderer`
  ignored the output file name given to the renderer
- `-a` command line arguments without a `=` crashed with a `TypeError`
- `STENCIL_TEMPLATE_PATH` only supported `;` as a separator (the OS path
  separator, e.g. `:` on Linux, now works too)

### Removed

- Leftover sandbox/scratch files from the repo root


## [0.8.0] - 2024-06-04

## Changed

- `FileRenderer` (and thus `DirectoryRenderer`) now use `\n` line endings in the 
  resulting file. This should probably just be an option with the default being
  to preserve the line ending format of the template file, but since this is 
  being used to render files that should run on Linux and apparently incorrect 
  line endings mess up the shebang reading and sh*t like that so I'm applying 
  this "sh*t fix" for now. 

## [0.7.0] - 2024-05-30

## Added

- A new `DirectoryRenderer` and `DirectoryTemplate` to render entire directories
  of templates in one go
- Support for `{% skip_if %}` and `{% setfilename %}` tags to control directory 
  names and skipping by adding them to a file called `__stencil_meta__` placed in
  any directory in a `DirectoryTemplate`
- The ability to run directory rendering via command line with the `-d` flag


## [0.6.0] - 2024-05-30

## Added

- A new `{% setfilename %}` tag where you can set the desired filename of the 
  rendered file dynamically in the tags body with normal template code e.g. 
  using the template context

## Changed

- The `FileRenderer` can now define a directory as output location which will 
  result in the rendered file to be the same as the input template file name 
  (if any) unless set explicitly via the `{% setfilename %}` tag.


## [0.5.1] - 2024-05-30

## Fixed

- FileRenderer was hitting an infinite loop
- Added dynamic path extension to include cwd to enable `${__PY__:...}` 
  injecting from project roots


## [0.5.0] - 2024-05-30

## Changed

- Bumped the version requirement of Alviss to 3.3 to get support for the new 
  `${__PY__:...}` expressions in order to inject module versions into Alviss 
  contexts for CI/CD manifests


## [0.4.0] - 2024-05-30

### Added

- New Extension that adds a `{% skip_if %}` tag where you can insert any 
  condition (e.g. checking the Context) and if it evals as True, a 
  `CancelRendering` exception is raised and caught by the Renderers causing 
  them to silently just skip rendering that template.
  - The `StringRenderer` returns `None`
  - The `StoutRenderer` prints out nothing
  - The `FileRenderer` doesn't create an output file
- Added unittests for the `{% skip_if %}` tag


## [0.3.0] - 2024-05-28

### Fixed

- A bug in the `guess_template_by_argument` method that raised exceptions while 
  checking to see if a given string could be interpreted as a path to an 
  existing file (which should be allowed to fail silently and then the string 
  returned as a `StringTemplate`)


## [0.2.0] - 2024-05-28

Embedding Extension & Base64 Filter update

### Added

- The `EmbedExtension` to the Jinja2 environment used that enables using the 
  `{% embed 'my_file.txt' %}` to embed the requested file "as-is" (so not 
  parsed as a template or anything like that) into templates wholesale with 
  these optional arguments:
  - `indent` (default: 0) to indent each line of the embedded file by a certain
    number of spaces, e.g. for embedding into YAML files, where indent is 
    syntactically important
  - `alviss` (default: `False`) to run the embedded file though the Alviss 
    "render_loader" before embedding the results
  - `env` (default: `False`) to make the Alviss parser render `${__ENV__:...}` 
    expressions
  - `fidelius` (default: `False`) to make the Alviss parser render 
    `${__FID__:...}` expressions
- The main use case here was considered things like creating Kubernetes File 
  Config maps where e.g. config file content is embedded wholesale into the 
  manifest's YAML
- The `base64` filter to the Jinja2 environment used to quicly encode context 
  variables as base64 encoded strings
  - The main use case here was considered things like rendering of Kubernetes 
    Secret manifests where keys need to be base64 encoded  
- A "shortcut" method called `render_stencil` for quicly rendering to `str` (via
  the `StringRenderer`) in code that takes two simple kwargs called `template` 
  and `context` and will use the appropriate Template and Context 
  implementations based on the type and/or value of those arguments (see below)
- Two utility functions that attempt to instantiate the appropriate Template and 
  Context types based on the argument types supplied as `template` and 
  `context`:
  - A template that is an instance of `pathlib.Path` will be a `FileTemplate`
  - A template that is a multi-line `str` will be a `StringTemplate`
  - A template that is a single-line `str` will:
    - First attempt to see if it refers to a template name that Jinja2 can load, 
      and return a `FileTemplate` if so
    - Then it'll see if the string can be interpreted as a file system path to a 
      file that exists, and then return a `FileTemplate`
    - If all that fails, it'll just assume the `str` is the template itself and 
      return a `StringTemplate`
  - A context that is an instance of `pathlib.Path` or a `str` will be an 
    `AlvissContext`
  - A context that is a `dict` will be a `DictContext`
- A bunch of "proper" unittests for the new embedding and filter functions

### Changed

- The `FileTemplate` now uses the Jinja2 environment's `FileSystemLoader`, 
  pre-seeded with search paths of the current working directory (`os.getcwd()`) 
  as well as the root directory of the script being executed (`sys.argv[0]`) 
  plus whatever paths are defined in the `STENCIL_TEMPLATE_PATH` environment 
  variable, if any (multiple paths seperated by `;`)
  - This change enables and vastly simplifies using the Jinaj2 built in 
    expressions like `{% extends ... %}` and `{% include ... %}` "out of the 
    box" so to speak as well as making custom `{% marcro ... %}` files to 
    include.


## [0.1.0] - 2024-05-24

Initial release

### Added

- The project in its entirety
- Template types:
  - `FileTemplate`
  - `StringTemplate`
- Context types:
  - `DictContext`
  - `KeyWordArgumentContext`
  - `AlvissContext`
- Renderer Types
  - `StringRenderer`
  - `StdOutRenderer`
  - `FileRenderer`
