import ssl
import unittest

from deckview.http import CertifiAiohttpClient


class HttpClientTests(unittest.TestCase):
    def test_uses_verified_certificate_store(self):
        client = CertifiAiohttpClient()

        self.assertEqual(client.ssl_context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(client.ssl_context.check_hostname)
        self.assertGreater(len(client.ssl_context.get_ca_certs()), 0)


if __name__ == "__main__":
    unittest.main()
