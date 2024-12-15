def persona_prompt(loc, data):
    msg = 'Among the total population, '

    # Include age distribution in the prompt
    for i in range(len(data['age'])):
        msg += "{}% are males aged {} to {}, while {}% are females in this age group. ".format(data['age'][i]['male'], i*5, i*5+4, data['age'][i]['female'])

    # Include employment data in the prompt
    if loc == 'Sydney': 
        msg += persona_employ_SYD_prompt(data['employment'])
    else:
        msg += persona_employ_TKY_prompt(data['employment'])

    msg += """Please generate 5 independent personas in {} and output the person's name, age, gender and occupation in JSON format based on the given population distribution.
""".format(loc)
    note = """Note:
1. All students, including college and university students, high school students, kids in kindergarten etc, shoudld all have occupation "student".
2. Children can choose to start preschool at the age of 4, and must be in compulsory schooling by 6.
3. Unemployed people (including young kids and old people) who are not student, can only have occupation "unemployed" or "retiree".
"""
    return msg + note

def persona_employ_SYD_prompt(data):
    # Include employment data in the prompt
    msg = "\nThe employment-to-population ratio for males is {}, for females is {}, where the ratio for males at working age (from 15 to 64 years old) is {}, for female is {}.\
The average age at retirement from labour force is {} years.\n"\
.format(data['total'][0], data['total'][1], data['working_age'][0], data['working_age'][1], data['retirement'])
    
    return msg

def persona_employ_TKY_prompt(data):
    # Include employment data in the prompt
    msg = "\nThe employment-to-population ratio for males (from 15 to 64 years old) is {}, for females (from 15 to 64 years old) is {}. The retirement age is {}.\n"\
.format(data['total'][0], data['total'][1], data['retirement'])
    
    return msg

def person_info_prompt(loc, name, age, gender, occ, ext, arg, con, neu, ope):
    msg = """You are a person who lived in {}. You have the following personal infomation: name: {}, age: {}, gender: {}, occupation: {}. 
Your personality is determined based on the following 5 domains, where the full score of each domain is 24:
1. extraversion: {} scores, where people high in extraversion are outgoing and tend to gain energy in social situations. \
People who are low in domain are more introverted and tend to be more reserved. They have less energy to expend in social settings and social events can feel draining. 
2. agreeableness: {} scores, where people who are high in agreeableness tend to be more cooperative while those low in this personality trait tend to be more competitive and sometimes even manipulative.
3. conscientiousness: {} scores, where people with higher score for conscientiousness tend to be organized and mindful of details. \
People low in this domain is less structured and less organized. They may procrastinate to get things done, sometimes missing deadlines completely.
4. neuroticism: {} scores, where people who are high in neuroticism tend to experience mood swings, anxiety, irritability, and sadness. Those low in this personality trait tend to be more stable and emotionally resilient.
5. openness to experience: {} scores, where people with high score in openness tend to have a broad range of interests and be more adventurous and creative. \
Conversely, people low in this domain are often much more traditional and may struggle with abstract thinking.
""".format(loc, name, age, gender, occ, ext, arg, con, neu, ope)
    return msg

def daily_activity_prompt(act_loc, loc):
    if loc == 'Sydney':
        example = activity_eg_SYD()
    else:
        example = activity_eg_TKY()

    msg = """The common activity list is given by {}, where the keys are the activities, and the values are lists of locations that the activitiies\
might take place.
Based on your personal information and personality, please pick some daily activities from the common activity list that you are likely to participate, together with some possible locations that you might choose for those activities. \
Also, generate the frequency of each activity.
Note:
1. The minimum amount of common activities a person may have is 5. There's not upper limit, as long as there's enough time for the person. Some people tend to have more daily activities than others.
2. The location list for each chosen activity cannot be empty.
3. The location list of an activity should be ordered in possibility of going to the location. For example, if a person's location list for "meal" is ["home", "cafe"], \
and they have their meals in cafe more often, then the location list should be ["cafe", "home"].
4. Only people from 15 to 64 are allowed to have activity "work". People who are students should have activity "education". Only a limited amount of students get a job, \
and most of these jobs are part-time. Hence, if a student get a 'work' activity, their 'work' activity is likely to have a low frequency.
5. People should all have activities "sleep", "meal" and "go home".
6. Children can go to preschools between the ages of 4 to 6. At the age of 6, children has to start primary school.
7. An persona may or may not have a "religious activities". But if they has one, they must have one and only one location cateory for their "religious activities".
8. You are only allowed to choose some of the activities from the given common activity list. \
The selected possible locations of each activity has to be picked from the possible location list of that activity.
9. You must NOT include activities that the person would never participate in. For example, an unemployed person should not have activity "work" as an element.
10. The strings for activity names and location categories are case-sensitive. When generating activities and corresponding possible locations, the names of activities \
and location categories should be excatly the same as provided activity list.
Answer in a dictionary format: {{activity 1: [frequency, [location 1, location 2, ...]], activity 2: [...], ...}}.
""" + example + """Important: You should always responds required data in json dictionary format, but without any additional introduction, text or explanation.
""".format(str(act_loc))
    return msg

