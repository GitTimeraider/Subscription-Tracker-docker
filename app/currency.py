import requests
import json
from datetime import datetime, timedelta
from flask import current_app
import os

class CurrencyConverter:
    def __init__(self):
        self.api_key = None
        self.cache = {}
        self.cache_duration = timedelta(hours=1)  # Cache for 1 hour
        
    def set_api_key(self, api_key):
        """Set the Fixer.io API key"""
        self.api_key = api_key
    
    def get_exchange_rates(self, base_currency='USD'):
        """Get exchange rates from Fixer.io API with caching"""
        if not self.api_key:
            return None
            
        cache_key = f"{base_currency}_{datetime.now().strftime('%Y%m%d%H')}"
        
        # Check cache first
        if cache_key in self.cache:
            cache_data = self.cache[cache_key]
            if datetime.now() - cache_data['timestamp'] < self.cache_duration:
                return cache_data['rates']
        
        try:
            # Fixer.io API endpoint
            url = f"https://api.fixer.io/latest"
            params = {
                'access_key': self.api_key,
                'base': base_currency,
                'symbols': 'USD,EUR,GBP,CAD,AUD,JPY,CHF,CNY,INR,SEK,NOK,DKK,PLN,CZK,HUF,BGN,RON,HRK,RUB,TRY,BRL,MXN,SGD,HKD,KRW,ZAR,NZD,THB,MYR,PHP,IDR,VND'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('success'):
                rates = data.get('rates', {})
                # Add base currency to rates
                rates[base_currency] = 1.0
                
                # Cache the result
                self.cache[cache_key] = {
                    'rates': rates,
                    'timestamp': datetime.now()
                }
                
                # Clean old cache entries
                self._clean_cache()
                
                return rates
            else:
                current_app.logger.error(f"Fixer.io API error: {data.get('error', {}).get('info', 'Unknown error')}")
                return None
                
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Currency API request failed: {e}")
            return None
        except Exception as e:
            current_app.logger.error(f"Currency conversion error: {e}")
            return None
    
    def _clean_cache(self):
        """Clean old cache entries"""
        current_time = datetime.now()
        keys_to_remove = []
        
        for key, data in self.cache.items():
            if current_time - data['timestamp'] > self.cache_duration:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.cache[key]
    
    def convert_amount(self, amount, from_currency, to_currency):
        """Convert amount from one currency to another"""
        if from_currency == to_currency:
            return amount
            
        rates = self.get_exchange_rates('USD')  # Use USD as base
        if not rates:
            return amount  # Return original amount if conversion fails
        
        try:
            # Convert to USD first if needed
            if from_currency != 'USD':
                if from_currency not in rates:
                    return amount
                amount_usd = amount / rates[from_currency]
            else:
                amount_usd = amount
            
            # Convert from USD to target currency
            if to_currency != 'USD':
                if to_currency not in rates:
                    return amount
                return amount_usd * rates[to_currency]
            else:
                return amount_usd
                
        except (KeyError, ZeroDivisionError, TypeError):
            return amount
    
    def get_supported_currencies(self):
        """Get list of supported currencies"""
        return [
            ('USD', 'US Dollar ($)'),
            ('EUR', 'Euro (€)'),
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
