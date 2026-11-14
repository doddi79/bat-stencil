import base64 as std_base64
import unittest

from batstencil.stencils import *
from batstencil.jinjaext.filters import base64


class TestBase64Filter(unittest.TestCase):
    def test_short_value(self):
        self.assertEqual('SGVsbG8=', base64('Hello'))
        self.assertEqual('SGVsbG8=', render_stencil('{{ v|base64 }}', {'v': 'Hello'}))

    def test_long_value_is_a_single_line(self):
        value = 'A long secret value that is certainly more than seventy-six characters of base64! ' * 5
        self.assertGreater(len(std_base64.b64encode(value.encode('utf-8'))), 76)
        res = base64(value)
        self.assertNotIn('\n', res)
        self.assertNotIn('\r', res)
        self.assertEqual(std_base64.b64encode(value.encode('utf-8')).decode('ascii'), res)
        self.assertEqual(value, std_base64.b64decode(res).decode('utf-8'))

    def test_long_value_in_template(self):
        value = 'x' * 200
        res = render_stencil('{{ v|base64 }}', {'v': value})
        self.assertEqual(1, len(res.splitlines()))
        self.assertEqual(std_base64.b64encode(value.encode()).decode(), res)

    def test_bytes_input(self):
        self.assertEqual('AAEC/w==', base64(b'\x00\x01\x02\xff'))
        long_bytes = bytes(range(256))
        res = base64(long_bytes)
        self.assertNotIn('\n', res)
        self.assertEqual(long_bytes, std_base64.b64decode(res))

    def test_bytes_in_template(self):
        self.assertEqual('SGk=', render_stencil('{{ v|base64 }}', {'v': b'Hi'}))

    def test_unicode_is_utf8_encoded(self):
        self.assertEqual('w7DDvuKckw==', base64('ðþ✓'))

    def test_non_str_value(self):
        self.assertEqual(std_base64.b64encode(b'42').decode(), base64(42))
