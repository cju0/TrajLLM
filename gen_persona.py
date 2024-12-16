import argparse
import pandas as pd
import numpy as np
import json
import random

from helper.utils import llama_generate, gpt_generate, random_in_quad
from helper.prompt import person_info_prompt, daily_activity_prompt, persona_prompt

occupation = ["Agriculture and forestry", "Fisheries", "Mining and quarrying of stone and gravel", "Construction", 
    "Manufacturing", "Electricity, gas, heat supply and water", "Information and communications", "Transport and postal activities", 
    "Wholesale and retail trade", "Finance and insurance", "Real estate and goods rental and leasing", "Scientific research, professional and technical services", 
    "Accommodations, eating and drinking services", "Living-related and personal services and amusement services", "Education, learning support", 
    "Medical, health care and welfare", "Compound services", "Services, N.E.C.", "Government, except elsewhere classified", "Other industries", 
    "student", "unemployed", "retiree"]

act_loc = {
    "work": ["Workplace"],
    "go home": ["Home"],
    "meal": ["Home", "Restaurant", "Cafe", "Pub and Bar", "Casual Dining"],
    "sleep": ["Home", "Hotel"],
    "shopping": ["Grocery", "Other Shopping"],
    "sports and exercise": ["Gym", "Field", "Outdoors"],
    "leisure activities": ["Home", "Art and Performance", "Entertainment", "Pub and Bar", "Outdoors", "Stadium", "Museum", 
        "Library", "Drink and Dessert Shop", "Social Event"],
    "education": ["College and University", "Vocational Training", "Primary and Secondary School", "Preschool"],
    "religious activities": ["Church", "Shrine", "Temple", "Synagogue", "Spiritual Center", "Mosque"],
    "trifles": ["Legal and Financial Service", "Automotive Service", "Health and Beauty Service", "Medical Service", "Other Service"],
}

def gen_random_trait(mean, std):
    return np.random.normal(loc=mean, scale=std)

def gen_random_personality(data):
    personality = {}

    for key, val in data.items():
        personality[key] = gen_random_trait(val[0], val[1])

    return personality

def gen_random_home_SYD(hdata: list[list[list[float]]]):
    c1, c2, c3, c4 = random.choice(hdata)
    return random_in_quad(c1, c2, c3, c4)

def gen_random_school_SYD(csv, school: str):
    if (school != 'Other education'):
        schools = csv[csv['Category'] == school]
    else:
        return ['undefined']

    return gen_random_place_SYD(schools)

def gen_random_place_SYD(csv):
    # Need to be changed tocreasonable workplace
    ran_p = csv.sample(n=1)
    return [ran_p['Latitude'].values[0], ran_p['Longitute'].values[0]]

def gen_random_school_TKY(school: str):
    data = open('POI_data/{}_ca_poi.csv'.format(school)) 
    schools = pd.read_csv(data)

    return gen_random_place_TKY(schools)

def gen_random_workplace_TKY(occ: str):
    if occ == 'student':
        data = open('POI_data/Workplace/Wholesale and retail trade_ca_poi.csv') 
    else:
        data = open('POI_data/Workplace/{}_ca_poi.csv'.format(occ)) 
    
    workplaces = pd.read_csv(data)
    return gen_random_place_TKY(workplaces)

def gen_random_place_TKY(csv):
    ran_p = csv.sample(n=1)
    return [ran_p['lat'].values[0], ran_p['lng'].values[0]]

def cleanup_persona_data(personas: list[dict[str, str]]):
    '''Ensure all generated personas are reasonable.'''
    res = []
    for p in personas:
        if p['occupation'] in occupation:
            res.append(p)
            continue

        persona = p.copy()
        found = False

        for occ in occupation:
            if p['occupation'].lower() == occ.lower() or (p['occupation'].lower() in occ.lower() and len(p['occupation']) >= 4):
                persona['occupation'] = occ
                found = True
                break

        if not found:
            persona['occupation'] = 'unemployed'
        
        res.append(persona)

    return res

def find_proper_school(age):
    '''Find proper education institution for the persona.'''
    if age < 6:
        return "Preschool"
    elif age < 19:
        return "Primary and Secondary School"
    else:
        return random.choice(["Vocational Training","College and University"])

