# 🔔 Subscription Tracker (Dockerized)
<p align="center">
  <img src="https://github.com/GitTimeraider/Assets/blob/main/Subscription-Tracker-docker/img/icon_sub.png" />
</p>

Welcome to the most wonderfully comprehensive and dockerized way to track your subscriptions and recurring costs! This application helps you manage all your recurring payments, from streaming services to software licenses, ensuring you never fall down the rabbit hole of forgotten subscriptions.

<p align="center" width="100%">
    <img width="80%" src="https://github.com/GitTimeraider/Assets/blob/main/Subscription-Tracker-docker/img/dashboard2.jpg">
</p>


## ✨ Features

### 🔐 **Multi-User System with Admin Controls**
- Secure multi-user environment with role-based access control
- **Admin Users**: Can manage all users, create new accounts, and access admin settings
- **Standard Users**: Can only manage their own subscriptions and settings
- No public registration - only admins can create new user accounts
- Individual user accounts with personalized settings and isolated data

### 📊 **Comprehensive Subscription Management**
- Add, edit, and remove subscriptions with ease
- Support for multiple categories: Software, Hardware, Entertainment, Utilities, Cloud Services, News & Media, Education, Fitness, Gaming, and more
- Detailed subscription information including notes

<p align="center" width="100%">
    <img width="80%" src="https://github.com/GitTimeraider/Assets/blob/main/Subscription-Tracker-docker/img/create.jpg">
</p>


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
- **Notification Settings**: Configure email preferences, timing, and timezone
- **General Settings**: Preferred currency, theme, accent color, date format, and exchange rate provider
- **Date Format Options**: Choose between European (DD/MM/YYYY) or US (MM/DD/YYYY) formatting
- **Admin Settings**: User management, create/edit/delete users (admin only)
- **Smart Sorting**: Dashboard defaults to nearest expiry first, with infinite subscriptions always last
- **Filters**: Filter subscriptions by category, status, and expiration
- **Exchange Rate Provider Selection**: Choose between multiple free, no‑API‑key data sources

<p align="center" width="100%">
    <img width="80%" src="https://github.com/GitTimeraider/Assets/blob/main/Subscription-Tracker-docker/img/settings.jpg">
</p>


### 🎨 **Beautiful Interface**
- Modern, responsive design using Bootstrap 5
- Intuitive navigation and user experience
- Mobile-friendly layout with configurable date formatting (DD/MM/YYYY or MM/DD/YYYY)
- Interactive dashboard with real-time updates and sorting capabilities (defaults to nearest expiry first)
- Status indicators for active/inactive subscriptions

<p align="center" width="100%">
    <img width="80%" src="https://github.com/GitTimeraider/Assets/blob/main/Subscription-Tracker-docker/img/analytics.jpg">
</p>


### 🐳 **Docker Support**
- Easy deployment with Docker
- Pre-built images available on GitHub Container Registry
- Environment variable configuration

## 🐳 Docker Deployment

### Database Options

The application supports three database backends:
- **SQLite** (default) - File-based, no additional setup required
- **PostgreSQL** - Robust relational database, recommended for production
- **MariaDB/MySQL** - Popular relational database alternative


### Using Docker Compose (Manual Configuration)
```yaml
version: '3.8'
services:
  web:
    image: ghcr.io/gittimeraider/subscription-tracker:latest
    ports:
      - "5000:5000"
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=${DATABASE_URL:-sqlite:///subscriptions.db}
      - MAIL_SERVER=${MAIL_SERVER}
      - MAIL_PORT=${MAIL_PORT}
      - MAIL_USE_TLS=${MAIL_USE_TLS}
      - MAIL_USERNAME=${MAIL_USERNAME}
      - MAIL_PASSWORD=${MAIL_PASSWORD}
      - MAIL_FROM=${MAIL_FROM}
      - PUID=${PUID:-1000}
      - PGID=${PGID:-1000}
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
   # SQLite (default)
   docker-compose up -d
   
   # PostgreSQL
   docker-compose --profile postgres up -d
   
   # MariaDB
   docker-compose --profile mariadb up -d
   ```

4. **Access the application:**
   - Navigate to `http://localhost:5000`
   - Default admin credentials: `admin` / `changeme`
   - **⚠️ Change the default password immediately!**
   - Only admins can create new user accounts

### Building from Source

If you're building the Docker image from source, the multi-stage build process will automatically handle database driver compilation:

