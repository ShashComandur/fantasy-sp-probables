import pandas as pd
import re
import requests
import streamlit as st
import unicodedata
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, Optional

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from yfpy import Data
from yfpy.query import YahooFantasySportsQuery


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# ENVIRONMENT SETUP # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

# Load environment variables (local development)
load_dotenv()


# Helper function to get secrets from Streamlit Cloud or local .env
def get_secret(key: str, default: str = "") -> str:
    """Get secret from Streamlit secrets or environment variable."""
    try:
        # Try Streamlit secrets first (for cloud deployment)
        return st.secrets.get(key, os.getenv(key, default))
    except (FileNotFoundError, AttributeError):
        # Fall back to environment variables (for local development)
        return os.getenv(key, default)


project_dir = Path(__file__).parent
data_dir = Path(__file__).parent / "output"
os.makedirs(data_dir, exist_ok=True)
data = Data(data_dir)

# Initialize Yahoo Fantasy Sports Query
# Auto-detecting current season for league 61442
query = YahooFantasySportsQuery(
    61442,  # league_id
    get_secret("GAME_CODE", "mlb"),
    yahoo_consumer_key=get_secret("YAHOO_CONSUMER_KEY"),
    yahoo_consumer_secret=get_secret("YAHOO_CONSUMER_SECRET"),
    yahoo_access_token_json=get_secret("YAHOO_ACCESS_TOKEN_JSON"),
    env_file_location=project_dir,
    save_token_data_to_env_file=True,
)


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# HELPER FUNCTIONS  # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


def normalize_name(name: str) -> str:
    """
    Normalize a name by removing accents and converting to lowercase.
    This handles discrepancies between data sources (e.g., 'López' vs 'Lopez').

    Args:
        name (str): The name to normalize

    Returns:
        str: Normalized name
    """
    # Decompose unicode characters (e.g., 'ó' becomes 'o' + combining accent)
    nfd = unicodedata.normalize("NFD", name)
    # Filter out combining characters (accents)
    without_accents = "".join(
        char for char in nfd if unicodedata.category(char) != "Mn"
    )
    # Convert to lowercase
    return without_accents.lower()


def is_deployed() -> bool:
    """
    Detect if running on Streamlit Cloud (deployment) vs local development.

    Returns:
        bool: True if deployed, False if local
    """
    try:
        # Check if st.secrets is accessible (indicates Streamlit Cloud)
        _ = st.secrets
        return True
    except (FileNotFoundError, AttributeError):
        return False


# MLB Team Colors - Primary logo colors from encycolorpedia.com
MLB_TEAM_COLORS = {
    "ARI": "#a71930",  # Arizona Diamondbacks
    "ATL": "#ce1141",  # Atlanta Braves
    "BAL": "#df4601",  # Baltimore Orioles
    "BOS": "#c62033",  # Boston Red Sox
    "CHC": "#cc3433",  # Chicago Cubs
    "CHW": "#27251f",  # Chicago White Sox
    "CIN": "#c6011f",  # Cincinnati Reds
    "CLE": "#e31937",  # Cleveland Guardians
    "COL": "#33006f",  # Colorado Rockies
    "DET": "#0c2c56",  # Detroit Tigers
    "HOU": "#eb6e1f",  # Houston Astros
    "KC": "#004687",   # Kansas City Royals
    "LAA": "#ba0021",  # Los Angeles Angels
    "LAD": "#005a9c",  # Los Angeles Dodgers
    "MIA": "#00a3e0",  # Miami Marlins
    "MIL": "#12284b",  # Milwaukee Brewers
    "MIN": "#002b5c",  # Minnesota Twins
    "NYM": "#002d72",  # New York Mets
    "NYY": "#003087",  # New York Yankees
    "OAK": "#003831",  # Oakland Athletics
    "PHI": "#e81828",  # Philadelphia Phillies
    "PIT": "#fdb827",  # Pittsburgh Pirates
    "SD": "#2f241d",   # San Diego Padres
    "SF": "#fd5a1e",   # San Francisco Giants
    "SEA": "#0c2c56",  # Seattle Mariners
    "STL": "#c41e3a",  # St. Louis Cardinals
    "TB": "#092c5c",   # Tampa Bay Rays
    "TEX": "#003278",  # Texas Rangers
    "TOR": "#134a8e",  # Toronto Blue Jays
    "WSH": "#ab0003",  # Washington Nationals
}


