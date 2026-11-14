__all__ = [
    'StencilRunner',
]
import os
import sys
from batstencil.structs import *
from batstencil.stencils import *
import logging
log = logging.getLogger(__name__)


class StencilRunner:
    """Runs the `bat-stencil` command line (also usable from code)"""
    def __init__(self):
        self.verbose: bool = False

        self.template: Optional[str] = None
        self.string_template: Optional[str] = None
        self.directory_template: Optional[str] = None

        self.input: Optional[str] = None
        self.additional_arg_list: List[str] = []

        self.output: Optional[str] = None
        self.no_overwrite: bool = False
        self.no_purge: bool = False

    def _make_cwd_importable(self):
        cwd = os.getcwd()
        log.debug(f'os.getcwd()={cwd}')
        if cwd not in sys.path:
            sys.path.append(cwd)

    def run(self):
        self._make_cwd_importable()
        rnd = self.get_renderer()
        rnd.template = self.get_template()
        rnd.context = self.get_context()
        res = rnd.render()
        if self.output:
            if isinstance(res, list):
                for f in res:
                    print(f'Wrote file: {f}')
            elif res is None:
                print('Skipped rendering (skip_if)')
            else:
                print(f'Wrote file: {res}')

    def get_template(self) -> ITemplate:
        if self.directory_template:
            return DirectoryTemplate(self.directory_template)
        elif self.template:
            return FileTemplate(self.template)
        else:
            return StringTemplate(self.string_template)

    def _parse_arg(self, arg_str: str) -> Tuple[str, str]:
        log.debug(f'_parse_arg({arg_str})')
        if '=' not in arg_str:
            raise ContextError(f'Invalid argument "{arg_str}", expected key=value (e.g. -a foo=bar)')
        key, value = arg_str.split('=', maxsplit=1)
        if not key.strip():
            raise ContextError(f'Invalid argument "{arg_str}", the key is empty')
        return key.strip(), value

    def get_context(self) -> IContext:
        if self.input:
            ctx = AllConfContext(self.input)
        else:
            ctx = DictContext()

        if self.additional_arg_list:
            for arg in self.additional_arg_list:
                ctx.nested_update(*self._parse_arg(arg))
        return ctx

    def get_renderer(self) -> IRenderer:
        if self.directory_template:
            if not self.output:
                raise RenderError('Must specify output directory for directory rendering')
            return DirectoryRenderer(output_path=self.output,
                                     overwrite=not self.no_overwrite,
                                     purge=not self.no_purge)
        elif self.output:
            return FileRenderer(self.output,
                                overwrite=not self.no_overwrite)
        else:
            return StdOutRenderer()