def cleanup_activity_data(personas, activities):
    '''Ensure all activities in the list are reasonable.'''
    res = []
    for i in range(len(activities)):
        std_act = {}
        for act_key, act_val in activities[i].items():
            matched_key = None
            for loc_key in act_loc.keys():
                if act_key.lower() == loc_key.lower() or (act_key.lower() in loc_key.lower() and len(act_key) >= 4):
                    matched_key = loc_key
                    break

            if not matched_key:
                continue

            potential_loc = act_val[1]
            if (matched_key == 'religious activities' or matched_key == 'education') and len(potential_loc) > 1:
                if matched_key == 'religious activities':
                    potential_loc = [random.choice(potential_loc)]
                else:
                    potential_loc = [find_proper_school(int(personas[i]['age']))]

            elif matched_key == 'work' and (personas[i]['occupation'] == 'unemployed' or personas[i]['occupation'] == 'retiree' or int(personas[i]['age']) < 15):
                continue
            elif not potential_loc:
                continue

            std_loc = []
            for location in potential_loc:
                matched_location = None
                for loc_list in act_loc[matched_key]:
                    if location.lower() == loc_list.lower() or (location.lower() in loc_list.lower() and len(location) >= 4):
                        matched_location = loc_list
                        break

                if matched_location:
                    std_loc.append(matched_location)
                else:    
                    std_loc.append(random.choice(act_loc[matched_key]))

            if std_loc:
                std_act[matched_key] = [act_val[0], std_loc]
        
        # Check for student:
        if personas[i]['occupation'] == 'student' and 'education' not in std_act:
            std_act['education'] = find_proper_school(int(personas[i]['age']))
        
        if 'sleep' not in std_act:
            std_act['sleep'] = random.choice(["Home", "Hotel"])
        
        if 'meal' not in std_act:
            num_items = random.choice([1, 2, 3, 4, 5])
            std_act['meal'] = random.choice(["Home", "Restaurant", "Cafe", "Pub and Bar", "Casual Dining"], num_items)

        if std_act:
            res.append(std_act)

    return res 

def gen_daily_activities(llm, data, loc):
    '''Generate daily activity list.'''
    daily_act = []
    count = 0
    for p in data:
        count += 1
        print("=== Activity Generation Round {} ===".format(count))
        global_context = person_info_prompt(loc, p["name"], p["age"], p["gender"], p["occupation"], p["personality"]["ext"], p["personality"]["agr"], p["personality"]["con"], p["personality"]["neu"], p["personality"]["ope"])
        msg = daily_activity_prompt(act_loc, args.location)

        while True:
            if llm == 'llama':
                print("--- llama ---")
                res = llama_generate(global_context, msg)
            else:
                print("--- gpt ---")
                res = gpt_generate(global_context, msg)
                res = res.replace("```json", "").replace("```", "").strip()

            try:
                parsed_json = json.loads(res)
                break
            except json.JSONDecodeError:
                print("Invalid JSON received, retrying...")
        
        print(parsed_json)
        daily_act.append(parsed_json)
    
    return cleanup_activity_data(data, daily_act)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='genPersona')
    parser.add_argument('-n', '--number', type=int, default=1, help="Amount of personas to generate (1 for 5)")
    parser.add_argument('--location', choices=['Sydney', 'Tokyo'], default='Tokyo', 
        help="Choose location: either 'Sydney' or 'Tokyo'", type=str)
    parser.add_argument('-a', '--activity', action='store_true', help="Only generate activity list for existing personas")
    parser.add_argument('-p', '--persona', action='store_true', help="Only generate personas")
    parser.add_argument('-u', '--p_update', action='store_true', help="Only update loc info for existing personas")
    parser.add_argument('-l', "--llm", choices=['llama', 'gpt'], default='gpt',
        help="Specify the model type to use: llama or gpt", type=str)

    args = parser.parse_args()

    if (args.location == 'Sydney'):
        f_path = 'data/SYD'
    else:
        f_path = 'data/TKY'

    if not args.activity and not args.p_update:
        f1 = open("{}/population.json".format(f_path))
        data = json.load(f1)

        occ_data = data['occupation']
        fields = list(occ_data.keys())
        weights = list(occ_data.values())

        msg = persona_prompt(args.location, data)

        ans_format = """Important: Output has to be a list of dictionary, where each dictionary has keys 'name', 'age', 'gender' and 'occupation'.
Output format: 
[{name, age, gender, occupation}, {...}, ...].
"""

