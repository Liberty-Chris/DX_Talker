"""Generate the maintained desktop code for the official Python 3.4 runtime.

Only language syntax and explicitly named compatibility boundaries change.
The generated code is parsed using the 3.4 grammar before it can be packaged.
"""
import argparse
import ast
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
MODULES = {name: 'xp_support.' + name for name in
           ('dataclasses', 'pathlib', 'datetime', 'subprocess', 'queue', 'traceback', 'ssl', 'json')}
MODULES['re'] = 'xp_support.regex'


class Target34(ast.NodeTransformer):
    def __init__(self, filename):
        self.filename = str(filename).replace('\\', '/')
    def application_module(self, name):
        return self.filename.endswith('/dxtalker/' + name + '.py')
    def visit_ImportFrom(self, node):
        if node.module == 'qrcode.image.pure' and any(name.name == 'PyPNGImage' for name in node.names):
            node.module = 'xp_support.qr_image'
        if node.module == '__future__':
            node.names = [name for name in node.names if name.name != 'annotations']
            return node if node.names else None
        if node.module and node.module.startswith('platforms.xp.support'):
            node.module = 'xp_support' + node.module[len('platforms.xp.support'):]
        if not node.level and node.module in MODULES:
            node.module = MODULES[node.module]
        return node

    def visit_Import(self, node):
        for name in node.names:
            if name.name in MODULES:
                name.asname = name.asname or name.name
                name.name = MODULES[name.name]
        return node

    def visit_FunctionDef(self, node):
        if self.application_module('updates') and node.name == 'update_ssl_context':
            node.body = ast.parse('return ssl.create_default_context()').body
        if node.args.posonlyargs:
            raise ValueError('Positional-only parameters need an explicit XP adapter')
        for arg in (*node.args.args, *node.args.kwonlyargs):
            arg.annotation = None
        if node.args.vararg: node.args.vararg.annotation = None
        if node.args.kwarg: node.args.kwarg.annotation = None
        node.returns = None
        return self.generic_visit(node)

    def visit_ClassDef(self, node):
        fields = [statement.target.id for statement in node.body
                  if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)]
        record = any((isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == 'dataclass')
                     or isinstance(d, ast.Name) and d.id == 'dataclass' for d in node.decorator_list)
        node = self.generic_visit(node)
        if record:
            node.body.append(ast.Assign(targets=[ast.Name(id='__xp_fields__', ctx=ast.Store())],
                                        value=ast.Tuple(elts=[ast.Constant(name) for name in fields], ctx=ast.Load())))
        return node

    def visit_Expr(self, node):
        node = self.generic_visit(node)
        if self.application_module('app') and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute) and node.value.func.attr == 'SetCurrentProcessExplicitAppUserModelID':
            return ast.Try(body=[node],handlers=[ast.ExceptHandler(type=ast.Name(id='AttributeError',ctx=ast.Load()),name=None,body=[ast.Pass()])],orelse=[],finalbody=[])
        return node

    def visit_AnnAssign(self, node):
        if node.value is None:
            return None
        return ast.Assign(targets=[node.target], value=self.visit(node.value))

    def visit_JoinedStr(self, node):
        values = []
        for value in node.values:
            if isinstance(value, ast.Constant):
                values.append(value)
            else:
                expression = self.visit(value.value)
                if value.conversion != -1:
                    expression = ast.Call(func=ast.Name(id={115: 'str', 114: 'repr', 97: 'ascii'}[value.conversion], ctx=ast.Load()), args=[expression], keywords=[])
                spec = self.visit(value.format_spec) if value.format_spec else ast.Constant('')
                values.append(ast.Call(func=ast.Name(id='format', ctx=ast.Load()), args=[expression, spec], keywords=[]))
        return ast.Call(func=ast.Attribute(value=ast.Constant(''), attr='join', ctx=ast.Load()),
                        args=[ast.List(elts=values, ctx=ast.Load())], keywords=[])

    def visit_Dict(self, node):
        node = self.generic_visit(node)
        if None not in node.keys:
            return ast.Call(func=ast.Name(id='_xp_ordered', ctx=ast.Load()), args=[ast.List(elts=[ast.Tuple(elts=[key,value],ctx=ast.Load()) for key,value in zip(node.keys,node.values)],ctx=ast.Load())], keywords=[])
        pieces = [value if key is None else ast.Dict(keys=[key], values=[value])
                  for key, value in zip(node.keys, node.values)]
        return ast.Call(func=ast.Name(id='_xp_merge', ctx=ast.Load()), args=pieces, keywords=[])

    def visit_DictComp(self, node):
        node = self.generic_visit(node)
        pairs = ast.GeneratorExp(elt=ast.Tuple(elts=[node.key,node.value],ctx=ast.Load()),generators=node.generators)
        return ast.Call(func=ast.Name(id='_xp_ordered',ctx=ast.Load()),args=[pairs],keywords=[])

    def _sequence(self, node, kind):
        node = self.generic_visit(node)
        if not any(isinstance(value, ast.Starred) for value in node.elts):
            return node
        pieces = [value.value if isinstance(value, ast.Starred) else ast.List(elts=[value], ctx=ast.Load()) for value in node.elts]
        flat = ast.Call(func=ast.Name(id='_xp_unpack', ctx=ast.Load()), args=pieces, keywords=[])
        return flat if kind == 'list' else ast.Call(func=ast.Name(id=kind, ctx=ast.Load()), args=[flat], keywords=[])

    def visit_List(self, node): return self._sequence(node, 'list')
    def visit_Tuple(self, node): return self._sequence(node, 'tuple')
    def visit_Set(self, node): return self._sequence(node, 'set')

    def visit_Call(self, node):
        node = self.generic_visit(node)
        if self.application_module('source') and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == 'request' and node.func.attr == 'build_opener':
            node.args.append(ast.parse('request.HTTPSHandler(context=ssl.create_default_context())', mode='eval').body)
        if isinstance(node.func, ast.Attribute) and node.func.attr == 'isascii' and not node.args and not node.keywords:
            return ast.Call(func=ast.Name(id='_xp_isascii',ctx=ast.Load()),args=[node.func.value],keywords=[])
        if self.application_module('diagnostics') and isinstance(node.func, ast.Attribute) and node.func.attr == 'OpenProcess' and len(node.args) == 3 and isinstance(node.args[0],ast.Constant) and node.args[0].value == 0x1000:
            node.args[0] = ast.Constant(0x400)
        if any(isinstance(value, ast.Starred) for value in node.args):
            pieces = [value.value if isinstance(value, ast.Starred) else ast.List(elts=[value], ctx=ast.Load()) for value in node.args]
            node.args = [ast.Starred(value=ast.Call(func=ast.Name(id='_xp_unpack', ctx=ast.Load()), args=pieces, keywords=[]), ctx=ast.Load())]
        if sum(item.arg is None for item in node.keywords) > 1 or any(item.arg is None for item in node.keywords) and len(node.keywords) > 1:
            pieces = [item.value if item.arg is None else ast.Dict(keys=[ast.Constant(item.arg)], values=[item.value]) for item in node.keywords]
            node.keywords = [ast.keyword(arg=None, value=ast.Call(func=ast.Name(id='_xp_keywords', ctx=ast.Load()), args=pieces, keywords=[]))]
        return node