def get_team_color(opponent_str: str) -> str:
    """
    Extract team abbreviation and return team color.

    Args:
        opponent_str (str): Opponent string like "@ ARI" or "v BOS"

    Returns:
        str: Hex color code for the team
    """
    # Extract team abbreviation (last 3 letters)
    team_abbr = opponent_str.strip().split()[-1]
    return MLB_TEAM_COLORS.get(team_abbr, "#808080")  # Default to gray


def style_opponent_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply team color styling to the Opponent column.

    Args:
        df (pd.DataFrame): DataFrame with Opponent column

    Returns:
        pd.DataFrame: Styled DataFrame
    """
    if df.empty or "Opponent" not in df.columns:
        return df

    def apply_color(row):
        color = get_team_color(row["Opponent"])
        return [f"background-color: {color}; color: white" if col == "Opponent" else "" 
                for col in row.index]

    return df.style.apply(apply_color, axis=1)


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# YAHOO API FUNCTIONS # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_current_week() -> int:
    """
    Get the current week number from the Yahoo Fantasy league.

    Returns:
        int: Current week number
    """
    try:
        league = query.get_league_metadata()
        return int(league.current_week)
    except Exception as e:
        st.error(f"Error fetching current week: {e}")
        return 1  # Default to week 1 if error


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_week_date_range(week_id: int) -> tuple:
    """
    Get the start and end dates for a given week.

    Args:
        week_id (int): Week number

    Returns:
        tuple: (start_date_str, end_date_str) formatted as "Mon M/D"
    """
    try:
        scoreboard = query.get_league_scoreboard_by_week(week_id)
        if scoreboard.matchups and len(scoreboard.matchups) > 0:
            matchup = scoreboard.matchups[0]
            # week_start and week_end are Unix timestamps
            week_start = datetime.fromtimestamp(int(matchup.week_start))
            week_end = datetime.fromtimestamp(int(matchup.week_end))
            
            start_str = week_start.strftime("%a %-m/%-d")
            end_str = week_end.strftime("%a %-m/%-d")
            return (start_str, end_str)
    except Exception:
        pass
    return ("", "")


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_all_teams() -> Dict[int, str]:
    """
    Get all teams in the league with their names.

    Returns:
        Dict[int, str]: Dictionary mapping team_id to team_name
    """
    try:
        standings = query.get_league_standings()
        teams = {}

        for team in standings.teams:
            team_id = int(team.team_id)
            name = team.name
            # Handle bytes vs string
            if isinstance(name, bytes):
                name = name.decode("utf-8")
            teams[team_id] = name

        return teams
    except Exception:
        # Return default team IDs if API fails
        return {i: f"Team {i}" for i in range(1, 15)}


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_team_name(team_id: int) -> str:
    """
    Get team name from Yahoo Fantasy API.

    Args:
        team_id (int): Team ID

    Returns:
        str: Team name
    """
    try:
        team = query.get_team_info(team_id)
        name = team.name
        # Handle bytes vs string
        if isinstance(name, bytes):
            name = name.decode("utf-8")
        return name
    except Exception:
        return f"Team {team_id}"


@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_team_roster(team_id: int, week_id: int) -> pd.DataFrame:
    """
    Fetch team roster from Yahoo Fantasy API.

    Args:
        team_id (int): Team ID (1-14)
        week_id (int): Week number

    Returns:
        pd.DataFrame: DataFrame with pitcher information
    """
    try:
        roster = query.get_team_roster_player_info_by_week(team_id, week_id)

        pitchers = []
        for player in roster:
            # Filter for pitchers (SP, RP, P positions)
            positions = getattr(player, "eligible_positions", [])
            display_pos = getattr(player, "display_position", "")

            # Check if player is a pitcher
            is_pitcher = any(
                pos in ["SP", "RP", "P"] for pos in positions
            ) or display_pos in ["SP", "RP", "P"]

            if is_pitcher:
                pitchers.append(
                    {
                        "pitcher_name": player.full_name.strip(),
                        "pitcher_name_normalized": normalize_name(
                            player.full_name.strip()
                        ),
                        "position": display_pos,
                        "team": getattr(player, "editorial_team_abbr", "N/A"),
                    }
                )

        return pd.DataFrame(pitchers)
    except Exception as e:
        st.error(f"Error fetching team roster: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_opponent_team_id(user_team_id: int, week_id: int) -> Optional[int]:
    """
    Get the opponent team ID for the current matchup.

    Args:
        user_team_id (int): User's team ID
        week_id (int): Week number

    Returns:
        Optional[int]: Opponent team ID or None if not found
    """
    try:
        scoreboard = query.get_league_scoreboard_by_week(week_id)

        # Find the matchup containing the user's team
        for matchup in scoreboard.matchups:
            # Access teams via the teams array (teams[0] and teams[1])
            team_keys = [matchup.teams[0].team_key, matchup.teams[1].team_key]

            # Extract team IDs from team keys (format: "458.l.84756.t.X")
            team_ids = []
            for key in team_keys:
                try:
                    team_id = int(key.split(".t.")[-1])
                    team_ids.append(team_id)
                except (ValueError, AttributeError, IndexError):
                    continue

            # Check if user's team is in this matchup
            if user_team_id in team_ids:
                # Return the other team ID
                return [tid for tid in team_ids if tid != user_team_id][0]

        return None
    except Exception as e:
        st.error(f"Error finding opponent: {e}")
        return None


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# FANGRAPHS SCRAPING FUNCTIONS  # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


@st.cache_data(ttl=60)  # Cache for 1 minute
def fetch_html(url: str) -> Optional[BeautifulSoup]:
    """
    Fetch HTML content from a given URL.

    Args:
        url (str): The URL to retrieve HTML from

    Returns:
        Optional[BeautifulSoup]: Parsed HTML content or None if an error occurs
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        return soup
    except requests.RequestException as e:
        st.error(f"Error fetching URL: {e}")
        return None


