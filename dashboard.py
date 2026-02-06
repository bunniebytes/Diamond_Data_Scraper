import sqlite3
import pandas as pd
from contextlib import closing
from dash import Dash, dcc, html, Input, Output, callback
import plotly.express as px
import plotly.graph_objects as go

with closing(sqlite3.connect("db/baseball_data.db")) as conn:
    
    draft_team_standings_df = pd.read_sql("SELECT d.name, d.team, d.picked, d.college_hs_hometown, d.Year, s.wins, s.losses, s.wp FROM draft AS d LEFT JOIN standing AS s ON d.Year = s.Year AND s.team LIKE '%' || d.team || '%'", conn)
    
    draft_efficiency = draft_team_standings_df.groupby(['team', 'Year']).agg({
        'picked': 'mean',  # Average Draft Position (ADP)
        'wp': 'first',     # Win % for that year
        'wins': 'first'
    }).reset_index().dropna(subset=['wp'])
    
    draft_efficiency["inverse_pick_size"] = 100 - draft_efficiency["picked"]
    
    roi_payroll_wins_df = pd.read_sql("SELECT s.team, s.Year, s.wins, s.payroll, (s.payroll / s.wins) as cost_per_win, AVG(s.payroll / s.wins) OVER(PARTITION BY s.Year) as league_avg_cost_win, m.[Minimum Salary] as min_salary, (s.payroll / m.[Minimum Salary]) as roster_cost_units FROM standing AS s JOIN salary as m ON s.Year = m.Year WHERE payroll > 0 AND wins > 0", conn)
    
    roi_trend_df = roi_payroll_wins_df.groupby("Year").agg({
    "cost_per_win" : "mean",
    "league_avg_cost_win" : "first",
    "roster_cost_units" : "mean"
    }).reset_index()
    
    salary_balance_df = pd.read_sql("SELECT s.Year, AVG(s.wp) AS avg_wp, s.wp, m.[Minimum Salary] FROM standing AS s JOIN salary AS m ON s.Year = m.YEAR GROUP BY s.Year ORDER BY s.YEAR ASC", conn)
    df_raw = pd.read_sql("SELECT Year, wp FROM standing", conn)
    # Need to add a standard deviation column
    df_raw["wp"] = pd.to_numeric(df_raw["wp"], errors = "coerce")
    spread_series = df_raw.groupby("Year")["wp"].std()
    salary_balance_df["competitive_spread"] = salary_balance_df["Year"].map(spread_series)
    
    tables = {"Draft Team Standings" : draft_efficiency,
              "ROI_Analysis" : roi_payroll_wins_df,
              "Salary Trends" : salary_balance_df}

# Initialize Dash app
app = Dash(__name__)

# Layout
app.layout = html.Div([
    html.H1("Baseball Data Analysis Dashboard", style={"textAlign": "center"}),
    
    html.Div([
        html.Label("Choose Analysis View:"),
        dcc.Tabs(id="tabs-selector", value="ROI_Analysis", children=[
            dcc.Tab(label="ROI Analysis", value="ROI_Analysis"),
            dcc.Tab(label="Salary Trends", value="Salary Trends"),
            dcc.Tab(label="Draft vs Standings", value="Draft Team Standings"),
        ]),
        ], style={"padding": "20px", "margin" : "auto", "text-align" : "center"}),
    
    html.Div([
        html.Label("Select Year to Compare Amount Spent:", style={"fontWeight": "bold"}),
        dcc.Dropdown(
            id = "year-selector-dropdown",
            # Use the years names from dataframe
            options = [{"label": t, "value": t} for t in sorted(roi_payroll_wins_df["Year"].unique())],
            multi = False,
            value = 1986, # Default starting year
            placeholder = "Select one or more years"
        )
        ], id = "year-container", style = {"display": "none"}),
    
    html.Div([
        html.Label("Select Teams to Compare Trajectories:", style = {"fontWeight": "bold"}),
        dcc.Dropdown(
            id = "team-selector-dropdown",
            # Use the unique team names from your dataframe
            options = [{"label": t, "value": t} for t in sorted(draft_efficiency["team"].unique())],
            multi = True,
            value = ["Angels"], # Default starting team
            placeholder = "Select one or more teams..."
        )
        ], id = "team-container", style = {"display": "none"}),

        html.Div([
            dcc.Graph(id = "main-graph-display")
        ])
])

@callback(
    Output("year-container", "style"),
    Output("team-container", "style"),
    Input("tabs-selector", "value")
)

def toggle_dropdown_visibility(selected_tab):
    show = {"width": "60%", "margin": "0 auto", "padding": "20px", "display": "block", "textAlign": "center"}
    hide = {"display": "none"}
    
    if selected_tab == "ROI_Analysis":
        # Hide Team selector, Show Year selector
        return show, hide
    
    elif selected_tab == "Draft Team Standings":
        # Show Team selector, Hide Year selector
        return hide, show
    
    # Default: hide both if on a different tab
    return hide, hide