def activity_eg_TKY():
    return """Five examples outputs:
1. {{"work": ["every workday", ["Workplace"]], "sleep": ["everyday", ["Home"]], "go home": ["everyday", ["Home"]], "meal": ["3 meals per day", ["Restaurant", "Cafe", "Home"]], "shopping": ["every weekends", ["Grocery"]], \
"leisure activities": ["everyday", ["Home"]], "sports and exercise": ["once a week", ["Gym"]], "religious activities": ["every weekends", ["Church"]], "trifles": ["twice a month", ["Automotive Service", "Other Service"]]}}
2. {{"go home": ["everyday", ["Home"]], "sleep": ["everyday", ["Home"]], "meal": ["2 meals per day", ["Home", "Casual Dining"]], "shopping": ["twice a week", ["Grocery", "Other shopping"]], "sports and exercise": ["twice a week", ["Gym", "Outdoors"]], \
"leisure activities": ["everyday", "Entertainment", "Drink and Dessert Shop", "Pub and Bar", "Home", "Art and Performance", "Social Event"]], "education": ["every workday", ["Vocational Training"]], "trifles": ["once every two weeks", ["Medical Service", "Other Service"]]}}
3. {{"work": ["every workday", ["Workplace"]], "go home": ["everyday", ["Home"]], "meal": ["3 meals per day", ["Home", "Cafe"]], "sleep": ["everyday", ["Home"]], "shopping": ["once a week", ["Grocery", "Other shopping"]], "sports and exercise": ["everyday", ["Outdoors"]], \
"leisure activities": ["ever two days", ["Outdoors", "Home", "Social Event", "Entertainment", "Pub and Bar"]], "trifles": ["once every two days", ["Medical Service", "Other Service"]]}}
4. {{"work": ["every workday", ["Workplace"]], "go home": ["everyday", ["Home"]], "meal": ["3 meals per day", ["Casual Dining", "Cafe", "Pub and Bar"]], "sleep": ["everyday", ["Home"]], "shopping": ["once every two weeks", ["Other shopping"]], \
"leisure activities": ["every week", ["Home", "Social Event", "Stadium", "Entertainment"]], "trifles": ["every week", ["Legal and Financial Service", "Medical Service", "Other Service"]]}}
5. {{"go home": ["everyday", ["Home"]], "meal": ["3 meals per day", ["Home"]], "sleep": ["everyday", ["Home"]], "shopping": ["once a week", ["Grocery", "Other shopping"]], "sports and exercise": ["everyday", ["Outdoors", "Field"]], \
"leisure activities": ["everyday", ["Social Event", "Art and Performance", "Home", "Museum"]], "trifles": ["every Wednesday", ["Medical Service", "Other Service"]]}}\n"""

def activity_eg_SYD():
    return """Three examples outputs:
1. {{"work": ["every workday", ["Workplace"]], "sleep": ["everyday", ["Home"]], "go home": ["everyday", ["Home"]], "meal": ["3 meals per day", ["Restaurant", "Cafe", "Home"]], "shopping": ["every weekends", ["Grocery"]], \
"sports and exercise": ["once a week", ["Gym"]], "religious activities": ["every weekends", ["Church"]], "trifles": ["once a month", ["Automotive Service"]]}}
2. {{"go home": ["everyday", ["Home"]], "sleep": ["everyday", ["Home"]], "meal": ["2 meals per day", ["Home", "Casual Dining"]], "shopping": ["twice a week", ["Grocery", "Other shopping"]], "sports and exercise": ["twice a week", ["Gym", "Field"]], \
"education": ["every workday", ["VET"]], "medical treatment": ["once every two weeks", ["Dentist"]]}}
3. {{"work": ["every workday", ["Workplace"]], "go home": ["everyday", ["Home"]], "meal": ["3 meals per day", ["Home", "Cafe"]], "sleep": ["everyday", ["Home"]], "shopping": ["once a week", ["Grocery", "Other shopping"]], "sports and exercise": ["everyday", ["Outdoors"]], \
"leisure activities": ["everyday", ["Outdoors"]], "medical treatment": ["once every two weeks", ["Clinic"]]}}\n"""