```bash
# Build the image
docker build -t subscription-tracker .

# Run with your preferred database
docker-compose up -d
```

The build process includes support for both PostgreSQL and MariaDB/MySQL drivers.

## ⚙️ Configuration

### Environment Variables

All of these are optional, though it is advised to use the SECRET_KEY and the MAIL_ environmentals to the very least.

#### Core Application Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key for sessions | Random string |
| `DATABASE_URL` | Database connection string | `sqlite:///subscriptions.db` |
| `DAYS_BEFORE_EXPIRY` | Default days before expiry to send notification | 7 |
| `ITEMS_PER_PAGE` | Pagination size for lists | 20 |
| `PUID` | Host user ID to run the app process as (for mounted volume ownership) | 1000 |
| `PGID` | Host group ID to run the app process as | 1000 |

#### Database URL Examples
```bash
# SQLite (default)
DATABASE_URL=sqlite:///subscriptions.db

# PostgreSQL
DATABASE_URL=postgresql://username:password@postgres:5432/database_name

# MariaDB/MySQL
DATABASE_URL=mysql+pymysql://username:password@mariadb:3306/database_name
```

#### Email Configuration Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `MAIL_SERVER` | SMTP server address | (unset) |
| `MAIL_PORT` | SMTP server port | 587 |
| `MAIL_USE_TLS` | Enable TLS for email (`true`/`false`) | true |
| `MAIL_USERNAME` | SMTP username | (unset) |
| `MAIL_PASSWORD` | SMTP password / app password | (unset) |
| `MAIL_FROM` | From email address | (unset) |

#### Currency Exchange Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `CURRENCY_REFRESH_MINUTES` | Freshness window for cached exchange rates (per provider) | 1440 (24h) |
| `CURRENCY_PROVIDER_PRIORITY` | Comma list controlling provider fallback order | frankfurter,floatrates,erapi_open |


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

### First Time Setup

1. **Access the application** at `http://localhost:5000`
2. **Login** with default admin credentials: `admin` / `changeme`
3. **⚠️ Immediately change the default password** in User Settings
4. **Create user accounts** (admin only):
   - Go to Settings → Admin Settings → Users
   - Click "Add User" to create new accounts
   - Set user roles (Admin or Standard User)

### User Management (Admin Only)

**Admins can:**
- View all users in the system
- Create new user accounts (both admin and standard users)
- Edit user details (username, email, password, role)
- Delete users (with safety restrictions)
- View user statistics

**Safety Restrictions:**
- Admins cannot delete themselves while logged in
- Cannot delete the last admin user
- Cannot remove admin role from the last admin user
- Deleting a user removes all their subscriptions and settings

### Adding a Subscription

1. **Login** to your account
2. Navigate to your **Dashboard**
3. Click **"Add Subscription"**
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

- **👀 View**: All subscriptions displayed on dashboard with filtering and sorting options
- **✏️ Edit**: Click "Edit" to modify subscription details
- **🔄 Toggle**: Activate/deactivate subscriptions without deleting
- **🗑️ Delete**: Remove subscriptions with confirmation
- **🔍 Filter**: By category, status, or expiration timeline
- **📊 Sort**: Click column headers or use dropdown to sort by:
  - **Name** (A-Z or Z-A)
  - **Company** (A-Z or Z-A) 
  - **Category** (A-Z or Z-A)
  - **Original Cost** (Low to High or High to Low)
  - **Monthly Cost** (Low to High or High to Low)
  - **Start Date** (Oldest to Newest or Newest to Oldest)
  - **End Date** (Earliest to Latest or Latest to Earliest)

### Setting Up Notifications

1. Go to **Settings → Notification Settings**
2. Configure your preferences:
   - Enable/disable email notifications
   - Set days before expiry for alerts
   - Set your timezone
3. **Test your email configuration**:
   - Use the "Send Test Email" button to verify your email settings
   - Ensure your email address is set in User Settings first
   - Check both inbox and spam folder for the test email

### Personal Settings

1. **User Settings**: Update your username, email, and password
2. **General Settings**: 
   - Set your preferred display currency
   - Choose theme mode (light/dark)
   - Select accent color
   - Configure exchange rate provider preference

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

## 👥 Multi-User System

### User Roles

**Admin Users:**
- Can access all application features
- Manage user accounts (create, edit, delete)
- Access admin settings and user management dashboard
- View system-wide statistics

**Standard Users:**
- Can manage their own subscriptions and settings
- Access to dashboard, analytics, and personal settings
- Cannot access admin functions or other users' data