def parse_pitcher_entry(entry: str) -> Optional[dict]:
    """
    Parse a pitcher entry string.
    Handles names with accents/unicode characters (e.g., "Reynaldo López").

    Args:
        entry (str): Raw pitcher entry string

    Returns:
        Optional[dict]: Parsed information about the pitcher start
    """
    # Updated pattern to handle unicode characters in names
    # (.+?) uses non-greedy matching to capture any characters (including accents)
    pattern = r"^(@)?\s*([A-Z]{3})\s*(.+?)\s*\(([LR])\)$"
    match = re.match(pattern, entry)

    if match:
        return {
            "handedness": match.group(4),  # L or R
            "pitcher_name": match.group(3).strip(),
            "pitcher_name_normalized": normalize_name(match.group(3).strip()),
            "formatted_opponent": f"{'@' if match.group(1) == '@' else 'v'} {match.group(2)}",
        }

    return None


def extract_dates_from_headers(soup: BeautifulSoup) -> Dict[int, str]:
    """
    Extract dates from table headers.

    Args:
        soup (BeautifulSoup): Parsed HTML

    Returns:
        Dict[int, str]: Mapping of header index to date
    """
    header_row = (
        soup.find("div", class_="table-scroll").find("table").find("tbody").find("tr")
    )

    dates: Dict[int, str] = {}
    for idx, th in enumerate(header_row.find_all("th")[1:], start=1):
        date_match = re.search(r"(\w{3})\s*(\d+/\d+)", th.get_text(strip=True))
        if date_match:
            day_name, month_day = date_match.groups()
            try:
                month, day = map(int, month_day.split("/"))
                current_year = datetime.now().year

                # Handle year boundary
                if month < datetime.now().month:
                    year = current_year + 1
                else:
                    year = current_year

                date_obj = datetime(year, month, day)
                dates[idx] = date_obj.strftime("%Y-%m-%d")
            except ValueError:
                pass

    return dates


