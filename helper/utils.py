import random
import torch
import datetime
from transformers import AutoTokenizer, AutoModelForCausalLM
from mem_module import MemoryModule
import openai

# Path to the llama model
model_name = ''

# OpenAI API
openai.api_key = ''

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

def llama_generate(context, msg):
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )

    messages = [
        {"role": "system", "content": context},
        {"role": "user", "content": msg },
    ]

    input_ids = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        return_tensors="pt"
    ).to(model.device)

    terminators = [
        tokenizer.eos_token_id,
        tokenizer.convert_tokens_to_ids("<|eot_id|>")
    ]

    outputs = model.generate(
        input_ids,
        max_new_tokens=512,
        eos_token_id=terminators,
        do_sample=True,
        temperature=1,
        top_p=0.8,
    )

    res = outputs[0][input_ids.shape[-1]:]
    return tokenizer.decode(res, skip_special_tokens=True)

def gpt_generate(context, msg, token=512):
    try: 
        res = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": msg}
            ],
            max_tokens=token,
        )
    except openai.OpenAIError as e:
        print(f"Error GPT no reponse: {e}")
        return e

    return res['choices'][0]['message']['content'].strip()

def random_in_quad(v1, v2, v3, v4):
    while True:
        s, t = random.random(), random.random()
        if s + t <= 1:
            x = s * v1[0] + t * v2[0] + (1 - s - t) * v3[0]
            y = s * v1[1] + t * v2[1] + (1 - s - t) * v3[1]
            return (x, y)

def mem_retrieval(memory_module: MemoryModule, persona: int, date, weekday):
    # Monthly/weekly/daily summary memory (the day of the week + weekly + recent 3 days)
    # print(weekday)
    # print(memory_module.monthly_summaries[str(persona)][datetime.datetime.strptime(date, "%d-%m-%Y").strftime('%m-%Y')])
    try:
        monthly_mem = memory_module.monthly_summaries[str(persona)][datetime.datetime.strptime(date, "%d-%m-%Y").strftime('%m-%Y')][weekday] # {'Monday': 'Summary', 'Tue'}
    except KeyError as e:
        # print("Monthly Memory unavailable...")
        monthly_mem = ''

    try:
        weekly_mem = memory_module.weekly_summaries[str(persona)][datetime.datetime.strptime(date, "%d-%m-%Y").isocalendar()[1]]
    except KeyError as e:
        # print("Weekly Memory unavailable...")
        weekly_mem = ''

    try:
        daily_mem = ''
        for d in range(5):
            rec_day = (datetime.datetime.strptime(date, '%d-%m-%Y') - datetime.timedelta(days=(d+1))).strftime("%d-%m-%Y")
            # print(rec_day)
            if rec_day in memory_module.summaries[str(persona)]:
                daily_mem += 'Daily routine summary for ' + rec_day + ' is: ' + memory_module.summaries[str(persona)][rec_day] + '. '
    except KeyError as e:
        print("Daily Memory: {}".format(daily_mem))

    return monthly_mem + weekly_mem + daily_mem
