import llm_toolkit as llm_toolkit
from sqlQueries import *
import os

db_file = os.path.join(os.path.dirname(__file__), 'CSC510_DB.db')

class MenuGenerator:

    def __init__(self, tokens = 2000):
        self.generator = llm_toolkit.LLM(tokens=tokens)

    def load_menu_items_to_csv(self):
        conn = create_connection(db_file)
        cur = conn.cursor()
        cur.execute("SELECT * FROM MenuItem WHERE instock == 1")
        rows = cur.fetchall()
        close_connection(conn)
        return rows

    def generate_weekly_menu(self, preferences, allergens) -> str:
        
        conn = create_connection(db_file)
        cur = conn.cursor()
        cur.execute("SELECT * FROM MenuItem WHERE instock == 1")
        rows = cur.fetchall()
        close_connection(conn)
        for row in rows:
            print(row)

        context = "You are a health and nutrition expert planning meals for a customer based on their preferences and allergies"
        prompt = f'''Create a list of 3 meals for each day of the week for a customer based on their preferences and allergies.
                    Make sure the meals fit the preferences given: {preferences}. For example:
                     - if the preference is vegetarian, do not include any meat-based dishes
                     - if the preference is low carb, avoid dishes with high carbohydrate content such as bread, pasta, rice, and sugary foods
                    It is imperative that the meals avoid the following allergens {allergens}. 
                    Use only the following database menu items {rows} and that the selections are diverse unless if specified otherwise in the preferences. 
                    Format the output as a comment separated list of meals for each day of the week, starting on the monday of next week as so:
                    [2025-10-20,35,3],[2025-10-21,8,1],[2025-10-21,36,2],[2025-10-21,5,3],[2025-10-22,21,1],[2025-10-22,16,2]
                    where each entry is in the format [date, menu_item_id, meal_number] where meal_number is 1 for breakfast, 2 for lunch, and 3 for dinner.
                    Ensure that the dates correspond to the next week from the current date.
                    '''
        output = self.generator.generate(context, prompt)
        return output

    