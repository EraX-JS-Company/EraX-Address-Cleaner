import os
import json
from typing import List, Dict
import io
import base64
import requests
import redis.asyncio as redis
import httpx
import asyncio
import yaml
from json_repair import repair_json

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi import (
    FastAPI,
    Header,
    Request,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles

from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

from pydantic import BaseModel, Field
from loguru import logger
from pathlib import Path
from contextlib import asynccontextmanager

from utils import load_data, load_prompt
from dotenv import load_dotenv
if os.path.exists(".env"):
    load_dotenv(".env")

########## LOAD DATA ##########
GEMINI_KEY = os.getenv("GEMINI_KEY")
data_address_dict = load_data()
url  = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-002:generateContent?key={GEMINI_KEY}"
TOKENS = os.getenv("TOKENS").split(",")


########## CUSTOM ASYNC FUNCTION ##########
async def gemini_caller(prompt):
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    data = {
        'contents': [{
            'parts': [{
                'text': prompt
            }]
        }],
        'generationConfig': {
            'temperature': 1.0, # 1.0
            'topP': 0.85, # 0.8
            'topK': 20 # 10
        },
        'safetySettings': [{
                'category': 'HARM_CATEGORY_DANGEROUS_CONTENT',
                'threshold': 'BLOCK_NONE'
            },
            {
                'category': 'HARM_CATEGORY_HARASSMENT',
                'threshold': 'BLOCK_NONE'
            },
            {
                'category': 'HARM_CATEGORY_HATE_SPEECH',
                'threshold': 'BLOCK_NONE'
            },
            {
                'category': 'HARM_CATEGORY_SEXUALLY_EXPLICIT',
                'threshold': 'BLOCK_NONE'
            }],
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url=url, headers=headers, json=data)

    if resp.status_code == 200:
        answer = resp.json()
        text = answer['candidates'][0]['content']['parts'][0]['text']
        return json.loads(repair_json(text.strip()))
    else:
        raise HTTPException(status_code=400, detail="Error in processing.")
            
    return None

async def clean_province(address):
    
    # PROMPT 1 - `tỉnh - thành phố
    province_list = ", ".join([i for i in data_address_dict.keys()])
    prompt_1 = await load_prompt('./prompt/prompt_1.txt')
    prompt_1_completed = prompt_1.replace('{province_list}', province_list)\
                                .replace('{address}', address)
    logger.info("clean_province")
    # print(prompt_1_completed)
    province = await gemini_caller(prompt_1_completed)
    province = province['province']
    return province

async def clean_district(address, province):
    # PROMPT 2 - quận - huyện - thị xã
    district_dict = data_address_dict[province]
    district_list = [i for i in district_dict.keys()]
    district_str = ", ".join(district_list)
    
    prompt_2 = await load_prompt('./prompt/prompt_2.txt')
    prompt_2_completed = prompt_2.replace('{num_district}', str(len(district_list)))\
                                .replace('{province}', province)\
                                .replace('{district_str}', district_str)\
                                .replace('{address}', address)
    logger.info("clean_district")
    # print(prompt_2_completed)
    
    district = await gemini_caller(prompt_2_completed)
    district = district['district']
    return district

async def clean_town(address, province, district):
    # Lấy danh sách các xã/phường/thị trấn của tỉnh và huyện
    town_dict = data_address_dict[province][district]
    town_list = list(town_dict.keys())  # Danh sách xã, phường, thị trấn
    town_str = ", ".join(town_list)  # Danh sách các xã/phường/thị trấn nối với nhau bằng dấu phẩy
    num_town = len(town_list)  # Số lượng các xã/phường/thị trấn

    # Load và thay thế các giá trị trong prompt
    prompt_3 = await load_prompt('./prompt/prompt_3.1.txt')
    prompt_3_completed = prompt_3.replace('{num_town}', str(num_town))\
                                  .replace('{dictrict}', district)\
                                  .replace('{town_str}', town_str)\
                                  .replace('{address}', address)
    logger.info("clean_town")
    # print(prompt_3_completed)  # In ra prompt đã được hoàn chỉnh

    # Gọi API hoặc function xử lý (gemini_caller)
    result = await gemini_caller(prompt_3_completed)
    return result['town']

async def clean_district_town(address, province):
    # Lấy danh sách các xã/phường/thị trấn ở tỉnh theo quận huyện
    district_dict = data_address_dict[province]
    district_town_list = [] # Danh sách xã, phường, thị trấn theo quận huyện
    for district, town_dict in district_dict.items():
        for town, _ in town_dict.items():
            district_town_list.append(f"{district}, {town}")
    
    district_town_str = "\n- ".join(district_town_list)  # Danh sách các xã/phường/thị trấn theo quận huyện nối với nhau bằng dấu phẩy
    num_district_town = len(district_town_list)  # Số lượng các xã/phường/thị trấn theo quận huyện

    # Load và thay thế các giá trị trong prompt
    prompt_3 = await load_prompt('./prompt/prompt_3.2.txt')
    prompt_3_completed = prompt_3.replace('{num_district_town}', str(num_district_town))\
                                  .replace('{province}', province)\
                                  .replace('{district_town_str}', district_town_str)\
                                  .replace('{address}', address)
    logger.info("clean_district_town")
    # print(prompt_3_completed)  # In ra prompt đã được hoàn chỉnh

    # Gọi API hoặc function xử lý (gemini_caller)
    result = await gemini_caller(prompt_3_completed)
    return result

async def clean_address_full(address, province, district, town):
    prompt_4 = await load_prompt('./prompt/prompt_4.txt')
    prompt_4_completed = prompt_4.replace('{province}', province)\
                                 .replace('{district}', district)\
                                 .replace('{town}', town)\
                                 .replace('{dirty_address}', address)

    logger.info("clean_address_full")
    #print(prompt_4_completed)
    cleaned_address = await gemini_caller(prompt_4_completed) 
    return cleaned_address

async def clean_address_pipeline(address):
    address=address.strip()
     # PROMPT 4 - địa chỉ
    province = await clean_province(address)
    province_list = ", ".join([i for i in data_address_dict.keys()])
    if province not in province_list:
        province = district = town = vi_address = en_address = "Không xác định"
    else:   
        district = await clean_district(address,province)
        district_list = ", ".join([i for i in data_address_dict[province].keys()])
        if district not in district_list:
            district = await clean_district_town(address, province)
            district = district['district']
            town = await clean_district_town(address, province)
            town = town['town']
        else:
            town = await clean_town(address,province,district)

        cleaned_address = await clean_address_full(address, province, district, town)
    
        # Trích xuất các phần của địa chỉ đã làm sạch
        vi_address = cleaned_address.get("vi_address")  # Địa chỉ bằng tiếng Việt
        en_address = cleaned_address.get("en_address")  # Địa chỉ dịch sang tiếng Anh
    
    # Tạo kết quả JSON
    result = {
        "raw_address": address,
        "address_components": {
            "province": province,
            "district": district,
            "town":town
        },
        "clean_address": {
            "vi_address": vi_address,
            "en_address": en_address
        }      
    }
    
    # Ghi kết quả vào file JSON
    # with open('/home/workspace/nguyenthaovy/GoogleMapApi/Api_clean_address/cleaned_address_3.json', 'w', encoding='utf-8') as f:
    #     json.dump(result, f, ensure_ascii=False, indent=4)
    return result

########## PYDANTIC ##########
class RequestBody(BaseModel):
    """Làm sạch địa chỉ theo các cấp đơn vị hành chính tại Việt Nam."""
    address: str = Field(default="", description="Địa chỉ bẩn.")

########## FASTAPI ##########
@asynccontextmanager
async def lifespan(_: FastAPI):
    redis_connection = redis.from_url("redis://localhost:6380", encoding="utf8")
    await FastAPILimiter.init(redis_connection)
    yield
    await FastAPILimiter.close()

tags_metadata = [
    {
        "name": "Làm sạch địa chỉ.",
        "description": "Hỗ trợ làm sạch địa chỉ theo các cấp đơn vị hành chính tại Việt Nam.",
    },
]

app = FastAPI(
    lifespan=lifespan,
    swagger_ui_parameters={
        "syntaxHighlight.theme": "obsidian",
    },
    title="EraX-Address-Cleaner",
    description='''<img src="/static/media/logo.png" width="200" alt="erax-logo"><br>
    Dịch vụ cung cấp giao diện lập trình ứng dụng (API) hỗ trợ làm sạch địa chỉ theo các cấp đơn vị hành chính tại Việt Nam.''',
    version="0.8",
    contact={
        "name": "EraX",
        "url": "https://github.com/EraX-JS-Company",
        "email": "nguyen@erax.ai",
    },

    openapi_tags=tags_metadata
)

app.mount("/static", StaticFiles(directory="."), name="static")

bearer_security = HTTPBearer()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Validate 
def validate_token(token: HTTPAuthorizationCredentials = Depends(bearer_security)):
    if token.credentials not in TOKENS:
        raise HTTPException(status_code=403, detail="Invalid or missing token")
    return token.credentials

async def token_identifier(token: str = Depends(validate_token)):
    return token

# Endpoints
@app.post("/clean_address", dependencies=[Depends(RateLimiter(times=10, seconds=5, identifier=token_identifier))], tags=["Làm sạch địa chỉ."])
async def clean_adsress(
    request_body: RequestBody,
    token: HTTPAuthorizationCredentials = Depends(validate_token)
):
    logger.info("Clean Adsress is called.")
    

    # Get prompt
    if request_body.address == "":
        raise HTTPException(status_code=400, detail="Invalid address.")
    else:
        address = request_body.address
        
    logger.info(f"--> Clean {address}")
    logger.info("Call Gemini API...")

    cleaned_address = await clean_address_pipeline(address)
    logger.info("Gemini API called sucessfully.")

    return cleaned_address
















