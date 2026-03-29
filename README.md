# Yahoo Fantasy Pitcher Starts Tracker

Automatically track probable starting pitchers for your Yahoo Fantasy Baseball matchup.

🚀 **[Deploy to Streamlit Cloud](DEPLOYMENT.md)** - See full deployment instructions

## Features

- ✅ **Auto-detects current fantasy week** - No manual week selection needed (auto-advances on Sundays)
- ✅ **Team names in dropdown** - Select your team by name, not just ID
- ✅ **Identifies your matchup opponent** - Automatically finds who you're playing against
- ✅ **Real-time probable starters** - Fetches latest data from FanGraphs
- ✅ **Accent-insensitive matching** - Handles names like "Reynaldo López" correctly
- ✅ **Copyable tables** - Select and copy data to Excel/Sheets
- ✅ **Pitcher details** - Shows handedness, opponents, and game dates
- ✅ **Matchup comparison** - Compare start volume between you and your opponent
- ✅ **Debug mode** - Troubleshoot pitcher matching issues

## Setup

1. **Create virtual environment** (if not already done):
```bash
cd yahoo-pitcher-tracker
python3 -m venv .venv
source .venv/bin/activate
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Environment variables** (already configured in parent .env):
   - YAHOO_CONSUMER_KEY
   - YAHOO_CONSUMER_SECRET
   - YAHOO_ACCESS_TOKEN_JSON
   - GAME_CODE

## Usage

Run the Streamlit app:
```bash
streamlit run app.py
```

Then:
1. Select your team ID (1-14) from the sidebar
2. Click "Load Pitcher Data"
3. Explore the three tabs:
   - **My Pitchers' Starts**: Your scheduled starters
   - **Opposition Schedule**: Your opponent's starters
   - **Team Comparison**: Side-by-side matchup view

## How It Works

1. Connects to Yahoo Fantasy Sports API to fetch:
   - Your team roster for the current week
   - Your opponent's team ID and roster
   - Current fantasy week number

2. Scrapes FanGraphs probable starters grid

3. Matches your pitchers (and opponent's) to probable starts

4. Displays results in an interactive dashboard

## Data Sources

- **Yahoo Fantasy Sports API** - Team rosters, matchups, league info
- **FanGraphs** - Probable starting pitchers schedule
