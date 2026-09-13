import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px

st.set_page_config(page_title="NYC TLC Trips", layout="wide")
RAW = "https://github.com/liuvincent818-debug/CIVL-6962-HW1/raw/refs/heads/main/yellow_2024-03.parquet"

@st.cache_resource
def get_connection():
    return duckdb.connect(database=":memory:")
con = get_connection()

@st.cache_data
def get_date_bounds():
    query = f"""
        SELECT 
            MIN(tpep_pickup_datetime)::DATE as min_date,
            MAX(tpep_pickup_datetime)::DATE as max_date
        FROM '{RAW}'
    """
    df_bounds = con.execute(query).df()
    return df_bounds["min_date"].iloc[0], df_bounds["max_date"].iloc[0]
min_date, max_date = get_date_bounds()

st.title("NYC TLC Taxi Trip Volume Analysis")

# Sidebar Filters
st.sidebar.header("Filter & Aggregation Options")

# 1. Date Range Selection
date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

# 2. Time-of-Day Filter (Hours 0 - 23)
start_hour, end_hour = st.sidebar.slider(
    "Filter by Pickup Hour of Day",
    min_value=0,
    max_value=23,
    value=(0, 23),
    format="%d:00",
)

# 3. Time Grouping Granularity
time_unit = st.sidebar.selectbox(
    "Aggregate Trips By",
    options=["Hour", "Day", "Month"],
    index=1,  # Default to 'Day'
)

# Map human-readable option to SQL DATE_TRUNC parameter
time_unit_map = {"Hour": "hour", "Day": "day", "Month": "month"}
trunc_unit = time_unit_map[time_unit]

# Optional Category Filter (e.g., Passenger Count)
passenger_filter = st.sidebar.multiselect(
    "Passenger Count Filter",
    options=[1, 2, 3, 4, 5, 6],
    default=[1, 2, 3, 4, 5, 6],
)

# DUCKDB Query 
if len(date_range) == 2:
    start_date, end_date = date_range

    # Convert inputs into SQL-ready conditions
    pass_str = (
        f"AND passenger_count IN ({','.join(map(str, passenger_filter))})"
        if passenger_filter
        else ""
    )

    query = f"""
        SELECT 
            DATE_TRUNC('{trunc_unit}', tpep_pickup_datetime) AS time_bucket,
            COUNT(*) AS total_trips,
            AVG(trip_distance) AS avg_distance,
            SUM(total_amount) AS total_revenue
        FROM '{RAW}'
        WHERE tpep_pickup_datetime >= '{start_date} 00:00:00'
          AND tpep_pickup_datetime <= '{end_date} 23:59:59'
          AND EXTRACT(HOUR FROM tpep_pickup_datetime) BETWEEN {start_hour} AND {end_hour}
          {pass_str}
        GROUP BY time_bucket
        ORDER BY time_bucket ASC
    """

    # Run query and pull only the aggregated time-series table into Pandas
    aggregated_df = con.execute(query).df()

    # ==========================================
    # METRICS DISPLAY
    # ==========================================
    total_trips = aggregated_df["total_trips"].sum()
    avg_trips_per_period = (
        aggregated_df["total_trips"].mean() if not aggregated_df.empty else 0
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Trips in Selection", f"{total_trips:,}")
    c2.metric(f"Avg Trips per {time_unit}", f"{int(avg_trips_per_period):,}")
    c3.metric(
        "Total Revenue", f"${aggregated_df['total_revenue'].sum():,.2f}"
    )

    st.divider()

# Plotly
if not aggregated_df.empty:
        fig = px.line(
            aggregated_df,
            x="time_bucket",
            y="total_trips",
            title=f"Trips Taken over Time (Grouped by {time_unit})",
            labels={
                "time_bucket": "Time Period",
                "total_trips": "Number of Trips",
            },
            markers=True,
        )

        fig.update_layout(
            hovermode="x unified",
            xaxis_title="Date / Time",
            yaxis_title="Trip Volume",
        )

        st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No trips found for the selected date and time range.")

#@st.cache_data
#def load_data(url):
#    return pd.read_parquet(url)

#df = load_data(RAW)
#filtered_df = df.copy()  # Create a copy to apply filters on

#st.dataframe(filtered_df)