def next_motivation_prompt(pre_mot, mem, date: str, weekday: str, time: str):
    msg = """Today is {}, {}. Now is {}. You've already done the following activities: {}.
Some summaries about your historial behaviours are given below:
{}

Task: Based on current date and time, your personal information, recent arrangements and historical behaviours, please randomly select your next activity from your daily activity dictionary, \
and pick a location from the location list corresponds to the chosen activity. You should also decide the time duration for the selected activity.

Requirements for routine generation:
1. You must consider how your character attributes and personality may affect your activity and location selection.
2. The next activity should start at now, which is {}.
3. You must consider how the date and time may affect your activity and location selection. For example, most people sleep at night, and most people only goes to work during weekdays.
4. You must take your historical behaviours into consideration. For example, some people may have similar routine on the same day of the week, some people's daily routine may be affected \
by the activities done during the recent days.
5. When selecting the activity, you must take the frequency of the activity into consideration.
6. Most people with a full time job tend to have full day works to do during the workday. Most of them goes to workplace during the day, but some may have different working hours, depends on their working industry. \
The basic working hours are 7 or 8 hours from 9:00 to 17:00 or 18:00, for 5 (or 6) days per week. However, many workers stay in the office until much later, for example until 21:00 to 22:00. \
If their working hours include meal breaks, they tend to eat nearby.
7. A primary or secondary school student’s day generally start their school at around 8:15 (30 mins variance), and classes end around 15:45 (30 mins variance). After school hours can be dedicated to club activities (in school). \
College and university stdents tend to have more flexible schedule.
8. During the workday, students at school/employees at work may or may not choose to eat out during mealtime.
9. Students/employees who leave school/work during the workday usually do so for: \
meals (possible activity: 'meal'), special activities(like social events etc.) or personal/sick leave (possible activity: 'go home', 'trifles'). \
If the activity/meal ends before school or get off work time, students/employees who leave school/work for reasons other than personal/sick leave usually return to school/work to continue their studies/work for the day after the outing.
10. For 'shopping' activity, slightly prioritize 'Other Shopping'. For 'trifles' activity, slightly prioritize 'Other Service'. This is due to the word Other implies many services/shopping options.


Important:
1. The format for the time should be in 24-hour format, i.e. 1:00 is 1 a.m., 13:00 is 1 p.m.
2. The routine of a day must start at 0:00 and end at 23:59. \
The routine should not have activities that exceed the time limit, i.e. you should not create activity that starts today and ends anytime tomorrow. \
For example, you should create activity like '["sleep", "Home", ["22:18", "23:59"]]'.
3. You can pick one activity only from your daily activitiy list, and one location for the chosen activity only from the location list of that activity. For example, "Social Event" is a location, and the cooresponding activity name is "leisure activities".
4. Most full time worker works around 8 hours a day during working day.
Answer format: [activity name, location, [start time, end time]].

10 example outputs:
1. ["sleep", "Home", ["0:00", "8:22"]]
2. ["work", "Workplace", ["13:32", "17:30"]]
3. ["eat", "Cafe", ["11:49", "12:12"]]
4. ["shopping", "Other Shopping", ["15:33", "18:09"]]
5. ["sports and exercise", "Gym", ["19:21", "20:02"]]
6. ["work", "Workplace", ["13:12", "20:27"]]
7. ["education", "Primary and Secondary School", ["8:23", "17:51"]]
8. ["sleep", "Home", ["0:00", "9:47"]]
9. ["leisure activities", "Entertainment", ["21:31", "23:14"]]
10. ["sleep", "Hotel", ["22:25", "23:59"]]


Important: You should always responds required data in json list format, but without any additional introduction, text or explanation.
""". format(date, weekday, time, [sublist[:3] for sublist in pre_mot], mem, time)
    return msg