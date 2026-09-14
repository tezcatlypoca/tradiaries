from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import FuturesTradingForm, SimpleInvestmentForm, SpotTradingForm
from .kraken_client import KrakenAPIError
from .models import FuturesTrading, KrakenOrderAttempt, SimpleInvestment, SpotTrading, WatcherHeartbeat
from .portfolio_service import futures_trade_pnl
from .trading_service import TradingError, check_tp_sl, close_position, open_position
from .watcher_health import touch_watcher_heartbeat
from apps.live_trading.forms import OpenPositionForm


@override_settings(ALLOWED_HOSTS=['testserver'])
class DomainValidationTests(TestCase):
    def test_positive_values_and_symbol_normalization(self):
        form = SimpleInvestmentForm(
            data={'symbol': ' btc ', 'amount': '1.5', 'price': '100', 'action': 'ACHAT'}
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['symbol'], 'BTC')

    def test_non_positive_amount_is_rejected(self):
        form = SpotTradingForm(
            data={'symbol': 'BTC', 'amount': '0', 'entry_price': '100', 'exchange': 'BINANCE'}
        )

        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)

    def test_second_exit_requires_first_exit(self):
        form = FuturesTradingForm(
            data={
                'symbol': 'BTC',
                'amount': '1',
                'entry_price': '100',
                'exit_price_2': '120',
                'direction': 'LONG',
                'trade_mode': 'PAPER',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('exit_price', form.errors)

    def test_two_equal_exits_use_average_price_for_pnl(self):
        trade = FuturesTrading(
            symbol='BTC',
            amount=Decimal('2'),
            entry_price=Decimal('100'),
            exit_price=Decimal('120'),
            exit_price_2=Decimal('140'),
            direction='LONG',
        )

        self.assertEqual(trade.effective_exit_price(), Decimal('130'))
        self.assertEqual(futures_trade_pnl(trade), Decimal('60'))


class OpenPositionFormTests(TestCase):
    def test_live_position_requires_two_validated_irc_criteria(self):
        form = OpenPositionForm(
            data={
                'category': 'SPOT',
                'trade_mode': 'LIVE',
                'symbol': 'BTC',
                'amount': '1',
                'entry_price': '100',
                'regime_confirmed': 'on',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('Ordre LIVE refusé', form.non_field_errors()[0])

    def test_live_position_accepts_two_validated_irc_criteria(self):
        form = OpenPositionForm(
            data={
                'category': 'SPOT',
                'trade_mode': 'LIVE',
                'symbol': 'BTC',
                'amount': '1',
                'entry_price': '100',
                'regime_confirmed': 'on',
                'sar_confirmed': 'on',
            }
        )

        self.assertTrue(form.is_valid())

    def test_short_position_rejects_inverted_take_profit(self):
        form = OpenPositionForm(
            data={
                'category': 'FUTURES',
                'trade_mode': 'PAPER',
                'symbol': 'BTC',
                'amount': '1',
                'entry_price': '100',
                'direction': 'SHORT',
                'take_profit': '110',
                'stop_loss': '120',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('take_profit', form.errors)


class TradingServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='trader', password='strong-test-password'
        )

    @patch('apps.core.trading_service.fetch_current_price', return_value=Decimal('100'))
    def test_open_paper_spot_at_market_creates_local_position(self, mocked_current_price):
        trade = open_position(
            user=self.user,
            category='SPOT',
            trade_mode='PAPER',
            symbol=' btc ',
            amount=Decimal('0.5'),
            entry_price=None,
        )

        self.assertEqual(trade.symbol, 'BTC')
        self.assertEqual(trade.entry_price, Decimal('100'))
        self.assertEqual(trade.trade_mode, 'PAPER')
        self.assertIsNone(trade.external_ref)
        mocked_current_price.assert_called_once_with('BTC')

    @patch('apps.core.trading_service.fetch_current_price', return_value=Decimal('120'))
    @patch('apps.core.trading_service.fetch_current_prices', return_value=({'BTC': Decimal('120')}, set()))
    def test_check_tp_sl_closes_long_position_at_take_profit(self, mocked_prices, mocked_current_price):
        trade = SpotTrading.objects.create(
            user=self.user,
            symbol='BTC',
            amount=Decimal('1'),
            entry_price=Decimal('100'),
            take_profit=Decimal('110'),
            trade_mode='PAPER',
        )

        closed = check_tp_sl()

        trade.refresh_from_db()
        self.assertEqual(len(closed), 1)
        self.assertEqual(closed[0]['reason'], 'TP')
        self.assertEqual(trade.exit_price, Decimal('120'))
        mocked_prices.assert_called_once_with({'BTC'})
        mocked_current_price.assert_called_once_with('BTC')

    def test_open_live_futures_is_rejected(self):
        with self.assertRaises(TradingError):
            open_position(
                user=self.user,
                category='FUTURES',
                trade_mode='LIVE',
                symbol='BTC',
                amount=Decimal('1'),
                entry_price=Decimal('100'),
            )


class LiveOrderReconciliationTests(TestCase):
    """Vérifie que chaque tentative d'ordre LIVE laisse une trace exploitable (P0-1)."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='trader', password='strong-test-password'
        )

    @patch('apps.core.trading_service.add_spot_order', side_effect=KrakenAPIError('boom'))
    def test_kraken_failure_before_submission_is_recorded_as_failed(self, mocked_add_order):
        with self.assertRaises(TradingError):
            open_position(
                user=self.user, category='SPOT', trade_mode='LIVE', symbol='BTC',
                amount=Decimal('1'), entry_price=Decimal('100'),
            )

        attempt = KrakenOrderAttempt.objects.get()
        self.assertEqual(attempt.status, 'FAILED')
        self.assertEqual(attempt.operation, 'OPEN')
        self.assertIsNone(attempt.spot_trade)
        self.assertFalse(SpotTrading.objects.exists())

    @patch('apps.core.trading_service.time.sleep', return_value=None)
    @patch('apps.core.trading_service.fetch_order_fill_price', return_value=Decimal('101'))
    @patch(
        'apps.core.trading_service.add_spot_order',
        return_value={'txid': 'TX123', 'descr': '', 'pair': 'XBTUSD'},
    )
    def test_successful_order_confirms_attempt_and_links_trade(self, mocked_add_order, mocked_fill, mocked_sleep):
        trade = open_position(
            user=self.user, category='SPOT', trade_mode='LIVE', symbol='BTC',
            amount=Decimal('1'), entry_price=None,
        )

        attempt = KrakenOrderAttempt.objects.get()
        self.assertEqual(attempt.status, 'CONFIRMED')
        self.assertEqual(attempt.external_ref, 'TX123')
        self.assertEqual(attempt.spot_trade_id, trade.pk)
        mocked_add_order.assert_called_once()
        self.assertEqual(mocked_add_order.call_args.kwargs['userref'], attempt.kraken_userref)


class ClosePositionConcurrencyTests(TestCase):
    """Vérifie la revendication atomique anti double-clôture (P0-3)."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='trader', password='strong-test-password'
        )

    @patch('apps.core.trading_service.fetch_current_price', return_value=Decimal('150'))
    def test_close_is_skipped_if_already_claimed(self, mocked_price):
        trade = SpotTrading.objects.create(
            user=self.user, symbol='BTC', amount=Decimal('1'), entry_price=Decimal('100'), trade_mode='PAPER',
        )
        # Simule une clôture déjà en cours (autre process/watcher).
        SpotTrading.objects.filter(pk=trade.pk).update(is_closing=True)

        result = close_position(trade)

        self.assertFalse(result)
        trade.refresh_from_db()
        self.assertIsNone(trade.exit_price)
        mocked_price.assert_not_called()


@override_settings(ALLOWED_HOSTS=['testserver'])
class TradingViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='trader', password='strong-test-password'
        )
        self.client.force_login(self.user)

    def test_invalid_spot_post_does_not_create_trade(self):
        response = self.client.post(
            reverse('spot_trading:create'),
            {'symbol': 'BTC', 'amount': 'not-a-number', 'entry_price': '100', 'exchange': 'BINANCE'},
        )

        self.assertRedirects(response, reverse('spot_trading:index'))
        self.assertFalse(SpotTrading.objects.exists())

    def test_valid_futures_post_persists_strategy_and_mode(self):
        response = self.client.post(
            reverse('futures_trading:create'),
            {
                'symbol': ' btc ',
                'amount': '1',
                'entry_price': '100',
                'direction': 'SHORT',
                'trade_mode': 'LIVE',
                'strategy': 'IRC 4h',
            },
        )

        self.assertRedirects(response, reverse('futures_trading:index'))
        trade = FuturesTrading.objects.get()
        self.assertEqual(trade.symbol, 'BTC')
        self.assertEqual(trade.strategy, 'IRC 4h')
        self.assertEqual(trade.trade_mode, 'LIVE')

    def test_invalid_simple_investment_post_does_not_create_investment(self):
        response = self.client.post(
            reverse('investment:create'),
            {'symbol': 'BTC', 'amount': '-1', 'price': '100', 'action': 'ACHAT'},
        )

        self.assertRedirects(response, reverse('investment:index'))
        self.assertFalse(SimpleInvestment.objects.exists())

    def test_health_endpoint_checks_database_without_login(self):
        self.client.logout()

        response = self.client.get(reverse('healthz'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})

    def test_watcher_health_endpoint_requires_recent_heartbeat(self):
        self.client.logout()
        WatcherHeartbeat.objects.all().delete()

        response = self.client.get(reverse('watcher_healthz'))
        self.assertEqual(response.status_code, 503)

        touch_watcher_heartbeat()
        response = self.client.get(reverse('watcher_healthz'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok', 'watcher': 'running'})


@override_settings(ALLOWED_HOSTS=['testserver'])
class MultiUserIsolationTests(TestCase):
    """Vérifie qu'un compte ne peut jamais voir/modifier/supprimer les données d'un autre (P1 audit)."""

    def setUp(self):
        self.alice = get_user_model().objects.create_user(username='alice', password='strong-test-password')
        self.bob = get_user_model().objects.create_user(username='bob', password='strong-test-password')
        self.alice_trade = SpotTrading.objects.create(
            user=self.alice, symbol='BTC', amount=Decimal('1'), entry_price=Decimal('100'), trade_mode='PAPER',
        )
        self.alice_investment = SimpleInvestment.objects.create(
            user=self.alice, symbol='BTC', amount=Decimal('1'), price=Decimal('100'), action='ACHAT',
        )

    def test_user_only_sees_own_spot_trades(self):
        self.client.force_login(self.bob)
        SpotTrading.objects.create(
            user=self.bob, symbol='ETH', amount=Decimal('2'), entry_price=Decimal('50'), trade_mode='PAPER',
        )

        response = self.client.get(reverse('spot_trading:index'))

        trades = list(response.context['trades'])
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].symbol, 'ETH')

    def test_user_cannot_update_another_users_trade(self):
        self.client.force_login(self.bob)

        response = self.client.post(
            reverse('spot_trading:update', args=[self.alice_trade.pk]),
            {'symbol': 'ETH', 'amount': '5', 'entry_price': '200', 'exchange': 'BINANCE'},
        )

        self.assertEqual(response.status_code, 404)
        self.alice_trade.refresh_from_db()
        self.assertEqual(self.alice_trade.symbol, 'BTC')

    def test_user_cannot_delete_another_users_trade(self):
        self.client.force_login(self.bob)

        response = self.client.post(reverse('spot_trading:delete', args=[self.alice_trade.pk]))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(SpotTrading.objects.filter(pk=self.alice_trade.pk).exists())

    def test_user_cannot_delete_another_users_investment(self):
        self.client.force_login(self.bob)

        response = self.client.post(reverse('investment:delete', args=[self.alice_investment.pk]))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(SimpleInvestment.objects.filter(pk=self.alice_investment.pk).exists())

    def test_created_trade_is_owned_by_the_authenticated_user(self):
        self.client.force_login(self.bob)

        self.client.post(
            reverse('spot_trading:create'),
            {'symbol': 'SOL', 'amount': '1', 'entry_price': '20', 'exchange': 'BINANCE', 'trade_mode': 'PAPER'},
        )

        trade = SpotTrading.objects.get(symbol='SOL')
        self.assertEqual(trade.user, self.bob)
