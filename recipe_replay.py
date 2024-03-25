#!/home/kebokatsu/Projects/RecipeReplay/env/bin/python3

import asyncio 
from dotenv import load_dotenv
from moviepy.editor import VideoFileClip
from openai import OpenAI
import os 
from playwright.async_api import async_playwright 
import requests 
import sys


load_dotenv('keys.env') 

OPENAI_KEY = os.environ.get('SECRET_KEY') 
client = OpenAI(api_key=OPENAI_KEY)
# instagram_video = "https://www.instagram.com/reel/C272uxmAVe3/?utm_source=ig_web_copy_link&igsh=MzRlODBiNWFlZA=="

# STEP 1: DOWNLOAD IG VIDEO 
async def download_instagram_video(instagram_url: str): 
    async with async_playwright() as playwright: 
        firefox = playwright.firefox
        browser = await firefox.launch(headless=False) 
        page = await browser.new_page() 
        await page.goto("https://snapinsta.app/") 

        await page.get_by_placeholder('Paste URL Instagram').click() 
        await page.get_by_placeholder('Paste URL Instagram').fill(instagram_url) 
        print("first download")
        await page.get_by_role('button', name='Download', exact=True).nth(0).click() 
        await page.get_by_role('button', name='Close').click() 
        href = await page.locator("a.btn.download-media.flex-center").get_attribute('href') 
        print(href) 
        await browser.close() 

    video_path = "./video.mp4"

    response = requests.get(href, stream=True) 
    if response.status_code == 200: 
        with open(video_path, "wb") as file: 
            for chunk in response.iter_content(chunk_size=8192): 
                if chunk: 
                    file.write(chunk) 
        return video_path 
    else: 
        print("Error download video")
        return None 
        
# STEP 2: CONVERT FROM VIDEO TO AUDIO 
def video_to_audio(video_file: str): 
    """
    Converts a given video file to audio, specifically to .wav format.
    
    The function will extract the audio from a given video file and save it
    to a .wav file in a directory named "audio". If the directory does not exist, 
    it will be created.

    Args:
        video_file (str): The path to the video file to be converted. This path 
        can be either absolute or relative.

    Returns:
        None. The function saves the output audio file in the "audio" directory.
    """
    print(f"video_to_audio(videio_file: {video_file})")
    audio_path = "./output_audio.wav" 

    video = VideoFileClip(video_file) 
    audio = video.audio 
    audio.write_audiofile(audio_path, codec="pcm_s16le") # Needed to convert to .wav fil
    print(f"video_to_audio[audio_path: {audio_path}])")
    return audio_path 

# STEP 3: TRANSCRIBE AUDIO TO TEXT 
def speech_to_text_whisper(audio_path): 
    audio_file = open(audio_path, "rb")
    transcription = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file
    )

    if transcription: 
        return transcription.text
    
def summarize_steps(instructions): 
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo", 
        messages=[
            {"role": "system", "content": "You're an at-home-chef assistant, skilled in formatting & summarizing instructions for cooking different dishes."}, 
            {"role": "user", "content": f"Could you format & summarize these instructions for cooking this meal: {instructions}"}
        ]
    )

    if completion: 
        return completion.choices[0].message 

def write_instructions_to_markdown(instructions): 
    instructions = instructions.content 
    file_name = "recipe.md" 

    with open(file_name, "w") as file: 
        file.write(instructions) 
    
    print(f"Content saved to {file_name}")

def main(instagram_url): 
    video_path = asyncio.run(download_instagram_video(instagram_url))
    audio_path = video_to_audio(video_path)
    transcription = speech_to_text_whisper(audio_path) 
    instructions = summarize_steps(transcription)
    # write_instructions_to_markdown(instructions) 
    os.remove(video_path)
    os.remove(audio_path)
    print(instructions.content)
    

if __name__ == '__main__':
    if len(sys.argv) < 2: 
        print("Usage: python3 recipe_replay.py <instagram_url>")
    else: 
        instagram_url = sys.argv[1] 
        main(instagram_url)