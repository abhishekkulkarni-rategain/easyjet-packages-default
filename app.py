import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="EasyJet Package Insights POC", layout="wide", initial_sidebar_state="expanded")

# --- DUMMY DATA GENERATOR ---
@st.cache_data
def load_dummy_data():
    """Generates 1500 rows of enriched dummy package shopping data including historical shops and unavailability."""
    np.random.seed(42)
    
    routes_map = {
        'LGW-BJV': {'Origin': 'LGW', 'Dest': 'BJV', 'Country': 'Turkey'},
        'MAN-DXB': {'Origin': 'MAN', 'Dest': 'DXB', 'Country': 'UAE'},
        'LHR-DXB': {'Origin': 'LHR', 'Dest': 'DXB', 'Country': 'UAE'},
        'LGW-PMI': {'Origin': 'LGW', 'Dest': 'PMI', 'Country': 'Spain'},
        'MAN-PMI': {'Origin': 'MAN', 'Dest': 'PMI', 'Country': 'Spain'}
    }
    
    hotels = ['Ambrosia Hotel', 'Waldorf Astoria', 'InterContinental', 'Jasmin Beach', 'Anantara Resort']
    competitors = ['LOVEHOLIDAYSPKG', 'ONTHEBEACHPACKAGE', 'Expedia', 'Booking']
    airlines = ['U2 (EasyJet)', 'FR (Ryanair)', 'BA (British Airways)', 'TK (Turkish)']
    occupancies = ['2 Adults', '1 Adult', '2 Adults + 1 Child', '2 Adults + 2 Children']
    star_ratings = [3, 4, 5]
    
    # Generate 14 days of historical shop dates for trendlines
    base_shop_date = datetime(2026, 5, 7)
    shop_dates = [(base_shop_date - timedelta(days=i)).date() for i in range(14)]
    base_dep_date = datetime(2026, 6, 1)
    
    data = []
    
    for _ in range(1500):
        route_key = np.random.choice(list(routes_map.keys()))
        geo = routes_map[route_key]
        hotel = np.random.choice(hotels)
        
        # New Dimensions
        shop_date = np.random.choice(shop_dates)
        airline = np.random.choice(airlines)
        occ = np.random.choice(occupancies)
        star = np.random.choice(star_ratings)
        
        # Dates and LOS
        dep_offset = np.random.randint(0, 90)
        dep_date = base_dep_date + timedelta(days=dep_offset)
        los = np.random.choice([3, 5, 7, 10, 14])
        ret_date = dep_date + timedelta(days=int(los))
        
        # Pricing
        base = np.random.randint(800, 2500)
        
        # Inject Availability Parity (EasyJet is Out of Stock/Not Available ~10% of the time)
        is_oos = np.random.random() < 0.10
        ej_price = np.nan if is_oos else base + np.random.randint(-150, 150)
        
        prices = {comp: base + np.random.randint(-120, 200) for comp in competitors}
        
        # Flights
        ej_dur = np.random.randint(4, 12)
        mkt_dur = ej_dur + np.random.randint(-3, 4)
        
        row = [
            shop_date, geo['Origin'], geo['Dest'], geo['Country'], dep_date.date(), ret_date.date(), los, 
            hotel, star, occ, airline,
            ej_price, prices['LOVEHOLIDAYSPKG'], prices['ONTHEBEACHPACKAGE'], 
            prices['Expedia'], prices['Booking'], ej_dur, mkt_dur
        ]
        data.append(row)
        
    df = pd.DataFrame(data, columns=[
        'Shop_Date', 'Origin_Airport', 'Destination_Airport', 'Destination_Country', 
        'Departure_Date', 'Inbound_Date', 'LOS', 'Hotel', 'Star_Rating', 'Occupancy', 'Airline',
        'EasyJet', 'LOVEHOLIDAYSPKG', 'ONTHEBEACHPACKAGE', 'Expedia', 'Booking', 
        'EJ_Flight_Duration', 'Mkt_Flight_Duration'
    ])
    
    # --- CORE PARITY LOGIC ---
    df['Market_Lowest'] = df[['LOVEHOLIDAYSPKG', 'ONTHEBEACHPACKAGE', 'Expedia', 'Booking']].min(axis=1)
    df['Price_Variance'] = df['EasyJet'] - df['Market_Lowest']
    df['Variance_Percent'] = (df['Price_Variance'] / df['Market_Lowest']) * 100
    df['Duration_Variance'] = df['EJ_Flight_Duration'] - df['Mkt_Flight_Duration']
    
    def determine_status(row):
        if pd.isna(row['EasyJet']): return 'Not Available'
        pct = row['Variance_Percent']
        if pct < -2.5: return 'Win'
        elif -2.5 <= pct <= 2.5: return 'Meet'
        else: return 'Loss'
    
    df['Status'] = df.apply(determine_status, axis=1)
    return df

