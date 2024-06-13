#!/home/kebokatsu/Projects/RecipeReplay/env/bin/python3

import asyncio 
from dotenv import load_dotenv
from moviepy.editor import VideoFileClip
from openai import OpenAI
import os 
from playwright.async_api import async_playwright 
from pydub import AudioSegment
import requests 
import sys
import tiktoken 
import yt_dlp 



load_dotenv('keys.env') 

OPENAI_KEY = os.environ.get('SECRET_KEY') 
client = OpenAI(api_key=OPENAI_KEY)
GPT_TURBO_MAX_TOKENS = 4096
# instagram_video = "https://www.instagram.com/reel/C272uxmAVe3/?utm_source=ig_web_copy_link&igsh=MzRlODBiNWFlZA=="

# STEP 1: DOWNLOAD IG VIDEO 
async def download_instagram_video(instagram_url: str): 
    async with async_playwright() as playwright: 
        firefox = playwright.firefox
        browser = await firefox.launch(headless=True) 
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

def download_youtube_video(youtube_url: str): 
    video_path = './video.mp4'
    
    ydl_options = { 
        'format': 'best', 
        'outtmpl': video_path
    }

    with yt_dlp.YoutubeDL(ydl_options) as ydl: 
        ydl.download([cooking_url])

    return video_path

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
    file_size = os.path.getsize(audio_path)

    if file_size > 26214400: 
        audio_path = compress_audio(audio_path)

    print(f"video_to_audio[audio_path: {audio_path}])")
    return audio_path 

def compress_audio(audio_file: str): 
    """
    Compresses .wav file to a .mp3 file. This is done to compress the size of the file, 
    so that it will hopefully work with OpenAI's Whisper API .

    Args: 
        audio_file (str): The path to the audio file to be compressed. This path can 
        be either absolute or relative. 

    Returns: 
        The path to audio_file. Also saves the audio to the directory. 
    """
    mp3_path = "./audio.mp3"

    audio = AudioSegment.from_wav(audio_file)

    audio.export(mp3_path, format='mp3', bitrate='64k') 

    return mp3_path  


# STEP 3: TRANSCRIBE AUDIO TO TEXT 
def speech_to_text_whisper(audio_path): 
    audio_file = open(audio_path, "rb")
    transcription = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file
    )

    if transcription: 
        # with open('transcription.txt', 'w') as file: 
        #     file.write(transcription.text) 
        return transcription.text
    
def summarize_steps(instructions): 
    prompt_tokens = count_tokens(instructions)

    if prompt_tokens < GPT_TURBO_MAX_TOKENS: 
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=[
                {"role": "system", "content": "You're an at-home-chef assistant, skilled in formatting & summarizing instructions for cooking different dishes."}, 
                {"role": "user", "content": f"""Could you format & summarize these instructions for cooking this meal in a markdown format: {instructions}\n\n
                                                I need you to have 2 sections, Ingredients & Instructions. If the amount of an ingredient is metioned, make
                                                sure to mention that in the ingredient section. If the temperature for a cooking appliance is stated, 
                                                be sure to include that as well. Thank you."""}
            ]
        )

        if completion: 
            return completion.choices[0].message 
    else: 
        return "Prompt is too large to use with OpenAI's GPT API."
    
def count_tokens(instructions): 
    prompt = """Could you format & summarize these instructions for cooking this meal in a markdown format: {instructions}\n\n
                I need you to have 2 sections, Ingredients & Instructions. If the amount of an ingredient is metioned, make
                sure to mention that in the ingredient section. If the temperature for a cooking appliance is stated, 
                be sure to include that as well. Thank you."""
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    num_tokens = len(encoding.encode(prompt))

    return num_tokens 

def write_instructions_to_markdown(instructions): 
    instructions = instructions.content 
    file_name = "recipe.md" 

    with open(file_name, "w") as file: 
        file.write(instructions) 
    
    print(f"Content saved to {file_name}")

def main(cooking_url): 
    # video_path = asyncio.run(download_instagram_video(cooking_url))
    video_path = download_youtube_video(cooking_url) 
    audio_path = video_to_audio(video_path)
    transcription = speech_to_text_whisper(audio_path) 
    # print(f'transcription length: {len(transcription)}') 
    instructions = summarize_steps(transcription)
    write_instructions_to_markdown(instructions) 
    os.remove(video_path)
    os.remove(audio_path)
    print(instructions.content)
    

if __name__ == '__main__':
    if len(sys.argv) < 2: 
        print("Usage: python3 recipe_replay.py <cooking_url>")
    else: 
        cooking_url = sys.argv[1] 
        main(cooking_url)