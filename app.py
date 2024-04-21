from flask import Flask, render_template, request, jsonify
import pandas as pd
import folium
from folium import FeatureGroup, Marker, CircleMarker, LayerControl, Icon, Popup, PolyLine, Tooltip
from math import cos, sin, radians
import math
import csv
from flask import Flask
from flask_cors import CORS
import logging
import pycountry
from itertools import cycle, islice
import random
from branca.element import Element, Template
from folium.features import DivIcon

logging.basicConfig(level=logging.DEBUG)


app = Flask(__name__)
CORS(app)



with app.app_context():

    global countries_data
    countries_data = {country.alpha_2: country.name for country in pycountry.countries}


@app.route('/', methods=['GET'])
def index():
    return render_template('upload.html')  # HTML form for file upload

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['datafile']
    try:
        data = pd.read_csv(file)
        required_columns = {'Latitude', 'Longitude', 'Country', 'City'}

        if not required_columns.issubset(data.columns):
            return jsonify({'error': 'Missing one or more required columns: Latitude, Longitude, Country'}), 400

        facility_types = [col for col in data.columns if col not in required_columns]
        if not facility_types:
            return jsonify({'error': 'No facility types found'}), 400

        for col in facility_types:
            data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0)

        max_count = data[facility_types].max().max() if data[facility_types].max().max() > 0 else 1

        map_facilities = folium.Map(location=[20, 0], zoom_start=2, tiles='cartodbpositron')

        color_palette = [
            "#7F3CFF", "#00D1FF", "#2FF3E0", "#F65164", "#FFB30F",
            "#FFED00", "#37D67A", "#2CCCE4", "#dce775", "#ff8a65",
            "#ba68c8", "#ff7043", "#00acc1", "#ab47bc", "#26c6da",
            "#ec407a", "#7e57c2", "#26a69a", "#78909c", "#8d6e63"
        ]
        color_dict = {facility: color_palette[i % len(color_palette)] for i, facility in enumerate(facility_types)}

        radius_degrees = 1
        bubble_size = 10
        angle_increment = 360 / len(facility_types)

        for _, row in data.iterrows():
            base_location = [row['Latitude'], row['Longitude']]
            location_group = FeatureGroup(name=f"Show {row['City']}", show=True)
            country_name = row['Country'] 
            popup_texts = [f"<strong>{country_name}</strong>"]
            popup_texts.extend(
                [f"{facility_type}: {row[facility_type]}" for facility_type in facility_types if row[facility_type] > 0 and facility_type not in required_columns]
                )
            popup_content = "<br>".join(popup_texts)

            for i, facility_type in enumerate(facility_types):
                count = row[facility_type]
                if count > 0:
                    opacity = (count / max_count) * 10
                    angle = radians(i * angle_increment)
                    offset_latitude = base_location[0] + radius_degrees * sin(angle)
                    offset_longitude = base_location[1] + radius_degrees * cos(angle)
                    bubble_location = [offset_latitude, offset_longitude]
                    
                    tooltip = Tooltip(f"{facility_type}: {count}")
                    
                    CircleMarker(
                        location=bubble_location,
                        radius=bubble_size,
                        color=color_dict[facility_type],
                        weight=0,
                        fill=True,
                        fill_opacity=opacity,
                        fill_color=color_dict[facility_type],
                        tooltip=tooltip
                    ).add_to(location_group)

                    # Add a line from the bubble to the base location
                    line = PolyLine(locations=[base_location, bubble_location], weight=1, color=color_dict[facility_type])
                    line.add_to(map_facilities)

            location_group.add_to(map_facilities)
            Marker(
                location=base_location,
                icon=DivIcon(
                    icon_size=(15, 15),  # Size of the custom icon area
                    icon_anchor=(10, 10),  # Ensures the pin's point is anchored to the location
                    html=custom_icon_html,
                ),
                popup=Popup(popup_content, max_width=500)
            ).add_to(map_facilities)

        LayerControl().add_to(map_facilities)

        legend_html = '''
        <div style="position: absolute;
            bottom: 50px;
            left: 50px;
            width: 200px;
            min-height: 100px; 
            border: 1px solid #999999;
            z-index: 9999;
            font-size: 14px;
            background-color: rgba(255, 255, 255, 0.8);
            padding: 10px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.4);
            border-radius: 5px;
            overflow: auto;
            text-align: left;"> 
            <strong>Legend</strong><br/>
            '''.format(len(facility_types) * 25 + 30)  

        for facility in facility_types:
            if facility not in required_columns:  
                color = color_dict[facility]
                
                legend_html += '''
                <div style="display: flex; align-items: center; margin-bottom: 5px;">
                    <div style="height: 10px; width: 10px; background: {}; border-radius: 50%; margin-right: 5px;"></div>
                    <span style="margin-left: 5px;">{}</span>
                </div>
                '''.format(color, facility)

        legend_html += '</div>'


        map_facilities.get_root().html.add_child(folium.Element(legend_html))

        return map_facilities._repr_html_()
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
    
@app.route('/api/countries')
def get_countries():
    return jsonify(countries_data)

custom_icon_html = '''
<div style="position: absolute; top: -1.5rem; left: -0.75rem;">
    <svg 
        xmlns="http://www.w3.org/2000/svg" 
        width="25" 
        height="25" 
        viewBox="0 0 24 24" 
        fill="#0c5fc5" 
        stroke="#ffffff" 
        stroke-width="2" 
        stroke-linecap="round" 
        stroke-linejoin="round" 
        class="feather feather-map-pin">
        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
        <circle cx="12" cy="10" r="3"></circle>
    </svg>
</div>
'''

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=50000)
