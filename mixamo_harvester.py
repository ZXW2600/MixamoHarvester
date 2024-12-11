import requests
import time
import os
import json
import logging
from urllib.parse import urljoin
from tqdm import tqdm
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

BASE_URL = "https://www.mixamo.com/api/v1"
ANIMATIONS_PER_PAGE = 96
MAX_THREADS = 18  # Adjust this based on your system's capabilities
MAX_RETRY=15

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("Logging initialized")

def get_bearer_token():
    token_file = "mixamo_token.txt"
    if os.path.exists(token_file):
        with open(token_file, "r") as f:
            return f.read().strip()
    else:
        raise Exception(f"Bearer token not found. Please authenticate and save the token to {token_file}")

def get_character_list(bearer_token):
    character_file = "characters.json"
    if os.path.exists(character_file):
        with open(character_file, "r") as f:
            return json.load(f)

    characters = {}
    page = 1
    while True:
        url = f"{BASE_URL}/products?page={page}&limit=96&type=Character"
        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "X-Api-Key": "mixamo2",
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        if 'results' in data:
            new_characters = data['results']
            for char in new_characters:
                characters[char['id']] = {
                    "name": char['name'],
                    "character_type": char['character_type'],
                }

            if len(new_characters) < 96:
                break
            page += 1
        else:
            break

    with open(character_file, "w") as f:
        json.dump(characters, f)

    return characters

def get_animation_list(bearer_token, page=1):
    url = f"{BASE_URL}/products?page={page}&limit=96&order=&type=Motion%2CMotionPack&query="
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "X-Api-Key": "mixamo2",
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def get_product(bearer_token, anim_id, character_id):
    url = f"{BASE_URL}/products/{anim_id}?similar=0&character_id={character_id}"
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "X-Api-Key": "mixamo2",
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

@retry(
    stop=stop_after_attempt(MAX_RETRY),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type(requests.exceptions.RequestException)
)
def export_animation(bearer_token, character_id, gms_hash_array, product_name):
    url = f"{BASE_URL}/animations/export"
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "X-Api-Key": "mixamo2",
        "Content-Type": "application/json",
    }
    payload = {
        "character_id": character_id,
        "gms_hash": gms_hash_array,
        "preferences": {"format": "fbx7", "skin": "false", "fps": "60", "reducekf": "0"},
        "product_name": product_name,
        "type": "Motion"
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

@retry(
    stop=stop_after_attempt(MAX_RETRY),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type(requests.exceptions.RequestException)
)
def monitor_export_progress(bearer_token, character_id):
    url = f"{BASE_URL}/characters/{character_id}/monitor"
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "X-Api-Key": "mixamo2",
    }
    while True:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        if data['status'] == 'completed':
            return data['job_result']
        elif data['status'] == 'failed':
            raise Exception(f"Export failed: {data.get('message', 'Unknown error')}")

        time.sleep(5)

def load_state(output_dir):
    if os.path.exists('state.json'):
        with open('state.json', 'r') as f:
            return json.load(f)
    else:
        # walk the output directory and create the state
        state={}
        # find all L1 subdirectories
        for character_dir in os.listdir(output_dir):
            # get the character id
            character_id=character_dir.split("_")[-1]
            # get all the files in the directory
            files=os.listdir(os.path.join(output_dir,character_dir))
            state[character_id]=files
        with open('state.json', 'w') as f:
            json.dump(state, f)
        return state


def save_state(state):
    with open('state.json', 'w') as f:
        json.dump(state, f)

def download_animation(url, output_dir, filename, character_id):
    filepath = os.path.join(output_dir, filename)

    if os.path.exists(filepath):
        logging.info(f"⏭️  Skipping existing file: {filepath}")
        return

    response = requests.get(url, stream=True)
    response.raise_for_status()

    total_size = int(response.headers.get('content-length', 0))

    with open(filepath, 'wb') as f, tqdm(
        desc=f"[{character_id}] {filename}",
        total=total_size,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as progress_bar:
        for data in response.iter_content(chunk_size=1024):
            size = f.write(data)
            progress_bar.update(size)

    logging.info(f"✅ Downloaded: {filepath}")

def process_animation(bearer_token, character_id, animation, output_dir, state,failed_log_dir):
    if animation["type"]=="MotionPack":
        logging.info(f"⏭️ Skipping Motion Pack: {animation['name']}")
        return
    
    filename = f"{animation['name']}_{animation['motion_id']}_{character_id}.fbx"
    # replace invalid characters
    for c in ['/', '\\', '?', '%', '*', ':', '|', '"', '<', '>']:
        filename = filename.replace(c, '-')
    
    
    filepath = os.path.join(output_dir, filename)

    if os.path.exists(filepath):
        logging.info(f"⏭️ Skipping existing file: {filepath}")
        return

    if filename in state.get(character_id, []):
        logging.info(f"⏭️ Skipping already processed: {filename}")
        return

    try:
        product_data = get_product(bearer_token, animation['id'], character_id)
        gms_hash = product_data['details']['gms_hash']
        gms_hash['params'] = ','.join(str(param[1]) for param in gms_hash['params'])

        export_data = export_animation(bearer_token, character_id, [gms_hash], animation['name'])
        download_url = monitor_export_progress(bearer_token, character_id)

        download_animation(download_url, output_dir, filename, character_id)

        if character_id not in state:
            state[character_id] = []
        state[character_id].append(filename)
        save_state(state)
        return 
    except Exception as e:
        logging.error(f"❌ Error processing animation {animation['name']}: {str(e)}")
        with open(os.path.join(failed_log_dir,f"{character_id}_{animation['name']}_{animation['motion_id']}.json"), "w") as f:
            animation["error"]=str(e)
            json.dump(animation,f)

from tqdm import tqdm
def process_animations_for_character(bearer_token, character_id, output_dir, state,failed_log_dir):
    logging.info(f"🔄 Processing animations for character: {character_id}")
    page = 1
    total_animations = 0
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = []
        while True:
            logging.info(f"🔍 Fetching animations for page: {page}")
            try:
                animations_data = get_animation_list(bearer_token, page)
                animations = animations_data.get("results", [])
            except Exception as e:
                logging.error(f"❌ Error fetching animations: {str(e)}")
                time.sleep(5)
                continue
            logging.info(f"🔍 Found {len(animations)} animations on this page")
            if not animations:
                break
            
            for animation in animations:
                future = executor.submit(process_animation, bearer_token, character_id, animation, output_dir, state,failed_log_dir)
                futures.append(future)

            page += 1
            total_animations += len(animations)
        logging.info(f"🔍 Found a total of {total_animations} animations for character: {character_id}")
        for future in tqdm(as_completed(futures), total=len(futures),leave=True):
            ret=future.result()  # This will raise any exceptions that occurred during execution
    logging.info(f"✅ Completed processing for character: {character_id}")

def main():
    setup_logging()
    bearer_token = get_bearer_token()
    characters = get_character_list(bearer_token)

    output_dir = "animations"
    saved_file = load_state(output_dir)
    failed_log_dir="failed_logs"
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(failed_log_dir, exist_ok=True)
    for character_id in characters:
        character_name = characters[character_id]['name']
        foder_name=f"{character_name}_{character_id}"
        iter_output_dir=os.path.join(output_dir,foder_name)
        # check if the folder exists
        if not os.path.exists(iter_output_dir):
            os.makedirs(iter_output_dir, exist_ok=True)
        process_animations_for_character(bearer_token, character_id, iter_output_dir, saved_file,failed_log_dir=failed_log_dir)

    logging.info("🎉 Script execution completed")

if __name__ == "__main__":
    main()