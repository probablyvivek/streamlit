import os
import pandas as pd
import streamlit as st
from mplsoccer import VerticalPitch
from dotenv import load_dotenv
import psycopg2

def main():
    load_dotenv(dotenv_path='secret.env', override=True)

    # Database connection parameters
    db_params = {
        'dbname': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT', 5432)  # Default to 5432 if not set
    }

    # Connect to the database
    try:
        conn = psycopg2.connect(**db_params)
    except psycopg2.OperationalError as e:
        st.error(f"Unable to connect to the database: {e}")
        return

    cursor = conn.cursor()

    # Query to get x and y coordinates of all shots
    query = """
    SELECT
      u.id,
      e.match_id,
      CONCAT(
        INITCAP(SPLIT_PART(
          REGEXP_REPLACE(
            SUBSTRING(
              u.url FROM 'International-European-Championship-(.*)'
            ), '-', ' '
          ), ' ', 1
        )),
        ' vs ',
        INITCAP(SPLIT_PART(
          REGEXP_REPLACE(
            SUBSTRING(
              u.url FROM 'International-European-Championship-(.*)'
            ), '-', ' '
          ), ' ', 2
        ))
      ) AS match_name,
      INITCAP(SPLIT_PART(
        REGEXP_REPLACE(
          SUBSTRING(
            u.url FROM 'International-European-Championship-(.*)'
          ), '-', ' '
        ), ' ', 1
      )) AS home_team,
      INITCAP(SPLIT_PART(
        REGEXP_REPLACE(
          SUBSTRING(
            u.url FROM 'International-European-Championship-(.*)'
          ), '-', ' '
        ), ' ', 2
      )) AS away_team,
      p.player_id,
      CASE
        WHEN e.is_own_goal AND INITCAP(SPLIT_PART(
          REGEXP_REPLACE(
            SUBSTRING(
              u.url FROM 'International-European-Championship-(.*)'
            ), '-', ' '
          ), ' ', 1)) = p.team_name THEN INITCAP(SPLIT_PART(
          REGEXP_REPLACE(
            SUBSTRING(
              u.url FROM 'International-European-Championship-(.*)'
            ), '-', ' '
          ), ' ', 2))
        WHEN e.is_own_goal AND INITCAP(SPLIT_PART(
          REGEXP_REPLACE(
            SUBSTRING(
              u.url FROM 'International-European-Championship-(.*)'
            ), '-', ' '
          ), ' ', 2)) = p.team_name THEN INITCAP(SPLIT_PART(
          REGEXP_REPLACE(
            SUBSTRING(
              u.url FROM 'International-European-Championship-(.*)'
            ), '-', ' '
          ), ' ', 1))
        ELSE p.team_name
      END AS team_name,
      CASE
        WHEN e.is_own_goal THEN 'Own Goal'
        ELSE p.name
      END AS name,
      CONCAT(
        CAST(e.minute AS TEXT),
        ':',
        CAST(e.second AS TEXT)
      ) AS minute_second,
      e.x_coordinate,
      e.y_coordinate,
      CASE
        WHEN e.is_goal THEN 1
        ELSE 0
      END AS is_goal
    FROM
      players_euros_2024 p
      LEFT JOIN euros_2024_match_events e ON p.player_id = e.player_id
      LEFT JOIN processed_urls u ON u.match_id = e.match_id
    WHERE
      e.is_shot = TRUE
    ORDER BY
      u.id ASC;
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    # Convert the data to a DataFrame
    columns = ['id', 'match_id', 'match_name', 'home_team', 'away_team', 'player_id', 'team_name', 'name', 'minute_second', 'x_coordinate', 'y_coordinate', 'is_goal']
    df = pd.DataFrame(rows, columns=columns)

    # Streamlit UI
    st.title("Euro Championship 2024 Shot Map")
    st.subheader("Filter to any team/player to see all their shots taken!")

    team = st.selectbox("Select a team", df['team_name'].unique())

    # Single-select for players
    player = st.selectbox(
        "Select a player", 
        options=df[df['team_name'] == team]['name'].unique()
    )

    # Filter data based on selections
    filtered_df = df[(df['team_name'] == team) & (df['name'] == player)]

    # Plot the shot map
    pitch = VerticalPitch(pitch_type='opta', line_zorder=2, pitch_color='#a7c957', line_color='black', half=True)
    fig, ax = pitch.draw(figsize=(10, 10))

    for _, shot in filtered_df.iterrows():
        color = 'white' if not shot['is_goal'] else 'yellow'
        marker = 'o' if not shot['is_goal'] else '*'
        size = 300 if not shot['is_goal'] else 600
        pitch.scatter(shot['x_coordinate'], shot['y_coordinate'], ax=ax, color=color, s=size, edgecolors='black', alpha=0.9, marker=marker)

    # Player and team annotation in the lower left corner of the plot
    player_name = player  # Assuming 'player' contains the selected player's name
    team_name = team  # Assuming 'team' contains the selected team's name
    ax.text(0.05, 0.02, f"{player_name}\n", fontsize=35, ha='left', va='bottom', transform=ax.transAxes, color='black', style='italic', fontname='Arial Black')
    ax.text(0.05, 0.045, f"{team_name}", fontsize=30, ha='left', va='bottom', transform=ax.transAxes, color='black', style='italic', fontname='Arial Black')


    st.pyplot(fig)

    from io import BytesIO

    # Save the figure to a BytesIO object
    buf = BytesIO()
    fig.savefig(buf, format='jpeg')
    buf.seek(0)

    # Create a download button and offer the plot for download
    st.download_button(
        label="Download Shot Map as JPEG",
        data=buf,
        file_name="shot_map.jpeg",
        mime="image/jpeg"
    )

    # Close the database connection
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
