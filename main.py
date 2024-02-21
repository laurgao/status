import os
from datetime import datetime, timedelta, timezone

import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# from discord_oauth import get_access_token, get_login_url, get_user_info

TTL = 60*60 # 1 hour


@st.cache_data() # basically constant for all time
def get_toggl_workspace() -> int:
    resp = httpx.get('https://api.track.toggl.com/api/v9/me', auth=(os.environ['TOGGL_API_KEY'], 'api_token'))
    resp.raise_for_status()
    return resp.json()['default_workspace_id']

@st.cache_data(ttl=TTL)
def get_toggl_day(start_date: str, end_date: str, grouping="projects"):
    workspace_id = get_toggl_workspace()

    resp = httpx.post(
        f'https://api.track.toggl.com/reports/api/v3/workspace/{workspace_id}/summary/time_entries',
        auth=(os.environ['TOGGL_API_KEY'], 'api_token'),
        json={
            "collapse": True,
            "grouping": grouping,
            "sub_grouping": "time_entries",
            "end_date": end_date,
            "start_date": start_date,
            "audit": {
                "show_empty_groups": False,
                "show_tracked_groups": True,
                "group_filter": {}
            },
            "include_time_entry_ids": True
        }
    )
    resp.raise_for_status()

    return resp.json()


@st.cache_data(ttl=TTL)
def get_toggl_projects():
    resp = httpx.get("https://api.track.toggl.com/api/v9/me/projects", auth=(os.environ['TOGGL_API_KEY'], 'api_token'))
    resp.raise_for_status()
    return resp.json()


@st.cache_data(ttl=TTL)
def get_toggl_clients():
    resp = httpx.get("https://api.track.toggl.com/api/v9/me/clients", auth=(os.environ['TOGGL_API_KEY'], 'api_token'))
    resp.raise_for_status()
    return resp.json()


def show_toggl_data(start_date: str, end_date: str):
    st.write("## Time tracking")

    # Multiple choice between "projects" and "clients"
    grouping = st.radio("Grouping", ("projects", "clients")) or "projects"
    toggl = get_toggl_day(start_date, end_date, grouping=grouping)
    toggl_groupings = get_toggl_projects() if grouping == "projects" else get_toggl_clients()

    # New schema processing
    data = []
    for group in toggl['groups']:
        grouping_id = group['id']
        grouping_name = None
        if grouping_id is not None:
            grouping_name = next((group['name'] for group in toggl_groupings if group['id'] == grouping_id), None)
        for sub_group in group['sub_groups']:
            data.append({
                f'{grouping}_id': grouping_id,
                f'{grouping}_name': grouping_name,
                'title': sub_group.get('title') or '<No title>',
                'duration': sub_group['seconds'] / 60 / 60
            })

    df = pd.DataFrame(data)

    # Check if df is empty
    if df.empty:
        st.write("No time tracking data found :(")
        return

    # Sum over group name
    df = df.groupby([f'{grouping}_name']).sum(numeric_only=True).reset_index()

    # Format duration as hours minutes
    df['formatted_duration'] = df['duration'].apply(lambda x: f"{int(x)}h {int((x - int(x)) * 60)}min")

    # Pie chart with plotly
    fig = px.pie(df[[f'{grouping}_name', 'duration', 'formatted_duration']], values='duration', names=f'{grouping}_name', custom_data=['formatted_duration'])
    fig.update_traces(hovertemplate='%{label}<br>Duration: %{customdata[0]}<extra></extra>')

    st.plotly_chart(fig)



def main():
    st.title("Laura's time tracker")
    st.write(f"How Laura has been ~~wasting~~ spending her time. Welcome, Baby Uli!!!! <3")

    # Use streamlit to get the date via a date picker
    default_date = datetime.now(timezone(timedelta(hours=-4))).date()
    date = st.date_input("Date", default_date).strftime('%Y-%m-%d') # type: ignore

    show_toggl_data(date, date)


if __name__ == '__main__':
    main()
