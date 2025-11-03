import os
import pandas as pd
import calendar
import time
import json
import random
import re
from typing import Tuple, List

import llm_toolkit as llm_toolkit
from sqlQueries import *

db_file = os.path.join(os.path.dirname(__file__), 'CSC510_DB.db')

## Increase to increase the sample size the AI can draw from at the cost of increased runtime
ITEM_CHOICES = 10

## Days of the week in an array - should be the same as in the database*
DAYS_OF_WEEK = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

## LLM Prompt - defined as global variables to enable testing
SYSTEM_TEMPLATE = "You are a health and nutrition expert planning meals for a customer based on their preferences. Use only the menu items provided under CSV CONTEXT."
PROMPT_TEMPLATE = '''Choose a meal for a customer based on their preferences: {preferences}
Make sure that the item makes sense for {meal}.
Provide only the itm_id as output

CSV CONTEXT:
{context}'''

## Regex used for finding LLM Output
LLM_OUTPUT_MATCH = r"<\|start_of_role\|>assistant<\|end_of_role\|>(\d+)<\|end_of_text\|>"

## Preset Meal times - In the future, times will be user-provided
BREAKFAST_TIME = 1000
LUNCH_TIME = 1400
DINNER_TIME = 2000



"""
Maps a meal number to it's cooresponding meal as a string as well as its cooreponding meal time

Args:
    meal_number (int): The meal number to get the meal and order times for

Returns:
    meal (str): The name of the meal as a string ("breakfast", "lunch", or "dinner")
    order_time (int): The time the meal is typically ordered at in HHMM format (in 24H time)

Raises:
    ValueError: if meal_number is not 1, 2, or 3
"""
def get_meal_and_order_time(meal_number : int) -> Tuple[str, int]:
    meal = ""
    order_time = -1
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
    return meal, order_time

"""
Converts a date string in YYYY-MM-DD format to the corresponding day of the week

Args:
    date (str): The date string in YYYY-MM-DD format

Returns:
    weekday (str): The corresponding day of the week ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

Raises:
    ValueError: if the date string is not in the correct format (YYYY-MM-DD) or is invalid
"""
def get_weekday(date: str) -> str:
    year, month, day = map(int, date.split("-"))
    try:
        return DAYS_OF_WEEK[calendar.weekday(year, month, day)]
    except:
        raise ValueError("Unable to parse date string. Ensure it is formatted properly as to YYYY-MM-DD format")

"""
Grabs the LLM output and extracts the item ID from it

Args:
    output (str): The output from the llm_toolkit LLM

Returns:
    itm_id (int): The item ID extracted from the LLM output

Raises:
    ValueError: if the LLM output does not match the expected format or if multiple matches are found
"""
def format_llm_output(output: str) -> int:
    print(output)
    match = LLM_OUTPUT_MATCH
    result = int(re.search(match, output).group(1))
    try:
        print(re.search(match, output).group(2))
        raise ValueError("Injection attack may have gotten through. There should not be multiple matches for LLM output.")
    except Exception:
        None   
    return result

"""
Limits the number of items to ITEM_CHOICES by randomly selecting items if necessary

Args:
    items (pd.DataFrame): The dataframe containing the items

Returns:
    choices (List[int]): The list of item_ids of the selected items
"""
def limit_scope(items: pd.DataFrame) -> List[int]:
    num_items = items.shape[0]
    choices = range(num_items)
    if num_items > ITEM_CHOICES:
        choices = random.sample(choices, ITEM_CHOICES)
    return choices

"""
Filters out menu items that contain any of the specified allergens from the provided DataFrame

Args:
    menu_items (pd.DataFrame): The DataFrame containing the menu items
    allergens (str): A comma-separated string of allergens to filter out

Returns:
    pd.DataFrame: The filtered DataFrame with menu items containing the specified allergens removed
"""
def filter_allergens(menu_items: pd.DataFrame, allergens: str) -> pd.DataFrame:
    for index, rows in menu_items.iterrows():
        if rows["allergens"] is not None:
            item_allergens = rows['allergens'].split(',')
            if any (allergen in item_allergens for allergen in allergens.split(',')):
                menu_items.drop(index, inplace=True)
    return menu_items

