# Currency Exchange API Migration

This document explains the changes made to migrate from APILayer (fixer.io) to UniRateAPI.com with daily caching.

## Changes Made

### 1. API Provider Change
- **Before**: Used APILayer (fixer.io) API at `api.apilayer.com/fixer/latest`
- **After**: Uses UniRateAPI.com at `api.unirateapi.com/v1/latest`

### 2. Daily Caching Implementation
- **Before**: Cached exchange rates for 1 hour in memory
- **After**: Caches exchange rates for the entire day in the database
- Exchange rates are fetched once per day and stored in the `exchange_rate` table
- If API is unavailable, uses the most recent cached rates as fallback

### 3. Database Changes
- Added new `exchange_rate` table for persistent daily caching
- Added `unirate_api_key` column to `user_settings` table
- Old `fixer_api_key` column is preserved for backward compatibility

### 4. Improved Fallback System
- If no API key is provided, uses cached rates from database
- If no cached rates exist, uses hardcoded approximate exchange rates
- Graceful degradation ensures the application continues working even without API access

## Migration Steps

### 1. Run Database Migration
```bash
python migrate_to_unirate.py
```

This will:
- Create a backup of your database
- Add the new `unirate_api_key` column
- Copy existing API keys from `fixer_api_key` to `unirate_api_key`
- Create the new `exchange_rate` table

### 2. Get UniRateAPI Key
1. Visit [unirateapi.com](https://unirateapi.com)
2. Sign up for a free account
3. Get your API key
4. Go to General Settings in the application
5. Enter your UniRateAPI key

### 3. Test the System
```bash
python test_currency.py
```

This will verify that:
- Currency conversion is working
- Database caching is functional
- Fallback rates are available

## API Differences

### APILayer (Old)
```http
GET https://api.apilayer.com/fixer/latest
Headers:
  apikey: YOUR_API_KEY
Parameters:
  base: EUR
  symbols: USD,GBP,CAD...
```

### UniRateAPI (New)
```http
GET https://api.unirateapi.com/v1/latest?base=EUR
Headers:
  Authorization: Bearer YOUR_API_KEY
```

## Benefits of the New System

### Daily Caching
- **Efficiency**: API is called only once per day instead of every hour
- **Cost Savings**: Significantly reduces API usage and costs
- **Reliability**: Cached rates available even if API is temporarily unavailable
- **Performance**: Faster response times for currency conversions

### Better Fallback System
- Uses most recent cached rates if API fails
- Hardcoded fallback rates if no cache exists
- Application continues working even without internet/API access

### Persistent Storage
- Exchange rates survive application restarts
- Historical rate data preserved in database
- Better debugging and troubleshooting capabilities

## Configuration

### Environment Variables (Optional)
You can also set the API key via environment variable:
```bash
export UNIRATE_API_KEY=your_api_key_here
```

### Database Schema
New `exchange_rate` table:
```sql
CREATE TABLE exchange_rate (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    base_currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
    rates_json TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, base_currency)
);
```

## Troubleshooting

### No Exchange Rates Available
1. Check if UniRateAPI key is configured in General Settings
2. Verify API key is valid at unirateapi.com
3. Check application logs for API errors
4. Run `python test_currency.py` to diagnose issues

### Old Data Migration
- Old `fixer_api_key` values are automatically copied to `unirate_api_key`
- You may need to get a new API key from UniRateAPI.com
- Old column is preserved for safety but no longer used

### API Rate Limits
- UniRateAPI free tier typically allows 1000 requests/month
- With daily caching, you'll use ~30 requests/month (one per day)
- Monitor your usage at unirateapi.com dashboard

## Support

If you encounter issues:
1. Check the application logs for error messages
2. Run the test script to verify functionality
3. Ensure your UniRateAPI key is valid and has remaining quota
4. Check network connectivity to unirateapi.com
