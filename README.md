
UNDER DEVELOPMENT! NOT READY FOR USAGE

<p align="center">
  <img src="img/icon_sub.png" />
</p>


# Subscription Tracker

Welcome to the most wonderfully mad way to track your subscriptions! This application helps you manage all your recurring payments, from streaming services to software licenses, ensuring you never fall down the rabbit hole of forgotten subscriptions.

## Features

- **Secure Login System** - Keep your subscription data safe

- **Comprehensive Subscription Management** - Add, edit, and remove subscriptions with ease

- **Flexible Billing Cycles** - Monthly, yearly, or custom periods (every 5 years? Why not!)

- **Email Notifications** - Get notified before subscriptions expire

- **Cost Tracking** - See your total monthly expenses at a glance

- **Docker Support** - Deploy anywhere with container magic

- **GitHub Container Registry** - Pull pre-built images from ghcr.io

## Quick Start

### Using Docker (Recommended)

1. **Pull the image from GitHub Container Registry:**

```bash

   docker pull ghcr.io/YOUR_USERNAME/subscription-tracker:main
```

2. **Run with docker-compose:**

```bash

   # Create a docker-compose.yml file with your environment variables

   docker-compose up -d

```

3. **Access the application:**

   - Navigate to ```http://localhost:5000```

   - Default credentials: ```admin``` / ```changeme```

### Local Development

1. **Clone the repository:**

```bash

   git clone https://github.com/YOUR_USERNAME/subscription-tracker.git

   cd subscription-tracker

```

2. **Set up virtual environment:**

```bash

   python -m venv venv

   source venv/bin/activate  # On Windows: venv\Scripts\activate

```

3. **Install dependencies:**

```bash

   pip install -r requirements.txt

```

4. **Run the application:**

```bash

   python run.py

```

## Configuration

### Environment Variables

Create a ```.env``` file based on ```.env.example```:

| Variable | Description | Default |
|----------|-------------|---------|
| ```SECRET_KEY``` | Flask secret key for sessions | Random string |
| ```DATABASE_URL``` | Database connection string | SQLite (local file) |
| ```MAIL_SERVER``` | SMTP server address | None |
| ```MAIL_PORT``` | SMTP server port | 587 |
| ```MAIL_USE_TLS``` | Enable TLS for email | true |
| ```MAIL_USERNAME``` | SMTP username | None |
| ```MAIL_PASSWORD``` | SMTP password | None |
| ```MAIL_FROM``` | From email address | None |
| ```DAYS_BEFORE_EXPIRY``` | Days before expiry to send notification | 7 |

### Email Configuration Example (Gmail)

```env

MAIL_SERVER=smtp.gmail.com

MAIL_PORT=587

MAIL_USE_TLS=true

MAIL_USERNAME=your-email@gmail.com

MAIL_PASSWORD=your-app-specific-password

MAIL_FROM=your-email@gmail.com

```

## Usage

### Adding a Subscription

1. Log in to the dashboard

2. Click "Add Subscription"

3. Fill in the details:

   - **Name**: Netflix, Spotify, etc.

   - **Company**: The service provider

   - **Cost**: Amount per billing cycle

   - **Billing Cycle**: Monthly, Yearly, or Custom

   - **Start Date**: When the subscription began

   - **End Date**: When it expires (optional)

### Managing Subscriptions

- **View**: All subscriptions are displayed on the dashboard with monthly cost calculations

- **Edit**: Click "Edit" next to any subscription to modify its details

- **Delete**: Click "Delete" to remove a subscription (with confirmation)

### Email Notifications

The application automatically checks daily for subscriptions expiring within the configured timeframe and sends email notifications.

## Docker Deployment

### Building the Image

```bash

docker build -t subscription-tracker .

```

### Running with Docker Compose

1\. **Create a ```docker-compose.yml``` file:**

```yaml

   version: '3.8'

   services:

     web:

       image: ghcr.io/YOUR_USERNAME/subscription-tracker:main

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

2. **Start the application:**

```bash

   docker-compose up -d

```

### Using GitHub Container Registry

The repository includes GitHub Actions that automatically build and publish Docker images to ghcr.io on every push to the main branch.

To use these images:

1. **Authenticate with GitHub Container Registry:**

```bash

   echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin

```

2. **Pull the latest image:**

```bash

   docker pull ghcr.io/YOUR_USERNAME/subscription-tracker:main

```

## Security Considerations

- **Change the default admin password immediately** after first login

- Use strong, unique passwords

- Set a secure ```SECRET_KEY``` in production

- Use HTTPS in production environments

- Keep your SMTP credentials secure

## Contributing

*Adjusts monocle* Contributions are most welcome at this tea party!

1. Fork the repository

2. Create your feature branch (```git checkout -b feature/AmazingFeature```)

3. Commit your changes (```git commit -m 'Add some AmazingFeature'```)

4. Push to the branch (```git push origin feature/AmazingFeature```)

5. Open a Pull Request

## License

This project is open source and available under the MIT License.





