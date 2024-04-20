from flask import Flask, render_template, request, jsonify
import pandas as pd
import folium
from math import cos, sin, radians
import math
import csv
from flask import Flask
from flask_cors import CORS
import logging
import pycountry

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
CORS(app)
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

def extract_countries(cities_list):
    country_dict = {}
    for entry in cities_list:
        country_code = entry['country_code']
        app.logger.debug(country_code)
        country = pycountry.countries.get(alpha_2=country_code)
        if country:
            country_name = country.name
            app.logger.debug(country_name)
            if country_code not in country_dict:
                country_dict[country_code] = country_name
    return country_dict

def load_city_data(file_path):
    cities_list = []
    with open(file_path, 'r', encoding='utf-8') as file:
        reader = csv.reader(file, delimiter='\t')
        for row in reader:
            if row:
                try:
                    city_entry = {
                        'name': row[1],
                        'lat': float(row[4]),
                        'lng': float(row[5]),
                        'country_code': row[8]
                    }
                    cities_list.append(city_entry)
                except (IndexError, ValueError) as e:
                    print(f"Data conversion error {e} in row: {row}")
    return cities_list

# When loading the data, replace the dictionary with a list:
city_data = load_city_data('static/cities500.txt')


@app.route('/api/city/<city_name>')
def get_city_info(city_name):
    matching_cities = [city for city in city_data if city['name'].lower() == city_name.lower()]
    if matching_cities:
        return jsonify(matching_cities)
    else:
        return jsonify({'error': 'City not found'}), 404
        
@app.route('/api/cities/country/<country_code>')
def get_cities_by_country(country_code):
    per_page = request.args.get('per_page', default=20, type=int)
    page = request.args.get('page', default=1, type=int)
    
    # Filter cities by country code
    filtered_cities = [city for city in city_data if city['country_code'].lower() == country_code.lower()]
    sorted_cities = sorted(filtered_cities, key=lambda x: x['name'])
    total = len(sorted_cities)
    total_pages = math.ceil(total / per_page)

    start = (page - 1) * per_page
    end = start + per_page
    result = sorted_cities[start:end]

    return jsonify({'cities': result, 'total_pages': total_pages, 'current_page': page})


@app.route('/cities')
def cities():
    return render_template('cities.html')

@app.route('/api/countries')
def get_countries():
    country_dict = extract_countries(city_data)  # Use the loaded city data
    app.logger.debug(country_dict)
    return jsonify(country_dict)

@app.route('/api/cities')
def api_cities():
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=50, type=int)  # Adjust default as needed
    start = (page - 1) * per_page
    end = start + per_page
    cities_list = [dict(name=k, **v) for k, v in list(city_data.items())[start:end]]
    return jsonify(cities_list)

@app.route('/api/coordinates')
def get_coordinates():
    city_name = request.args.get('city', default=None, type=str)
    if city_name and city_name.lower() in city_data:
        city_info = city_data[city_name.lower()]
        return jsonify({'lat': city_info['lat'], 'lng': city_info['lng']})
    else:
        return jsonify({'error': 'City not found'}), 404


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=50000)
