import json
from typing import List, Tuple
import openai
from datetime import datetime, timedelta
import spacy
import pandas as pd
import numpy as np
from math import exp
import random

# OpenAI API
openai.api_key = ''

class MemoryModule:
    def __init__(self):
        # dictionary to store daily activities 
        self.daily_activities = {}  # dict[str(persona id), dict[str, List[List[str]]](dict with key as date and value is the list of activities) ]

        # dictionary to store daily summaries 
        self.summaries = {}  
        # dict[str(persona id), dict[str, str](dict with str as date and string as the summary)] 

        # dictionary to store weekly summaries
        self.weekly_summaries = {} 
        #  dict[str(persona id), dict[int, str](dict with key number as int and string as the weekly summary)]

        # counter to keep track of the number of days
        self.day_counters = {} 
        # dict[str, int] (dict with key as persona id and value as the number of accesses)

        # dictionary to store monthly summaries 
        self.monthly_summaries = {} 
        # dict[str(persona id), dict[str, str](dict with the key as the month and the value as the monthly summary)]

        # counter to see how many times a memory is accessed 
        self.memory_access_counter = {} 
        # dict[str(persona id), dict[str, int](dict with the key as the date and the value is the number of the times the memory is accessed)]

        #  pre defined threshold 
        self.memory_threshold = 0.76
    
        #YET TO DECIDE THE VALUE

        # Loading the spaCy model
        self.nlp = spacy.load("en_core_web_sm") #check

    def store_daily_activities(self, activities_dict: dict[str, dict[str, List[List[str]]]]):
        """
        Stores the activities for a specific date and persona.
        activities_dict: A dictionary containing the activities for each persona and date.
        Sample format: {"1": {"2024-07-10": [["sleep", "Hotel", ["0:00", "7:29"], "name", "coord"], ...]}}
        """
        for persona_id, dates in activities_dict.items():
            if persona_id not in self.daily_activities:
                self.daily_activities[persona_id] = {}
                self.day_counters[persona_id] = 0
            for date, activities in dates.items():
                processed_activities = [[activity[0], activity[1], activity[2]] for activity in activities]
                self.daily_activities[persona_id][date] = processed_activities
                if persona_id not in self.day_counters:
                    self.day_counters[persona_id] = len(self.daily_activities[persona_id])
                self.day_counters[persona_id] += 1


    ########################################################################################## 
    # FOR SUMMARIZATION
    ########################################################################################## 
    def summarize_day(self, persona_id: str, date: str):
        """
        Summarizes the activities of a specific day for a specific persona using GPT model.
        persona_id: The ID of the persona
        date: The date of the activities to be summarized.
        """
        # retrieve the activities for each date and then converts the activities to a json string format for input to the LLM
        activities = self.daily_activities.get(persona_id, {}).get(date, [])
        activities_json = json.dumps(activities)
        
        # Call OpenAI's API to generate a summary of the activities
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": f"Please summarize the following activities for the day in a concise, coherent paragraph: {activities_json}"}
                ],
                max_tokens=150,
            )
        except openai.OpenAIError as e:
            print(f"Error generating summary: {e}")
            return
            
        # Get the summary text from the response and store it in the summaries dictionary  
        summary = response['choices'][0]['message']['content'].strip()

        if persona_id not in self.summaries:
            self.summaries[persona_id] = {}
        self.summaries[persona_id][date] = summary

        # initialize the memory access counter for the date
        if persona_id not in self.memory_access_counter:
            self.memory_access_counter[persona_id] = {}
        self.memory_access_counter[persona_id][date] = 0
        # return summary

    def summarize_week(self, persona_id: str, end_date: str):
        """
        Summarizes the activities of a specific week for a specific persona using GPT model.
        persona_id: The ID of the persona.
        end_date: The end date of the week to be summarized.
        """
        # making the date in the right format 
        end_date_dt = datetime.strptime(end_date, '%d-%m-%Y')

        # get the last 7 dates before
        dates = []
        for i in range(7):
            date = end_date_dt - timedelta(days=i)
            dates.append(date.strftime('%d-%m-%Y'))

        # then combine daily summaries of those 7 days
        input_weekly_summary = []
        for date in dates:
            # Checking if the date exists in the summaries dictionary
            if date in self.summaries.get(persona_id, {}):
                input_weekly_summary.append(self.summaries[persona_id][date])

        input_weekly_summary = " ".join(input_weekly_summary)

        # call the api to generate the summary
        try: 
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": f"Here are the daily summaries for the week ending on {end_date}. Please provide a concise and coherent weekly summary in a single paragraph, focusing on the main activities and events:\n{input_weekly_summary}"}
                ],
                max_tokens=200,
            )
        except openai.OpenAIError as e:
            print(f"Error generating weekly summary: {e}")
            return

        weekly_summary = response['choices'][0]['message']['content'].strip()
        week_number = end_date_dt.isocalendar()[1]
        
        if persona_id not in self.weekly_summaries:
            self.weekly_summaries[persona_id] = {}

        self.weekly_summaries[persona_id][week_number] = weekly_summary

    
    def summarize_month(self, persona_id: str, end_date: str):
        """
        Summarizes the activities of a specific month using GPT model.
        persona_id: The ID of the persona.
        end_date: The end date of the month to be summarized.
        """

        end_date_dt = datetime.strptime(end_date, '%d-%m-%Y')
        start_date_dt = end_date_dt.replace(day=1)

        daywise_summaries = {
            "Monday": [],
            "Tuesday": [],
            "Wednesday": [],
            "Thursday": [],
            "Friday": [],
            "Saturday": [],
            "Sunday": []
        }

        current_date_dt = start_date_dt
        # loop through all the days of the month
        while current_date_dt <= end_date_dt: 
            date_str = current_date_dt.strftime('%d-%m-%Y')
            day_name = current_date_dt.strftime('%A')

            # if a summary exists for that day then add it to the dict 
            if date_str in self.summaries.get(persona_id, {}):
                daywise_summaries[day_name].append(self.summaries[persona_id][date_str])
            
            current_date_dt += timedelta(days=1)

        monthly_summary = {}

        for day, summaries in daywise_summaries.items():
            if summaries:
                input_monthly_summary = " ".join(summaries)

                try:
                    response = openai.ChatCompletion.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": f"Please summarize the following activities for all {day}s in the month in a structured and coherent paragraph:\n{input_monthly_summary}"}
                        ],
                        max_tokens=300,
                    )
                except openai.OpenAIError as e:
                    print(f"Error generating monthly summary for {day}: {e}")
                    continue

                monthly_summary[day] = response['choices'][0]['message']['content'].strip()
            

        month_year = end_date_dt.strftime('%m-%Y')
        if persona_id not in self.monthly_summaries:
            self.monthly_summaries[persona_id] = {}

        self.monthly_summaries[persona_id][month_year] = monthly_summary
                           
    ########################################################################################## 
    # FOR RETRIEVAL
    ##########################################################################################
    
    def retrieve_activities_by_location(self, persona_id: str, activity_info: List):
        """
        Retrieves historical activities based on a specific activity information.
        activity_info: List containing the intention, location category, and the time range.
        Sample input: ["sports and exercise", "Gym", ["19:21", "20:02"]]
        """
        global cata_act

        # getting the info from the list
        intention = activity_info[0].lower() 
        location_category = activity_info[1].lower()
        # time_range = activity_info[2]

        locations = cata_act.get(intention, [])
        relevant_activities = []

        for date, activities in self.daily_activities.get(persona_id, {}).items():
            for activity in activities:
                if activity[0] == intention and activity[1] in locations:
                    relevant_activities.append(f"{activity[0]} at {activity[1]} on {date}")
        return relevant_activities

    def generate_recommendation(self, persona_id: str, activity_info: List):
        """
        Generates a recommendation based on the intention and location and also looks at historically where all the person has gone.
        activity_info: List containing the intention, location category, and the time range.
        Sample input: ["sports and exercise", "Gym", ["19:21", "20:02"]]
        """
        # getting the relevant activities from history for the type of location category
        relevant_activities = self.retrieve_activities_by_location(persona_id, activity_info)

        activities_str = "; ".join(relevant_activities)
        if not activities_str:
            activities_str = "No relevant historical activities found."
        
        intention = activity_info[0]
        location_category = activity_info[1]
        # time_range = activity_info[2]
        
        # creating the prompt
        prompt = (
            f"The persona has an intention to '{intention}' and a preference for the '{location_category}' category. "
            # f"The time range is from {time_range[0]} to {time_range[1]}. "
            f"Based on historical activities: {activities_str}. Please give a line that can be used as a recommendation and help the persona choose a location for the activity."
        )
        try:
            response = openai.ChatCompletion.create(
                model = "gpt-4o-mini",
                messages=[
                    {"role":"system", "content":"You are a helpful assistant"},
                    {"role":"user", "content":prompt}
                ],
                max_tokens = 150,
            )
            recommendation = response['choices'][0]['message']['content'].strip()
            return recommendation
        except openai.OpenAIError as e:
            print(f"Error generating recommendation: {e}")
            return "Error generating the recommendation. Please try again later."

    def get_places_from_csv(self, file_path: str, activity_info: List) -> List[dict[str, str]]:
        places = []
        df = pd.read_csv(file_path)
        location_category = activity_info[1].lower()

        df['Category'] = df['Category'].str.lower()

        relevant_places = []
        relevant_places = df[df['Category'] == location_category]

        for _, row in relevant_places.iterrows():
            places.append({
                'Name': row['Name'],
                'Coordinates': (row['Latitude'], row['Longitute'])
            })
        return places
    
    def get_places_from_csv_TKY(self, file_path: str) -> List[dict[str, str]]:
        columns = ['ID', 'Category', 'lat', 'lng']
        df = pd.read_csv(file_path, usecols=columns)

        # Correct column references for 'lat' and 'lng'
        df['Coordinates'] = df.apply(lambda row: [row['lat'], row['lng']], axis=1)
        df = df[['ID', 'Category', 'Coordinates']]

        return df.to_dict(orient='records')
    
    def haversine_dist(self, coord1: list[float, float], coord2: list[float, float]) -> float:
        """
        Calculate the great-circle distance between two points on the Earth (in km).
        coord1, coord2: (latitude, longitude) in decimal degrees.
        """
        # Earth radius in kilometers
        R = 6371.0

        # Convert latitude and longitude from degrees to radians
        lat1, lon1 = np.radians(coord1)
        lat2, lon2 = np.radians(coord2)

        # Differences in coordinates
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        # Haversine formula
        a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

        # Distance in km
        return R * c

    def filter_places_within_radius(self, places: List[dict[str, any]], user_loc: Tuple[float, float], radius_km=10) -> List[dict[str, any]]:
        filtered_places = []
        for place in places:
            distance = self.haversine_dist(user_loc, place['Coordinates'])
            if distance <= radius_km:
                place_with_dist = place.copy()
                place_with_dist['Distance'] = distance  # Add distance to the place data
                filtered_places.append(place_with_dist)
        return filtered_places

    def generate_choice(self, loc: str, user_loc, activity_info: List, recommendation: str, file_path: str) -> dict[str, any]:
        if loc == 'Sydney': 
            places = self.get_places_from_csv(file_path, activity_info)
        else:
            places = self.get_places_from_csv_TKY(file_path)
            places = self.filter_places_within_radius(places, user_loc)

        if len(places) > 150:
            places = random.sample(places, 150)

        activities_str = f"Activity: {activity_info[0]}, Location Category: {activity_info[1]}, Time: {activity_info[2]}"
        
        # Creating the prompt
        prompt = (
        f"The persona has an activity info: {activities_str}. Based on the recommendation: '{recommendation}', "
        f"please pick the best choice from the list of places in the attached CSV file. Provide the location ID, coordinates, "
        f"and an estimated transport time in minutes.\n"
        f"Return the choice in this format - ID, [latitude, longitude], minutes.\n"
        f"The ID should be a string that is exactly the same as the picked location, and the latitude and longitude should be floats. The minutes should be an integer.(do not include the word minutes, in the minutes, just the integer)\n"
        f"Make sure not to output any other information other than just the choice, do not include any extra words"
        f"You should always respond with the required data in the format i mentioned above without any additional information, text or explanation.\n"
        f"The following is the location dataset you can pick from: \n"
    )
        for place in places:
            if loc == 'Sydney': 
                prompt += f"{place['Name']}, Coordinates: ({place['Coordinates'][0]}, {place['Coordinates'][1]})\n"
            else:
                prompt += f"ID: {place['ID']}, Category: {place['Category']}, Coordinates: ({place['Coordinates'][0]}, {place['Coordinates'][1]}), Distance from current location: {place['Distance']}\n"

        # Call the OpenAI API to generate the choice
        while True:
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant who generate response without any additional introduction, text or explanation other then the required output. You should \
                         generate a list without square brackets, where index 0 is the ID as str, index 1 is the coorfinate as a sublist [latitude, longitude], and index 2 is an integer represents the estimated transport time to the location in min."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=200,
                )
                choice = response['choices'][0]['message']['content'].strip()

                while not choice[-1].isdigit():
                    choice = choice[:-1]

                comma_idx = choice.find(',')
                if choice[0] != '"':
                    name = '"' + choice[:comma_idx] + '"'
                    choice = "[" + name + choice[comma_idx:] + "]"
                
                res = json.loads(choice)

                if len(res) != 3:
                    continue

                break
                
            except openai.OpenAIError as e:
                print(f"Error generating choice: {e}")
                # return {}
            
            except json.JSONDecodeError:
                print("Invalid JSON received, retrying...")

        return res


    ##########################################################################################
    # FOR STORING MEMORY
    ##########################################################################################

    def store_memory_to_file(self):
        with open('mem/daily_activities.json', 'w') as f:
            json.dump(self.daily_activities, f, indent = 4)
        
        with open('mem/summaries.json', 'w') as f:
            json.dump(self.summaries, f, indent = 4)
        
        with open('mem/weekly_summaries.json', 'w') as f:
            json.dump(self.weekly_summaries, f, indent = 4)

        with open('mem/monthly_summaries.json', 'w') as f:
            json.dump(self.monthly_summaries, f, indent = 4)
        
        with open('mem/memory_access_counter.json', 'w') as f:
            json.dump(self.memory_access_counter, f, indent = 4)
    

    def load_memory_from_file(self):
        try:
            with open('mem/daily_activities.json', 'r') as f:
                self.daily_activities = json.load(f)
            
            for persona_id in self.daily_activities.keys():
                self.day_counters[persona_id] = len(self.daily_activities[persona_id])

        except FileNotFoundError:
            self.daily_activities = {}
        
        try:
            with open('mem/summaries.json', 'r') as f:
                self.summaries = json.load(f)
        except FileNotFoundError:
            self.summaries = {}

        try:
            with open('mem/weekly_summaries.json', 'r') as f:
                self.weekly_summaries = json.load(f)
        except FileNotFoundError:   
            self.weekly_summaries = {}
        
        try:
            with open('mem/monthly_summaries.json', 'r') as f:
                self.monthly_summaries = json.load(f)
        except FileNotFoundError:
            self.monthly_summaries = {}
        
        try:
            with open('mem/memory_access_counter.json', 'r') as f:
                self.memory_access_counter = json.load(f)
        except FileNotFoundError:
            self.memory_access_counter = {}

    ##########################################################################################
    # FOR MEMORY DELETION
    ##########################################################################################
    def calculate_information_density(self, summary: str): #category_weights: dict
        #need to include a way to make it personal for each user and generate the values for the categories in persona generation
        """
        Calculates the weighted information density of a summary.
        Output would be a float
        """

        ##### - - - - - next lines 
        categories = {
            "events" : 0.5, # (e.g., "passed a test," "attended a meeting")   #check if you can personalize this
            "entities": 0.2, # (e.g., "person," "location")
            "actions": 0.2, # (e.g., "completed," "started")
            "attributes": 0.1 # (e.g., "high score," "difficult task")
        }

        # NER using spacy
        doc = self.nlp(summary)

        # Initial counts of each type of thing 
        counts = {
            "events": 0,
            "entities": 0,
            "actions": 0,
            "attributes": 0
        }

        # Going through summaries to see how much of each type is present in the summary
        for ent in doc.ents:
            if ent.label_ in ["EVENT"]:
                counts["events"] += 1
            elif ent.label_ in ["PERSON", "ORG", "GPE", "LOC"]:
                counts["entities"] += 1

        for token in doc:
            if token.pos_ in ["VERB"]:
                counts["actions"] += 1
            elif token.pos_ in ["ADJ", "ADV"]:
                counts["attributes"] += 1

        # print(f"Counts for summary '{summary}': {counts}")
        # print()
        # print()
        
        weighted_sum = sum(categories[cat] * counts[cat] for cat in categories)
        total_words = len(summary.split())
        if total_words == 0:
            return 0
        max_weighted_sum = sum(categories[cat] * total_words for cat in categories)
        weighted_info_density = weighted_sum / max_weighted_sum if max_weighted_sum > 0 else 0

        """
        weighted_sum = sum(category_weights[cat] * counts[cat] for cat in category_weights)
        total_words = len(summary.split())

        if total_words == 0:
            return 0

        max_weighted_sum = sum(category_weights[cat] * total_words for cat in category_weights)
        weighted_info_density = weighted_sum / max_weighted_sum if max_weighted_sum > 0 else 0
        """


        # print(f"Information density for summary '{summary}': {weighted_info_density}")
        # print()
        # print()

        return weighted_info_density
    
    def sigmoid(self,x):
        """
        Sigmoid function to normalize the importance score.
        """
        return 1 / (1 + exp(-x))
    
    def calculate_importance_score(self, persona_id: str, date: str, summary: str):
        """
        Calculates the importance score based on recency, frequency, and information density.
        """
        frequency = self.memory_access_counter.get(persona_id, {}).get(date, 0)
        recency = (datetime.now() - datetime.strptime(date, '%d-%m-%Y')).days
        weighted_info_density = self.calculate_information_density(summary)

        # Normalizing the recency and frequency 
        max_recency = 30 #last 1 month
        normalized_recency = 1 - min(recency / max_recency, 1) # it is (1 -) because the more recent memory should have higher score
        
        max_frequency = max(self.memory_access_counter.get(persona_id, {}).values(), default=0)  
        max_frequency = max(1, max_frequency)  # Ensure max_frequency is at least 1 to avoid division by zero
    
        normalized_frequency = min(frequency / max_frequency, 1)

        # Calculating the overall importance score for the memory
        importance_score = (0.6 * weighted_info_density + 0.2 * normalized_frequency + 0.2 * normalized_recency)
        normalized_importance_score = self.sigmoid((importance_score * 10 ) - 5)
        return normalized_importance_score * 100

    def deleting_memory(self):
        """
        Deletes the memory of the user based on the memory access threshold.
        """
        # getting the list of dates to delete
        for persona_id, summaries in list(self.summaries.items()):
            dates_to_delete = []
            for date, summary in list(summaries.items()):
                importance_score = self.calculate_importance_score(persona_id, date, summary)
                print(f"Importance score for persona {persona_id} on {date}: {importance_score}")
                if (importance_score) < self.memory_threshold:
                    dates_to_delete.append(date)
        
            # deleting the memories that are selected to be deleted
            for date in dates_to_delete:
                del self.summaries[persona_id][date]
                self.memory_access_counter[persona_id].pop(date, None)
                if date in self.daily_activities.get(persona_id, {}):
                    self.daily_activities[persona_id].pop(date, None)

        # for persona_id, summaries in list(self.summaries.items()):
        #     for date, summary in list(summaries.items()):
        #         # iterates over the summaries dictionary and deletes the low scoring daily summaries and daily activities
        #         importance_score = self.calculate_importance_score(persona_id, date, summary)
        #         if importance_score < self.memory_threshold:
        #             del self.summaries[persona_id][date]
        #             self.memory_access_counter[persona_id].pop(date, None)
        #             if date in self.daily_activities.get(persona_id, {}):
        #                 self.daily_activities[persona_id].pop(date, None)


