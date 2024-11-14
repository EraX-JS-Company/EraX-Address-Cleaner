import aiofiles
import json

def load_data():
    with open('./config/tinh_huyen_xa.json', 'r', encoding='utf-8') as f:
        data_address_dict = json.load(f)
    return data_address_dict

async def load_prompt(path):
    async with aiofiles.open(path, 'r', encoding='utf8') as f:
        prompt = await f.read()
    return prompt