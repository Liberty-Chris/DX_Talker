"""Remember rendered values so idle polling does not invalidate Tk layouts."""


class RenderCache:
    def __init__(self):
        self.values = {}

    def changed(self, key, value):
        if key in self.values and self.values[key] == value:
            return False
        self.values[key] = value
        return True

    def set(self, variable, value):
        if self.changed(('variable', id(variable)), value):
            variable.set(value)

    def configure(self, widget, **options):
        if self.changed(('options', id(widget)), options):
            widget.configure(**options)

    def coords(self, canvas, item, *coordinates):
        if self.changed(('coords', id(canvas), item), coordinates):
            canvas.coords(item, *coordinates)