#Testing the module 
cata_act = {
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

############################################################################################################
# TESTING THE MEMORY MODULE FOR MEMORY DELETION
# if __name__ == "__main__":
#     memory_module = MemoryModule()

#     activities_dict = {   #activities for testing extreme values
#     "1": {
#         # Balanced day with some entities, events, actions
#         "01-07-2024": [["sports and exercise", "Gym", ["19:21", "20:02"], "Fitness First Randwick", (-33.918, 151.2412)], 
#                         ["eat breakfast", "home", ["07:24", "08:00"]], 
#                         ["go to work", "university", ["09:00", "12:00"], "The University of New South Wales", (-33.9173, 151.2313)]],
        
#         # Action-focused, project completion and task management, more attributes and actions
#         "02-07-2024": [["project completion", "office", ["08:00", "12:00"], "UNSW Office", (-33.9173, 151.2313), "Completed two research projects with high complexity"],
#                        ["task management", "home", ["14:00", "15:00"], "Managed 5 team members for event planning"],
#                        ["evening workout", "gym", ["18:30", "19:30"], "Fitness First", (-33.918, 151.2412)]],  # More actions, attributes (complexity)
        
#         # Simple day, low event count, fewer entities, more attributes
#         "03-07-2024": [["relaxing at home", "home", ["10:00", "12:00"], "Simple morning with easy tasks"], 
#                        ["short walk", "park", ["16:00", "17:00"], "Local Park", (-33.917, 151.232)]]
#     },
#     "2": {
#         # Event-heavy day with multiple entities involved
#         "01-07-2024": [["attend board meeting", "office", ["09:00", "11:00"], "Global Corp HQ", (-33.918, 151.2301), "Discuss company performance with CEO and board members"], 
#                        ["client meeting", "conference room", ["12:00", "13:00"], "Sydney Financial Center", (-33.919, 151.232)], 
#                        ["team discussion", "office", ["14:00", "15:30"], "Main Office", (-33.920, 151.2330), "Discuss upcoming project launch"]],
        
#         # Focus on actions and attributes
#         "02-07-2024": [["writing detailed report", "home", ["09:00", "11:00"], "Prepared in-depth financial analysis for Q2", "High difficulty"], 
#                        ["gym session", "Fitness First", ["17:00", "18:00"], "Fitness First Randwick", (-33.918, 151.2412)]],
        
#         # Low-density day with simple actions and events
#         "03-07-2024": [["grocery shopping", "local market", ["08:00", "09:00"], "Randwick Market", (-33.9201, 151.234)], 
#                        ["afternoon nap", "home", ["13:00", "14:30"]]]
#     },
#     "3": {
#         # Event-heavy, more entities and events
#         "01-07-2024": [["attend tech conference", "Sydney Convention Center", ["09:00", "17:00"], "Tech Expo 2024", (-33.870, 151.206), "Network with industry leaders"], 
#                        ["dinner with colleagues", "restaurant", ["19:00", "20:00"], "Sydney Harbour Restaurant", (-33.861, 151.210)]],
        
#         # Balanced day with moderate number of actions, entities, and events
#         "02-07-2024": [["prepare for client meeting", "home", ["08:00", "09:00"], "Prepared presentation"], 
#                        ["client meeting", "office", ["10:00", "11:30"], "Global HQ", (-33.920, 151.232)], 
#                        ["workout", "gym", ["18:00", "19:00"], "Fitness First", (-33.918, 151.2412)]],
        
#         # Low-density day, more attributes and actions
#         "03-07-2024": [["work on personal project", "home", ["09:00", "12:00"], "Developed personal website"], 
#                        ["afternoon relaxation", "park", ["15:00", "16:00"], "Centennial Park", (-33.8915, 151.2497)]]
#     },
#     "4": {
#         # High-density day, mostly events and actions
#         "01-07-2024": [["presentation preparation", "office", ["08:00", "12:00"], "Corporate Office", (-33.920, 151.232), "Prepared presentation for company board"], 
#                        ["attend product launch", "office", ["14:00", "16:00"], "Corporate HQ", (-33.918, 151.230)]],
        
#         # Low-density, balanced
#         "02-07-2024": [["write product report", "home", ["10:00", "12:00"], "Summary of product features", "Moderate complexity"], 
#                        ["evening stroll", "park", ["18:00", "19:00"], "Local Park", (-33.917, 151.2312)]],
        
#         # Simple day with more attributes and few actions
#         "03-07-2024": [["brainstorm ideas", "home", ["11:00", "13:00"], "Conceptualized new marketing strategies"], 
#                        ["read book", "home", ["15:00", "17:00"], "Quiet afternoon reading"]]
#     }
# }
    
# # Storing activities and generating summaries for each day
#     memory_module.store_daily_activities(activities_dict)
#     for persona_id, dates in activities_dict.items():
#         for date in dates.keys():
#             memory_module.summarize_day(persona_id, date)
#             if date in memory_module.summaries[persona_id]:  # Check if the summary was successfully generated
#                 print(f"Summary for persona {persona_id} on {date}: {memory_module.summaries[persona_id][date]}")
#             else:
#                 print(f"Summary for persona {persona_id} on {date} was not generated.")
#             print("\n")
            
#             # Checking if 7 days have passed to generate a weekly summary
#             if memory_module.day_counters[persona_id] % 7 == 0:
#                 memory_module.summarize_week(persona_id, date)

#     # Count the number of memories before deletion
#     total_memories_before = 0
#     for persona_id in activities_dict.keys():
#         total_memories_before += len(memory_module.summaries[persona_id])
#     print(f"Total number of memories before deletion: {total_memories_before}\n")

#     # Perform memory deletion
#     memory_module.deleting_memory()

#     # Count the number of memories after deletion
#     total_memories_after = 0
#     for persona_id in activities_dict.keys():
#         total_memories_after += len(memory_module.summaries[persona_id])
#     print()
#     print(f"Total number of memories after deletion: {total_memories_after}\n")

#     # Storing memory to files (if needed)
#     memory_module.store_memory_to_file()

#     # Example output to check remaining summaries after deletion
#     for persona_id in activities_dict.keys():
#         print(f"Summaries for persona {persona_id} after deletion: {memory_module.summaries[persona_id]}")



############################################################################################################
# TESTING THE MEMORY MODULE

# Testing the MemoryModule normally
if __name__ == "__main__":
    memory_module = MemoryModule()
    
    # Example activities for 7 days starting from today
    activities_dict = {
    "1": {
        "01-07-2024": [["sports and exercise", "Gym", ["19:21", "20:02"], "Fitness First Randwick", (-33.918, 151.2412)],["eat breakfast", "home", ["07:24", "08:00"]],["go to work", "university", ["09:00", "12:00"], "The University of New South Wales", (-33.9173, 151.2313)]],
        "02-07-2024": [["go to sleep", "home", ["00:00", "07:00"]],["jogging", "gym", ["08:30", "09:30"], "Plus Fitness 24/7 Kensington", (-33.9181, 151.228)]],
        "03-07-2024": [["go to sleep", "home", ["00:00", "06:45"]],["eat breakfast", "home", ["07:15", "07:45"]],["office work", "university", ["08:30", "12:00"], "The University of New South Wales", (-33.9173, 151.2313)]],
        "04-07-2024": [["go to sleep", "home", ["00:00", "06:30"]],["emails", "home", ["08:00", "09:00"]],["client call", "home", ["11:30", "12:30"]]],
        "05-07-2024": [["go to sleep", "home", ["00:00", "07:15"]],["marketing research", "university", ["09:00", "11:00"], "The University of New South Wales", (-33.9173, 151.2313)],["brainstorming session", "university", ["14:00", "16:00"], "The University of New South Wales", (-33.9173, 151.2313)]],
        "06-07-2024": [["go to sleep", "home", ["00:00", "07:00"]],["gardening", "home", ["14:00", "16:00"]],["dinner", "restaurant", ["18:00", "19:00"], "Tropical Green (Pho House)", (-33.9173, 151.2356)]],
        "07-07-2024": [["go to sleep", "home", ["00:00", "06:45"]],["eat breakfast", "home", ["07:15", "07:45"]],["relaxing", "home", ["08:00", "09:00"]],["watch movie", "cinemas", ["10:00", "12:00"]]]
    },
    "2": {
        "01-07-2024": [["sleep", "home", ["23:00", "06:00"]],["exercise", "gym", ["06:30", "07:30"], "Snap Fitness Randwick", (-33.9175, 151.2415)]],
        "02-07-2024": [["sleep", "home", ["23:00", "06:00"]],["eat breakfast", "cafe", ["08:00", "08:30"], "Sharetea", (-33.9174, 151.233)]],
        "03-07-2024": [["sleep", "home", ["23:00", "06:00"]],["online meeting", "home", ["14:00", "15:00"]]]
    },
    "3": {
        "01-07-2024": [["sleep", "home", ["22:00", "06:00"]],["morning run", "park", ["06:30", "07:00"], "Queens Park", (-33.907, 151.2428)]],
        "02-07-2024": [["sleep", "home", ["22:00", "06:00"]],["eat breakfast", "home", ["07:30", "08:00"]]],
        "03-07-2024": [["sleep", "home", ["22:00", "06:00"]],["work", "office", ["09:00", "17:00"]]]
    },
    "4": {
        "01-07-2024": [["sleep", "home", ["23:00", "07:00"]],["yoga", "gym", ["07:30", "08:00"], "UNSW Fitness & Aquatic Centre", (-33.9165, 151.233)]],
        "02-07-2024": [["sleep", "home", ["23:00", "07:00"]],["eat breakfast", "cafe", ["08:30", "09:00"], "Campus Village Cafe", (-33.9176, 151.2333)]],
        "03-07-2024": [["sleep", "home", ["23:00", "07:00"]],["work", "university", ["10:00", "16:00"], "The University of New South Wales", (-33.9173, 151.2313)]]
    }
}

    
    # Storing activities and generating summaries for each day
    memory_module.store_daily_activities(activities_dict)
    for persona_id, dates in activities_dict.items():
        for date in dates.keys():
            memory_module.summarize_day(persona_id, date)
            if date in memory_module.summaries[persona_id]:  # Check if the summary was successfully generated
                print(f"Summary for persona {persona_id} on {date}: {memory_module.summaries[persona_id][date]}")
            else:
                print(f"Summary for persona {persona_id} on {date} was not generated.")
            print("\n")
            
            # Checking if 7 days have passed to generate a weekly summary
            if memory_module.day_counters[persona_id] % 7 == 0:
                memory_module.summarize_week(persona_id, date)

    # Check the generated weekly summary for each persona
    most_recent_date_str = max(date for persona in activities_dict.values() for date in persona.keys())
    week_number = datetime.strptime(most_recent_date_str, '%d-%m-%Y').isocalendar()[1]

    for persona_id in activities_dict.keys():
        if persona_id in memory_module.weekly_summaries and week_number in memory_module.weekly_summaries[persona_id]:
            print(f"Weekly summary for persona {persona_id} for week {week_number}: {memory_module.weekly_summaries[persona_id][week_number]}")
        else:
            print(f"Weekly summary for persona {persona_id} for week {week_number} was not generated.")
        print("\n")

    # Generating and checking the monthly summary
    end_date_str = "07-07-2024"  # assume this is the date that is passed on to the summarize month function to generate the monthly summary for
    for persona_id in activities_dict.keys():
        memory_module.summarize_month(persona_id, end_date_str)
        month_year = datetime.strptime(end_date_str, '%d-%m-%Y').strftime('%m-%Y')
        if month_year in memory_module.monthly_summaries[persona_id]:  # Check if the monthly summary was generated
            print(f"Monthly summary for persona {persona_id} for {month_year}: {memory_module.monthly_summaries[persona_id][month_year]}")
        else:
            print(f"Monthly summary for persona {persona_id} for {month_year} was not generated.")
        print("\n")

    # Example: Retrieving historical tasks based on location category and intention
    for persona_id in activities_dict.keys():
        activity_info = ["shopping", "grocery", ["06:30", "07:30"]]
        recommendation = memory_module.generate_recommendation(persona_id, activity_info)
        print(f"Recommendation for persona {persona_id} with activity info '{activity_info}': {recommendation}")
        print("\n")

        choice = memory_module.generate_choice(activity_info, recommendation, 'around_unsw.csv')
        print(f"Choice for persona {persona_id} with activity info '{activity_info}': {choice}")
        print("\n")
    
    # Count the number of memories before deletion
    total_memories_before = 0
    for persona_id in activities_dict.keys():
        total_memories_before += len(memory_module.summaries[persona_id])
    print(f"Total number of memories before deletion: {total_memories_before}\n")

    # Example: Deleting less important information
    memory_module.deleting_memory()
    for persona_id in activities_dict.keys():
        print(f"Summaries for persona {persona_id} after deletion: {memory_module.summaries[persona_id]}")

    # Count the number of memories after deletion
    total_memories_after = 0
    for persona_id in activities_dict.keys():
        total_memories_after += len(memory_module.summaries[persona_id])
    print()
    print(f"Total number of memories after deletion: {total_memories_after}\n")

    # Storing memory to files
    memory_module.store_memory_to_file()

