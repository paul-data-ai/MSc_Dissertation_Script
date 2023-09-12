from flask import Flask, request, jsonify
import requests
import os
from collections import OrderedDict

app = Flask(__name__)


def get_api_response(url):
    response = requests.get(url)
    return response.json()


import logging
from urllib.parse import quote
import json
# import pandas as pd


@app.route('/get_directions/', methods=['GET'])
def get_directions():
    origin = request.args.get('origin')
    destination = request.args.get('destination')
    mode = request.args.get('mode', default=None)

    api_url = f'https://api.tfl.gov.uk/Journey/JourneyResults/{origin}/to/{destination}/?via={mode}&app_key=d7a5f797643d42d4baee9258a7b69b87'

    logging.info(f"API URL: {api_url}")

    api_response = get_api_response(api_url)

    logging.info(f"API Response: {api_response}")

    origin_icsCode = [i['place']['icsCode'] for i in api_response['fromLocationDisambiguation']['disambiguationOptions'] if 'icsCode' in i['place']]
    dest_icsCode = [i['place']['icsCode'] for i in api_response['toLocationDisambiguation']['disambiguationOptions'] if 'icsCode' in i['place']]

    logging.info(f"Origin ICS Codes: {origin_icsCode}")
    logging.info(f"Destination ICS Codes: {dest_icsCode}")

    if origin_icsCode and dest_icsCode:
        best_origin = origin_icsCode[0]
        best_dest = dest_icsCode[0]
        
        api_url = f'https://api.tfl.gov.uk/Journey/JourneyResults/{best_origin}/to/{best_dest}/?app_key=d7a5f797643d42d4baee9258a7b69b87'

        logging.info(f"API URL 2: {api_url}")
        
        api_response2 = get_api_response(api_url)
        route_options = api_response2['journeys']
        
        route_info = {}
        for index, route in enumerate(route_options):
            route_info[index] = {
                'startBy': route['startDateTime'],
                'arrivedBy': route['arrivalDateTime'],
                'duration': route['duration'],
                'alternativeRoute': route['alternativeRoute'],
                'legs': []
            }
            
            for leg in route['legs']:
                # leg_info = OrderedDict()
                leg_info = {}
                leg_info['destination'] = leg['arrivalPoint']['commonName']
                leg_info['_origin'] = leg['departurePoint']['commonName']
                leg_info['__Summary'] = leg['instruction']['summary']
                leg_info['mode'] = leg['mode']['name']
                leg_info['mps_link'] = f"https://www.google.com/maps/dir/?api=1&origin={quote(leg['departurePoint']['commonName'])}&destination={quote(leg['arrivalPoint']['commonName'])}&travelmode={leg['mode']['name']}"
                        
                route_info[index]['legs'].append(leg_info)

        sorted_routes = sorted(route_info.values(), key=lambda x: x['duration'])

        sorted_route_info = OrderedDict((f"route{index + 1}", route) for index, route in enumerate(sorted_routes))

        route_data_with_fares = estimate_fares(sorted_route_info, mode_cost_per_minute)

        lowest_fare_route = get_lowest_fare_route(route_data_with_fares)

        return jsonify(lowest_fare_route)
    else:
        return jsonify({'error': 'Try modifying the origin or destination'})



from datetime import datetime
def format_timestamp(date_string):

    # Parse the string to a datetime object
    date_object = datetime.fromisoformat(date_string)

    # Format the datetime object to a more user-friendly string
    info = date_object.strftime("%A, %B %d, %Y at %I:%M %p")    
    return info


def get_lowest_fare_route(data):
    lowest_fare_route = min(data.values(), key=lambda x: x['estimated_fare'])
    _status = (f"The route with the lowest fare is route with start time {format_timestamp(lowest_fare_route['startBy'])} and fare £{lowest_fare_route['estimated_fare']}")
    return {'_status': _status, 'lowest_fare_route' : lowest_fare_route}

def estimate_fares(route_data, mode_cost_per_minute):
    for route_name, route_details in route_data.items():
        total_fare = 0
        for leg in route_details["legs"]:
            mode = leg["mode"]
            # Assuming each leg's duration can be calculated based on start and end times of the route
            leg_duration = route_details["duration"] / len(route_details["legs"])
            
            # Calculate fare for this leg based on the mode
            # If the mode is walking, the cost is zero
            total_fare += leg_duration * mode_cost_per_minute.get(mode, 0)
        
        # Add total fare to route details
        route_details["estimated_fare"] = round(total_fare, 2)
    
    return route_data


# Defining an hypothetical average cost per minute for each mode
mode_cost_per_minute = {
    "bus": 0.15,  
    "overground": 0.20,  
    "tube": 0.25,  
    "dlr": 0.20, 
    "tram": 0.15,  
    "tflrail": 0.20, 
    "river": 0.50, 
    "walking": 0.00,  
    "cycling": 0.05, 
    "taxi": 0.60
}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
