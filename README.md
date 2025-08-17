# 🔔 Subscription Tracker (Dockerized)
<p align="center">
  <img src="https://github.com/GitTimeraider/Assets/blob/main/Subscription-Tracker-docker/img/icon_sub.png" />
</p>
Welcome to the most wonderfully comprehensive and dockerized way to track your subscriptions and recurring costs! This application helps you manage all your recurring payments, from streaming services to software licenses, ensuring you never fall down the rabbit hole of forgotten subscriptions.

## ✨ Features

### 🔐 **User Management**
- Secure user registration and login system
- Individual user accounts with personalized settings
- Password change functionality

### 📊 **Comprehensive Subscription Management**
- Add, edit, and remove subscriptions with ease
- Support for multiple categories: Software, Hardware, Entertainment, Utilities, Cloud Services, News & Media, Education, Fitness, Gaming, and more
- Detailed subscription information including notes

### 💰 **Flexible Billing Cycles**
- **Daily** - Perfect for daily service charges
- **Weekly** - For weekly subscriptions
- **Bi-weekly** - Every 2 weeks
- **Monthly** - The most common billing cycle
- **Bi-monthly** - Every 2 months
- **Quarterly** - Every 3 months
- **Semi-annually** - Every 6 months
- **Yearly** - Annual subscriptions
- **Custom** - Define your own billing period (every 5 years? Why not!)

### 📧 **Smart Email Notifications**
- Get notified before subscriptions expire
- Customizable notification timing (1-365 days before expiry)
- Rich HTML email format with urgency indicators
- Multiple daily checks to ensure timely notifications
- User-specific notification preferences

### 📈 **Analytics & Insights**
- Cost tracking with monthly and yearly projections
- Category-based spending breakdown
- Interactive charts and visualizations
- Upcoming renewals dashboard
- Billing cycle distribution analysis

### 💹 **Accurate Multi-Currency Conversion**
- Per-user preferred display currency (defaults to EUR)
- High-precision Decimal math (no floating point drift)
- Multi-provider live EUR base exchange rates with automatic fallback
- Cached daily (per provider) with manual refresh & force-refetch
- Transparent attempt chain + active provider/mismatch badges in settings & dashboard

### ⚙️ **Powerful Settings**
- **User Settings**: Change username, email, and password
- **Notification Settings**: Configure email preferences, timing, currency, and timezone
- **Email Settings**: Admin-configurable SMTP settings
- **Filters**: Filter subscriptions by category, status, and expiration
- **Exchange Rate Provider Selection**: Choose between multiple free, no‑API‑key data sources

### 🎨 **Beautiful Interface**
- Modern, responsive design using Bootstrap 5
- Intuitive navigation and user experience
- Mobile-friendly layout
- Interactive dashboard with real-time updates
- Status indicators for active/inactive subscriptions

### 🐳 **Docker Support**
- Easy deployment with Docker
- Pre-built images available on GitHub Container Registry
- Environment variable configuration

## 🐳 Docker Deployment

### Using Docker Compose
```yaml
version: '3.8'
services:
  web:
    image: ghcr.io/gittimeraider/subscription-tracker:latest
    ports:
      - "5000:5000"
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - MAIL_SERVER=${MAIL_SERVER}
      - MAIL_PORT=${MAIL_PORT}
      - MAIL_USE_TLS=${MAIL_USE_TLS}
      - MAIL_USERNAME=${MAIL_USERNAME}
      - MAIL_PASSWORD=${MAIL_PASSWORD}
      - MAIL_FROM=${MAIL_FROM}
      - DAYS_BEFORE_EXPIRY=${DAYS_BEFORE_EXPIRY}
    volumes:
      - ./data:/app/instance
```

### Using Docker

1. **Pull the image from GitHub Container Registry:**
   ```bash
   docker pull ghcr.io/gittimeraider/subscription-tracker:latest
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Run with docker-compose:**
   ```bash
   docker-compose up -d
   ```

4. **Access the application:**
   - Navigate to `http://localhost:5000`
   - Default credentials: `admin` / `changeme`
   - **⚠️ Change the default password immediately!**

## ⚙️ Configuration

### Environment Variables

All of these are optional, though it is adviced to use the SECRET_KEY and the MAIL_ environmentals to the very least.

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key for sessions | Random string |
| `DATABASE_URL` | Database connection string | `sqlite:///subscriptions.db` |
| `MAIL_SERVER` | SMTP server address | (unset) |
| `MAIL_PORT` | SMTP server port | 587 |
| `MAIL_USE_TLS` | Enable TLS for email (`true`/`false`) | true |
| `MAIL_USERNAME` | SMTP username | (unset) |
| `MAIL_PASSWORD` | SMTP password / app password | (unset) |
| `MAIL_FROM` | From email address | (unset) |
| `DAYS_BEFORE_EXPIRY` | Default days before expiry to send notification | 7 |
| `ITEMS_PER_PAGE` | Pagination size for lists | 20 |
| `CURRENCY_REFRESH_MINUTES` | Freshness window for cached exchange rates (per provider) | 1440 (24h) |
| `CURRENCY_PROVIDER_PRIORITY` | Comma list controlling provider fallback order | frankfurter,floatrates,erapi_open |
| `PUID` | Host user ID to run the app process as (for mounted volume ownership) | 1000 |
| `PGID` | Host group ID to run the app process as | 1000 |

### Exchange Rate Providers