#     example = """Example output 1:
# [{"name": "Ethan Grayson", "age": 33, "gender": "male", "occupation": "fisherman"}, {"name": "Olivia Lee", "age": 3, "gender": "female", "occupation": "unemployed"}, \
# {"name": "Mia Harris", "age": 69, "gender": "female", "occupation": "retiree"}, {"name": "Thomas Turner", "age": 41, "gender": "male", "occupation": "YouTuber"}, {"name": "Li Wei", "age": 26, "gender": "female", "occupation": "electrical engineer"}]
# Example output 2:
# [{"name": "Jake Evans", "age": 17, "gender": "male", "occupation": "student"}, {"name": "Yuki Tanaka", "age": 31, "gender": "female", "occupation": "dentist"}, \
# {"name": "Lily O'Connor", "age": 59, "gender": "female", "occupation": "traffic controller"}, {"name": "Maxwell Rivera", "age": 36, "gender": "male", "occupation": "retail assistant"}, {"name": "Ella Winter", "age": 28, "gender": "female", "occupation": "research assistant"}]
# """

        context = "You are a json generator who always responds required data in json format, but without any additional introduction, text or explanation. You output format has to be a list of dictionary."

        print("======== Start! ========")
        personas = []
        for i in range(args.number):
            # Pick 5 potential jobs for selection
            potential_jobs = random.choices(fields, weights=weights, k=5)
            final_msg = msg + \
            "4. If the persona is employed, please pick one of the industry division from {}, and then assign the 'occupation' attribute of the persona \
to be the picked industry division. e.g. {{\"name\": Hikaru Satou, \"age\": 29, \"gender\": female, \"occupation\": \"Manufacturing\"}} \n\
The occupation can only be assigned to one of the element in this industry division list, don't create a specific job for it. \n".format(potential_jobs) + \
            "5. When generating personas, don't have to always include student, retiree or unemployed people. \
Generate persona based on the distribution of population, and the age and sex of the persona." + ans_format

            print("=== Round {}: Waiting for LLAMA ===".format(i+1))

            while True:
                if args.llm == 'llama':
                    print("--- llama ---")
                    res = llama_generate(context, final_msg)
                else:
                    print("--- gpt ---")
                    res = gpt_generate(context, final_msg)
                    res = res.replace("```json", "").replace("```", "").strip()

                try:
                    print("Persona iteration {}:\nOutput: {}".format(i, res))
                    res = json.loads(res)
                    break
                except json.JSONDecodeError:
                    print("Invalid JSON received, retrying...")

            personas.extend(cleanup_persona_data(res))
            print("=== Next Round ===")

        # Finialise personality
        big5 = open("{}/big5.json".format(f_path))
        big5_data = json.load(big5)
        for p in personas:
            p["personality"] = gen_random_personality(big5_data)

        with open('res/personas.json','w+') as f3:
            json.dump(personas, f3)
    else:
        print("=== Load Existing Personas ===")
        f = open("res/personas.json", 'r')
        personas = json.load(f)

    if not args.persona and not args.p_update:
        # Generate act-loc list for each persona
        daily_act = gen_daily_activities(args.llm, personas, args.location)
        with open('res/activities.json','w+') as f2:
            json.dump(daily_act, f2)
    elif not args.persona:
        print("=== Load Existing Act Lists ===")
        f = open("res/activities.json", 'r')
        daily_act = json.load(f)

    if not args.persona:
        print("=== Completing Personas & Activity ===")
        if (args.location == 'Sydney'):
            csv = pd.read_csv('data/SYD/around_unsw.csv')
            homes = open('data/SYD/home.json') 
            hdata = json.load(homes)

            for i in range(len(personas)):
                personas[i]["home"] = gen_random_home_SYD(hdata)
                if (personas[i]["occupation"] == "student"):
                    personas[i]["school"] = gen_random_school_SYD(csv, daily_act[i]["education"][1][0])
                elif (personas[i]["occupation"] != "unemployed" and personas[i]["occupation"] != "retiree"):
                    personas[i]["work"] = gen_random_place_SYD(csv)
        else:
            homes = open('POI_data/Home_ca_poi.csv') 
            hdata = pd.read_csv(homes)
            for i in range(len(personas)):
                personas[i]["home"] = gen_random_place_TKY(hdata)
                if (personas[i]["occupation"] == "student"):
                    personas[i]["school"] = gen_random_school_TKY(daily_act[i]["education"][1][0])
                
                if ('work' in daily_act[i]):
                    personas[i]["work"] = gen_random_workplace_TKY(personas[i]["occupation"])

    with open('res/personas.json','w+') as f3:
        json.dump(personas, f3)
