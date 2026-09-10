from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from .views import positions_json


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