import time
import requests
import openai
import os
from config import *
from prompts import *

openai.api_key = OPENAI_API_KEY

BASE_URL = "https://api.clawgig.ai"
SKILLS_DIR = r"c:\Users\mohamed.elgendy\Desktop\blog\skills-main\skills dv"

def get_jobs():
    headers = {"Authorization": f"Bearer {CLAWGIG_API_KEY}"}
    r = requests.get(f"{BASE_URL}/jobs", headers=headers)
    return r.json()

def evaluate(task):
    res = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role":"user","content":EVALUATION_PROMPT.replace("{task_description}", task)}]
    )
    return res.choices[0].message.content.strip()

def price(task):
    res = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role":"user","content":PRICE_PROMPT.replace("{task_description}", task)}]
    )
    return res.choices[0].message.content.strip()

def classify_task(task):
    classification_prompt = f"""Analyze the following task and decide its category and a skill keyword.
Categories: TRANSLATION, WRITING, SKILL
Keyword: A single word representing the technical or specific skill needed (e.g., python, react, seo, marketing, docker). If no specific skill is needed, write NONE.

Format your response EXACTLY as: CATEGORY,KEYWORD
Example 1: SKILL,python
Example 2: TRANSLATION,NONE
Example 3: WRITING,seo

Task: {task}"""
    res = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role":"user","content":classification_prompt}]
    )
    return res.choices[0].message.content.strip().upper()

def find_skill_content(keyword):
    if keyword == "NONE" or not keyword:
        return ""
    try:
        if not os.path.exists(SKILLS_DIR):
            return ""
        for folder in os.listdir(SKILLS_DIR):
            if keyword.lower() in folder.lower():
                skill_path = os.path.join(SKILLS_DIR, folder, "SKILL.md")
                if os.path.exists(skill_path):
                    with open(skill_path, "r", encoding="utf-8") as f:
                        return f.read()
                readme_path = os.path.join(SKILLS_DIR, folder, "README.md")
                if os.path.exists(readme_path):
                    with open(readme_path, "r", encoding="utf-8") as f:
                        return f.read()
    except Exception as e:
        print(f"Error loading skill: {e}")
    return ""

def do_task(task, category, keyword):
    if "TRANSLATION" in category:
        final_prompt = TRANSLATION_PROMPT.replace("{task_description}", task)
    elif "SKILL" in category:
        skill_content = find_skill_content(keyword)
        if skill_content:
            final_prompt = SKILL_PROMPT.replace("{task_description}", task).replace("{skill_content}", skill_content)
            print(f"Loaded skill context for keyword: {keyword}")
        else:
            final_prompt = WRITING_PROMPT.replace("{task_description}", task)
            print(f"Skill not found for {keyword}, fallback to WRITING.")
    else:
        final_prompt = WRITING_PROMPT.replace("{task_description}", task)
        
    res = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role":"user","content":final_prompt}]
    )
    return res.choices[0].message.content

def submit_bid(job_id, price_value):
    headers = {"Authorization": f"Bearer {CLAWGIG_API_KEY}"}
    requests.post(f"{BASE_URL}/jobs/{job_id}/bid",
                  json={"price": price_value},
                  headers=headers)

def submit_work(job_id, result):
    headers = {"Authorization": f"Bearer {CLAWGIG_API_KEY}"}
    requests.post(f"{BASE_URL}/jobs/{job_id}/submit",
                  json={"result": result},
                  headers=headers)

if __name__ == "__main__":
    print("Agent Started with Skills Engine...")
    while True:
        try:
            jobs = get_jobs()
            if not isinstance(jobs, list):
                jobs = jobs.get("jobs", [])

            for job in jobs:
                task = job["description"]

                decision = evaluate(task)
                if "ACCEPT" not in decision.upper():
                    print(f"Skipped job {job.get('id')}: Not suitable.")
                    continue

                p = price(task)
                submit_bid(job["id"], p)
                print(f"Bid placed for job {job.get('id')} at ${p}")

                classification = classify_task(task)
                try:
                    category, keyword = classification.split(",")
                except:
                    category, keyword = "WRITING", "NONE"
                    
                print(f"Task {job.get('id')} classified as: {category} with skill: {keyword}")

                result = do_task(task, category.strip(), keyword.strip())
                
                submit_work(job["id"], result)
                print(f"Job {job.get('id')} completed and submitted.")

        except Exception as e:
            print(f"Error occurred: {e}")

        time.sleep(60)
