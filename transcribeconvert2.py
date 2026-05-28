# still in progress

import os, sys, re, math
from pathlib import Path

SLOW_KEYWORDS = {'slow': 10, 'slowly': 15, 'pause': 20, 'hold': 15, 'breathe': 10, 'deep': 10, 'quiet': 20, 'rest': 20}

def split_sentences(text):
    """Splits text into sentences cleanly without relying on massive external libraries."""
    text = re.sub(r'\s+', ' ', text).strip()
    return [s.strip() + '.' for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]

def calculate_duration(text):
    """Calculates time weight based on sentence content and custom slow words."""
    base = 10
    lower = text.lower()
    for kw, bonus in SLOW_KEYWORDS.items():
        base += lower.count(kw) * bonus
    return base

def process_transcript(content, title="workout"):
    # Strip double spaces but preserve all raw text content safely
    sentences = split_sentences(content.replace('\n', ' '))
    if not sentences: return ""
    
    output = [f"7:30 am {title}"] if "flow" in title.lower() else [f"12:00 pm {title}"]
    block, block_time = [], 0
    
    for sent in sentences:
        block.append(sent)
        block_time += calculate_duration(sent)
        word_count = len(" ".join(block).split())
        
        # Flush block when target sizes or timing constraints are hit
        if len(block) >= 3 or word_count >= 25 or block_time >= 45:
            rounded = max(30, int(5 * round(block_time / 5)))
            output.append(f"[{rounded}s] {' '.join(block)}")
            block, block_time = [], 0
            
    if block:
        rounded = max(30, int(5 * round(block_time / 5)))
        output.append(f"[{rounded}s] {' '.join(block)}")
        
    return "\n".join(output)

def convert_folder(folder_path):
    dir_path = Path(folder_path)
    if not dir_path.is_dir(): return print("Directory not found.")
    
    txt_files = [f for f in dir_path.glob("*.txt") if not f.stem.endswith("_ybc")]
    print(f"Found {len(txt_files)} file(s) to process...\n")
    
    for fp in txt_files:
        clean_title = fp.stem.replace("-", " ").replace("_", " ")
        with open(fp, 'r', encoding='utf-8') as f:
            converted = process_transcript(f.read(), title=clean_title)
            
        with open(fp.with_name(f"{fp.stem}_ybc{fp.suffix}"), 'w', encoding='utf-8') as f:
            f.write(converted)
        print(f"-> Saved: {fp.stem}_ybc{fp.suffix}")

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit("Usage: python transcribeconvert.py <folder>")
    convert_folder(sys.argv[1])