def transform(text, filename='<generated>'):
    tree = Target34(filename).visit(ast.parse(text, filename=filename))
    helper = ast.parse('from xp_support.runtime import merge as _xp_merge, unpack as _xp_unpack, keywords as _xp_keywords, ordered as _xp_ordered, isascii as _xp_isascii').body[0]
    position = 1 if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant) and isinstance(tree.body[0].value.value, str) else 0
    while position < len(tree.body) and isinstance(tree.body[position], ast.ImportFrom) and tree.body[position].module == '__future__':
        position += 1
    tree.body.insert(position, helper)
    ast.fix_missing_locations(tree)
    result = ast.unparse(tree) + '\n'
    ast.parse(result, filename=filename, feature_version=(3, 4))
    return result


def build(destination, with_tests=False):
    destination = Path(destination).resolve()
    if destination == ROOT or ROOT in destination.parents and 'build' not in destination.relative_to(ROOT).parts:
        raise ValueError('Use a separate build directory')
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / 'platforms/xp/support', destination / 'xp_support', dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
    trees = ['dxtalker'] + (['tests', 'scripts'] if with_tests else [])
    for name in trees:
        for path in (ROOT / name).rglob('*.py'):
            target = destination / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            content = transform(path.read_text(encoding='utf-8'), str(path))
            if path.name == 'audio.py' and name == 'dxtalker':
                content += '\nfrom xp_support.winmm import AudioOutput\nfrom xp_support.sapi import WindowsSpeech\n'
            if path.name == 'ptt.py' and name == 'dxtalker':
                content += '\nfrom xp_support.serial import SerialPTT, serial_ports\n'
            if path.name == 'updates.py' and name == 'dxtalker':
                content += '\nINSTALLER = "DXTalker-Setup-Windows-XP-" + ("32bit" if struct.calcsize("P") == 4 else "64bit") + ".exe"\n'
            if path.name == 'app.py' and name == 'dxtalker':
                content = content.replace('Windows pilot', 'Windows XP pilot')
            target.write_text(content, encoding='utf-8')
    for name in ('assets', 'docs/help'):
        shutil.copytree(ROOT / name, destination / name, dirs_exist_ok=True)
    if with_tests:
        shutil.copytree(ROOT / 'tests/fixtures', destination / 'tests/fixtures', dirs_exist_ok=True)
        shutil.copytree(ROOT / 'android/app/src/test/resources', destination / 'android/app/src/test/resources', dirs_exist_ok=True)
        reference = Path('android/app/src/main/java/club/dxtalker/android/SpotFilters.kt')
        (destination / reference).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / reference, destination / reference)
    (destination / 'sounddevice.py').write_text('from xp_support.sounddevice import query_devices, query_hostapis, RawInputStream\n',encoding='utf-8')
    (destination / 'run_xp.py').write_text("import os, sys\nsys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\nimport xp_support.bootstrap\nif len(sys.argv)==3 and sys.argv[1]=='--self-test':\n from xp_support.selftest import run\n raise SystemExit(run(sys.argv[2]))\nfrom dxtalker.app import main\nmain()\n",encoding='utf-8')
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('--tests', action='store_true')
    options = parser.parse_args()
    print(build(options.out, options.tests))