@st.cache_data(ttl=60)  # Cache for 1 minute
def fetch_all_pitcher_starts() -> pd.DataFrame:
    """
    Extract all pitcher starts from FanGraphs.

    Returns:
        pd.DataFrame: DataFrame with all pitcher starts
    """
    url = "https://www.fangraphs.com/roster-resource/probables-grid"
    soup = fetch_html(url)

    if not soup:
        return pd.DataFrame()

    table_div = soup.find("div", class_="table-scroll")
    if not table_div:
        st.warning("Could not find table with class 'table-scroll'")
        return pd.DataFrame()

    table = table_div.find("table")
    if not table:
        st.warning("No table found within the 'table-scroll' div")
        return pd.DataFrame()

    date_mapping = extract_dates_from_headers(soup)
    parsed_rows = []

    for tr in table.find_all("tr")[1:]:  # Skip header row
        row_data = [td.get_text(strip=True) for td in tr.find_all("td")]

        for col_idx, item in enumerate(row_data, start=1):
            parsed_entry = parse_pitcher_entry(item)

            if parsed_entry:
                full_row = {
                    "Date": date_mapping.get(col_idx - 1, "Unknown"),
                    "Handedness": parsed_entry["handedness"],
                    "Pitcher": parsed_entry["pitcher_name"],
                    "Pitcher_Normalized": parsed_entry["pitcher_name_normalized"],
                    "Opponent": parsed_entry["formatted_opponent"],
                }
                parsed_rows.append(full_row)

    # Sort by date
    parsed_rows.sort(key=lambda x: x["Date"])

    return pd.DataFrame(parsed_rows)


