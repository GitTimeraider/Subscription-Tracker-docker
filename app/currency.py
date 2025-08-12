import requests
import json
from datetime import datetime, date
from flask import current_app
import os

class CurrencyConverter:
    def __init__(self):
        self.api_key = None
        
    def set_api_key(self, api_key):
        """Set the UniRateAPI API key"""
        self.api_key = api_key
    
    def get_exchange_rates(self, base_currency='EUR'):
        """Get exchange rates with daily caching using database storage"""
        from app.models import ExchangeRate
        
        # First, try to get today's rates from database
        cached_rates = ExchangeRate.get_latest_rates(base_currency)
        if cached_rates:
            current_app.logger.info(f"Using cached exchange rates for {date.today()}")
            return cached_rates
        
        # If no cached rates for today, fetch from API
        if not self.api_key:
            current_app.logger.warning("No UniRateAPI key provided, using fallback rates")
            return self._get_fallback_rates(base_currency)
            
        try:
            # UniRateAPI endpoint
            url = f"https://api.unirateapi.com/v1/latest?base={base_currency}"
            headers = {
                'Authorization': f'Bearer {self.api_key}'
            }
            
            current_app.logger.info(f"Fetching fresh exchange rates from UniRateAPI for base: {base_currency}")
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('success', True):  # UniRateAPI uses 'success' field
                rates = data.get('rates', {})
                # Add base currency to rates
                rates[base_currency] = 1.0
                
                # Save to database for daily caching
                ExchangeRate.save_rates(rates, base_currency)
                current_app.logger.info(f"Successfully fetched and cached {len(rates)} exchange rates")
                
                return rates
            else:
                error_msg = data.get('error', {}).get('message', 'Unknown error')
                current_app.logger.error(f"UniRateAPI error: {error_msg}")
                return self._get_fallback_rates(base_currency)
                
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Currency API request failed: {e}")
            return self._get_fallback_rates(base_currency)
        except Exception as e:
            current_app.logger.error(f"Currency conversion error: {e}")
            return self._get_fallback_rates(base_currency)
    
    def _get_fallback_rates(self, base_currency='EUR'):
        """Get fallback exchange rates when API is unavailable"""
        from app.models import ExchangeRate
        
        # Try to get the most recent rates from database (any date)
        latest_rate = ExchangeRate.query.filter_by(base_currency=base_currency).order_by(ExchangeRate.date.desc()).first()
        if latest_rate:
            current_app.logger.info(f"Using fallback rates from {latest_rate.date}")
            return json.loads(latest_rate.rates_json)
        
        # If no database rates available, use hardcoded fallback rates (approximate values)
        current_app.logger.warning("Using hardcoded fallback exchange rates")
        if base_currency == 'EUR':
            return {
                'EUR': 1.0, 'USD': 1.09, 'GBP': 0.86, 'CAD': 1.48, 'AUD': 1.65,
                'JPY': 157.0, 'CHF': 0.96, 'CNY': 7.85, 'INR': 91.0, 'SEK': 11.3,
                'NOK': 11.8, 'DKK': 7.46, 'PLN': 4.35, 'CZK': 24.7, 'HUF': 390.0,
                'BGN': 1.96, 'RON': 4.97, 'HRK': 7.53, 'RUB': 100.0, 'TRY': 32.0,
                'BRL': 6.15, 'MXN': 18.5, 'SGD': 1.45, 'HKD': 8.5, 'KRW': 1450.0,
                'ZAR': 19.8, 'NZD': 1.78, 'THB': 38.5, 'MYR': 5.0, 'PHP': 61.0,
                'IDR': 16800.0, 'VND': 26500.0
            }
        else:
            # For other base currencies, convert from EUR base
            eur_rates = self._get_fallback_rates('EUR')
            if base_currency in eur_rates:
                base_rate = eur_rates[base_currency]
                converted_rates = {}
                for currency, rate in eur_rates.items():
                    converted_rates[currency] = rate / base_rate
                return converted_rates
            else:
                return {base_currency: 1.0}
    
    def convert_amount(self, amount, from_currency, to_currency, rates=None, base_currency='EUR'):
        """Convert amount from one currency to another.

        Parameters:
            amount (float): numeric amount
            from_currency (str): source currency code
            to_currency (str): destination currency code
            rates (dict|None): optional pre-fetched rates dictionary with base 'base_currency'
            base_currency (str): base currency the rates are expressed against (default EUR)
        """
        if amount is None:
            return 0.0
        if from_currency == to_currency:
            return amount

        # Fetch rates if not provided
        if rates is None:
            rates = self.get_exchange_rates(base_currency)
        if not rates:
            return amount

        # Ensure base currency rate present
        if base_currency not in rates:
            rates[base_currency] = 1.0

        try:
            # Normalize source amount into base currency first
            if from_currency == base_currency:
                amount_in_base = amount
            else:
                if from_currency not in rates or not rates[from_currency]:
                    return amount
                amount_in_base = amount / rates[from_currency]

            # From base to target
            if to_currency == base_currency:
                return amount_in_base
            if to_currency not in rates or not rates[to_currency]:
                return amount
            return amount_in_base * rates[to_currency]
        except (KeyError, ZeroDivisionError, TypeError):
            return amount
    
    def get_supported_currencies(self):
        """Get list of supported currencies with EUR at the top"""
        return [
            ('EUR', 'Euro (€)'),
            ('USD', 'US Dollar ($)'),
            ('GBP', 'British Pound (£)'),
            ('CAD', 'Canadian Dollar (C$)'),
            ('AUD', 'Australian Dollar (A$)'),
            ('JPY', 'Japanese Yen (¥)'),
            ('CHF', 'Swiss Franc (CHF)'),
            ('CNY', 'Chinese Yuan (¥)'),
            ('INR', 'Indian Rupee (₹)'),
            ('SEK', 'Swedish Krona (kr)'),
            ('NOK', 'Norwegian Krone (kr)'),
            ('DKK', 'Danish Krone (kr)'),
            ('PLN', 'Polish Zloty (zł)'),
            ('CZK', 'Czech Koruna (Kč)'),
            ('HUF', 'Hungarian Forint (Ft)'),
            ('BGN', 'Bulgarian Lev (лв)'),
            ('RON', 'Romanian Leu (lei)'),
            ('HRK', 'Croatian Kuna (kn)'),
            ('RUB', 'Russian Ruble (₽)'),
            ('TRY', 'Turkish Lira (₺)'),
            ('BRL', 'Brazilian Real (R$)'),
            ('MXN', 'Mexican Peso ($)'),
            ('SGD', 'Singapore Dollar (S$)'),
            ('HKD', 'Hong Kong Dollar (HK$)'),
            ('KRW', 'South Korean Won (₩)'),
            ('ZAR', 'South African Rand (R)'),
            ('NZD', 'New Zealand Dollar (NZ$)'),
            ('THB', 'Thai Baht (฿)'),
            ('MYR', 'Malaysian Ringgit (RM)'),
            ('PHP', 'Philippine Peso (₱)'),
            ('IDR', 'Indonesian Rupiah (Rp)'),
            ('VND', 'Vietnamese Dong (₫)')
        ]
    
    def get_currency_symbol(self, currency_code):
        """Get currency symbol for display"""
        currency_symbols = {
            'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥', 'CNY': '¥',
            'CAD': 'C$', 'AUD': 'A$', 'CHF': 'CHF', 'INR': '₹',
            'SEK': 'kr', 'NOK': 'kr', 'DKK': 'kr', 'PLN': 'zł',
            'CZK': 'Kč', 'HUF': 'Ft', 'BGN': 'лв', 'RON': 'lei',
            'HRK': 'kn', 'RUB': '₽', 'TRY': '₺', 'BRL': 'R$',
            'MXN': '$', 'SGD': 'S$', 'HKD': 'HK$', 'KRW': '₩',
            'ZAR': 'R', 'NZD': 'NZ$', 'THB': '฿', 'MYR': 'RM',
            'PHP': '₱', 'IDR': 'Rp', 'VND': '₫'
        }
        return currency_symbols.get(currency_code, currency_code)

# Global converter instance
currency_converter = CurrencyConverter()
