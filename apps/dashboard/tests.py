from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.core.models import ApiCredential, UserPreferences


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


class DashboardViewTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(
			username='dashboard-tester', password='strong-test-password'
		)

	def test_dashboard_requires_login(self):
		response = self.client.get(reverse('dashboard:index'))

		self.assertEqual(response.status_code, 302)
		self.assertIn('/accounts/login/', response.url)

	def test_dashboard_renders_for_authenticated_user(self):
		self.client.force_login(self.user)

		response = self.client.get(reverse('dashboard:index'))

		self.assertEqual(response.status_code, 200)
		self.assertIn('kpi_cards', response.context)


class SignupViewTests(TestCase):
	def test_signup_creates_account_and_logs_in(self):
		response = self.client.post(reverse('signup'), {
			'username': 'new-trader',
			'password1': 'a-strong-test-password-1',
			'password2': 'a-strong-test-password-1',
		})

		self.assertRedirects(response, reverse('dashboard:index'))
		self.assertTrue(get_user_model().objects.filter(username='new-trader').exists())
		# Connexion automatique après inscription : la page protégée est accessible sans re-login.
		follow_up = self.client.get(reverse('dashboard:index'))
		self.assertEqual(follow_up.status_code, 200)

	def test_signup_already_authenticated_redirects_without_creating_account(self):
		user = get_user_model().objects.create_user(username='existing', password='strong-test-password')
		self.client.force_login(user)

		response = self.client.get(reverse('signup'))

		self.assertRedirects(response, reverse('dashboard:index'))


class SaveStrategyViewTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(
			username='strategy-tester', password='strong-test-password'
		)
		self.other_user = get_user_model().objects.create_user(
			username='strategy-other', password='strong-test-password'
		)

	def test_save_strategy_persists_for_current_user_only(self):
		self.client.force_login(self.user)

		self.client.post(reverse('settings:strategy_save'), {'strategy': 'Breakout 4h'})

		self.assertEqual(
			UserPreferences.objects.get(user=self.user).strategy, 'Breakout 4h'
		)
		self.assertFalse(UserPreferences.objects.filter(user=self.other_user).exists())


class ApiCredentialViewTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(
			username='credential-tester', password='strong-test-password'
		)
		self.other_user = get_user_model().objects.create_user(
			username='credential-other', password='strong-test-password'
		)

	def test_create_api_credential_scoped_to_current_user(self):
		self.client.force_login(self.user)

		self.client.post(reverse('settings:api_credential_create'), {
			'platform': 'KRAKEN', 'label': 'Perso', 'api_key': 'key123', 'api_secret': 'c2VjcmV0',
		})

		credential = ApiCredential.objects.get(platform='KRAKEN', user=self.user)
		self.assertEqual(credential.user, self.user)

	def test_delete_api_credential_of_another_user_returns_404(self):
		credential = ApiCredential(user=self.other_user, platform='KRAKEN', label='Other')
		credential.set_credentials(api_key='key123', api_secret='c2VjcmV0', passphrase='')
		credential.save()
		self.client.force_login(self.user)

		response = self.client.post(
			reverse('settings:api_credential_delete', args=[credential.pk])
		)

		self.assertEqual(response.status_code, 404)
		self.assertTrue(ApiCredential.objects.filter(pk=credential.pk).exists())

	def test_delete_own_api_credential_succeeds(self):
		credential = ApiCredential(user=self.user, platform='KRAKEN', label='Mine')
		credential.set_credentials(api_key='key123', api_secret='c2VjcmV0', passphrase='')
		credential.save()
		self.client.force_login(self.user)

		self.client.post(
			reverse('settings:api_credential_delete', args=[credential.pk])
		)

		self.assertFalse(ApiCredential.objects.filter(pk=credential.pk).exists())
