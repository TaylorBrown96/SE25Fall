import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import os
import time

from proj2.sqlQueries import create_connection, close_connection, fetch_one, fetch_all, execute_query

"""
LLM class for local language model interactions
"""
class LLM:

    ## LLM parameters
    device = "gpu" if torch.cuda.is_available() else "cpu"
    model = "ibm-granite/granite-4.0-micro"

    """
    Initializes the LLM with the specified number of tokens

    Args:
        tokens (int): The max number of generated characters
    """
    def __init__(self, tokens: int = 500):
        self.tokenizer = AutoTokenizer.from_pretrained(self.model, cache_dir=os.path.join(os.path.dirname(__file__), '.hf_cache'))
        # drop device_map if running on CPU
        if self.device == "cpu":    
            self.model = AutoModelForCausalLM.from_pretrained(self.model, device_map=self.device)
        self.model.eval()
        self.tokens = tokens

    """
    Uses the local LLM to generate text based on the provided context and prompt

    Args:
        context (str): The system context to provide to the LLM
        prompt (str): The user prompt to provide to the LLM  

    Returns:
        str: The raw, unformatted output from the LLM
    """
    def generate(self, context: str, prompt: str) -> str:
        start = time.time()
        chat = [
            {"role": "system", "content": context},
            {"role": "user", "content": prompt},
        ]
        chat = self.tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
        # tokenize the text
        input_tokens = self.tokenizer(chat, return_tensors="pt").to(self.device)
        # generate output tokens
        output = self.model.generate(**input_tokens, 
                                    max_new_tokens=self.tokens)
        # decode output tokens into text
        output = self.tokenizer.batch_decode(output)[0]
        end = time.time()
        print("Menu Item selected in %.4f seconds" % (end - start))
        return output