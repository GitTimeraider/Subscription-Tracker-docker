UNDER DEVELOPMENT! NOT READY FOR USAGE

<p align="center">
  <img src="https://github.com/GitTimeraider/Assets/blob/main/img/Subscription-Tracker/icon_sub.png" />
</p>

# 🔔 Subscription Tracker

Welcome to the most wonderfully comprehensive way to track your subscriptions! This application helps you manage all your recurring payments, from streaming services to software licenses, ensuring you never fall down the rabbit hole of forgotten subscriptions.

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

### ⚙️ **Powerful Settings**
- **User Settings**: Change username, email, and password
- **Notification Settings**: Configure email preferences, timing, currency, and timezone
- **Email Settings**: Admin-configurable SMTP settings
- **Filters**: Filter subscriptions by category, status, and expiration

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

## 🚀 Quick Start

### Using Docker (Recommended)

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

### Local Development

1. **Clone the repository:**
   ```bash
   git clone https://github.com/gittimeraider/subscription-tracker.git
   cd subscription-tracker
   ```

2. **Set up virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Run the application:**
   ```bash
   python run.py
   ```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key for sessions | Random string |
| `DATABASE_URL` | Database connection string | SQLite (local file) |
| `MAIL_SERVER` | SMTP server address | None |
| `MAIL_PORT` | SMTP server port | 587 |
| `MAIL_USE_TLS` | Enable TLS for email | true |
| `MAIL_USERNAME` | SMTP username | None |
| `MAIL_PASSWORD` | SMTP password | None |
| `MAIL_FROM` | From email address | None |
| `DAYS_BEFORE_EXPIRY` | Default days before expiry to send notification | 7 |

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
- Total monthly and yearly costs
- Spending breakdown by category
- Billing cycle distribution
- Upcoming renewals
- Cost projections

## 🐳 Docker Deployment

### Building the Image
```bash
docker build -t subscription-tracker .
```

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

## 🔒 Security Considerations

- **🚨 Change the default admin password immediately** after first login
- Use strong, unique passwords for all accounts
- Set a secure `SECRET_KEY` in production
- Use app-specific passwords for email accounts (especially Gmail)
- Keep your environment variables secure and never commit them to version control

## 🛠️ Development

### Project Structure
```
subscription-tracker/
├── app/
│   ├── __init__.py          # App factory
│   ├── models.py            # Database models
│   ├── routes.py            # Application routes
│   ├── forms.py             # WTForms
│   ├── email.py             # Email notifications
│   └── templates/           # Jinja2 templates
├── config.py                # Configuration
├── requirements.txt         # Python dependencies
├── run.py                  # Application entry point
├── Dockerfile              # Docker configuration
└── docker-compose.yml      # Docker Compose setup
```

### Adding New Features

1. **Models**: Add new database models in `models.py`
2. **Forms**: Create forms in `forms.py`
3. **Routes**: Add new routes in `routes.py`
4. **Templates**: Create HTML templates in `templates/`
5. **Database**: Run migrations by restarting the app (auto-migration enabled)

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

### Performance Issues
1. Consider using PostgreSQL for production instead of SQLite
2. Monitor system resources if running many subscriptions
3. Check email server response times

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For support, questions, or feature requests, please open an issue on GitHub.

---

**Happy subscription tracking!** 🎉

