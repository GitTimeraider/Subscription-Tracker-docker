#!/usr/bin/env python3
"""
Test script for the new UniRateAPI currency conversion system
"""

import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.currency import CurrencyConverter
from app.models import ExchangeRate
from app import create_app
from datetime import date
import json

def test_currency_conversion():
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        print("Testing Currency Conversion System")
        print("=" * 50)
        
        converter = CurrencyConverter()
        
        # Test without API key (should use fallback rates)
        print("\n1. Testing without API key (fallback rates):")
        rates = converter.get_exchange_rates('EUR')
        if rates:
            print(f"✓ Got {len(rates)} exchange rates")
            print(f"  EUR to USD: {rates.get('USD', 'N/A')}")
            print(f"  EUR to GBP: {rates.get('GBP', 'N/A')}")
        else:
            print("✗ Failed to get exchange rates")
        
        # Test conversion
        print("\n2. Testing currency conversion:")
        result = converter.convert_amount(100, 'EUR', 'USD')
        print(f"  100 EUR = {result:.2f} USD")
        
        result = converter.convert_amount(100, 'USD', 'EUR')
        print(f"  100 USD = {result:.2f} EUR")
        
        # Test with API key (if you have one)
        print("\n3. Testing with API key:")
        print("  To test with a real API key, set it here:")
        print("  converter.set_api_key('your-unirate-api-key')")
        print("  Then call converter.get_exchange_rates() again")
        
        # Test database caching
        print("\n4. Testing database caching:")
        today = date.today()
        
        # Check if there are any cached rates
        cached = ExchangeRate.get_latest_rates('EUR')
        if cached:
            print(f"✓ Found cached rates for today ({today})")
            print(f"  Cached EUR to USD: {cached.get('USD', 'N/A')}")
        else:
            print(f"  No cached rates found for today ({today})")
        
        # Test saving rates to cache
        test_rates = {'EUR': 1.0, 'USD': 1.09, 'GBP': 0.86}
        ExchangeRate.save_rates(test_rates, 'EUR')
        print(f"✓ Saved test rates to cache")
        
        # Verify cached rates
        cached_again = ExchangeRate.get_latest_rates('EUR')
        if cached_again and cached_again.get('USD') == 1.09:
            print("✓ Cache save/load working correctly")
        else:
            print("✗ Cache save/load not working")
        
        print("\n" + "=" * 50)
        print("Test completed!")

if __name__ == "__main__":
    test_currency_conversion()