def match_pitchers_to_starts(
    roster_df: pd.DataFrame, all_starts_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Match roster pitchers to their starts from FanGraphs data.
    Uses accent-insensitive name matching (e.g., 'López' matches 'Lopez').

    Args:
        roster_df (pd.DataFrame): Roster with pitcher names
        all_starts_df (pd.DataFrame): All pitcher starts from FanGraphs

    Returns:
        pd.DataFrame: Matched pitcher starts
    """
    if roster_df.empty or all_starts_df.empty:
        return pd.DataFrame()

    # Get list of normalized pitcher names
    roster_names = set(roster_df["pitcher_name_normalized"].tolist())

    # Filter starts for pitchers in roster (using normalized names)
    matched = all_starts_df[
        all_starts_df["Pitcher_Normalized"].isin(roster_names)
    ].copy()

    # Remove the normalized column from output
    if not matched.empty:
        matched = matched[["Date", "Pitcher", "Opponent", "Handedness"]]

    return matched


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# STREAMLIT UI # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


def main():
    st.set_page_config(
        page_title="Yahoo Fantasy Pitcher Tracker", page_icon="⚾", layout="wide"
    )

    st.title("⚾ Yahoo Fantasy Pitcher Starts Tracker")
    st.markdown("Automatically track probable starts for your fantasy baseball matchup")

    # Sidebar controls
    st.sidebar.header("Settings")

    # Debug mode toggle (only show in local development)
    debug_mode = False
    if not is_deployed():
        debug_mode = st.sidebar.checkbox(
            "🔍 Debug Mode", value=False, help="Show raw scraped data for troubleshooting"
        )

    # Get all teams
    all_teams = get_all_teams()

    # Get current week
    current_week = get_current_week()

    # Auto-advance to next week on Sundays
    today = datetime.now()
    default_week = (
        current_week + 1 if today.weekday() == 6 else current_week
    )  # 6 = Sunday

    # Ensure default_week doesn't exceed max weeks
    default_week = min(default_week, 26)

    # Get week date range for display
    week_dates = get_week_date_range(default_week)
    week_label = "Select Week"
    if week_dates[0] and week_dates[1]:
        week_label = f"Select Week ({week_dates[0]} - {week_dates[1]})"

    # Week selection
    week_id = st.sidebar.selectbox(
        week_label,
        options=list(range(1, 27)),  # MLB typically has ~26 weeks
        index=default_week - 1,
        help="Choose the week to view (auto-advances on Sundays)",
    )

    st.sidebar.info(f"📅 Current Week: **{current_week}**")

    # Team selection with names
    team_options = [f"{team_id}. {name}" for team_id, name in sorted(all_teams.items())]

    # Default to team 8 (index 7 since list is 0-indexed)
    default_team_index = 7 if len(team_options) > 7 else 0

    selected_team = st.sidebar.selectbox(
        "Select Your Team",
        options=team_options,
        index=default_team_index,
        help="Choose your team",
    )

    # Extract team_id from selection (format: "1. Team Name")
    team_id = int(selected_team.split(".")[0])

    # Load data button
    if st.sidebar.button("🔄 Load Pitcher Data", type="primary"):
        with st.spinner("Fetching data from Yahoo Fantasy and FanGraphs..."):
            # Fetch all data
            user_roster = fetch_team_roster(team_id, week_id)
            opponent_id = get_opponent_team_id(team_id, week_id)
            all_starts = fetch_all_pitcher_starts()

            # Fetch team names
            user_team_name = get_team_name(team_id)

            # Store in session state
            st.session_state["user_roster"] = user_roster
            st.session_state["opponent_id"] = opponent_id
            st.session_state["all_starts"] = all_starts
            st.session_state["team_id"] = team_id
            st.session_state["week_id"] = week_id
            st.session_state["user_team_name"] = user_team_name
            st.session_state["data_loaded"] = True
            st.session_state["debug_mode"] = debug_mode

            if opponent_id:
                opponent_roster = fetch_team_roster(opponent_id, week_id)
                opponent_team_name = get_team_name(opponent_id)
                st.session_state["opponent_roster"] = opponent_roster
                st.session_state["opponent_team_name"] = opponent_team_name

    # Display data if loaded
    if st.session_state.get("data_loaded", False):
        user_roster = st.session_state["user_roster"]
        opponent_id = st.session_state["opponent_id"]
        all_starts = st.session_state["all_starts"]
        team_id = st.session_state["team_id"]
        week_id = st.session_state["week_id"]
        user_team_name = st.session_state.get("user_team_name", f"Team {team_id}")
        debug_mode = st.session_state.get("debug_mode", False)

        # Create tabs
        tab1, tab2, tab3 = st.tabs(
            ["📊 My Pitchers' Starts", "🎯 Opposition Schedule", "⚖️ Team Comparison"]
        )

        # Tab 1: My Pitchers' Starts
        with tab1:
            st.header(f"📊 {user_team_name} - Probable Starts (Week {week_id})")

            if debug_mode and not is_deployed() and not all_starts.empty:
                with st.expander("🔍 Debug: All Scraped Starts from FanGraphs"):
                    st.data_editor(
                        all_starts[["Date", "Pitcher", "Opponent", "Handedness"]],
                        disabled=True,
                        use_container_width=True,
                    )
                    st.caption(f"Total scraped starts: {len(all_starts)}")

            if not user_roster.empty:
                st.subheader("My Team's Pitchers")
                st.data_editor(
                    user_roster[["pitcher_name", "position", "team"]],
                    hide_index=True,
                    disabled=True,
                    use_container_width=True,
                )

                # Match pitchers to starts
                my_starts = match_pitchers_to_starts(user_roster, all_starts)

                if not my_starts.empty:
                    st.subheader(f"Scheduled Starts ({len(my_starts)} total)")
                    st.dataframe(
                        style_opponent_column(my_starts),
                        hide_index=True,
                        use_container_width=True,
                    )

                    # Summary stats
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Starts", len(my_starts))
                    with col2:
                        lefties = len(my_starts[my_starts["Handedness"] == "L"])
                        st.metric("Left-Handed", lefties)
                    with col3:
                        righties = len(my_starts[my_starts["Handedness"] == "R"])
                        st.metric("Right-Handed", righties)
                else:
                    st.info(
                        "No probable starts found for your pitchers in the upcoming schedule."
                    )
            else:
                st.warning("No pitchers found on your roster.")

        # Tab 2: Opposition Schedule
        with tab2:
            if opponent_id:
                opponent_team_name = st.session_state.get(
                    "opponent_team_name", f"Team {opponent_id}"
                )
                st.header(f"🎯 {opponent_team_name} - Probable Starts (Week {week_id})")

                opponent_roster = st.session_state.get(
                    "opponent_roster", pd.DataFrame()
                )

                if not opponent_roster.empty:
                    st.subheader(f"{opponent_team_name}'s Pitchers")
                    st.data_editor(
                        opponent_roster[["pitcher_name", "position", "team"]],
                        hide_index=True,
                        disabled=True,
                        use_container_width=True,
                    )

                    # Match opponent pitchers to starts
                    opp_starts = match_pitchers_to_starts(opponent_roster, all_starts)

                    if not opp_starts.empty:
                        st.subheader(f"Scheduled Starts ({len(opp_starts)} total)")
                        st.dataframe(
                            style_opponent_column(opp_starts),
                            hide_index=True,
                            use_container_width=True,
                        )

                        # Summary stats
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Starts", len(opp_starts))
                        with col2:
                            lefties = len(opp_starts[opp_starts["Handedness"] == "L"])
                            st.metric("Left-Handed", lefties)
                        with col3:
                            righties = len(opp_starts[opp_starts["Handedness"] == "R"])
                            st.metric("Right-Handed", righties)
                    else:
                        st.info("No probable starts found for opponent's pitchers.")
                else:
                    st.warning("Could not load opponent's roster.")
            else:
                st.header("🎯 Opposition Schedule")
                st.warning("Could not determine your opponent for this week.")

        # Tab 3: Team Comparison
        with tab3:
            if opponent_id and not user_roster.empty:
                opponent_team_name = st.session_state.get(
                    "opponent_team_name", f"Team {opponent_id}"
                )
                st.header(
                    f"⚖️ Week {week_id} Matchup: {user_team_name} vs {opponent_team_name}"
                )

                opponent_roster = st.session_state.get(
                    "opponent_roster", pd.DataFrame()
                )

                # Get starts for both teams
                my_starts = match_pitchers_to_starts(user_roster, all_starts)
                opp_starts = match_pitchers_to_starts(opponent_roster, all_starts)

                # Side-by-side comparison
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader(f"🏠 {user_team_name}")
                    st.metric("Probable Starts", len(my_starts))

                    if not my_starts.empty:
                        lefties = len(my_starts[my_starts["Handedness"] == "L"])
                        righties = len(my_starts[my_starts["Handedness"] == "R"])
                        st.write(f"**Handedness:** {lefties} LHP, {righties} RHP")

                        # Show starts
                        st.dataframe(
                            style_opponent_column(my_starts[["Date", "Pitcher", "Opponent"]]),
                            hide_index=True,
                            use_container_width=True,
                        )
                    else:
                        st.info("No starts scheduled")

                with col2:
                    st.subheader(f"🔥 {opponent_team_name}")
                    st.metric("Probable Starts", len(opp_starts))

                    if not opp_starts.empty:
                        lefties = len(opp_starts[opp_starts["Handedness"] == "L"])
                        righties = len(opp_starts[opp_starts["Handedness"] == "R"])
                        st.write(f"**Handedness:** {lefties} LHP, {righties} RHP")

                        # Show starts
                        st.dataframe(
                            style_opponent_column(opp_starts[["Date", "Pitcher", "Opponent"]]),
                            hide_index=True,
                            use_container_width=True,
                        )
                    else:
                        st.info("No starts scheduled")
            else:
                st.header("⚖️ Team Comparison")
                st.info("Load data to see matchup comparison")
    else:
        # Initial state - show instructions
        st.info("👈 Select your team and click **Load Pitcher Data** to get started")

        st.markdown("""
        ### How to Use
        
        1. **Select your team ID** from the sidebar (1-14)
        2. Click **Load Pitcher Data** to fetch your roster and matchup info
        3. View three different perspectives:
           - **My Pitchers' Starts**: See all probable starts for your pitchers
           - **Opposition Schedule**: Check your opponent's probable starters
           - **Team Comparison**: Compare start volume and matchup advantages
        
        ### Features
        
        - ✅ Auto-detects current fantasy week
        - ✅ Identifies your matchup opponent automatically
        - ✅ Fetches real-time probable starters from FanGraphs
        - ✅ Shows pitcher handedness and opponent info
        - ✅ Compares start volume between teams
        """)


if __name__ == "__main__":
    main()
