import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import os
import time

from sqlQueries import create_connection, close_connection, fetch_one, fetch_all, execute_query

class LLM:

    device = "cpu"
    model = "ibm-granite/granite-4.0-micro"

    def __init__(self, tokens=500):
        self.tokenizer = AutoTokenizer.from_pretrained(self.model, cache_dir=os.path.join(os.path.dirname(__file__), '.hf_cache'))
        # drop device_map if running on CPU
        self.model = AutoModelForCausalLM.from_pretrained(self.model, device_map=self.device)
        self.model.eval()
        self.tokens = tokens

    def generate(self, context, prompt) -> str:
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
        ##output = self.tokenizer.batch_decode(output, skip_special_tokens=True)[0]
        ##output = output[len(chat):].strip()
        output = self.tokenizer.batch_decode(output)[0]
        end = time.time()
        print("Menu Item selected in %.4f seconds" % (end - start))
        return output