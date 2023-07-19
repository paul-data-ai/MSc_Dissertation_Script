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


@app.route('/ask_and_get/', methods=['GET'])
def ask_and_get():
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
        
        # route_info = {}
        # for index, route in enumerate(route_options):
        #     key = f"route{index + 1}" 
        #     route_info[key] = {
        #         'startDateTime': route['startDateTime'],
        #         'arrivalDateTime': route['arrivalDateTime'],
        #         'est. duration': route['duration'],
        #         'alternativeRoute': route['alternativeRoute'],
        #         'legs': []
        #     }
            
        #     for leg in route['legs']:
        #         leg_info = {
        #             'Origin': leg['departurePoint']['commonName'],
        #             'Destination': leg['arrivalPoint']['commonName'],
        #             'Summary': leg['instruction']['summary'],
        #             'mode': leg['mode']['name'],
        #             'google_maps_link': f"https://www.google.com/maps/dir/?api=1&origin=?{quote(leg['departurePoint']['commonName'])}&destination={quote(leg['arrivalPoint']['commonName'])}&travelmode={leg['mode']['name']}"
        #         }
                
        #         route_info[key]['legs'].append(leg_info)

        # sorted_routes = sorted(route_info.values(), key=lambda x: x['est. duration'])

        # sorted_route_info = {f"route{index + 1}": route for index, route in enumerate(sorted_routes)}
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
                leg_info = OrderedDict()
                leg_info['destination'] = leg['arrivalPoint']['commonName']
                leg_info['_origin'] = leg['departurePoint']['commonName']
                leg_info['__Summary'] = leg['instruction']['summary']
                leg_info['mode'] = leg['mode']['name']
                leg_info['mps_link'] = f"https://www.google.com/maps/dir/?api=1&origin={quote(leg['departurePoint']['commonName'])}&destination={quote(leg['arrivalPoint']['commonName'])}&travelmode={leg['mode']['name']}"
                        
                route_info[index]['legs'].append(leg_info)

        sorted_routes = sorted(route_info.values(), key=lambda x: x['duration'])
        sorted_route_info = OrderedDict((f"route{index + 1}", route) for index, route in enumerate(sorted_routes))

        # json_response = json.dumps(sorted_route_info, indent=4, sort_keys=True)

        # print (route_info.keys())
        return jsonify(sorted_route_info)
    else:
        return jsonify({'error': 'Try modifying the origin or destination'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
