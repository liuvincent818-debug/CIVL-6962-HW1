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

where_clause = f"""
        WHERE tpep_pickup_datetime >= '{start_date} 00:00:00'
          AND tpep_pickup_datetime <= '{end_date} 23:59:59'
          AND EXTRACT(HOUR FROM tpep_pickup_datetime) BETWEEN {start_hour} AND {end_hour}
          {pass_str}
    """

    # Query 1: Time Series Aggregation (Trips, Revenue, Distance)
ts_query = f"""
        SELECT 
            DATE_TRUNC('{trunc_unit}', tpep_pickup_datetime) AS time_bucket,
            COUNT(*) AS total_trips,
            SUM(total_amount) AS total_revenue,
            AVG(trip_distance) AS avg_distance
        FROM '{RAW_URL}'
        {where_clause}
        GROUP BY time_bucket
        ORDER BY time_bucket ASC
    """
ts_df = con.execute(ts_query).df()

    # Query 2: Payment Type Breakdown
pay_query = f"""
        SELECT 
            CASE payment_type 
                WHEN 1 THEN 'Credit Card'
                WHEN 2 THEN 'Cash'
                WHEN 3 THEN 'No Charge'
                WHEN 4 THEN 'Dispute'
                ELSE 'Unknown'
            END AS payment_method,
            COUNT(*) AS trip_count
        FROM '{RAW_URL}'
        {where_clause}
        GROUP BY payment_type
        ORDER BY trip_count DESC
    """
pay_df = con.execute(pay_query).df()

    # Query 3: Hourly Demand Distribution (0 - 23 Hours)
hourly_query = f"""
        SELECT 
            EXTRACT(HOUR FROM tpep_pickup_datetime)::INT AS hour_of_day,
            COUNT(*) AS trip_count
        FROM '{RAW_URL}'
        {where_clause}
        GROUP BY hour_of_day
        ORDER BY hour_of_day ASC
    """
hourly_df = con.execute(hourly_query).df()

    # ==========================================
    # METRICS & DISPLAY
    # ==========================================
if not ts_df.empty:
        total_trips = ts_df["total_trips"].sum()
        avg_trips = ts_df["total_trips"].mean()
        total_rev = ts_df["total_revenue"].sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Trips", f"{total_trips:,}")
        c2.metric(f"Avg Trips per {time_unit}", f"{int(avg_trips):,}")
        c3.metric("Total Revenue", f"${total_rev:,.2f}")

        st.divider()

        # CHART 1: Trip Volume Time Series
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

        # CHART 2: Total Revenue Time Series
        fig_rev = px.line(
            ts_df, x="time_bucket", y="total_revenue",
            title=f"2. Total Revenue ($) from {start_date} to {end_date} (Grouped by {time_unit})",
            labels={"time_bucket": "Time Period", "total_revenue": "Revenue ($)"},
            markers=True
        )
        fig_rev.update_traces(hovertemplate="%{x}<br>Revenue: $%{y:,.2f}")
        fig_rev.update_layout(hovermode="x unified")
        st.plotly_chart(fig_rev, use_container_width=True)

        st.divider()

        # SECTION FOR 3rd OPTION CHARTS
        st.subheader("Supplemental Analytics")
        col_left, col_right = st.columns(2)

        # CHART 3A: Payment Type Distribution (Donut Chart)
        with col_left:
            fig_pay = px.pie(
                pay_df, values="trip_count", names="payment_method",
                title="3A. Payment Method Distribution",
                hole=0.4
            )
            fig_pay.update_traces(textinfo="percent+label")
            st.plotly_chart(fig_pay, use_container_width=True)

        # CHART 3B: Hourly Demand Distribution (Bar Chart)
        with col_right:
            fig_hour = px.bar(
                hourly_df, x="hour_of_day", y="trip_count",
                title="3B. Demand by Hour of Day (0-23)",
                labels={"hour_of_day": "Hour (24h)", "trip_count": "Total Trips"},
            )
            fig_hour.update_layout(xaxis=dict(tickmode="linear", tick0=0, dtick=2))
            st.plotly_chart(fig_hour, use_container_width=True)

        # CHART 3C: Average Distance Time Series
        fig_dist = px.line(
            ts_df, x="time_bucket", y="avg_distance",
            title=f"3C. Average Trip Distance (Miles) (Grouped by {time_unit})",
            labels={"time_bucket": "Time Period", "avg_distance": "Avg Distance (mi)"},
            markers=True
        )
        fig_dist.update_layout(hovermode="x unified")
        st.plotly_chart(fig_dist, use_container_width=True)

else:
        st.warning("No records found matching the specified parameters.")