### Data Isolation

- Each user has their own isolated subscriptions and settings
- Users cannot view or modify other users' data
- Analytics and reports are calculated per-user
- Email notifications are sent per-user based on their preferences

### Default Admin Account

On first startup, if no admin users exist, the system creates:
- **Username:** `admin`
- **Password:** `changeme`
- **⚠️ Change this password immediately after first login!**

### User Management

Admins can manage users through **Settings → Admin Settings → Users**:
- View all users with their statistics
- Create new users (admin or standard)
- Edit user details and roles
- Delete users (with safety restrictions)

## 🔒 Security Considerations

- **🚨 Change the default admin password immediately** after first login (`admin` / `changeme`)
- **👥 User Access Control**: Only admins can create new user accounts
- **🔐 Data Isolation**: Users can only access their own subscriptions and settings
- **🛡️ Admin Protections**: 
  - Admins cannot delete themselves while logged in
  - System prevents deletion of the last admin user
  - Cannot remove admin privileges from the last admin
- Use strong, unique passwords for all accounts
- Set a secure `SECRET_KEY` in production
- Use app-specific passwords for email accounts (especially Gmail)
- Keep your environment variables secure and never commit them to version control
- Regularly review user accounts and remove unused ones

## 🐛 Troubleshooting

### Email Notifications Not Working
1. **Use the Test Email feature**: Go to Settings → Notification Settings and click "Send Test Email"
2. Verify SMTP settings in environment variables
3. Check that email credentials are correct
4. For Gmail, ensure 2FA is enabled and use app-specific password
5. Ensure your email address is set in User Settings
6. Check both inbox and spam folder for test emails
7. Check application logs for error messages

### Database Issues

#### SQLite Issues
1. Stop the application
2. Delete `subscriptions.db` (⚠️ this will delete all data)
3. Restart the application to recreate the database

#### PostgreSQL Connection Issues
1. **Check if PostgreSQL service is running:**
   ```bash
   docker-compose logs postgres
   ```
2. **Verify connection parameters** in your `.env` file
3. **Check DATABASE_URL format:**
   ```bash
   DATABASE_URL=postgresql://username:password@postgres:5432/database_name
   ```
4. **Restart PostgreSQL service:**
   ```bash
   docker-compose restart postgres
   ```

#### MariaDB/MySQL Connection Issues
1. **Check if MariaDB service is running:**
   ```bash
   docker-compose logs mariadb
   ```
2. **Verify connection parameters** in your `.env` file
3. **Check DATABASE_URL format:**
   ```bash
   DATABASE_URL=mysql+pymysql://username:password@mariadb:3306/database_name
   ```
4. **Restart MariaDB service:**
   ```bash
   docker-compose restart mariadb
   ```

#### Database Migration Issues
- When switching database types, you'll start with a fresh database
- The application will automatically create tables on first startup
- Check application logs for database connection errors:
  ```bash
  docker-compose logs web
  ```

#### Common Database Connection Errors
- **"Connection refused"**: Database service isn't running or wrong host/port
- **"Authentication failed"**: Wrong username/password combination
- **"Database does not exist"**: Database name doesn't match or wasn't created
- **"SSL required"**: Some cloud databases require SSL connections in the DATABASE_URL

### Exchange Rates Not Updating / Provider Unavailable
1. Open General Settings and use the Refresh Rates button.
2. Check the attempt chain badges – look for `failed:` entries.
3. Ensure outbound HTTPS is allowed from the container/host.
4. Reduce `CURRENCY_REFRESH_MINUTES` temporarily to force more frequent refetch during testing.
5. If all live sources fail, the app will log an error and fall back to cached or static rates (may be outdated).


### Performance Issues
1. Monitor system resources if running many subscriptions
2. Check email server response times

### Multi-User Issues
1. **Cannot access admin settings**: Ensure you're logged in as an admin user
2. **Cannot create users**: Only admin users can create new accounts
3. **Missing subscriptions**: Check you're logged in as the correct user - data is isolated per user
4. **Default admin account issues**: 
   - If default admin doesn't exist, restart the container to recreate it
   - Check logs for user creation messages during startup

### Locked Out of Admin Account
1. Stop the container
2. Delete the database file: `rm ./data/subscriptions.db`
3. Restart the container (this will recreate the default admin account)
4. **⚠️ Warning: This deletes ALL data including all users and subscriptions**

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.



















