import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from natsort import index_natsorted


# Set page configuration to wide layout
st.set_page_config(layout="wide")

# Load the dataset
@st.cache_data
def load_data():
    return pd.read_csv('hotel_booking.csv')

hotel_booking_df = load_data()

# Replace NaN values with 0 for numeric columns
hotel_booking_df.fillna(0, inplace=True)

# Filter out anomalies
hotel_booking_df = hotel_booking_df[
    ~((hotel_booking_df['adults'] == 0) & (hotel_booking_df['children'] == 0) & (hotel_booking_df['babies'] == 0)) &
    ((hotel_booking_df['adults'] + hotel_booking_df['children'] + hotel_booking_df['babies']) <= 12) &
    (hotel_booking_df['children'] <= 5) &
    (hotel_booking_df['babies'] <= 5) &
    (hotel_booking_df['adults'] <= 6) &
    (hotel_booking_df['adr'] <= 500) &
    (hotel_booking_df['adr'] >= 0)  
]

hotel_booking_df['children'] = hotel_booking_df['children'].apply(lambda x: int(x)) 
# Function to map months to seasons
def get_season(month):
    if month in ['December', 'January', 'February']:
        return 'Winter'
    elif month in ['March', 'April', 'May']:
        return 'Spring'
    elif month in ['June', 'July', 'August']:
        return 'Summer'
    else:
        return 'Fall'

# Add a season column to the dataframe
hotel_booking_df['season'] = hotel_booking_df['arrival_date_month'].apply(get_season)
month_order = ['December','January', 'February'][::-1] + ['March', 'April', 'May'][::-1]+ ['June',
               'July', 'August'][::-1] + ['September', 'October', 'November'][::-1]
season_order = ['Winter', 'Fall', 'Summer', 'Spring'] 

hotel_booking_df['arrival_date_month'] = pd.Categorical(hotel_booking_df['arrival_date_month'], categories=month_order, ordered=True)

# Sidebar filters
st.sidebar.header('Filter Options')
selected_season = st.sidebar.selectbox('Select Season', options=['All'] + list(hotel_booking_df['season'].unique()))
selected_month = st.sidebar.multiselect('Select Month', options=month_order, default=month_order)
selected_adults = st.sidebar.multiselect('Select Number of Adults', options=hotel_booking_df['adults'].unique(), default=hotel_booking_df['adults'].unique())
selected_children = st.sidebar.multiselect('Select Number of Children', options=hotel_booking_df['children'].unique(), default=hotel_booking_df['children'].unique())
selected_babies = st.sidebar.multiselect('Select Number of Babies', options=hotel_booking_df['babies'].unique(), default=hotel_booking_df['babies'].unique())
price_range = st.sidebar.slider('Select Price Range (ADR)', min_value=int(hotel_booking_df['adr'].min()), max_value=int(hotel_booking_df['adr'].max()), value=(int(hotel_booking_df['adr'].min()), int(hotel_booking_df['adr'].max())))

# Apply filters
filtered_data = hotel_booking_df[
    ((hotel_booking_df['season'] == selected_season) if selected_season != 'All' else True) &
    (hotel_booking_df['arrival_date_month'].isin(selected_month)) &
    (hotel_booking_df['adults'].isin(selected_adults)) &
    (hotel_booking_df['children'].isin(selected_children)) &
    (hotel_booking_df['babies'].isin(selected_babies)) &
    (hotel_booking_df['adr'] >= price_range[0]) & (hotel_booking_df['adr'] <= price_range[1])
]

# Data preprocessing to get country statistics and filter out countries with less than 10 bookings
country_stats = filtered_data.groupby('country').agg(
    total_bookings=('is_canceled', 'count'),
    total_cancellations=('is_canceled', 'sum')
).reset_index()
country_stats['cancellation_rate'] = country_stats['total_cancellations'] / country_stats['total_bookings']
country_stats = country_stats[country_stats['total_bookings'] >= 10]

# Prepare data for the month and season histogram
grouped_data_month_season = filtered_data.groupby(['arrival_date_month', 'season']).agg(
    total_bookings=('is_canceled', 'count'),
    total_cancellations=('is_canceled', 'sum')
).reset_index()
grouped_data_month_season['cancellation_rate'] = grouped_data_month_season['total_cancellations'] / grouped_data_month_season['total_bookings']