df = load_dummy_data()

# --- SIDEBAR FILTERS ---
st.sidebar.markdown("### Global Filters")

# Shop Date Filter (For Trendlines)
min_shop = df['Shop_Date'].min()
max_shop = df['Shop_Date'].max()
shop_range = st.sidebar.date_input("Shop Date (Data Pulled On)", value=(min_shop, max_shop), min_value=min_shop, max_value=max_shop)

# Departure Date Filter
min_dep = df['Departure_Date'].min()
max_dep = df['Departure_Date'].max()
dep_range = st.sidebar.date_input("Travel Departure Date", value=(min_dep, max_dep), min_value=min_dep, max_value=max_dep)

# New Categorical Filters
st.sidebar.markdown("### Package Dimensions")
sel_airline = st.sidebar.multiselect("Airline", options=df['Airline'].unique(), default=df['Airline'].unique())
sel_occ = st.sidebar.multiselect("Occupancy", options=df['Occupancy'].unique(), default=df['Occupancy'].unique())

# Reintegrated Hotel & Star Filters
sel_hotel = st.sidebar.multiselect("Hotels", options=df['Hotel'].unique(), default=df['Hotel'].unique())
sel_star = st.sidebar.multiselect("Hotel Star Rating", options=sorted(df['Star_Rating'].unique()), default=sorted(df['Star_Rating'].unique()))

# Existing Geo Filters
st.sidebar.markdown("### Geography")
sel_country = st.sidebar.multiselect("Destination Country", options=df['Destination_Country'].unique(), default=df['Destination_Country'].unique())
sel_origin = st.sidebar.multiselect("Origin Airport", options=df['Origin_Airport'].unique(), default=df['Origin_Airport'].unique())
sel_dest = st.sidebar.multiselect("Destination Airport", options=df['Destination_Airport'].unique(), default=df['Destination_Airport'].unique())
sel_los = st.sidebar.multiselect("Length of Stay (Days)", options=sorted(df['LOS'].unique()), default=sorted(df['LOS'].unique()))

# Apply Filters
if len(shop_range) == 2 and len(dep_range) == 2:
    f_df = df[
        (df['Shop_Date'] >= shop_range[0]) & (df['Shop_Date'] <= shop_range[1]) &
        (df['Departure_Date'] >= dep_range[0]) & (df['Departure_Date'] <= dep_range[1]) &
        (df['Airline'].isin(sel_airline)) & (df['Occupancy'].isin(sel_occ)) & 
        (df['Star_Rating'].isin(sel_star)) & (df['Hotel'].isin(sel_hotel)) &
        (df['Destination_Country'].isin(sel_country)) & (df['Origin_Airport'].isin(sel_origin)) &
        (df['Destination_Airport'].isin(sel_dest)) & (df['LOS'].isin(sel_los))
    ]
else:
    f_df = df.copy()

# Ensure we separate "Available" from "Not Available" for pricing math
available_df = f_df[f_df['Status'] != 'Not Available']

# --- DASHBOARD HEADER ---
st.title("EasyJet Packages Analytics")
st.markdown("Evaluating EasyJet's packaged competitiveness. *Note: 'Meet' defined as within ±2.5% of market lowest.*")

