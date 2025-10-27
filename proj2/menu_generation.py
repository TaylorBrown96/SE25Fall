import llm_toolkit as llm_toolkit
from sqlQueries import *
import os
import pandas as pd
import calendar
import time
import json
import random
import re

db_file = os.path.join(os.path.dirname(__file__), 'CSC510_DB.db')
#cache_file = os.path.join(os.path.dirname(__file__), '.hf_cache/menu_cache.csv')

## increase to increase the sample size the AI can draw from at the cost of increased runtime
ITEM_CHOICES = 10

DAYS_OF_WEEK = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

BREAKFAST_TIME = 1000
LUNCH_TIME = 1400
DINNER_TIME = 2000

class MenuGenerator:

    def __init__(self, tokens = 1000):
        conn = create_connection(db_file)
        self.menu_items = pd.read_sql_query("SELECT * FROM MenuItem WHERE instock == 1", conn)
        self.restaurants = pd.read_sql_query("SELECT rtr_id, hours FROM Restaurant WHERE status==\"Open\"", conn)
        close_connection(conn)
        
        self.generator = llm_toolkit.LLM(tokens=tokens)
        
    def get_context(self, allergens, date, order_time) -> str:
        start = time.time()
        year, month, day = map(int, date.split("-"))
        day_of_week = DAYS_OF_WEEK[calendar.weekday(year, month, day)]

        combined = pd.merge(self.menu_items, self.restaurants, on="rtr_id", how="left")

        ## Removes restaurants that are closed during the order time
        for index, rows in self.restaurants.iterrows():
            opening_times = json.loads(rows["hours"])[day_of_week]
            if len(opening_times) % 2 == 1:
                print("Odd opening times - cannot process")
                combined = combined[combined["rtr_id"] != rows["rtr_id"]]
            elif len(opening_times) >= 2:
                open = False
                for x in range(int(len(opening_times) / 2)):
                    if opening_times[x*2] < order_time and opening_times[x*2+1] > order_time:
                        open = True
                if not open:
                    combined = combined[combined["rtr_id"] != rows["rtr_id"]]
            else:
                combined = combined[combined["rtr_id"] != rows["rtr_id"]]

        ## Removes items that contain allergens
        for index, rows in combined.iterrows():
            item_allergens = []
            if rows["allergens"] is not None:
                item_allergens = rows['allergens'].split(',')
            if any (allergen in item_allergens for allergen in allergens.split(',')):
                combined.drop(index, inplace=True)

        ## Randomly selects ITEM_CHOICES number of items to present to the LLM
        num_items = combined.shape[0]
        choices = range(num_items)
        if num_items > ITEM_CHOICES:
            choices = random.sample(choices, ITEM_CHOICES)

        context_data = "item_id,name,description,price,calories\n"
        
        for x in choices:
            row = combined.iloc[x]
            context_data += f"{row['itm_id']},{row['name']},{row['description']},{row['price']},{row['calories']}\n"

        end = time.time()
        print("Context blocks generated in %.4f seconds" % (end - start))
        return context_data

    def pick_menu_item(self, preferences, allergens, date, meal_number) -> int:
        
        order_time = 0
        meal = ""
        match meal_number:
            case 1:
                meal = "breakfast"
                order_time = BREAKFAST_TIME
            case 2:
                meal = "lunch"
                order_time = LUNCH_TIME
            case 3:
                meal = "dinner"
                order_time = DINNER_TIME
            case _:
                raise ValueError("The meal number must be 1, 2, or 3")

        context = self.get_context(allergens, date, order_time)

        system = "You are a health and nutrition expert planning meals for a customer based on their preferences. Use only the menu items provided under CSV CONTEXT."
        prompt = f'''Choose a meal for a customer based on their preferences: {preferences}
Make sure that the item makes sense for {meal}.
Provide only the itm_id as output

CSV CONTEXT:
{context}'''

        llm_output = self.generator.generate(system, prompt)
        
        match = "<\|start_of_role\|>assistant<\|end_of_role\|>(\d+)<\|end_of_text\|>"
        output = int(re.search(match, llm_output).group(1))

        return output