# Prepare data for the ADR histogram
filtered_data['adr'] =filtered_data['adr'].apply(lambda x: int(x))
adr_bins = pd.cut(filtered_data['adr'], bins=np.arange(0, filtered_data['adr'].max() + 30, 30))
filtered_data['adr_bins'] = adr_bins
price_stats = filtered_data.groupby('adr_bins').agg(
    total_bookings=('is_canceled', 'count'),
    total_cancellations=('is_canceled', 'sum')
).reset_index()
price_stats['cancellation_rate'] = price_stats['total_cancellations'] / price_stats['total_bookings']

# Ensure bins are ordered by range minimum
price_stats['adr_bins'] = price_stats['adr_bins'].astype(str)
price_stats['range_min'] = price_stats['adr_bins'].apply(lambda x: float(x.split(',')[0][1:]))
price_stats = price_stats.sort_values(by='range_min')


# Prepare data for the 3D scatter plot
grouped_data_3d = filtered_data.groupby(['adults', 'children', 'babies']).agg(
    total_bookings=('is_canceled', 'count'),
    total_cancellations=('is_canceled', 'sum')
).reset_index()
grouped_data_3d['cancellation_rate'] = grouped_data_3d['total_cancellations'] / grouped_data_3d['total_bookings']
grouped_data_3d = grouped_data_3d[grouped_data_3d['total_bookings'] >= 10]

# Create columns for layout with custom widths
col1,col2 = st.columns([2, 2])

# with con:
#     st.title("Cancellation rate accross all filters")
#     fig = px.pie(
#     cancellation_data,
#     names='status',
#     values='count',
#     color='status',
#     color_discrete_sequence=px.colors.sequential.Blues_r,
# )
# st.plotly_chart(fig, use_container_width=True, height = 700)

# Display the map in the first column
with col1:
    st.title("Cancellation by Country")
    fig = px.choropleth(
        country_stats,
        locations="country",
        locationmode='ISO-3',
        color="cancellation_rate",
        hover_name="country",
        hover_data={
            "country": True,
            "total_bookings": True,
            "total_cancellations": True,
            "cancellation_rate": ':.2f'
        },
        color_continuous_scale=px.colors.sequential.Blues,  # Blue color scale
        labels={'cancellation_rate': 'Cancellation Rate'}
    )
    fig.update_geos(showcoastlines=True, coastlinecolor="Black", showland=True, landcolor="White")
    st.plotly_chart(fig, use_container_width=True, height=700)

# Display the 3D plot in the second column
#with col2:
    # st.title("Cancellation by Composition")
    # fig = px.scatter_3d(
    #     grouped_data_3d,
    #     x='adults',
    #     y='children',
    #     z='babies',
    #     color='cancellation_rate',
    #     size_max=100,  # Set a larger maximum size for the dots
    #     color_continuous_scale=px.colors.sequential.Blues,  # Blue color scale
    #     hover_name='total_bookings',
    #     labels={
    #         'adults': 'Adults',
    #         'children': 'Children',
    #         'babies': 'Babies',
    #         'total_bookings': 'Total Bookings',
    #         'cancellation_rate': 'Cancellation Rate',
    #     }
    # )
    # fig.update_layout(
    #     scene=dict(
    #         xaxis=dict(
    #             tickmode='linear',
    #             tick0=0,
    #             dtick=1,
    #             title='Adults'
    #         ),
    #         yaxis=dict(
    #             tickmode='linear',
    #             tick0=0,
    #             dtick=1,
    #             title='Children'
    #         ),
    #         zaxis=dict(
    #             tickmode='linear',
    #             tick0=0,
    #             dtick=1,
    #             title='Babies'
    #         ),
    #     )
    # )
    # fig.update_traces(marker=dict(line=dict(width=2, color='DarkSlateGrey')))
    # st.plotly_chart(fig, use_container_width=True, height=700)

# Create columns for the second row of visualizations with custom widths
col3, col4 = st.columns([2, 2])

# Display the histogram by Month and Season in the third column
# with col3:


# Display the histogram by ADR in the fourth column
with col4:
    st.title("Cancellation by Price")
    fig = px.bar(
        price_stats,
        x='adr_bins',
        y='cancellation_rate',
        color='cancellation_rate',  # Correlate color with cancellation rate
        color_continuous_scale=px.colors.sequential.Blues,  # Darker blue color scale
        labels={
            'adr_bins': 'Average Daily Rate',
            'cancellation_rate': 'Average Cancellation Rate'
        },
        title="Average Cancellation Rate by ADR",
    )
    st.plotly_chart(fig, use_container_width=True, height=700)

# Prepare data for the month and season pie chart
grouped_data_month_season = filtered_data.groupby(['arrival_date_month', 'season']).agg(
    total_bookings=('is_canceled', 'count'),
    total_cancellations=('is_canceled', 'sum')
).reset_index()

