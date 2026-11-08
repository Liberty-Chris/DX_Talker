"""Frozen record operations used by the shared application, on Python 3.4.

Field names come exclusively from the checked build transformation. Defaults
are supplied as objects rather than interpolated into generated Python code.
"""
import copy

MISSING = object()

class FrozenInstanceError(AttributeError):
    pass

class Field:
    def __init__(self, name, default=MISSING):
        self.name, self.default = name, default
        self.type = type(default) if default is not MISSING else None


def fields(value):
    cls = value if isinstance(value, type) else type(value)
    try: return cls.__xp_record_fields__
    except AttributeError: raise TypeError('Expected an application record')


def dataclass(cls=None, frozen=False):
    def decorate(cls):
        record_fields = tuple(Field(name, getattr(cls, name, MISSING)) for name in cls.__xp_fields__)
        cls.__xp_record_fields__ = record_fields
        namespace = {'_set': object.__setattr__}
        parameters = ['self']
        statements = []
        for index, item in enumerate(record_fields):
            parameter = item.name
            if item.default is not MISSING:
                key = '_default' + str(index)
                namespace[key] = item.default
                parameter += '=' + key
            parameters.append(parameter)
            statements.append('    _set(self, ' + repr(item.name) + ', ' + item.name + ')')
        if hasattr(cls, '__post_init__'): statements.append('    self.__post_init__()')
        source = 'def __init__(' + ','.join(parameters) + '):\n' + '\n'.join(statements or ['    pass'])
        exec(compile(source, '<XP record constructor>', 'exec'), namespace)
        cls.__init__ = namespace['__init__']
        names = tuple(item.name for item in record_fields)
        def values(instance): return tuple(getattr(instance, name) for name in names)
        def equal(self, other):
            if type(self) is not type(other): return NotImplemented
            return values(self) == values(other)
        def representation(self):
            return cls.__name__ + '(' + ', '.join(name + '=' + repr(getattr(self, name)) for name in names) + ')'
        cls.__eq__, cls.__repr__ = equal, representation
        if frozen:
            def immutable(self, name, value=None): raise FrozenInstanceError('Cannot change a frozen record')
            cls.__setattr__ = cls.__delattr__ = immutable
            cls.__hash__ = lambda self: hash(values(self))
        return cls
    return decorate(cls) if cls is not None else decorate


def replace(value, **changes):
    values = {item.name: getattr(value, item.name) for item in fields(value)}
    for name in changes:
        if name not in values: raise TypeError('Unknown record field: ' + name)
    values.update(changes)
    return type(value)(**values)


def is_dataclass(value):
    return hasattr(value, '__xp_record_fields__')


def asdict(value):
    def convert(item):
        if is_dataclass(item): return {field.name: convert(getattr(item, field.name)) for field in fields(item)}
        if isinstance(item, dict): return {convert(k): convert(v) for k, v in item.items()}
        if isinstance(item, (list, tuple)): return type(item)(convert(v) for v in item)
        return copy.deepcopy(item)
    if not is_dataclass(value): raise TypeError('Expected an application record')
    return convert(value)
