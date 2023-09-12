# Import necessary modules from the Flask library, the Python standard library, and other third-party libraries
from flask import Flask, request, jsonify
from collections import OrderedDict
from urllib.parse import quote

import logging
import json
import requests
import os


# Initialize the Flask application
app = Flask(__name__)

# Define a helper function to send a GET request to a given URL and return the JSON response
def get_api_response(url):
    # Send a GET request to the given URL
    response = requests.get(url)
    # Parse and return the JSON response
    return response.json()


# Define a new route for your application where you can access the get_directions function through a GET request
@app.route('/get_directions/', methods=['GET'])
def get_directions():
    # Get the origin, destination, and mode from the URL parameters
    origin = request.args.get('origin')
    destination = request.args.get('destination')
    mode = request.args.get('mode', default=None)

    # Create the API URL using the origin, destination, and mode parameters
    api_url = f'https://api.tfl.gov.uk/Journey/JourneyResults/{origin}/to/{destination}/?via={mode}&app_key=d7a5f797643d42d4baee9258a7b69b87'

    # Log the API URL for debugging purposes
    logging.info(f"API URL: {api_url}")

    # Get the response from the TfL API
    api_response = get_api_response(api_url)

    # Log the API response for debugging purposes
    logging.info(f"API Response: {api_response}")

    # Extract the ICS codes for the origin and destination locations from the API response
    origin_icsCode = [i['place']['icsCode'] for i in api_response['fromLocationDisambiguation']['disambiguationOptions'] if 'icsCode' in i['place']]
    dest_icsCode = [i['place']['icsCode'] for i in api_response['toLocationDisambiguation']['disambiguationOptions'] if 'icsCode' in i['place']]

    # Log the ICS codes for debugging purposes
    logging.info(f"Origin ICS Codes: {origin_icsCode}")
    logging.info(f"Destination ICS Codes: {dest_icsCode}")

    # Check if valid ICS codes were found for both origin and destination
    if origin_icsCode and dest_icsCode:
        # Take the first ICS code for both origin and destination as the best option
        best_origin = origin_icsCode[0]
        best_dest = dest_icsCode[0]
        
        # Create a new API URL using the best origin and destination ICS codes
        api_url = f'https://api.tfl.gov.uk/Journey/JourneyResults/{best_origin}/to/{best_dest}/?app_key=d7a5f797643d42d4baee9258a7b69b87'

        # Log the new API URL for debugging purposes
        logging.info(f"API URL 2: {api_url}")

        # Get the response from the TfL API using the new API URL
        api_response2 = get_api_response(api_url)
        # Extract the different route options from the API response
        route_options = api_response2['journeys']
        
        # Create a dictionary to store information about each route
        route_info = {}
        for index, route in enumerate(route_options):
            # Store details of each route including start time, arrival time, duration, and alternative routes
            route_info[index] = {
                'startBy': route['startDateTime'],
                'arrivedBy': route['arrivalDateTime'],
                'duration': route['duration'],
                'alternativeRoute': route['alternativeRoute'],
                'legs': []
            }
            
            # Loop through each leg of the route to store detailed information
            for leg in route['legs']:
                leg_info = {}
                # Store details such as destination, origin, summary of instructions, mode of transport, and a Google Maps link for the leg
                leg_info['destination'] = leg['arrivalPoint']['commonName']
                leg_info['_origin'] = leg['departurePoint']['commonName']
                leg_info['__Summary'] = leg['instruction']['summary']
                leg_info['mode'] = leg['mode']['name']
                leg_info['mps_link'] = f"https://www.google.com/maps/dir/?api=1&origin={quote(leg['departurePoint']['commonName'])}&destination={quote(leg['arrivalPoint']['commonName'])}&travelmode={leg['mode']['name']}"
                        
                # Add the leg information to the route information
                route_info[index]['legs'].append(leg_info)

        # Sort the routes based on the duration
        sorted_routes = sorted(route_info.values(), key=lambda x: x['duration'])

        # Create an ordered dictionary to store the sorted routes
        sorted_route_info = OrderedDict((f"route{index + 1}", route) for index, route in enumerate(sorted_routes))

        # Estimate the fares for each route using the estimate_fares function
        route_data_with_fares = estimate_fares(sorted_route_info, mode_cost_per_minute)

        # Get the route with the lowest fare using the get_lowest_fare_route function
        lowest_fare_route = get_lowest_fare_route(route_data_with_fares)

        # Return the lowest fare route as a JSON object
        return jsonify(lowest_fare_route)
    else:
        # If no valid ICS codes were found, return an error message as a JSON object
        return jsonify({'error': 'Try modifying the origin or destination'})


# Importing datetime module to work with date and time data
from datetime import datetime

# Defining a function to format timestamp strings to a more readable format
def format_timestamp(date_string):

    # Converting the ISO format date string to a datetime object
    date_object = datetime.fromisoformat(date_string)

    # Formatting the datetime object to a string with a user-friendly format
    info = date_object.strftime("%A, %B %d, %Y at %I:%M %p")    
    return info

# Function to find and return the route with the lowest fare
def get_lowest_fare_route(data):
    # Finding the route with the minimum estimated fare
    lowest_fare_route = min(data.values(), key=lambda x: x['estimated_fare'])
    # Formatting a status message to include start time and fare of the cheapest route
    _status = (f"The route with the lowest fare is route with start time {format_timestamp(lowest_fare_route['startBy'])} and fare £{lowest_fare_route['estimated_fare']}")
    # Returning the status message and details of the cheapest route as a dictionary
    return {'_status': _status, 'lowest_fare_route' : lowest_fare_route}

# Function to estimate the fares for each route based on the duration of each leg and the mode of transportation used
def estimate_fares(route_data, mode_cost_per_minute):
    # Looping over each route in the data
    for route_name, route_details in route_data.items():
        total_fare = 0
        # Looping over each leg of the route
        for leg in route_details["legs"]:
            mode = leg["mode"]
            # Calculating the duration of this leg based on the total duration of the route and the number of legs
            leg_duration = route_details["duration"] / len(route_details["legs"])
            # Calculating the fare for this leg based on the mode of transportation and the duration
            total_fare += leg_duration * mode_cost_per_minute.get(mode, 0)
        # Assigning the total estimated fare to this route
        route_details["estimated_fare"] = round(total_fare, 2)
    
    # Returning the data with the estimated fares
    return route_data

# Dictionary defining the hypothetical average cost per minute for each mode of transportation
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

# The entry point for the Flask application
if __name__ == '__main__':
    # Getting the port number from the environment variables, with a default of 5000
    port = int(os.environ.get('PORT', 5000))
    # Running the Flask application with debugging enabled and listening on all network interfaces
    app.run(debug=True, host='0.0.0.0', port=port)
