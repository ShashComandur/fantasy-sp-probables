# Deploying to Streamlit Cloud

## Prerequisites

1. **GitHub Account** - Your code needs to be in a GitHub repository
2. **Yahoo API Credentials** - Your consumer key, secret, and access tokens
3. **Streamlit Cloud Account** - Free at [share.streamlit.io](https://share.streamlit.io)

## Step 1: Push to GitHub

1. Initialize git repository (if not already done):
```bash
cd /home/shashank/baseball/fantasy/yahoo-pitcher-tracker
git init
git add .
git commit -m "Initial commit - Yahoo Fantasy Pitcher Tracker"
```

2. Create a new repository on GitHub (don't initialize with README)

3. Push your code:
```bash
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main
```

## Step 2: Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click "New app"
4. Select:
   - **Repository:** YOUR_USERNAME/YOUR_REPO_NAME
   - **Branch:** main
   - **Main file path:** app.py
5. Click "Advanced settings"

## Step 3: Add Secrets

In the "Secrets" section, paste your credentials in TOML format:

```toml
YAHOO_CONSUMER_KEY = "dj0yJmk9VXA5NDJna1o5Q1drJmQ9WVdrOU9VVmxWVTlGVjNZbWNHbzlNQT09JnM9Y29uc3VtZXJzZWNyZXQmc3Y9MCZ4PTEz"
YAHOO_CONSUMER_SECRET = "934867387a682cd3638dac339b55e76f7eece99e"
YAHOO_ACCESS_TOKEN_JSON = "YOUR_ACCESS_TOKEN_HERE"
GAME_CODE = "mlb"
```

**Important:** Get these values from your parent `.env` file:
- Copy the exact values for YAHOO_CONSUMER_KEY, YAHOO_CONSUMER_SECRET, and YAHOO_ACCESS_TOKEN_JSON
- Make sure to use the JSON format for YAHOO_ACCESS_TOKEN_JSON if required by yfpy

## Step 4: Deploy

1. Click "Deploy!"
2. Wait for the app to build (usually 2-3 minutes)
3. Your app will be live at: `https://YOUR_APP_NAME.streamlit.app`

## Updating Your App

After initial deployment, any push to your main branch will automatically redeploy:

```bash
git add .
git commit -m "Your update message"
git push
```

## Troubleshooting

### App fails to start
- Check the logs in Streamlit Cloud
- Verify all secrets are correctly set
- Ensure requirements.txt includes all dependencies

### Yahoo API errors
- Verify your access token is still valid
- Check that all credentials are copied exactly (no extra spaces)
- Token may need to be refreshed periodically

### Module import errors
- Make sure `yfpy` and all other packages are in requirements.txt
- Check that package versions are compatible

## Local Testing

Before deploying, test that secrets work locally:

1. Create `.streamlit/secrets.toml` (gitignored):
```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

2. Fill in your credentials in `.streamlit/secrets.toml`

3. Run locally:
```bash
streamlit run app.py
```

## Notes

- The app uses Streamlit's cache to minimize API calls
- Yahoo tokens may need periodic refresh
- FanGraphs data is scraped in real-time (cached for 60 seconds)
- Free tier has usage limits - monitor your app's performance
