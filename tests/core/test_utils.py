from contextlib import contextmanager
import os.path
from tempfile import TemporaryDirectory
import unittest

import rasterio
import shapely.geometry
from shapely.geometry import Polygon, MultiPolygon

import stactools.core.utils.antimeridian
from stactools.core.utils.convert import cogify
from tests import test_data


class CogifyTest(unittest.TestCase):

    @contextmanager
    def cogify(self, **kwargs):
        infile = test_data.get_path("data-files/core/byte.tif")
        with TemporaryDirectory() as directory:
            outfile = os.path.join(directory, "byte.tif")
            cogify(infile, outfile, **kwargs)
            yield outfile

    def test_default(self):
        with self.cogify() as outfile:
            self.assertTrue(os.path.exists(outfile))
            with rasterio.open(outfile) as dataset:
                self.assertEqual(dataset.compression,
                                 rasterio.enums.Compression.deflate)

    def test_profile(self):
        with self.cogify(profile={"compress": "lzw"}) as outfile:
            self.assertTrue(os.path.exists(outfile))
            with rasterio.open(outfile) as dataset:
                self.assertEqual(dataset.compression,
                                 rasterio.enums.Compression.lzw)

    def test_antimeridian_split(self) -> None:
        # From https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.9
        canonical = Polygon(
            ((170, 40), (170, 50), (-170, 50), (-170, 40), (170, 40)))
        split = stactools.core.utils.antimeridian.split(canonical)
        assert split
        expected = MultiPolygon((
            shapely.geometry.box(170, 40, 180, 50),
            shapely.geometry.box(-180, 40, -170, 50),
        ))
        for actual, expected in zip(split.geoms, expected.geoms):
            assert actual.equals(expected)

        doesnt_cross = Polygon(
            ((170, 40), (170, 50), (180, 50), (180, 40), (170, 40)))
        split = stactools.core.utils.antimeridian.split(doesnt_cross)
        assert split is None

        canonical_other_way = Polygon(
            ((-170, 40), (170, 40), (170, 50), (-170, 50), (-170, 40)))
        split = stactools.core.utils.antimeridian.split(canonical_other_way)
        expected = MultiPolygon((
            shapely.geometry.box(-180, 40, -170, 50),
            shapely.geometry.box(170, 40, 180, 50),
        ))
        for actual, expected in zip(split.geoms, expected.geoms):
            assert actual.equals(
                expected), f"actual={actual}, expected={expected}"

    def test_antimeridian_split_complicated(self) -> None:
        complicated = Polygon(((170, 40), (170, 50), (-170, 50), (170, 45),
                               (-170, 40), (170, 40)))
        split = stactools.core.utils.antimeridian.split(complicated)
        assert split
        expected = MultiPolygon((
            Polygon(((170, 40), (170, 45), (180, 42.5), (180, 40), (170, 40))),
            Polygon(((170, 45), (170, 50), (180, 50), (180, 47.5), (170, 45))),
            Polygon(((-180, 50), (-170, 50), (-180, 47.5), (-180, 50))),
            Polygon(((-180, 42.5), (-170, 40), (-180, 40), (-180, 42.5))),
        ))
        for actual, expected in zip(split.geoms, expected.geoms):
            assert actual.equals(
                expected), f"actual={actual}, expected={expected}"

    def test_antimeridian_normalize(self) -> None:
        canonical = Polygon(
            ((170, 40), (170, 50), (-170, 50), (-170, 40), (170, 40)))
        normalized = stactools.core.utils.antimeridian.normalize(canonical)
        expected = shapely.geometry.box(170, 40, 190, 50)
        assert normalized.equals(
            expected), f"actual={normalized}, expected={expected}"

        canonical_other_way = Polygon(
            ((-170, 40), (170, 40), (170, 50), (-170, 50), (-170, 40)))
        normalized = stactools.core.utils.antimeridian.normalize(
            canonical_other_way)
        expected = shapely.geometry.box(-170, 40, -190, 50)
        assert normalized.equals(
            expected), f"actual={normalized}, expected={expected}"
