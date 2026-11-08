"""PNG QR rendering for the pinned QR encoder without Pillow or pymaging."""
import png
from qrcode.image.base import BaseImage

class PyPNGImage(BaseImage):
    kind = 'PNG'
    allowed_kinds = ('PNG',)
    def new_image(self, **options):
        if not 1 <= self.box_size <= 32 or not 0 <= self.border <= 32 or not 1 <= self.width <= 177:
            raise ValueError('QR image dimensions exceed the supported range')
        return set()
    def drawrect(self, row, column):
        self._img.add((row, column))
    def save(self, stream, kind=None):
        self.check_kind(kind)
        def rows():
            for row in range(-self.border, self.width + self.border):
                pixels = []
                for column in range(-self.border, self.width + self.border):
                    pixels.extend([0 if (row, column) in self._img else 1] * self.box_size)
                for repeat in range(self.box_size):
                    yield pixels
        png.Writer(self.pixel_size, self.pixel_size, greyscale=True, bitdepth=1).write(stream, rows())
