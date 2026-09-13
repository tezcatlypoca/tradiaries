from django.test import SimpleTestCase
from django.urls import reverse


class PwaEndpointTests(SimpleTestCase):
	"""Validate the public HTTP contract required by the PWA."""

	def test_service_worker_is_served_from_root_without_http_cache(self) -> None:
		response = self.client.get(reverse('service_worker'))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response['Content-Type'], 'application/javascript')
		self.assertEqual(response['Service-Worker-Allowed'], '/')
		self.assertIn('no-cache', response['Cache-Control'])
		self.assertContains(response, "const CACHE_NAME = 'tradiaries-cache-v1';")

	def test_manifest_is_public_and_has_global_scope(self) -> None:
		response = self.client.get(reverse('manifest'))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response['Content-Type'], 'application/manifest+json')
		self.assertContains(response, '"scope": "/"')
