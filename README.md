# Discord Auth 🛡️
FastAPI backend for Discord OAuth2 authentication using SQLAlchemy and JWT

# Features
- Users can securely log in using their Discord account.
- JWT Based authentication.
- Stores and manages user data using SQLAlchemy.
- SHA256 encrypted refresh tokens allowing users to stay signed in for 7 days.
- Easy configuration.

# Configuration
- Install the required libraries.
```
pip install -r requirements.txt
```
- Create an application in the [Discord Developer Portal](https://discord.com/developers/applications).
- Set the following in your **.env** file.
```
Example:

DISCORD_CLIENT_ID="1234567890123456789"
DISCORD_CLIENT_SECRET="Abc123"
JWT_SECRET_KEY="Secret_123"
```
- View your client ID and secret in the OAuth2 section, set a JWT secret key of your choice.
- Add a redirect URI in the Discord Developer Portal in this format: **http://127.0.0.1/auth**.
- Set the URI, CORS, redirects in `main.py`. Find them easily by searching `# Set`.
- Create a database and set the URL in `database.py`.