# Filter out rows where total bookings are zero before calculating the cancellation rate
grouped_data_month_season = grouped_data_month_season[grouped_data_month_season['total_bookings'] > 0]

# Calculate the cancellation rate
grouped_data_month_season['cancellation_rate'] = grouped_data_month_season['total_cancellations'] / grouped_data_month_season['total_bookings']

# Define the month and season order
month_order = ['December', 'January', 'February'][::-1] + ['March', 'April', 'May'][::-1] + ['June', 'July', 'August'][::-1] + ['September', 'October', 'November'][::-1]
season_order = ['Winter', 'Fall', 'Summer', 'Spring']
grouped_data_month_season['arrival_date_month'] = pd.Categorical(grouped_data_month_season['arrival_date_month'], categories=month_order, ordered=True)
grouped_data_month_season['season'] = pd.Categorical(grouped_data_month_season['season'], categories=season_order, ordered=True)

# Sort the data
grouped_data_month_season = grouped_data_month_season.sort_values(by=['season', 'arrival_date_month'])


# Display the pie chart by Month and Season in the third column
with col3:
    try:
        st.title("Cancellation by Season")
        fig = px.sunburst(
            grouped_data_month_season,
            path=['season', 'arrival_date_month'],
            #values='total_bookings',
            color='cancellation_rate',
            color_continuous_scale=px.colors.sequential.Blues,  #blue color scale
            labels={
                'arrival_date_month': 'Month',
                'cancellation_rate': 'Cancellation Rate',
                'season': 'Season'
            },
            title="Hotel Bookings by Month and Season",
        )
        fig.update_layout(margin=dict(t=0, l=0, r=0, b=0))
        fig.update_traces(sort=False)
        st.plotly_chart(fig, use_container_width=True, height=700)
    
    except:

        # st.title("Cancellation by Month")
        fig = px.histogram(
            grouped_data_month_season,
            x='arrival_date_month',
            y='cancellation_rate',
            color='cancellation_rate',
            color_discrete_sequence=px.colors.sequential.Blues_r,  # Darker blue color scale
            #barmode='group',
            labels={
                'arrival_date_month': 'Month',
                'cancellation_rate': 'Cancellation Rate',
                'season': 'Season'
            },
            title="Hotel Bookings by Month and Season",
        )
        #fig.update_coloraxes(fig.update_coloraxes(showscale = False))
        st.plotly_chart(fig, use_container_width=True, height=700)
# Calculate overall cancellation rate
total_bookings = filtered_data['is_canceled'].count()
total_cancellations = filtered_data['is_canceled'].sum()
cancellation_rate = (total_cancellations / total_bookings) * 100 if total_bookings > 0 else 0

# Display the overall cancellation rate with a progress bar
st.markdown(f"### Overall Cancellation Rate: {cancellation_rate:.2f}%")
progress_bar = st.progress(0)
progress_bar.progress(int(cancellation_rate))        

grouped_data_heatmap = filtered_data.groupby(['adults', 'children', 'babies']).agg(
    total_bookings=('is_canceled', 'count'),
    total_cancellations=('is_canceled', 'sum')
    ).reset_index()
grouped_data_heatmap['cancellation_rate'] = grouped_data_heatmap['total_cancellations'] / grouped_data_heatmap['total_bookings']
#grouped_data_heatmap['adults'] = pd.Categorical(grouped_data_heatmap['adults'], categories=sorted(grouped_data_heatmap['adults'].unique()), ordered=True)
#grouped_data_heatmap['children'] = pd.Categorical(grouped_data_heatmap['children'], categories=sorted(grouped_data_heatmap['children'].unique()), ordered=True)

#col5,col6 = st.columns([2, 2])
with col2:
    st.title('Cancellation Rate by Vacationeer Composition')
    fig = px.density_heatmap(
    grouped_data_heatmap,
    x='adults',
    y='children',
    z='cancellation_rate',
    facet_col='babies',
    color_continuous_scale=px.colors.sequential.Blues,
    labels={'adults': 'Number of Adults', 'children': 'Number of Children', 'cancellation_rate': 'Average Cancellation Rate', 'Total Bookings':'total_bookings'},
    #title='Heatmaps of Average Cancellation Rate by Number of Adults and Children, Faceted by Number of Babies'
    )
    fig.update_xaxes(type='category')
    fig.update_yaxes(tickvals=list(range(len(grouped_data_heatmap['children'].unique()))))
    fig.update_layout(margin=dict(t=40, l=0, r=0, b=40))
    st.plotly_chart(fig, use_container_width=True, height=700)