Currently bundled free, no‑key providers (all EUR base):

1. `frankfurter` – https://api.frankfurter.app (ECB sourced, daily; sometimes mid-day updates)
2. `floatrates` – https://www.floatrates.com/daily/eur.json (frequent refresh, community mirror)
3. `erapi_open` – https://open.er-api.com/v6/latest/EUR (daily with status metadata)

You can set a personal preference in General Settings. The system builds a dynamic priority list putting your choice first, followed by the remaining providers, then falls back to: any cached provider for today → most recent historical cached record → static hardcoded approximations (last resort). A mismatch warning appears if your preferred provider is temporarily unavailable.

Manual Refresh: In General Settings click the “Refresh Rates” button (POST `/refresh_rates`) to clear today’s cache and force a live refetch. A debug JSON endpoint is also available at `/debug/refresh_rates` (authenticated) to inspect raw values and sample conversions.

Precision: All conversions use Python `Decimal` with high precision to avoid cumulative rounding issues when summing many subscriptions.

Attempt Chain Diagnostics: The settings page shows a badge chain like `frankfurter:cache → floatrates:fetched` indicating which providers were consulted and how (cache / fetched / failed / fallback-cached / static). This aids troubleshooting provider outages.

Environment Override: You can predefine `CURRENCY_PROVIDER_PRIORITY` (e.g. `floatrates,frankfurter,erapi_open`) in the container environment; user preference still reshuffles at runtime per session.

### Running as a Specific Host User (PUID/PGID)

To avoid permission issues on the mounted `./data` directory, the image now supports providing a host UID/GID.

Example docker-compose override:
```yaml
services:
   web:
      environment:
         - PUID=1001
         - PGID=1001
```

Or with plain docker run:
```bash
docker run -d \
   -e PUID=$(id -u) -e PGID=$(id -g) \
   -v $(pwd)/data:/app/instance \
   -p 5000:5000 \
   ghcr.io/gittimeraider/subscription-tracker:latest
```

On container start an unprivileged user matching those IDs is created/updated and the process is dropped to it using `gosu`.

### Email Configuration Examples

#### Gmail Setup
```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-specific-password
MAIL_FROM=your-email@gmail.com
```

#### Outlook/Hotmail Setup
```env
MAIL_SERVER=smtp-mail.outlook.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@outlook.com
MAIL_PASSWORD=your-password
MAIL_FROM=your-email@outlook.com
```

## 📱 Usage Guide

### Adding a Subscription

1. **Login** to your dashboard
2. Click **"Add Subscription"**
3. Fill in the details:
   - **Name**: Netflix, Spotify, Adobe Creative Suite, etc.
   - **Company**: The service provider
   - **Category**: Choose from predefined categories
   - **Cost**: Amount per billing cycle
   - **Billing Cycle**: Select from available options or use custom
   - **Start Date**: When the subscription began
   - **End Date**: When it expires (leave blank for infinite)
   - **Notes**: Any additional information

### Managing Subscriptions

- **👀 View**: All subscriptions displayed on dashboard with filtering options
- **✏️ Edit**: Click "Edit" to modify subscription details
- **🔄 Toggle**: Activate/deactivate subscriptions without deleting
- **🗑️ Delete**: Remove subscriptions with confirmation
- **🔍 Filter**: By category, status, or expiration timeline

### Setting Up Notifications

1. Go to **Settings → Notification Settings**
2. Configure your preferences:
   - Enable/disable email notifications
   - Set days before expiry for alerts
   - Choose your preferred currency
   - Set your timezone

### Viewing Analytics

Visit the **Analytics** page to see:
- Total monthly and yearly costs (converted into your chosen display currency)
- Spending breakdown by category
- Billing cycle distribution
- Upcoming renewals
- Cost projections

Behind the scenes, each subscription’s native currency is normalized via EUR base rates, then aggregated. Conversion happens once per request using a cached rates dict for efficiency.

### Currency & Provider Tips

- Set your preferred display currency and provider in General Settings.
- If totals look stale, click Refresh Rates; check attempt chain for failures.
- To test fallback, temporarily set an invalid provider order in `CURRENCY_PROVIDER_PRIORITY` and observe the chain (not recommended in production).

## 🔒 Security Considerations

- **🚨 Change the default admin password immediately** after first login
- Use strong, unique passwords for all accounts
- Set a secure `SECRET_KEY` in production
- Use app-specific passwords for email accounts (especially Gmail)
- Keep your environment variables secure and never commit them to version control

## 🐛 Troubleshooting

### Email Notifications Not Working
1. Verify SMTP settings in environment variables
2. Check that email credentials are correct
3. For Gmail, ensure 2FA is enabled and use app-specific password
4. Check application logs for error messages

### Database Issues
1. Stop the application
2. Delete `subscriptions.db` (⚠️ this will delete all data)
3. Restart the application to recreate the database

### Exchange Rates Not Updating / Provider Unavailable
1. Open General Settings and use the Refresh Rates button.
2. Check the attempt chain badges – look for `failed:` entries.
3. Ensure outbound HTTPS is allowed from the container/host.
4. Reduce `CURRENCY_REFRESH_MINUTES` temporarily to force more frequent refetch during testing.
5. If all live sources fail, the app will log an error and fall back to cached or static rates (may be outdated).


### Performance Issues
1. Monitor system resources if running many subscriptions
2. Check email server response times

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.










