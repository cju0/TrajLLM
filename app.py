from flask import Flask, jsonify, render_template, request
import os
import json

app = Flask(__name__)

ROUTINE_DIR = './res/demo'  # adjust this path as needed

# Route for the homepage
@app.route('/')
def home():
    return render_template('index.html')  # Assuming index.html exists in the templates folder

@app.route('/start_day', methods=['POST'])
def start_day():
    agents_data = {}
    data = request.get_json()
    num_agents = data.get('numAgents', 10)  # Default to 10 if not provided

    # Load personas.json
    with open('./res/personas.json', 'r') as personas_file:
        personas = json.load(personas_file)

    # Get a sorted list of files in the directory
    routine_files = [f for f in os.listdir(ROUTINE_DIR) if f.endswith('.json')]

    # Limit num_agents to available data
    num_agents = min(num_agents, len(routine_files), len(personas))

    for i in range(num_agents):
        filename = routine_files[i]
        file_path = os.path.join(ROUTINE_DIR, filename)
        with open(file_path, 'r') as file:
            data = json.load(file)

        agent_id = str(i)
        # Get the corresponding persona
        persona = personas[i]

        activities = []
        for entry in data:
            activity = {
                "activityType": entry[0],
                "locationType": entry[1],
                "startTime": entry[2][0],
                "endTime": entry[2][1],
                "locationId": entry[3],
                "lat": entry[4][0],
                "lng": entry[4][1]
            }
            activities.append(activity)

        # Include persona data
        agents_data[agent_id] = {
            "activities": activities,
            "name": persona.get('name', ''),
            "age": persona.get('age', ''),
            "gender": persona.get('gender', ''),
            "occupation": persona.get('occupation', '')
        }

    return jsonify({"agents": agents_data})




if __name__ == '__main__':
    app.run(debug=True)