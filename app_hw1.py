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
        WHERE tpep_pickup_datetime >= '2024-03-01' AND tpep_pickup_datetime <= '2024-03-31'
    """
    df_bounds = con.execute(query).df()
    return df_bounds["min_date"].iloc[0], df_bounds["max_date"].iloc[0]
min_date, max_date = get_date_bounds()

st.title("NYC TLC Taxi Trip Volume Analysis")

# Sidebar Filters
st.sidebar.header("Filter & Aggregation Options")

# Selection Mode Toggle
date_mode = st.sidebar.radio(
    "Date Selection Mode",
    options=["Individual Date Pickers", "Calendar Range Picker"],
    index=0
)

# 2. Flexible Date Input Controls
if date_mode == "Individual Date Pickers":
    col_start, col_end = st.sidebar.columns(2)
    with col_start:
        start_date = st.date_input(
            "Start Date",
            value=min_date,
            min_value=min_date,
            max_value=max_date
        )
    with col_end:
        end_date = st.date_input(
            "End Date",
            value=max_date,
            min_value=min_date,
            max_value=max_date
        )
else:
    # Single Range Calendar Input
    selected_range = st.sidebar.date_input(
        "Select Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    if len(selected_range) == 2:
        start_date, end_date = selected_range
    else:
        start_date, end_date = min_date, max_date

# Validate that Start Date isn't set after End Date
if start_date > end_date:
    st.sidebar.error("Error: Start Date must be before or equal to End Date.")
else:
    # Rest of your DuckDB query and plotting logic...
    query = f"""
        SELECT 
            DATE_TRUNC('day', tpep_pickup_datetime) AS time_bucket,
            COUNT(*) AS total_trips
        FROM '{RAW}'
        WHERE tpep_pickup_datetime >= '{start_date} 00:00:00'
          AND tpep_pickup_datetime <= '{end_date} 23:59:59'
        GROUP BY time_bucket
        ORDER BY time_bucket ASC
    """
    aggregated_df = con.execute(query).df()

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
# Guardrail: Only run the query if start_date is on or before end_date
if start_date > end_date:
    st.sidebar.error("Error: 'Start Date' cannot be after 'End Date'.")
    st.info("Please adjust your date inputs in the sidebar to view the dashboard.")

else:
    # Build dynamic passenger filter string safely
    pass_str = (
        f"AND passenger_count IN ({','.join(map(str, passenger_filter))})"
        if passenger_filter
        else ""
    )

    # Dynamic SQL Query integrating date range, hour bounds, and time aggregation
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

    # Execute query in DuckDB and load only the summary rows into Pandas
    aggregated_df = con.execute(query).df()

    # ==========================================
    # METRICS & DISPLAY
    # ==========================================
    if not aggregated_df.empty:
        total_trips = aggregated_df["total_trips"].sum()
        avg_trips = aggregated_df["total_trips"].mean()
        total_rev = aggregated_df["total_revenue"].sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Trips", f"{total_trips:,}")
        c2.metric(f"Avg Trips per {time_unit}", f"{int(avg_trips):,}")
        c3.metric("Total Revenue", f"${total_rev:,.2f}")

        st.divider()

        # Render interactive Plotly Chart
        fig = px.line(
            aggregated_df,
            x="time_bucket",
            y="total_trips",
            title=f"Trips from {start_date} to {end_date} (Grouped by {time_unit})",
            labels={
                "time_bucket": "Time Period",
                "total_trips": "Trip Count"
            },
            markers=True
        )

        fig.update_layout(hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("No trip records found matching your current filter criteria.")
