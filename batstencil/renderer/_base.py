__all__ = [
    '_BaseRenderer',
]

import os
import sys
from pathlib import Path
from batutils.tpu import strimp
from batstencil.structs import *
from jinja2.ext import Extension
from allconf import quickloader

import logging
log = logging.getLogger(__name__)


class _BaseRenderer(IRenderer, abc.ABC):
    _VALID_CONTEXTS: Optional[Tuple[Type[IContext], ...]] = None
    _INVALID_CONTEXTS: Optional[Tuple[Type[IContext], ...]] = None

    _VALID_TEMPLATES: Optional[Tuple[Type[ITemplate], ...]] = None
    _INVALID_TEMPLATES: Optional[Tuple[Type[ITemplate], ...]] = None

    STENCIL_INFO_KEY = '__stencil__'
    """The name of the "dynamic context" variable added to every render"""

    def __init__(self, context: Optional[IContext] = None, template: Optional[ITemplate] = None, **kwargs):
        self._context: Optional[IContext] = None
        self._template: Optional[ITemplate] = None
        self._output_file_name: Optional[str] = None

        # Extra info added to the `__stencil__` context variable (e.g. by the
        # DirectoryRenderer) and extra context variables (e.g. the items of
        # `{% repeat_for %}` loops) layered on top of the context
        self.stencil_info: Dict[str, Any] = {}
        self.extra_context: Dict[str, Any] = {}

        # How `{% repeat_for %}` tags behave: `None` means they are not
        # supported (an error), `'raise'` means they raise `RepeatRendering`
        # (for the DirectoryRenderer to catch) and `'ignore'` means the loop
        # item has already been set so they do nothing
        self.repeat_mode: Optional[str] = None

        if kwargs:
            log.warning(f'Unrecognized kwargs for {self.__class__.__name__}: {kwargs}')
        self._search_paths: List[Path] = []
        self._load_search_paths()
        self._env: jinja2.Environment = self._make_environment()
        self._load_filters()

        # This is to trigger the Setters!
        if context is not None:
            self.context = context
        if template is not None:
            self.template = template

    def _make_environment(self) -> jinja2.Environment:
        env = jinja2.Environment(
            lstrip_blocks=True,
            trim_blocks=True,
            keep_trailing_newline=True,
            undefined=jinja2.ChainableUndefined,
            extensions=self._get_extensions(),
            loader=jinja2.FileSystemLoader([str(p) for p in self._search_paths], encoding='utf-8')
        )
        env.stencil_renderer = self
        return env

    def _get_extensions(self) -> List[Type[Extension]]:
        buffer_list = []
        extension_module = strimp.get_module('batstencil.jinjaext.extensions')
        for name, item in extension_module.__dict__.items():
            if name.startswith('_'):
                continue
            if isinstance(item, type) and issubclass(item, Extension):
                buffer_list.append(item)
        return buffer_list

    def _load_filters(self):
        filter_module = strimp.get_module('batstencil.jinjaext.filters')
        for name, item in filter_module.__dict__.items():
            if name.startswith('_'):
                continue
            if callable(item):
                self.jinja_environment.filters[name] = item

    def _add_search_path(self, path: Union[str, Path]):
        p = Path(path).absolute()
        if p not in self._search_paths:
            self._search_paths.append(p)

    def _load_search_paths(self):
        self._add_search_path(os.getcwd())  # Current Working Directory!
        self._add_search_path(Path(sys.argv[0] if sys.argv and sys.argv[0] else '.').parent)
        stp = os.environ.get('STENCIL_TEMPLATE_PATH', None)  # Extra paths! :D
        if stp:
            # Multiple paths are separated by `;` (or the OS path separator, e.g. `:` on Linux)
            for tp in stp.replace(os.pathsep, ';').split(';'):
                if tp.strip():
                    self._add_search_path(tp.strip())

    @property
    def search_paths(self) -> List[Path]:
        """The paths templates (for `{% include %}`, `{% extends %}` etc.) and
        embedded files are looked up in"""
        return list(self._search_paths)

    def _pre_flight(self):
        if not self.template:
            raise NoTemplateSetError(f'No template set for {self.__class__.__name__}')

    def _is_valid_context(self, context: IContext) -> bool:
        if self._INVALID_CONTEXTS:  # Deny?
            if isinstance(context, self._INVALID_CONTEXTS):
                return False

        if self._VALID_CONTEXTS:  # Allow?
            if isinstance(context, self._VALID_CONTEXTS):
                return True
            return False  # If there is an "allow list" then we deny everything else!
        return True

    def _is_valid_template(self, template: ITemplate) -> bool:
        if self._INVALID_TEMPLATES:  # Deny?
            if isinstance(template, self._INVALID_TEMPLATES):
                return False

        if self._VALID_TEMPLATES:  # Allow?
            if isinstance(template, self._VALID_TEMPLATES):
                return True
            return False  # If there is an "allow list" then we deny everything else!
        return True

    @property
    def context(self) -> Optional[IContext]:
        return self._context

    @context.setter
    def context(self, value: IContext):
        if not self._is_valid_context(value):
            raise InvalidContextTypeForRendererError(f'Context of {value.__class__.__name__} type does not work with a {self.__class__.__name__} Renderer')
        self._context = value

    @property
    def template(self) -> Optional[ITemplate]:
        return self._template

    @template.setter
    def template(self, value: ITemplate):
        if not self._is_valid_template(value):
            raise InvalidTemplateTypeForRendererError(f'Template of {value.__class__.__name__} type does not work with a {self.__class__.__name__} Renderer')
        value.set_renderer(self)
        self._template = value

    def get_render_context(self) -> Dict[str, Any]:
        """The variables the template is rendered with: the context, any extra
        context (e.g. `{% repeat_for %}` loop items) and `__stencil__`."""
        data = dict(self.context.as_dict()) if self.context is not None else {}
        data.update(self.extra_context)
        data[self.STENCIL_INFO_KEY] = self.get_stencil_info()
        return data

    def get_stencil_info(self) -> Dict[str, Any]:
        """The "dynamic context" available as `__stencil__` in templates"""
        from batstencil import __version__
        info: Dict[str, Any] = {
            'version': __version__,
            'template_name': None,
            'template_path': None,
        }
        file_path = getattr(self._template, 'get_file_path', None)
        if file_path is not None:
            p = file_path()
            info['template_name'] = p.name
            info['template_path'] = str(p.absolute())
        info.update(self.stencil_info)
        return info

    def describe_template(self) -> str:
        """A human readable description of the current template (for errors)"""
        file_path = getattr(self._template, 'get_file_path', None)
        if file_path is not None:
            return str(file_path())
        return f'<{self._template.__class__.__name__}>'

    def render(self):
        self._pre_flight()
        try:
            rendered_string = self._render_as_string()
        except CancelRendering:
            log.debug(f'Rendering of {self.describe_template()} cancelled by skip_if tag')
            return None
        except RepeatRendering:
            if self.repeat_mode == 'raise':
                raise
            raise RenderError(f'The repeat_for tag is only supported when rendering directories'
                              f' (in {self.describe_template()})')
        return self._output_rendered_results(rendered_string)

    @abc.abstractmethod
    def _output_rendered_results(self, rendered_string: str):
        pass

    @abc.abstractmethod
    def _render_as_string(self) -> str:
        pass

    @property
    def jinja_environment(self) -> jinja2.Environment:
        return self._env

    def is_template_loadable(self, template_name: str) -> bool:
        try:
            self.jinja_environment.get_template(template_name)
            return True
        except jinja2.TemplateNotFound:
            return False

    def get_embed(self, file_path: str, source_file: Optional[str] = None,
                  allconf: bool = False, env: bool = False, fidelius: bool = False, py: bool = False,
                  alviss: Optional[bool] = None, **kwargs) -> str:
        """Finds and reads a file to embed (via the `{% embed %}` tag).

        Relative paths are looked up relative to the template doing the
        embedding first, then in the search paths.

        :param allconf: Render the file with AllConf (`alviss` is a deprecated alias)
        :param env: Resolve `${__ENV__:...}` expressions (with `allconf`)
        :param fidelius: Resolve `${__FID__:...}` expressions (with `allconf`)
        :param py: Resolve `${__PY__:...}` expressions (with `allconf`)
        """
        if kwargs:
            log.warning(f'Unrecognized embed arguments: {kwargs}')
        allconf = bool(allconf or alviss)
        file_path = str(file_path)
        as_path = Path(file_path)
        if as_path.is_absolute():
            if not as_path.is_file():
                raise EmbedFileNotFound(f'Embed file not found via absolute path: {file_path}')
            return self._get_embed(file_path, allconf=allconf, env=env, fidelius=fidelius, py=py)

        search_paths = []

        if source_file:
            search_paths.append(Path(source_file).absolute().parent)

        search_paths += self._search_paths

        for p in search_paths:
            f = p / file_path
            if f.is_file():
                return self._get_embed(str(f.absolute()), allconf=allconf, env=env, fidelius=fidelius, py=py)

        raise EmbedFileNotFound(f'Embed file not found in any search path: {file_path}')

    def _get_embed(self, abs_file_path: str, allconf: bool = False, env: bool = False,
                   fidelius: bool = False, py: bool = False) -> str:
        if allconf:
            return quickloader.render_load(abs_file_path,
                                           skip_env_loading=not env,
                                           skip_fidelius=not fidelius,
                                           skip_py_inject=not py)

        else:
            with open(abs_file_path, 'r', newline=None, encoding='utf-8') as fin:
                return fin.read()

    def _default_output_file_name(self) -> Optional[str]:
        file_path = getattr(self._template, 'get_file_path', None)
        if file_path is not None:
            return file_path().name
        return None

    @property
    def output_file_name(self) -> Optional[str]:
        """The name of the file to render to: the one set by the
        `{% setfilename %}` tag (or explicitly) if any, otherwise a default
        (e.g. the template's file name)."""
        return self._output_file_name or self._default_output_file_name()

    @output_file_name.setter
    def output_file_name(self, value: Optional[str]):
        self._output_file_name = value or None
