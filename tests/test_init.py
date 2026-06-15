import datetime
import logging
import unittest
from io import StringIO

logStream = StringIO()
logging.basicConfig(stream=logStream, level=logging.DEBUG)
logger = logging.getLogger(__name__)

from managedYoutubeDL import convertTime

UTC = datetime.timezone.utc


class test_ConvertTime(unittest.TestCase):

  def setUp(self):
    logStream.truncate(0)

  def assertUTCAware(self, dt):
    self.assertIsNotNone(dt.tzinfo, "datetime should be UTC-aware but tzinfo is None")

  def test_none(self):
    self.assertIsNone(convertTime(None))

  def test_aware_datetime_passthrough(self):
    dt = datetime.datetime(2020, 6, 15, 12, 0, 0, tzinfo=UTC)
    result = convertTime(dt)
    self.assertIs(result, dt)
    self.assertUTCAware(result)

  def test_naive_datetime_gets_utc(self):
    naive = datetime.datetime(2020, 6, 15, 12, 0, 0)
    result = convertTime(naive)
    self.assertUTCAware(result)
    self.assertEqual(result.year,   2020)
    self.assertEqual(result.month,  6)
    self.assertEqual(result.day,    15)
    self.assertEqual(result.hour,   12)
    self.assertEqual(result.minute, 0)
    self.assertEqual(result.second, 0)

  def test_youtube_api_string_z_suffix(self):
    result = convertTime("2020-01-01T00:00:01Z")
    self.assertUTCAware(result)
    self.assertEqual(result, datetime.datetime(2020, 1, 1, 0, 0, 1, tzinfo=UTC))

  def test_youtube_api_string_microseconds_z_suffix(self):
    result = convertTime("2020-01-01T00:00:01.000002Z")
    self.assertUTCAware(result)
    self.assertEqual(result, datetime.datetime(2020, 1, 1, 0, 0, 1, 2, tzinfo=UTC))

  def test_legacy_plain_string(self):
    result = convertTime("2020-01-01 00:00:01")
    self.assertUTCAware(result)
    self.assertEqual(result, datetime.datetime(2020, 1, 1, 0, 0, 1, tzinfo=UTC))

  def test_legacy_plain_string_microseconds(self):
    result = convertTime("2020-01-01 00:00:01.000002")
    self.assertUTCAware(result)
    self.assertEqual(result, datetime.datetime(2020, 1, 1, 0, 0, 1, 2, tzinfo=UTC))

  def test_invalid_type_raises(self):
    for bad in [42, 3.14, [], {}]:
      with self.subTest(bad=bad):
        self.assertRaises(TypeError, convertTime, bad)