@callback(
    Output("main-graph-display", "figure"),
    [Input("tabs-selector", "value"),
     Input("year-selector-dropdown", "value"),
     Input("team-selector-dropdown", "value")]
)


def update_all_visuals(selected_tab, selected_year, selected_teams):
    # 1. Get the correct dataframe from your dictionary
    # Use .get() to avoid KeyError if names don't match perfectly
    df = tables.get(selected_tab)
    
    if df is None:
        return px.scatter(title="Data not found")

    # Logic Switch for the 3 Tabs
    if selected_tab == "ROI_Analysis":
        year_df = df[df["Year"] == selected_year].copy()
        year_df = year_df.sort_values("cost_per_win", ascending=False)
        
        # finds the league average cost per win
        league_avg = year_df["league_avg_cost_win"].iloc[0]
        
        # finds the minimum cost per win with roster of 25 players (pre 2021 and since we only have data before then) for average season of 81 games
        min_sal = year_df["min_salary"].iloc[0]
        min_cost_per_win = (min_sal * 25) / 81

        # colors bars red or green depending on how efficiently they spend (above or below avg cost of win)
        bar_colors = [
        "rgba(46, 204, 113, 0.7)" if cost <= league_avg else "rgba(231, 76, 60, 0.7)" 
        for cost in year_df["cost_per_win"]
         ]
        
        # creates blank graph
        fig = go.Figure()
        
        # Bars for Cost per Win
        fig.add_trace(go.Bar(
            x = year_df["team"],
            y = year_df["cost_per_win"],
            name = "Cost Per Win",
            marker_color = bar_colors,
            customdata = year_df[["payroll", "roster_cost_units"]],
            # Use %{customdata[0]} to access payroll in the hovertemplate
            hovertemplate = "<b>%{x}</b><br>Cost per Win: $%{y:,.0f}<br>Total Payroll: $%{customdata[0]:,.0f}<br>Roster Units: %{customdata[1]:.1f}<extra></extra>",
            yaxis = 'y1'
        ))

        # Line for league average cost per win
        fig.add_hline(
            y=league_avg, 
            line_dash="dash", 
            line_color="black", 
            annotation_text=f"Avg Cost: ${league_avg:,.0f}",
            annotation_position="top left",
            layer="above"
        )

        # Adds the Win Average Line (Secondary Y-Axis)
        fig.add_hline(
            y=81, 
            line_dash="dot", 
            line_color="firebrick", 
            opacity=0.3,
            yref="y2", # Crucial: Tells Plotly to use the Wins axis
            annotation_text="Avg Wins (81)",
            annotation_position="bottom right"
        )
        
        # Line for Total Wins
        fig.add_trace(go.Scatter(
            x = year_df['team'],
            y = year_df['wins'],
            name = 'Total Wins',
            mode = 'lines+markers',
            line = dict(color = 'firebrick', width = 3),
            yaxis = 'y2' # This tells it to use a different axis
        ))
        
        # shows the minimum cost per win that year
        fig.add_hrect(
            y0 = 0, 
            y1 = min_cost_per_win, 
            fillcolor = "gray", 
            opacity = 0.1, 
            layer = "below",
            annotation_text = f"League Minimum Floor Cost Per Win: ${min_cost_per_win:,.0f}",
            annotation_position = "bottom left"
        )

        # Create the Dual Axis Layout
        fig.update_layout(
            title = {'text': f"Efficiency vs. Results ({selected_year})", 'x': 0.5, 'xanchor': 'center'},
            xaxis_title = "Team",
            # Primary Axis (Left)
            yaxis = dict(
                title = dict(
                    text = "Cost Per Individual Win ($)",
                    font = dict(color="#6496FA")),
                tickfont = dict(color="#6496FA"),
                tickprefix = "$"
            ),
            # Secondary Axis (Right)
            yaxis2 = dict(
                title = dict(
                    text = "Total Wins",
                    font = dict(color = "firebrick")),
                tickfont = dict(color = "firebrick"),
                anchor = "x",
                overlaying = "y",
                side = "right",
                range = [0, 110] # Baseball seasons are 162 games, 110 is a safe max
            ),
            hovermode = "x unified",
            showlegend = True
        )
        fig.add_annotation(
            dict(
                xref='paper', yref='paper',
                x=0.53, y=1.15,
                xanchor="center",
                showarrow=False,
                text=f"Note: The MLB Minimum Salary in {selected_year} was ${min_sal:,.0f}",
                font=dict(size=12, color="gray")
            )
        )

    elif selected_tab == 'Salary Trends':
        # This makes the Parity easier to read - scaling them by 100
        salary_balance_df["spread_points"] = salary_balance_df["competitive_spread"] * 100
        
        # Find the relationship between the 2 items we are comparing
        correlation = salary_balance_df['Minimum Salary'].corr(salary_balance_df['competitive_spread'])
        
        if correlation > 0.5:
            result_text = "Strong Link: Higher pay = More Inequality"
        elif correlation < -0.5:
            result_text = "Strong Link: Higher pay = More Equality"
        else:
            result_text = "No Clear Link: Salary doesn't change the gap"
        
        # They ended up being the same so will only show one
        avg_90s = salary_balance_df[(salary_balance_df['Year'] >= 1990) & (salary_balance_df['Year'] <= 1999)]["spread_points"].mean()
        avg_2010s = salary_balance_df[(salary_balance_df['Year'] >= 2010) & (salary_balance_df['Year'] <= 2019)]["spread_points"].mean()
        
        fig = go.Figure()

        # Line for the 'Spread' (How unequal the league is)
        fig.add_trace(go.Scatter(
            x = salary_balance_df["Year"], 
            y = salary_balance_df["spread_points"],
            name = "League Inequality",
            hovertemplate = "<b>Year: %{x}</b><br>Competitiveness Gap: %{y:.2f} points<br><extra></extra>",
            line = dict(color = "purple", width = 4)
        ))

        # Line for Minimum Salary
        fig.add_trace(go.Scatter(
            x = salary_balance_df["Year"], 
            y = salary_balance_df["Minimum Salary"],
            name = "Min Salary",
            line = dict(color = "gold", dash = "dot"),
            yaxis = "y2"
        ))

        # Baseline
        fig.add_hline(
            y = avg_2010s, 
            line_dash = "dot", 
            line_color = "orange", 
            annotation_text = f"Avg: {avg_2010s:.1f} pts",
            annotation_position = "top left"
        )
        
        fig.add_annotation(
            dict(
                xref="paper", yref="paper",
                x=.55, y=1.15, # Top right corner
                showarrow=False,
                text=f"Correlation Score: {correlation:.2f} ({result_text})",
                font=dict(size=14, color="purple", family="Arial Black"),
                bgcolor="white",
                bordercolor="purple",
                borderwidth=2
            )
        )

        fig.update_layout(
            title = {"text": "League Parity: Is the Gap Between Best and Worst Growing?", "x": 0.5},
            yaxis = dict(range=[0, 10], title = "Competitive Spread (Points)",
                         ticksuffix = "pts"),
            yaxis2 = dict(title = "Minimum Salary ($)", overlaying = "y", side = "right"),
            hovermode = "x unified"
        )
        
    elif selected_tab == "Draft Team Standings":
        filtered_df = df[df["team"].isin(selected_teams)].copy()
        filtered_df = filtered_df.sort_values(["team", "Year"])
        
        # Exaggerating the size of the bubbles for better clarity
        filtered_df["scaled_size"] = (100 / filtered_df["picked"]) * 3
        
        fig = px.line(
            filtered_df, 
            x = "Year", 
            y = "wp", 
            color = "team",
            markers = True,
            hover_data = ["team", "Year", "picked"],
            title = f"Team Performance Trajectory & Draft Priority"
            )
        
        # print(f"AVAILABLE COLUMNS: {list(df.columns)}")

        fig.update_traces(mode="lines+markers", marker = dict(size = filtered_df["scaled_size"], sizemode = "area", sizeref = 2.*max(filtered_df["scaled_size"])/(40.**2), line = dict(width = 1, color = "DarkSlateGrey")))
        
        fig.update_layout(
            title = {'y': 0.95, 'x': 0.5, 'xanchor': 'center'},
            yaxis_title = "Winning Percentage",
            xaxis_title = "Season Year",
            hovermode = "x unified"
        )

        avg_wp_trend = draft_team_standings_df.groupby("Year")["wp"].mean().reset_index()
        
        fig.add_traces(
            px.line(avg_wp_trend, x = "Year", y = "wp").update_traces(
                line_color = "black", 
                line_dash = "dash", 
                name = "League Avg WP",
                hovertemplate = "<br>Year: %{x}<br>Avg WP: %{y:.3f}"
            ).data
        )
        
    return fig

# Run the app
if __name__ == "__main__": 
    app.run(debug=True) 


# Need at least 3 visualizations
# drop down menu to select certain data or sliders to adjust view
# need to dynamically update based on user input
# deploy on render or streamlit.io

# maybe show player where player picked in draft and how their teams performed?
# growth of salary over time vs payroll for that same time frame? Also show how teams that put more money into it did?
# player stat vs team stat with same name over years?