"""Rendering cost and preserved artwork, without machine speed thresholds."""
import hashlib
import struct
import unittest
import zlib

from dxtalker.rounded import _coverage, _surface


class RoundedTests(unittest.TestCase):
    def test_large_tile_preserves_original_corners(self):
        png = _surface('#20303e', '#324758')
        width, height = struct.unpack('!II', png[16:24])
        self.assertEqual((width, height), (256, 256))
        # With a 10 pixel border, a 600 x 500 panel needs nine center copies
        # instead of the 1,960 copies required by the original 32 pixel image.
        center = width - 20
        self.assertLessEqual(((580 + center - 1) // center) * ((480 + center - 1) // center), 9)
        data = bytearray()
        offset = 8
        while offset < len(png):
            size = struct.unpack('!I', png[offset:offset + 4])[0]
            if png[offset + 4:offset + 8] == b'IDAT':
                data.extend(png[offset + 8:offset + 8 + size])
            offset += size + 12
        rows = zlib.decompress(data)
        original = bytearray()
        for y in (*range(16), *range(height - 16, height)):
            row = rows[y * (width * 4 + 1):(y + 1) * (width * 4 + 1)]
            self.assertEqual(row[0], 0)
            original.extend(b'\0' + row[1:65] + row[-64:])
        # Golden pixels from the a14 artwork. Only solid strips are enlarged.
        self.assertEqual(hashlib.sha256(original).hexdigest(),
                         '95e06b3a1a567e8d050a19db81fd98e6d852d0795c76f86b36e7657867407b20')

    def test_new_colors_reuse_corner_geometry(self):
        _surface.cache_clear()
        _coverage.cache_clear()
        for fill in ('#20303e', '#00b6dc', '#542334'):
            _surface(fill, '#324758')
        self.assertEqual(_coverage.cache_info().misses, 1)
        self.assertEqual(_coverage.cache_info().hits, 2)
