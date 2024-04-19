from flask import Flask, render_template, request
import pandas as pd
import folium
from math import cos, sin, radians

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return render_template('upload.html')  # HTML form for file upload

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['datafile']
    data = pd.read_csv(file)
    # Use a cleaner tile layer for a more modern look
    map_facilities = folium.Map(location=[20, 0], zoom_start=2, tiles='cartodbpositron')

    # Define colors for each facility type
    color_dict = {
        "Headquarters": "red",
        "Offices": "blue",
        "Production Sites": "green",
        "R&I Centers": "purple"
    }

    # Function to add circle markers for each facility type
    for _, row in data.iterrows():
        location = [row['Latitude'], row['Longitude']]
        # Calculate the maximum bubble size based on the highest count of facilities
        max_count = max(row[facility_type] for facility_type in color_dict)
        # Define a minimum size for visibility at a zoomed-out scale
        min_size = 4000 * 5  # Adjust as needed
        index = 0  # Reset index for each row
        # Iterate over each facility type
        for facility_type, color in color_dict.items():
            count = row[facility_type]
            if count > 0:
                # Determine the radius of the circle
                radius = max(count / max_count * min_size, min_size)
                # Use the offset function to space out the bubbles
                offset_lat, offset_lon = offset_location(location[0], location[1], index, max_offset=len(color_dict))
                # Construct the popup and tooltip text
                popup_text = f"{row['Country']} - {facility_type}: {count}"
                tooltip_text = f"{row['Country']}<br>{facility_type}: {count}"
                # Create a CircleMarker with the count displayed inside
                folium.CircleMarker(
                    location=[offset_lat, offset_lon],
                    radius=radius / 1000,  # Adjusted for visual clarity
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.5,
                    popup=popup_text,
                    tooltip=tooltip_text  # Tooltip will show on hover
                ).add_to(map_facilities)
                index += 1

    return map_facilities._repr_html_()  # Render the map directly in the browser

def offset_location(lat, lon, index, max_offset):
    # Increase the offset multiplier to space out the bubbles more
    offset_multiplier = 0.5 * 5  # Adjusted to separate the bubbles 5 times further apart
    angle = index * (360 / max_offset)
    radius = index * offset_multiplier  # Scale for geographic coordinates
    new_lat = lat + radius * cos(radians(angle))
    new_lon = lon + radius * sin(radians(angle))
    return new_lat, new_lon

if __name__ == '__main__':
    app.run(debug=True)
