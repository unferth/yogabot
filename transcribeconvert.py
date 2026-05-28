# transcribeconvert.py
# converts a transcript to a format yogabot can read.
# usage: python transcribeconvert.py FOLDERNAME

import os
import sys
import re
from pathlib import Path
import spacy

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Downloading spaCy model... please wait.")
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

# Timings for specific movement cues (added to the block's total time)
SLOW_KEYWORDS = {
    'slow': 10, 'slowly': 15, 'pause': 20, 'hold': 15, 
    'breathe': 10, 'deep': 10, 'quiet': 20, 'rest': 20
}

MOVEMENT_INDICATORS = {
    'step', 'reach', 'bend', 'lower', 'lift', 'stretch', 'press', 'send', 
    'place', 'bring', 'roll', 'fold', 'drop', 'open', 'round', 'inhale', 
    'exhale', 'come', 'walk', 'extend', 'draw', 'curl', 'straighten', 'turn',
    'up', 'down', 'forward', 'back', 'left', 'right', 'side', 'wide', 'into',
    'cross', 'criss', 'pedal', 'sawing', 'interlace', 'wobble', 'shake', 'sit'
}

ANATOMY_AND_PROPS = {
    'foot', 'feet', 'hand', 'hands', 'knee', 'knees', 'hip', 'hips', 'pose', 
    'spine', 'chest', 'chin', 'navel', 'abs', 'belly', 'finger', 'fingertips', 
    'toe', 'toes', 'neck', 'head', 'arm', 'arms', 'palm', 'palms', 'wrist', 
    'wrists', 'shoulder', 'shoulders', 'leg', 'legs', 'heel', 'heels', 'thigh', 
    'thighs', 'mat', 'floor', 'ground', 'blanket', 'block', 'strap', 'seat',
    'tabletop', 'dog', 'plank', 'child', 'cat', 'cow', 'lunge', 'body', 'tailbone'
}

def trim_and_clean(raw_text):
    """Cleans up the raw transcription artifacts and structural marks."""
    cleaned = re.sub(r'[\(\[][^\]\)]*?[\)\]]', '', raw_text)
    cleaned = re.sub(r'^\s*-\s*', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def calculate_sentence_duration(text_segment):
    """Calculates the time weight of an individual sentence based on keywords."""
    base = 10  # Quick 10s baseline per sentence
    lower_text = text_segment.lower()
    for keyword, bonus in SLOW_KEYWORDS.items():
        base += lower_text.count(keyword) * bonus
    return base

def is_instructional(sentence_text):
    """Filters out heavy promotional filler, keeping core physical concepts."""
    lower_text = sentence_text.lower()
    if any(filler in lower_text for filler in ["welcome back", "subscribe", "channel"]):
        return False
    
    words = set(re.findall(r'\b\w+\b', lower_text))
    return not words.isdisjoint(MOVEMENT_INDICATORS) or not words.isdisjoint(ANATOMY_AND_PROPS)

def process_transcript(file_content, filename_clean="workout"):
    """
    Groups filtered sentences into continuous blocks of roughly 2-3 sentences, 
    aggregating their durations seamlessly.
    """
    cleaned_text = trim_and_clean(file_content)
    doc = nlp(cleaned_text)
    
    output_lines = [f"12:00 pm {filename_clean}"]
    sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
    
    if not sentences:
        return ""

    current_block = []
    current_block_time = 0
    
    for sentence in sentences:
        # Check if the sentence has any instructional value
        if not is_instructional(sentence):
            continue
            
        sentence_time = calculate_sentence_duration(sentence)
        current_block.append(sentence)
        current_block_time += sentence_time
        
        # Once the block hits a natural chunk size (approx 25+ words or 2-3 sentences)
        # or accumulates over 35 seconds of movement, flush it out.
        block_word_count = len(" ".join(current_block).split())
        
        if len(current_block) >= 3 or block_word_count >= 25 or current_block_time >= 45:
            # Round the time up to the nearest clean 5 or 10 second mark for readability
            rounded_time = max(20, int(5 * round(current_block_time / 5)))
            combined_text = " ".join(current_block)
            output_lines.append(f"[{rounded_time}s] {combined_text}")
            
            # Reset buffers
            current_block = []
            current_block_time = 0
            
    # Flush any trailing sentences left over in the final buffer
    if current_block:
        rounded_time = max(30, int(5 * round(current_block_time / 5)))
        combined_text = " ".join(current_block)
        output_lines.append(f"[{rounded_time}s] {combined_text}")
            
    return "\n".join(output_lines)

def convert_folder(folder_path):
    """Loops through directory and outputs bundled multi-sentence files."""
    dir_path = Path(folder_path)
    if not dir_path.is_dir():
        print(f"Error: Directory '{folder_path}' does not exist.")
        return

    txt_files = [f for f in dir_path.glob("*.txt") if not f.stem.endswith("_ybc")]
    if not txt_files:
        print("No eligible text files found.")
        return
        
    print(f"Found {len(txt_files)} file(s) to convert into workout blocks...\n")
    
    for file_path in txt_files:
        print(f"Processing: {file_path.name}")
        
        # Dynamically grab a clean label from the filename to use in the header
        clean_title = file_path.stem.replace("-", " ").replace("_", " ")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        converted_content = process_transcript(content, filename_clean=clean_title)
        
        new_file_path = file_path.with_name(f"{file_path.stem}_ybc{file_path.suffix}")
        with open(new_file_path, 'w', encoding='utf-8') as f:
            f.write(converted_content)
            
        print(f"-> Successfully saved packaged blocks to: {new_file_path.name}")
    
    print("\nAll files successfully bundled!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python transcribeconvert.py <path_to_folder>")
        sys.exit(1)
    convert_folder(sys.argv[1])