# --- TAB SETUP ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "1. Executive Parity", 
    "2. Trendlines & Pivot", 
    "3. Availability Gap", 
    "4. Margin & Distributions", 
    "5. Attribution Matrix",
    "6. Raw Data Log"
])

# --- TAB 1: EXECUTIVE PARITY ---
with tab1:
    win_count = len(available_df[available_df['Status'] == 'Win'])
    total_avail = len(available_df)
    win_rate = (win_count / total_avail) * 100 if total_avail > 0 else 0
    oos_rate = (len(f_df[f_df['Status'] == 'Not Available']) / len(f_df)) * 100 if len(f_df) > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("EasyJet Win Rate (Available)", f"{win_rate:.1f}%")
    col2.metric("Availability Gap (OOS)", f"{oos_rate:.1f}%", delta="Missed Revenue", delta_color="inverse")
    col3.metric("Avg £ Gap (Losses)", f"£{available_df[available_df['Status'] == 'Loss']['Price_Variance'].mean():.2f}")
    col4.metric("Avg £ Margin (Wins)", f"£{abs(available_df[available_df['Status'] == 'Win']['Price_Variance'].mean()):.2f}")

    col_pie, col_dist = st.columns([1, 2])
    with col_pie:
        status_counts = f_df['Status'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Count']
        fig_donut = px.pie(status_counts, values='Count', names='Status', hole=0.5, 
                           color='Status', color_discrete_map={'Win':'#2ca02c', 'Loss':'#d62728', 'Meet':'#ff7f0e', 'Not Available':'#7f7f7f'},
                           title="Market Position (All Shopped Data)")
        st.plotly_chart(fig_donut, use_container_width=True)

    with col_dist:
        fig_hist_price = px.histogram(available_df, x="Variance_Percent", color="Status", nbins=50,
                                      color_discrete_map={'Win':'#2ca02c', 'Loss':'#d62728', 'Meet':'#ff7f0e'},
                                      title="Distribution of Percentage Variance (%)",
                                      labels={'Variance_Percent': 'Variance to Market Lowest (%)'})
        fig_hist_price.add_vrect(x0=-2.5, x1=2.5, fillcolor="orange", opacity=0.1, layer="below", line_width=0)
        st.plotly_chart(fig_hist_price, use_container_width=True)

# --- TAB 2: TRENDLINES & PIVOT ---
with tab2:
    st.subheader("Time-Series Market Position (DoD / WoW)")
    
    daily_metrics = f_df.groupby('Shop_Date').apply(lambda x: pd.Series({
        'Total_Shops': len(x),
        'Win_Rate_Pct': (len(x[x['Status'] == 'Win']) / len(x[x['Status'] != 'Not Available']) * 100) if len(x[x['Status'] != 'Not Available']) > 0 else 0,
        'Avg_Lowest_Market_Price': x['Market_Lowest'].mean(),
        'Avg_EasyJet_Price': x['EasyJet'].mean()
    })).reset_index()

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        fig_trend_win = px.line(daily_metrics, x='Shop_Date', y='Win_Rate_Pct', markers=True, 
                                title="Daily Win Rate Trend", labels={'Win_Rate_Pct': 'Win Rate (%)'})
        fig_trend_win.update_yaxes(range=[0, 100])
        st.plotly_chart(fig_trend_win, use_container_width=True)
        
    with col_t2:
        fig_trend_price = px.line(daily_metrics, x='Shop_Date', y=['Avg_EasyJet_Price', 'Avg_Lowest_Market_Price'], markers=True,
                                  title="Average Price Trend (£)", labels={'value': 'Average Price (£)', 'variable': 'Metric'})
        st.plotly_chart(fig_trend_price, use_container_width=True)

    st.markdown("#### Status Pivot Table by Shop Date")
    pivot_df = pd.pivot_table(f_df, values='Market_Lowest', index='Shop_Date', columns='Status', aggfunc='count', fill_value=0)
    pivot_df['Total Shops'] = pivot_df.sum(axis=1)
    st.dataframe(pivot_df.style.highlight_max(axis=0, color='#e6f2ff'), use_container_width=True)

# --- TAB 3: AVAILABILITY GAP ---
with tab3:
    st.subheader("Availability Parity: Packages Missing from EasyJet")
    st.markdown("These packages returned competitor prices but yielded no result (or 'Closed' status) from EasyJet.")
    
    oos_df = f_df[f_df['Status'] == 'Not Available']
    
    if not oos_df.empty:
        col_o1, col_o2 = st.columns(2)
        with col_o1:
            fig_oos_geo = px.histogram(oos_df, y="Destination_Airport", color="LOVEHOLIDAYSPKG", 
                                       title="Missed Opportunities by Destination",
                                       category_orders={"Destination_Airport": oos_df['Destination_Airport'].value_counts().index})
            st.plotly_chart(fig_oos_geo, use_container_width=True)
            
        with col_o2:
            fig_oos_occ = px.pie(oos_df, names="Occupancy", title="Missed Opportunities by Occupancy Type", hole=0.4)
            st.plotly_chart(fig_oos_occ, use_container_width=True)
            
        st.markdown("#### Log of Missing Inventory")
        st.dataframe(oos_df[['Shop_Date', 'Departure_Date', 'Origin_Airport', 'Destination_Airport', 'Hotel', 'Occupancy', 'Market_Lowest']], use_container_width=True)
    else:
        st.success("No availability gaps found for the current filter selection! EasyJet is present on all packages.")

# --- TAB 4: MARGIN OPTIMIZATION ---
with tab4:
    col_box, col_los = st.columns(2)
    with col_box:
        melted_df = available_df.melt(id_vars=['Destination_Country'], value_vars=['EasyJet', 'LOVEHOLIDAYSPKG', 'ONTHEBEACHPACKAGE', 'Expedia', 'Booking'], 
                                      var_name='Brand', value_name='Price')
        fig_spread = px.violin(melted_df, x='Destination_Country', y='Price', color='Brand', 
                               box=True, points="all", title="Package Price Clustering & Density")
        fig_spread.update_traces(marker=dict(size=3, opacity=0.6), line_width=1.5)
        fig_spread.update_layout(violingap=0.2, violinmode='group')
        st.plotly_chart(fig_spread, use_container_width=True)

    with col_los:
        fig_hist_los = px.histogram(available_df, x="LOS", color="Status", barmode='group',
                                    color_discrete_map={'Win':'#2ca02c', 'Loss':'#d62728', 'Meet':'#ff7f0e'},
                                    title="Win/Loss Distribution by Length of Stay")
        fig_hist_los.update_xaxes(type='category', categoryorder='category ascending')
        st.plotly_chart(fig_hist_los, use_container_width=True)

# --- TAB 5: ATTRIBUTION MATRIX ---
with tab5:
    fig_scatter = px.scatter(available_df, x="Price_Variance", y="Duration_Variance", 
                             color="Status", hover_data=['Origin_Airport', 'Destination_Airport', 'Hotel', 'Airline'],
                             color_discrete_map={'Win':'#2ca02c', 'Loss':'#d62728', 'Meet':'#ff7f0e'},
                             title="Price Variance (£) vs. Flight Duration Variance (Hours)")

    fig_scatter.add_vline(x=0, line_width=2, line_dash="dash", line_color="black")
    fig_scatter.add_hline(y=0, line_width=2, line_dash="dash", line_color="black")
    st.plotly_chart(fig_scatter, use_container_width=True)

# --- TAB 6: RAW DATA LOG ---
with tab6:
    st.subheader("Raw Intelligence Log")
    st.markdown("Line-by-line breakdown of the filtered dataset for auditing and specific query lookups.")
    
    # Selecting the most relevant columns for display so the table isn't overwhelmingly wide
    display_cols = [
        'Shop_Date', 'Departure_Date', 'Inbound_Date', 'LOS', 'Origin_Airport', 'Destination_Airport', 
        'Hotel', 'Star_Rating', 'Occupancy', 'Airline', 'EasyJet', 'Market_Lowest', 'Status', 
        'Variance_Percent', 'Price_Variance'
    ]
    st.dataframe(f_df[display_cols], use_container_width=True)
