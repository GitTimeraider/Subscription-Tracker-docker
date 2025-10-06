import requests
import json
import os
from datetime import datetime, date, timezone
from flask import current_app
import xml.etree.ElementTree as ET
from decimal import Decimal, getcontext, InvalidOperation

# High precision for chained conversions
getcontext().prec = 28

FLOATRATES_URL = "https://www.floatrates.com/daily/eur.json"
ERAPI_URL = "https://open.er-api.com/v6/latest/EUR"

class CurrencyConverter:
    """Currency converter with multi-provider fallback and provider-specific caching."""

    def __init__(self):
        self.last_provider = None
        self.last_attempt_chain = []  # list of (provider, status)
        self._circuit_breaker = {}  # Track failed providers

    def _is_circuit_open(self, provider):
        """Check if circuit breaker is open for a provider"""
        if provider not in self._circuit_breaker:
            return False
        
        failures, last_failure = self._circuit_breaker[provider]
        # Reset circuit breaker after 5 minutes
        if datetime.now().timestamp() - last_failure > 300:
            del self._circuit_breaker[provider]
            return False
        
        # Open circuit after 3 consecutive failures
        return failures >= 3

    def _record_failure(self, provider):
        """Record a failure for circuit breaker"""
        if provider not in self._circuit_breaker:
            self._circuit_breaker[provider] = (1, datetime.now().timestamp())
        else:
            failures, _ = self._circuit_breaker[provider]
            self._circuit_breaker[provider] = (failures + 1, datetime.now().timestamp())

    def _record_success(self, provider):
        """Record a success and reset circuit breaker"""
        if provider in self._circuit_breaker:
            del self._circuit_breaker[provider]

    def get_exchange_rates(self, base_currency: str = 'EUR', force_refresh: bool = False):
        from app.models import ExchangeRate
        self.last_attempt_chain = []
        base_currency = 'EUR'
        refresh_minutes = int(os.getenv('CURRENCY_REFRESH_MINUTES', '1440'))
        provider_priority_env = os.getenv('CURRENCY_PROVIDER_PRIORITY', 'frankfurter,floatrates,erapi_open')
        provider_priority = [p.strip().lower() for p in provider_priority_env.split(',') if p.strip()]
        provider_priority = ['floatrates' if p == 'jsdelivr' else p for p in provider_priority]
        primary_provider = provider_priority[0] if provider_priority else None

        if not force_refresh and primary_provider:
            record = ExchangeRate.query.filter_by(date=date.today(), base_currency=base_currency, provider=primary_provider).first()
            if record:
                age_min = (datetime.now(timezone.utc) - record.created_at).total_seconds() / 60.0
                if age_min <= refresh_minutes:
                    try:
                        self.last_provider = primary_provider
                        self.last_attempt_chain.append((primary_provider, 'cache'))
                        return json.loads(record.rates_json)
                    except Exception:
                        pass

        for provider in provider_priority:
            try:
                # Skip provider if circuit breaker is open
                if self._is_circuit_open(provider):
                    self.last_attempt_chain.append((provider, 'circuit-open'))
                    continue
                    
                if not force_refresh:
                    cached = ExchangeRate.query.filter_by(date=date.today(), base_currency=base_currency, provider=provider).first()
                    if cached:
                        age_min = (datetime.now(timezone.utc) - cached.created_at).total_seconds() / 60.0
                        if age_min <= refresh_minutes:
                            try:
                                self.last_provider = provider
                                self.last_attempt_chain.append((provider, 'cache'))
                                return json.loads(cached.rates_json)
                            except Exception:
                                pass
                if provider == 'frankfurter':
                    rates = self._fetch_frankfurter()
                elif provider == 'floatrates':
                    rates = self._fetch_floatrates()
                elif provider == 'erapi_open':
                    rates = self._fetch_erapi_open()
                else:
                    continue
                if rates and 'USD' in rates:
                    self.last_provider = provider
                    self._record_success(provider)  # Reset circuit breaker on success
                    ExchangeRate.save_rates({k: str(v) for k, v in rates.items()}, base_currency, provider=provider)
                    self.last_attempt_chain.append((provider, 'fetched'))
                    return rates
            except Exception as e:
                current_app.logger.warning(f"Provider {provider} failed: {e}")
                self._record_failure(provider)  # Record failure for circuit breaker
                self.last_attempt_chain.append((provider, f'failed:{e.__class__.__name__}'))

        fallback_cached = ExchangeRate.query.filter_by(date=date.today(), base_currency=base_currency).order_by(ExchangeRate.created_at.desc()).first()
        if fallback_cached:
            try:
                self.last_provider = fallback_cached.provider
                self.last_attempt_chain.append((fallback_cached.provider, 'fallback-cached'))
                return json.loads(fallback_cached.rates_json)
            except Exception:
                pass

        current_app.logger.error("All currency providers failed; using static fallback rates")
        self.last_provider = 'fallback'
        self.last_attempt_chain.append(('fallback', 'static'))
        return self._get_fallback_rates(base_currency)

    def _fetch_frankfurter(self):
        url = 'https://api.frankfurter.app/latest?from=EUR'
        r = requests.get(url, timeout=3)  # Further reduced timeout from 5 to 3 seconds
        r.raise_for_status()
        data = r.json()
        rates = data.get('rates') or {}
        out = {'EUR': Decimal('1')}
        for k,v in rates.items():
            try:
                out[k] = Decimal(str(v))
            except Exception:
                continue
        return out

    def _fetch_floatrates(self):
        r = requests.get(FLOATRATES_URL, timeout=3)  # Further reduced timeout from 5 to 3 seconds
        r.raise_for_status()
        data = r.json()  # keys are lowercase currency codes
        out = {'EUR': Decimal('1')}
        for code, meta in data.items():
            # meta expected to have 'rate'
            rate = meta.get('rate') if isinstance(meta, dict) else None
            if rate is None:
                continue
            try:
                out[code.upper()] = Decimal(str(rate))
            except Exception:
                continue
        return out

    def _fetch_erapi_open(self):
        r = requests.get(ERAPI_URL, timeout=3)  # Further reduced timeout from 5 to 3 seconds
        r.raise_for_status()
        data = r.json()
        if data.get('result') != 'success':
            raise ValueError('erapi_open result not success')
        rates = data.get('rates') or {}
        out = {'EUR': Decimal('1')}
        for k, v in rates.items():
            try:
                out[k.upper()] = Decimal(str(v))
            except Exception:
                continue
        return out
    
    def _get_fallback_rates(self, base_currency='EUR'):
        """Get fallback exchange rates when API is unavailable"""
        from app.models import ExchangeRate
        
        # Try to get the most recent rates from database (any date)
        latest_rate = ExchangeRate.query.filter_by(base_currency=base_currency).order_by(ExchangeRate.date.desc()).first()
        if latest_rate:
            current_app.logger.info(f"Using fallback rates from {latest_rate.date}")
            raw = json.loads(latest_rate.rates_json)
            # Convert any stored string/float to Decimal safely
            dec = {}
            for k, v in raw.items():
                try:
                    if k == 'EUR':
                        dec[k] = Decimal('1')
                    else:
                        dec[k] = Decimal(str(v))
                except (InvalidOperation, TypeError):
                    continue
            return dec
        
    # If no database rates available, use hardcoded fallback rates (approximate values)
        current_app.logger.warning("Using hardcoded fallback exchange rates")
        if base_currency == 'EUR':
            base_fallback = {
                'EUR': '1', 'USD': '1.09', 'GBP': '0.86', 'CAD': '1.48', 'AUD': '1.65',
                'JPY': '157.0', 'CHF': '0.96', 'CNY': '7.85', 'INR': '91.0', 'SEK': '11.3',
                'NOK': '11.8', 'DKK': '7.46', 'PLN': '4.35', 'CZK': '24.7', 'HUF': '390.0',
                'BGN': '1.96', 'RON': '4.97', 'HRK': '7.53', 'RUB': '100.0', 'TRY': '32.0',
                'BRL': '6.15', 'MXN': '18.5', 'SGD': '1.45', 'HKD': '8.5', 'KRW': '1450.0',
                'ZAR': '19.8', 'NZD': '1.78', 'THB': '38.5', 'MYR': '5.0', 'PHP': '61.0',
                'IDR': '16800.0', 'VND': '26500.0'
            }
            return {k: Decimal(v) for k, v in base_fallback.items()}
        else:
            # For other base currencies, convert from EUR base
            eur_rates = self._get_fallback_rates('EUR')
            if base_currency in eur_rates:
                base_rate = eur_rates[base_currency]
                converted_rates = {}
                for currency, rate in eur_rates.items():
                    try:
                        converted_rates[currency] = (rate / base_rate)
                    except (InvalidOperation, ZeroDivisionError):
                        continue
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
            return float(amount)

        # Fetch rates if not provided
        if rates is None:
            rates = self.get_exchange_rates(base_currency)
        if not rates:
            return float(amount)

        # Normalize all rates to Decimal
        dec_rates = {}
        for k, v in rates.items():
            try:
                if isinstance(v, Decimal):
                    dec_rates[k] = v
                else:
                    dec_rates[k] = Decimal(str(v))
            except (InvalidOperation, TypeError):
                continue
        if base_currency not in dec_rates:
            dec_rates[base_currency] = Decimal('1')
        try:
            amount_dec = Decimal(str(amount))
        except (InvalidOperation, TypeError):
            return float(amount)

        try:
            # Normalize source amount into base currency first
            if from_currency == base_currency:
                amount_in_base = amount_dec
            else:
                if from_currency not in dec_rates or not dec_rates[from_currency]:
                    return float(amount)
                amount_in_base = amount_dec / dec_rates[from_currency]

            # From base to target
            if to_currency == base_currency:
                return float(amount_in_base)
            if to_currency not in dec_rates or not dec_rates[to_currency]:
                return float(amount)
            return float(amount_in_base * dec_rates[to_currency])
        except (KeyError, ZeroDivisionError, TypeError):
            return float(amount)

    def clear_today_cache(self, base_currency='EUR'):
        """Clear today's cached rates to force a refetch next call."""
        try:
            from app.models import ExchangeRate
            from app import db
            today_records = ExchangeRate.query.filter_by(date=date.today(), base_currency=base_currency).all()
            if today_records:
                for rec in today_records:
                    db.session.delete(rec)
                db.session.commit()
                current_app.logger.info(f"Cleared today's exchange rate cache for base {base_currency} (all providers)")
                return True
        except Exception as e:
            current_app.logger.error(f"Failed to clear cache: {e}")
        return False
    
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
