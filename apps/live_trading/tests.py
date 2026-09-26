import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.core.models import UserPreferences

from .views import ohlc_json, positions_json, vigil_signals_json


class LiveTradingViewTests(TestCase):
    @patch('apps.live_trading.views.live_positions')
    def test_positions_json_serializes_decimals_and_entry_date(self, mocked_live_positions):
        mocked_live_positions.return_value = (
            [{
                'kind': 'spot',
                'pk': 42,
                'symbol': 'BTC',
                'amount': Decimal('0.5'),
                'entry_price': Decimal('100'),
                'entry_date': datetime(2026, 9, 9, 12, 30),
                'current_price': Decimal('110'),
                'pnl': Decimal('5'),
            }],
            set(),
        )
        request = RequestFactory().get('/live/positions.json')
        request.user = get_user_model().objects.create_user(
            username='trader', password='strong-test-password'
        )

        response = positions_json(request)

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {
                'positions': [{
                    'kind': 'spot',
                    'pk': 42,
                    'symbol': 'BTC',
                    'amount': '0.5',
                    'entry_price': '100',
                    'entry_date': '09/09/2026 12:30',
                    'current_price': '110',
                    'pnl': '5',
                }],
                'unavailable_symbols': [],
            },
        )


class OhlcJsonViewTests(TestCase):
    @patch('apps.live_trading.views.fetch_ohlc')
    def test_returns_candles_for_valid_symbol_and_interval(self, mocked_fetch_ohlc):
        mocked_fetch_ohlc.return_value = [
            {'time': 1700000000, 'open': 100.0, 'high': 110.0, 'low': 90.0, 'close': 105.0, 'volume': 5.0},
        ]
        request = RequestFactory().get('/live/ohlc.json', {'symbol': 'btc', 'interval': '240'})
        request.user = get_user_model().objects.create_user(
            username='trader', password='strong-test-password'
        )

        response = ohlc_json(request)

        self.assertEqual(response.status_code, 200)
        mocked_fetch_ohlc.assert_called_once_with('BTC', interval=240)
        self.assertJSONEqual(
            response.content,
            {'candles': [
                {'time': 1700000000, 'open': 100.0, 'high': 110.0, 'low': 90.0, 'close': 105.0, 'volume': 5.0},
            ]},
        )

    @patch('apps.live_trading.views.fetch_ohlc')
    def test_invalid_interval_falls_back_to_default(self, mocked_fetch_ohlc):
        mocked_fetch_ohlc.return_value = []
        request = RequestFactory().get('/live/ohlc.json', {'symbol': 'BTC', 'interval': '7'})
        request.user = get_user_model().objects.create_user(
            username='trader2', password='strong-test-password'
        )

        ohlc_json(request)

        mocked_fetch_ohlc.assert_called_once_with('BTC', interval=60)


class TradingPageRenderingTests(TestCase):
    """La page Trading redessinée expose bien le graphique, le sélecteur d'actif et le ticket."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='trader3', password='strong-test-password')
        self.client.force_login(self.user)

    @patch('apps.live_trading.views.live_positions', return_value=([], set()))
    def test_page_renders_chart_and_ticket_elements(self, _mocked_positions):
        response = self.client.get(reverse('live_trading:index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="tradingChart"')
        self.assertContains(response, 'id="assetSelect"')
        self.assertContains(response, 'id="tradingVolume"')
        self.assertContains(response, 'id="riskPreview"')
        self.assertContains(response, reverse('live_trading:ohlc_json'))
        self.assertContains(response, 'lightweight-charts.standalone.production.js')


class VigilSignalsJsonViewTests(TestCase):
    """`vigil_signals_json` : filtrage par actifs suivis + signaux macro toujours inclus, affichage neutre."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='trader4', password='strong-test-password')

    @patch('apps.live_trading.views.fetch_vigil_signals')
    def test_filters_by_tracked_assets_and_keeps_macro_signals(self, mocked_fetch):
        UserPreferences.objects.create(user=self.user, tracked_assets=['BTC'])
        mocked_fetch.return_value = [
            {
                'ticker': 'BTC', 'summary': 'ETF Bitcoin inflows', 'source': 'etf_flow',
                'timestamp': 't1', 'reliability_tier': 2, 'raw_payload': {'flow_usd': 1},
            },
            {
                'ticker': 'ETH', 'summary': 'Ethereum upgrade', 'source': 'news_editorial',
                'timestamp': 't2', 'reliability_tier': 3,
            },
            {
                'ticker': None, 'summary': 'Fed rate decision', 'source': 'news_aggregator',
                'timestamp': 't3', 'reliability_tier': 3,
            },
        ]
        request = RequestFactory().get('/live/vigil-signals.json')
        request.user = self.user

        response = vigil_signals_json(request)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual([s['ticker'] for s in data['signals']], ['BTC', None])
        # Affichage neutre : jamais de raw_payload/news_score bruts exposés au front.
        self.assertNotIn('raw_payload', data['signals'][0])

    @patch('apps.live_trading.views.fetch_vigil_signals', return_value=[])
    def test_returns_empty_list_when_vigil_unavailable(self, _mocked_fetch):
        request = RequestFactory().get('/live/vigil-signals.json')
        request.user = self.user

        response = vigil_signals_json(request)

        self.assertJSONEqual(response.content, {'signals': []})

    @patch('apps.live_trading.views.fetch_vigil_signals')
    def test_no_preferences_only_macro_signals_shown(self, mocked_fetch):
        mocked_fetch.return_value = [
            {'ticker': 'BTC', 'summary': 'ETF Bitcoin inflows', 'source': 'etf_flow', 'timestamp': 't1', 'reliability_tier': 2},
            {'ticker': None, 'summary': 'Fed rate decision', 'source': 'news_aggregator', 'timestamp': 't3', 'reliability_tier': 3},
        ]
        request = RequestFactory().get('/live/vigil-signals.json')
        request.user = self.user

        response = vigil_signals_json(request)

        data = json.loads(response.content)
        self.assertEqual([s['ticker'] for s in data['signals']], [None])