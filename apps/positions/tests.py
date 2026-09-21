from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from apps.core.models import FuturesTrading, SpotTrading


class PositionsPageTests(TestCase):
    """Page Positions : fusion Spot/Futures, lecture seule (pas d'ouverture ni de clôture ici)."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='trader', password='strong-test-password')
        self.other = get_user_model().objects.create_user(username='other', password='strong-test-password')
        self.client.force_login(self.user)

    @patch('apps.core.portfolio_service.fetch_current_prices', return_value=({}, set()))
    def test_default_tab_shows_only_closed_spot_trades(self, _mocked_prices):
        SpotTrading.objects.create(
            user=self.user, symbol='BTC', amount=Decimal('1'), entry_price=Decimal('100'),
            exit_price=Decimal('110'), trade_mode='PAPER',
        )
        FuturesTrading.objects.create(
            user=self.user, symbol='ETH', amount=Decimal('1'), entry_price=Decimal('50'),
            exit_price=Decimal('55'), trade_mode='PAPER',
        )

        response = self.client.get(reverse('positions:index'))

        self.assertEqual(response.status_code, 200)
        trades = list(response.context['trades'])
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].symbol, 'BTC')
        self.assertEqual(response.context['active_category'], 'SPOT')

    @patch('apps.core.portfolio_service.fetch_current_prices', return_value=({}, set()))
    def test_futures_tab_shows_only_closed_futures_trades(self, _mocked_prices):
        SpotTrading.objects.create(
            user=self.user, symbol='BTC', amount=Decimal('1'), entry_price=Decimal('100'),
            exit_price=Decimal('110'), trade_mode='PAPER',
        )
        FuturesTrading.objects.create(
            user=self.user, symbol='ETH', amount=Decimal('1'), entry_price=Decimal('50'),
            exit_price=Decimal('55'), trade_mode='PAPER',
        )

        response = self.client.get(reverse('positions:index'), {'category': 'FUTURES'})

        trades = list(response.context['trades'])
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].symbol, 'ETH')
        self.assertEqual(response.context['active_category'], 'FUTURES')

    @patch('apps.core.portfolio_service.fetch_current_prices', return_value=({}, set()))
    def test_mode_filter_is_applied(self, _mocked_prices):
        SpotTrading.objects.create(
            user=self.user, symbol='BTC', amount=Decimal('1'), entry_price=Decimal('100'),
            exit_price=Decimal('110'), trade_mode='LIVE',
        )
        SpotTrading.objects.create(
            user=self.user, symbol='ETH', amount=Decimal('1'), entry_price=Decimal('50'),
            exit_price=Decimal('55'), trade_mode='PAPER',
        )

        response = self.client.get(reverse('positions:index'), {'mode': 'LIVE'})

        trades = list(response.context['trades'])
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].symbol, 'BTC')

    @patch('apps.core.portfolio_service.fetch_current_prices', return_value=({}, set()))
    def test_open_positions_are_excluded(self, _mocked_prices):
        """Les positions ouvertes ne s'affichent plus ici : uniquement sur la page Trading."""
        SpotTrading.objects.create(
            user=self.user, symbol='BTC', amount=Decimal('1'), entry_price=Decimal('100'), trade_mode='PAPER',
        )
        FuturesTrading.objects.create(
            user=self.user, symbol='ETH', amount=Decimal('1'), entry_price=Decimal('50'), trade_mode='PAPER',
        )

        response = self.client.get(reverse('positions:index'))
        self.assertEqual(list(response.context['trades']), [])

        response = self.client.get(reverse('positions:index'), {'category': 'FUTURES'})
        self.assertEqual(list(response.context['trades']), [])

    @patch('apps.core.portfolio_service.fetch_current_prices', return_value=({}, set()))
    def test_user_only_sees_own_positions(self, _mocked_prices):
        SpotTrading.objects.create(
            user=self.other, symbol='SOL', amount=Decimal('1'), entry_price=Decimal('20'),
            exit_price=Decimal('22'), trade_mode='PAPER',
        )

        response = self.client.get(reverse('positions:index'))

        self.assertEqual(list(response.context['trades']), [])

    @patch('apps.core.portfolio_service.fetch_current_prices', return_value=({}, set()))
    def test_page_exposes_no_create_action(self, _mocked_prices):
        response = self.client.get(reverse('positions:index'))

        self.assertNotContains(response, 'openTradeModal')

    @patch('apps.core.portfolio_service.fetch_current_prices', return_value=({}, set()))
    def test_delete_form_targets_existing_scoped_endpoint(self, _mocked_prices):
        trade = SpotTrading.objects.create(
            user=self.user, symbol='BTC', amount=Decimal('1'), entry_price=Decimal('100'),
            exit_price=Decimal('110'), trade_mode='PAPER',
        )

        response = self.client.get(reverse('positions:index'))

        self.assertContains(response, reverse('spot_trading:delete', args=[trade.pk]))
