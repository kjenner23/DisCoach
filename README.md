# DisCoach – Table Tennis Coaching Agent

This purpose of this project is to scrape, clean, and structure table tennis blogs and articles into a JSON
format suitable for LLM training. 

## 🚀 Features
- Scrapes text articles from tabletenniscoaching.com, pingskills.com, and experttabletennis.com
- Converts raw TXT articles into structured JSON 
- Processes entire datasets in batch mode
- Organizes processed outputs for use in a training pipeline
- Includes prompts and FastAPI endpoints for interacting with the agent

## 📂 Project Structure
tabletennis_agent/
│
├── app/                                   # All project code
│   │
│   ├── Scripts/                           # Main Python scripts
│   │   └── Text Processor/                # Organized text-processing pipeline
│   │       ├── batch_process.py           # Batch JSON transformation script
│   │       └── main.py                    # Core processing / entry point
│   │
│   ├── prompts/                           # Prompt templates for LLM processing
│   │   └── article_to_json_prompt.txt     # LLM prompt for JSON formatting
│   │
│   └── __pycache__/                       # Ignored (Python cache files)
│
├── data/                                   # Raw input files
│   ├── TableTennisCoaching.com/            # Raw scraped text files
│   │   ├── Scraped output.txt              # Unprocessed raw dump
│   │   └── ...                             # Additional raw data
│   │
│   └── .DS_Store                           # Ignored (macOS metadata)
│
├── processed/                              # Processed outputs ready for training
│   ├── JSON outputs/
│   │   ├── Blogs/
│   │   │   ├── ExpertTableTennis/          # Cleaned TXT from ExpertTableTennis
│   │   │   │   ├── (1) OCT_2_2025.txt
│   │   │   │   ├── (2) OCT_2_2025.txt
│   │   │   │   └── ...
│   │   │   │
│   │   │   └── PingSkills/                 # JSON articles from PingSkills
│   │   │       ├── (10) OCT_8_2025.json
│   │   │       └── ...
│   │   │
│   │   └── raw.json                        # Combined or unstructured JSON
│   │
│   └── TableTennisCoaching.com/            # Earlier processed JSON articles
│       ├── Before Nov 20 2025/
│       ├── Nov 20 2025/
│       └── ...
│
├── notes/                                  # Project notes and documentation
│
├── .gitignore                              # Ignore cache, venv, system files
├── README.md                               # Project documentation
└── .DS_Store                               # Ignored (macOS system file)