"""
Filters out restaurants that are closed at the specified time on the specified weekday

Args:
    restaurant (pd.DataFrame): The DataFrame containing the restaurant data
    weekday (str): The day of the week to check (e.g., "Mon", "Tue", etc.)
    time (int): The time to check in HHMM format (24H time)

Returns:
    pd.DataFrame: The filtered DataFrame with closed restaurants removed
"""
def filter_closed_restaurants(restaurant: pd.DataFrame, weekday: str, time: int) -> pd.DataFrame:
    for index, rows in restaurant.iterrows():
        opening_times = json.loads(rows["hours"])[weekday]
        if len(opening_times) % 2 == 1:
            print("Odd opening times - cannot process")
            restaurant = restaurant[restaurant["rtr_id"] != rows["rtr_id"]]
        elif len(opening_times) >= 2:
            open = False
            for x in range(int(len(opening_times) / 2)):
                if opening_times[x*2] <= time and opening_times[x*2+1] >= time:
                    open = True
            if not open:
                restaurant = restaurant[restaurant["rtr_id"] != rows["rtr_id"]]
        else:
            restaurant = restaurant[restaurant["rtr_id"] != rows["rtr_id"]]
    return restaurant


"""
MenuGenerator class that uses an LLM to generate menu items based on user preferences and restrictions
"""
class MenuGenerator:

    """
    Initializes the MenuGenerator with menu items and restaurants from the database and initializes
    the local LLM.
    Args:
        tokens (int): The number of tokens to use for the LLM generation
    """
    def __init__(self, tokens: int = 500):
        conn = create_connection(db_file)
        self.menu_items = pd.read_sql_query("SELECT * FROM MenuItem WHERE instock == 1", conn)
        self.restaurants = pd.read_sql_query("SELECT rtr_id, hours FROM Restaurant WHERE status==\"Open\"", conn)
        close_connection(conn)
        
        self.generator = llm_toolkit.LLM(tokens=tokens)

    """
    Generates the context block for the LLM based on the provided allergens, date, and order time

    Args:
        allergens (str): A comma-separated string of allergens to filter out
        date (str): The date string in YYYY-MM-DD format
        order_time (int): The time the meal is typically ordered at in HHMM format (in 24H time)
    
    Returns:
        context (str): The context block for the LLM in CSV format
    """
    def get_context(self, allergens: str, date: str, order_time:int) -> str:
        start = time.time()
        
        combined = pd.merge(self.menu_items, self.restaurants, on="rtr_id", how="left")

        ## Removes restaurants that are closed during the order time
        combined = filter_closed_restaurants(combined, get_weekday(date), order_time)
        
        ## Removes items that contain allergens
        combined = filter_allergens(combined, allergens)

        ## Randomly selects ITEM_CHOICES number of items to present to the LLM
        choices = limit_scope(combined)

        context_data = "item_id,name,description,price,calories\n"
        
        for x in choices:
            row = combined.iloc[x]
            context_data += f"{row['itm_id']},{row['name']},{row['description']},{row['price']},{row['calories']}\n"

        end = time.time()
        print("Context block generated in %.4f seconds" % (end - start))
        return context_data

    """
    Picks a menu item based on user preferences, allergens, date, and meal number

    Args:
        preferences (str): A comma-separated string of user preferences
        allergens (str): A comma-separated string of allergens to filter out
        date (str): The date string in YYYY-MM-DD format
        meal_number (int): The meal number (1 for breakfast, 2 for lunch, 3 for dinner)

    Returns:
        itm_id (int): The item_id of the selected menu item
    """
    def pick_menu_item(self, preferences: str, allergens: str, date: str, meal_number: int) -> int:
        
        meal, order_time = get_meal_and_order_time(meal_number)

        context = self.get_context(allergens, date, order_time)

        system = SYSTEM_TEMPLATE
        prompt = PROMPT_TEMPLATE
        
        prompt = prompt.replace("{preferences}", preferences)
        prompt = prompt.replace("{context}", context)
        prompt = prompt.replace("{meal}", meal)

        llm_output = self.generator.generate(system, prompt)
        return format_llm_output(llm_output)
    
    """
    Updates the menu string with a new menu item based on user preferences, allergens, date, and meal number
    
    Args:
        menu (str): The current menu string (can be empty or None)
        preferences (str): A comma-separated string of user preferences
        allergens (str): A comma-separated string of allergens to avoid
        date (str): The date string in YYYY-MM-DD format
        meal_number (int): The meal number (1 for breakfast, 2 for lunch, 3 for dinner)
    
    Returns:
        menu (str): The updated menu string
    """
    def update_menu(self, menu: str, preferences: str, allergens: str, date: str, meal_number: int) -> str:
        itm_id = self.pick_menu_item(preferences, allergens, date, meal_number)
        if menu is None or len(menu) < 1:
            return f"[{date},{itm_id},{meal_number}]"
        return f"{menu},[{date},{itm_id},{meal_number}]"
        