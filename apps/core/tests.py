from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import FuturesTradingForm, SimpleInvestmentForm, SpotTradingForm
from .kraken_client import KrakenAPIError
from .models import (
    ApiCredential,
    ApiCredentialAuditLog,
    FuturesTrading,
    KrakenOrderAttempt,
    SimpleInvestment,
    SpotTrading,
    UserPreferences,
    WatcherHeartbeat,
)
from .kraken_client import (
    add_spot_order,
    cancel_order,
    fetch_ohlc,
    fetch_order_fill_price,
    query_orders,
)
from .portfolio_service import (
    build_chart_series,
    compute_futures_analytics,
    compute_futures_stats,
    compute_global_stats,
    compute_investment_stats,
    compute_spot_stats,
    futures_trade_pnl,
)
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

    def test_valid_futures_post_persists_strategy_mode_and_timeframe(self):
        response = self.client.post(
            reverse('futures_trading:create'),
            {
                'symbol': ' btc ',
                'amount': '1',
                'entry_price': '100',
                'direction': 'SHORT',
                'trade_mode': 'LIVE',
                'strategy': 'IRC 4h',
                'timeframe': '15min',
            },
        )

        self.assertRedirects(response, reverse('futures_trading:index'))
        trade = FuturesTrading.objects.get()
        self.assertEqual(trade.symbol, 'BTC')
        self.assertEqual(trade.strategy, 'IRC 4h')
        self.assertEqual(trade.trade_mode, 'LIVE')
        self.assertEqual(trade.timeframe, '15min')

    def test_trading_lists_display_timeframes(self):
        SpotTrading.objects.create(
            user=self.user,
            symbol='ETH',
            amount=Decimal('1'),
            entry_price=Decimal('100'),
            timeframe='1h',
        )
        FuturesTrading.objects.create(
            user=self.user,
            symbol='BTC',
            amount=Decimal('1'),
            entry_price=Decimal('100'),
            timeframe='4h',
        )

        self.assertContains(self.client.get(reverse('spot_trading:index')), '1h')
        self.assertContains(self.client.get(reverse('futures_trading:index')), '4h')

    def test_user_can_save_and_view_strategy(self):
        response = self.client.post(
            reverse('settings:strategy_save'),
            {'strategy': 'Attendre une confirmation sur plusieurs unités de temps.'},
        )

        self.assertRedirects(response, reverse('settings:index'))
        preferences = UserPreferences.objects.get(user=self.user)
        self.assertEqual(
            preferences.strategy,
            'Attendre une confirmation sur plusieurs unités de temps.',
        )
        self.assertContains(
            self.client.get(reverse('settings:index')),
            'Attendre une confirmation sur plusieurs unités de temps.',
        )

    def test_coaching_page_is_available_and_empty(self):
        response = self.client.get(reverse('dashboard:coaching'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<h1>')

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

    def test_user_strategy_is_isolated(self):
        UserPreferences.objects.create(user=self.alice, strategy='Stratégie Alice')
        self.client.force_login(self.bob)

        self.client.post(
            reverse('settings:strategy_save'),
            {'strategy': 'Stratégie Bob'},
        )

        self.assertEqual(
            UserPreferences.objects.get(user=self.alice).strategy,
            'Stratégie Alice',
        )
        self.assertEqual(
            UserPreferences.objects.get(user=self.bob).strategy,
            'Stratégie Bob',
        )


class ApiCredentialAuditTests(TestCase):
    """Audit trail des accès `ApiCredential` (2026-09-22) : chaque lecture/création/suppression doit être tracée."""

    def setUp(self):
        self.alice = get_user_model().objects.create_user(username='alice', password='strong-test-password')
        self.credential = ApiCredential(user=self.alice, platform='KRAKEN', label='Principale')
        self.credential.set_credentials(api_key='key123', api_secret='secret123')
        self.credential.save()

    def test_masked_api_key_logs_a_read_access(self):
        self.credential.masked_api_key()

        log = ApiCredentialAuditLog.objects.get()
        self.assertEqual(log.action, 'READ')
        self.assertEqual(log.user, self.alice)
        self.assertEqual(log.platform, 'KRAKEN')
        self.assertEqual(log.credential, self.credential)

    def test_kraken_client_read_logs_a_read_access(self):
        from .kraken_client import _get_kraken_credentials

        _get_kraken_credentials(self.alice)

        self.assertEqual(ApiCredentialAuditLog.objects.filter(action='READ').count(), 1)

    def test_audit_log_survives_credential_deletion(self):
        self.credential.log_access('DELETE')
        self.credential.delete()

        log = ApiCredentialAuditLog.objects.get()
        self.assertIsNone(log.credential)
        self.assertEqual(log.platform, 'KRAKEN')
        self.assertEqual(log.action, 'DELETE')

    def test_create_view_logs_a_create_access(self):
        self.client.force_login(self.alice)

        self.client.post(
            reverse('settings:api_credential_create'),
            {'platform': 'BINANCE', 'label': '', 'api_key': 'k', 'api_secret': 's'},
        )

        log = ApiCredentialAuditLog.objects.get(platform='BINANCE')
        self.assertEqual(log.action, 'CREATE')
        self.assertEqual(log.user, self.alice)

    def test_delete_view_logs_a_delete_access(self):
        self.client.force_login(self.alice)

        self.client.post(reverse('settings:api_credential_delete', args=[self.credential.pk]))

        log = ApiCredentialAuditLog.objects.get(action='DELETE')
        self.assertEqual(log.platform, 'KRAKEN')
        self.assertEqual(log.user, self.alice)


class KrakenOhlcTests(TestCase):
    """`fetch_ohlc` : parsing des chandeliers publics Kraken et gestion des erreurs."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    @patch('apps.core.kraken_client.resolve_pair', return_value='XXBTZUSD')
    @patch('apps.core.kraken_client._public_request')
    def test_parses_candles_into_chronological_dicts(self, mocked_request, _mocked_pair):
        mocked_request.return_value = {
            'XXBTZUSD': [
                [1700000000, '100', '110', '90', '105', '102', '5.5', 12],
                [1700000900, '105', '115', '100', '110', '107', '3.2', 8],
            ],
            'last': 1700000900,
        }

        candles = fetch_ohlc('BTC', interval=15)

        self.assertEqual(len(candles), 2)
        self.assertEqual(candles[0], {
            'time': 1700000000, 'open': 100.0, 'high': 110.0, 'low': 90.0, 'close': 105.0, 'volume': 5.5,
        })
        self.assertEqual(candles[1]['close'], 110.0)

    def test_invalid_interval_raises(self):
        with self.assertRaises(KrakenAPIError):
            fetch_ohlc('BTC', interval=7)

    @patch('apps.core.kraken_client.resolve_pair', return_value='XXBTZUSD')
    @patch('apps.core.kraken_client._public_request', side_effect=KrakenAPIError('boom'))
    def test_returns_empty_list_when_kraken_unavailable(self, _mocked_request, _mocked_pair):
        self.assertEqual(fetch_ohlc('BTC', interval=15), [])


class WatchTpSlCommandTests(TestCase):
    """Commande `watch_tp_sl` : un cycle réussi met à jour le heartbeat, un cycle en échec ne le fait pas."""

    @patch('apps.core.management.commands.watch_tp_sl.touch_watcher_heartbeat')
    @patch('apps.core.management.commands.watch_tp_sl.check_tp_sl', return_value=[])
    def test_once_runs_single_cycle_and_returns(self, mocked_check, mocked_heartbeat):
        call_command('watch_tp_sl', '--once')

        mocked_check.assert_called_once()
        mocked_heartbeat.assert_called_once()

    @patch('apps.core.management.commands.watch_tp_sl.touch_watcher_heartbeat')
    @patch('apps.core.management.commands.watch_tp_sl.check_tp_sl')
    def test_successful_cycle_touches_heartbeat(self, mocked_check, mocked_heartbeat):
        trade = SpotTrading(symbol='BTC', trade_mode='PAPER')
        mocked_check.return_value = [{'trade': trade, 'reason': 'take_profit', 'price': Decimal('123')}]

        # stdout forcé en UTF-8 (StringIO) : le message de succès contient un caractère
        # '✓' qui n'est pas encodable en cp1252 (console Windows par défaut) et ferait
        # planter la commande avant même d'atteindre touch_watcher_heartbeat().
        call_command('watch_tp_sl', '--once', stdout=StringIO())

        mocked_heartbeat.assert_called_once()

    @patch('apps.core.management.commands.watch_tp_sl.touch_watcher_heartbeat')
    @patch('apps.core.management.commands.watch_tp_sl.check_tp_sl', side_effect=RuntimeError('boom'))
    def test_failed_cycle_does_not_touch_heartbeat(self, mocked_check, mocked_heartbeat):
        call_command('watch_tp_sl', '--once')

        mocked_check.assert_called_once()
        mocked_heartbeat.assert_not_called()

    @patch('apps.core.management.commands.watch_tp_sl.time.sleep')
    @patch('apps.core.management.commands.watch_tp_sl.touch_watcher_heartbeat')
    @patch('apps.core.management.commands.watch_tp_sl.check_tp_sl', return_value=[])
    def test_custom_interval_is_passed_to_sleep(self, _mocked_check, _mocked_heartbeat, mocked_sleep):
        # Sans --once la commande boucle indéfiniment : on force la sortie après le premier sleep.
        mocked_sleep.side_effect = KeyboardInterrupt

        with self.assertRaises(KeyboardInterrupt):
            call_command('watch_tp_sl', '--interval', '42')

        mocked_sleep.assert_called_once_with(42)


class KrakenClientTests(TestCase):
    """`kraken_client.py` : construction des payloads, gestion d'erreurs, sans mock bas niveau sur `requests`/`_sign`."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='kraken-client-tester', password='strong-test-password'
        )

    # -- add_spot_order ------------------------------------------------

    @patch('apps.core.kraken_client._private_request')
    @patch('apps.core.kraken_client.resolve_pair', return_value='XBTUSD')
    def test_add_spot_order_builds_expected_payload(self, mocked_resolve, mocked_private):
        mocked_private.return_value = {'txid': ['ABC-123'], 'descr': {'order': 'buy 0.5 XBTUSD'}}

        result = add_spot_order('btc', 'buy', Decimal('0.5'), user=self.user, ordertype='market')

        mocked_resolve.assert_called_once_with('btc')
        mocked_private.assert_called_once_with(
            'AddOrder',
            {'pair': 'XBTUSD', 'type': 'buy', 'ordertype': 'market', 'volume': '0.5'},
            user=self.user, retryable=False,
        )
        self.assertEqual(result, {'txid': 'ABC-123', 'descr': 'buy 0.5 XBTUSD', 'pair': 'XBTUSD'})

    @patch('apps.core.kraken_client._private_request')
    @patch('apps.core.kraken_client.resolve_pair', return_value='XBTUSD')
    def test_add_spot_order_includes_price_validate_and_userref(self, _mocked_resolve, mocked_private):
        mocked_private.return_value = {'txid': ['ABC-123'], 'descr': {'order': ''}}

        add_spot_order(
            'BTC', 'sell', Decimal('1'), user=self.user,
            ordertype='limit', price=Decimal('30000'), validate=True, userref=42,
        )

        payload = mocked_private.call_args[0][1]
        self.assertEqual(payload['price'], '30000')
        self.assertEqual(payload['validate'], 'true')
        self.assertEqual(payload['userref'], '42')

    def test_add_spot_order_invalid_side_raises(self):
        with self.assertRaises(KrakenAPIError):
            add_spot_order('BTC', 'hold', Decimal('1'), user=self.user)

    def test_add_spot_order_limit_without_price_raises(self):
        with self.assertRaises(KrakenAPIError):
            add_spot_order('BTC', 'buy', Decimal('1'), user=self.user, ordertype='limit')

    @patch('apps.core.kraken_client._private_request', return_value={'txid': [], 'descr': {}})
    @patch('apps.core.kraken_client.resolve_pair', return_value='XBTUSD')
    def test_add_spot_order_raises_without_txid_when_not_validating(self, _mocked_resolve, _mocked_private):
        with self.assertRaises(KrakenAPIError):
            add_spot_order('BTC', 'buy', Decimal('1'), user=self.user)

    @patch('apps.core.kraken_client._private_request', return_value={'txid': [], 'descr': {}})
    @patch('apps.core.kraken_client.resolve_pair', return_value='XBTUSD')
    def test_add_spot_order_validate_mode_allows_missing_txid(self, _mocked_resolve, _mocked_private):
        result = add_spot_order('BTC', 'buy', Decimal('1'), user=self.user, validate=True)

        self.assertEqual(result['txid'], '')

    # -- query_orders / fetch_order_fill_price / cancel_order ----------

    @patch('apps.core.kraken_client._private_request')
    def test_query_orders_returns_empty_dict_without_calling_kraken(self, mocked_private):
        self.assertEqual(query_orders([], user=self.user), {})
        mocked_private.assert_not_called()

    @patch('apps.core.kraken_client._private_request')
    def test_query_orders_joins_txids(self, mocked_private):
        mocked_private.return_value = {'TX1': {}, 'TX2': {}}

        query_orders(['TX1', 'TX2'], user=self.user)

        mocked_private.assert_called_once_with('QueryOrders', {'txid': 'TX1,TX2'}, user=self.user)

    @patch('apps.core.kraken_client.query_orders')
    def test_fetch_order_fill_price_returns_none_when_order_absent(self, mocked_query):
        mocked_query.return_value = {}

        self.assertIsNone(fetch_order_fill_price('TX1', user=self.user))

    @patch('apps.core.kraken_client.query_orders')
    def test_fetch_order_fill_price_returns_none_when_not_closed(self, mocked_query):
        mocked_query.return_value = {'TX1': {'status': 'open', 'price': '100'}}

        self.assertIsNone(fetch_order_fill_price('TX1', user=self.user))

    @patch('apps.core.kraken_client.query_orders')
    def test_fetch_order_fill_price_returns_price_when_closed(self, mocked_query):
        mocked_query.return_value = {'TX1': {'status': 'closed', 'price': '30123.5'}}

        self.assertEqual(fetch_order_fill_price('TX1', user=self.user), Decimal('30123.5'))

    @patch('apps.core.kraken_client._private_request')
    def test_cancel_order_calls_private_request_not_retryable(self, mocked_private):
        cancel_order('TX1', user=self.user)

        mocked_private.assert_called_once_with('CancelOrder', {'txid': 'TX1'}, user=self.user, retryable=False)

    # -- _private_request (frontière HTTP/signature, sans mocker requests/_sign) --

    @patch('apps.core.kraken_client._get_kraken_credentials', return_value=('', ''))
    def test_private_request_raises_without_credentials(self, _mocked_creds):
        from .kraken_client import _private_request

        with self.assertRaises(KrakenAPIError):
            _private_request('Balance', user=self.user)

    @patch('apps.core.kraken_client._http_session')
    @patch('apps.core.kraken_client._get_kraken_credentials', return_value=('key', 'c2VjcmV0'))
    def test_private_request_raises_on_kraken_error(self, _mocked_creds, mocked_session_factory):
        from .kraken_client import _private_request

        mocked_response = mocked_session_factory.return_value.post.return_value
        mocked_response.raise_for_status.return_value = None
        mocked_response.json.return_value = {'error': ['EGeneral:Invalid arguments']}

        with self.assertRaises(KrakenAPIError):
            _private_request('Balance', user=self.user)

    @patch('apps.core.kraken_client._http_session')
    @patch('apps.core.kraken_client._get_kraken_credentials', return_value=('key', 'c2VjcmV0'))
    def test_private_request_raises_on_invalid_json(self, _mocked_creds, mocked_session_factory):
        from .kraken_client import _private_request

        mocked_response = mocked_session_factory.return_value.post.return_value
        mocked_response.raise_for_status.return_value = None
        mocked_response.json.side_effect = ValueError('not json')

        with self.assertRaises(KrakenAPIError):
            _private_request('Balance', user=self.user)


class PortfolioServiceTests(TestCase):
    """`portfolio_service.py` : agrégation des stats dashboard, isolation multi-utilisateur."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='portfolio-tester', password='strong-test-password'
        )
        self.other_user = get_user_model().objects.create_user(
            username='portfolio-other', password='strong-test-password'
        )

    def test_compute_investment_stats_empty(self):
        stats = compute_investment_stats(self.user)

        self.assertEqual(stats['nb_positions'], 0)
        self.assertEqual(stats['capital_investi'], Decimal('0'))
        self.assertEqual(stats['valeur_actuelle'], Decimal('0'))

    @patch('apps.core.portfolio_service.fetch_current_prices', return_value=({'BTC': Decimal('120')}, set()))
    def test_compute_investment_stats_nets_buy_and_sell(self, _mocked_prices):
        SimpleInvestment.objects.create(
            user=self.user, symbol='BTC', amount=Decimal('2'), price=Decimal('100'), action='ACHAT'
        )
        SimpleInvestment.objects.create(
            user=self.user, symbol='BTC', amount=Decimal('1'), price=Decimal('110'), action='VENTE'
        )

        stats = compute_investment_stats(self.user)

        self.assertEqual(stats['nb_positions'], 2)
        self.assertEqual(stats['capital_investi'], Decimal('90'))  # 2*100 - 1*110
        self.assertEqual(stats['valeur_actuelle'], Decimal('120'))  # 1 BTC restant * 120
        self.assertEqual(stats['pnl'], Decimal('30'))

    @patch('apps.core.portfolio_service.fetch_current_prices', return_value=({}, set()))
    def test_compute_spot_stats_filters_by_trade_mode(self, _mocked_prices):
        SpotTrading.objects.create(
            user=self.user, symbol='BTC', amount=Decimal('1'), entry_price=Decimal('100'),
            trade_mode='LIVE',
        )
        SpotTrading.objects.create(
            user=self.user, symbol='ETH', amount=Decimal('1'), entry_price=Decimal('50'),
            trade_mode='PAPER',
        )

        live_stats = compute_spot_stats(self.user, trade_mode='LIVE')
        all_stats = compute_spot_stats(self.user)

        self.assertEqual(live_stats['nb_open'], 1)
        self.assertEqual(all_stats['nb_open'], 2)

    @patch('apps.core.portfolio_service.fetch_current_prices', return_value=({}, set()))
    def test_compute_spot_stats_realized_pnl_on_closed_position(self, _mocked_prices):
        SpotTrading.objects.create(
            user=self.user, symbol='BTC', amount=Decimal('2'),
            entry_price=Decimal('100'), exit_price=Decimal('150'), trade_mode='LIVE',
        )

        stats = compute_spot_stats(self.user, trade_mode='LIVE')

        self.assertEqual(stats['nb_closed'], 1)
        self.assertEqual(stats['pnl_realized'], Decimal('100'))
        self.assertEqual(stats['pnl_total'], Decimal('100'))

    @patch('apps.core.portfolio_service.fetch_current_prices', return_value=({'BTC': Decimal('110')}, set()))
    def test_compute_futures_stats_unrealized_pnl_depends_on_direction(self, _mocked_prices):
        FuturesTrading.objects.create(
            user=self.user, symbol='BTC', amount=Decimal('1'),
            entry_price=Decimal('100'), direction='LONG', trade_mode='LIVE',
        )
        FuturesTrading.objects.create(
            user=self.user, symbol='BTC', amount=Decimal('1'),
            entry_price=Decimal('100'), direction='SHORT', trade_mode='LIVE',
        )

        stats = compute_futures_stats(self.user, trade_mode='LIVE')

        # LONG gagne (+10), SHORT perd (-10) : le PnL non réalisé net est nul.
        self.assertEqual(stats['pnl_unrealized'], Decimal('0'))
        self.assertEqual(stats['nb_open'], 2)

    @patch('apps.core.portfolio_service.fetch_current_prices', return_value=({}, set()))
    def test_compute_global_stats_excludes_paper_positions(self, _mocked_prices):
        SpotTrading.objects.create(
            user=self.user, symbol='BTC', amount=Decimal('1'),
            entry_price=Decimal('100'), exit_price=Decimal('200'), trade_mode='PAPER',
        )
        SpotTrading.objects.create(
            user=self.user, symbol='ETH', amount=Decimal('1'),
            entry_price=Decimal('50'), exit_price=Decimal('80'), trade_mode='LIVE',
        )

        stats = compute_global_stats(self.user)

        # Seule la position LIVE (ETH, +30) doit compter, pas la PAPER (BTC, +100).
        self.assertEqual(stats['pnl_global'], Decimal('30'))

    @patch('apps.core.portfolio_service.fetch_current_prices', return_value=({}, set()))
    def test_stats_are_isolated_per_user(self, _mocked_prices):
        SpotTrading.objects.create(
            user=self.other_user, symbol='BTC', amount=Decimal('5'),
            entry_price=Decimal('100'), trade_mode='LIVE',
        )

        stats = compute_spot_stats(self.user, trade_mode='LIVE')

        self.assertEqual(stats['nb_open'], 0)

    def test_compute_futures_analytics_win_rate_none_without_closed_trades(self):
        FuturesTrading.objects.create(
            user=self.user, symbol='BTC', amount=Decimal('1'),
            entry_price=Decimal('100'), direction='LONG', trade_mode='LIVE',
        )

        analytics = compute_futures_analytics(self.user, trade_mode='LIVE')

        self.assertIsNone(analytics['win_rate'])
        self.assertIsNone(analytics['profit_factor'])
        self.assertEqual(analytics['nb_open'], 1)

    def test_compute_futures_analytics_breaks_down_by_strategy(self):
        FuturesTrading.objects.create(
            user=self.user, symbol='BTC', amount=Decimal('1'), entry_price=Decimal('100'),
            exit_price=Decimal('120'), direction='LONG', trade_mode='LIVE', strategy='breakout',
        )
        FuturesTrading.objects.create(
            user=self.user, symbol='ETH', amount=Decimal('1'), entry_price=Decimal('100'),
            exit_price=Decimal('80'), direction='LONG', trade_mode='LIVE', strategy='breakout',
        )

        analytics = compute_futures_analytics(self.user, trade_mode='LIVE')

        self.assertEqual(analytics['nb_closed'], 2)
        self.assertEqual(analytics['win_rate'], Decimal('50'))
        breakout_row = next(r for r in analytics['by_strategy'] if r['label'] == 'breakout')
        self.assertEqual(breakout_row['count'], 2)
        self.assertEqual(breakout_row['pnl'], Decimal('0'))  # +20 puis -20

    def test_build_chart_series_excludes_paper_but_keeps_investment(self):
        SimpleInvestment.objects.create(
            user=self.user, symbol='BTC', amount=Decimal('1'), price=Decimal('100'), action='ACHAT'
        )
        SpotTrading.objects.create(
            user=self.user, symbol='ETH', amount=Decimal('1'),
            entry_price=Decimal('50'), trade_mode='PAPER',
        )

        series = build_chart_series(self.user)

        self.assertEqual(len(series['investment']), 1)
        self.assertEqual(series['spot'], [])
        self.assertEqual(len(series['all']), 1)
