"""
Script to obtain citations per year for downloaded papers
usage (inside root folder):  python ./scraping/get_citations.py
"""
import glob
import pandas as pd
import requests
import time
from collections import Counter
from tqdm import tqdm
import csv
import re
from dotenv import find_dotenv, load_dotenv
import os

YEARS = [2024,2023,2022,2021,2020,2019,2018,2017,2016,2015,2014,2013]


def get_paper_semanticscholarID(paper_title):
    semanticscholarID = None
    headers = {'x-api-key': os.environ.get("API_KEY")}
    url = f'https://api.semanticscholar.org/graph/v1/paper/search?query="{paper_title}"&limit=3'
    request_id = requests.get(url,headers=headers,allow_redirects=True,timeout=120)
    nb_try = 0
    while request_id.status_code != 200:
        print(paper_title,request_id.status_code)
        nb_try += 1
        if nb_try >= 4:
            print("Number of try exceeded to get ID")
            return None
        elif request_id.status_code != 429:
            print(f"Error {request_id.status_code}")
            return None
        time.sleep(5)
        request_id = requests.get(url,headers=headers,allow_redirects=True,timeout=120)

    r_json = request_id.json()
    if "data" in r_json:
        semanticscholarID = r_json["data"][0]["paperId"]
    
    return semanticscholarID

def get_paper_semanticscholar_data(semanticscholarID):
    headers = {'x-api-key': os.environ.get("API_KEY")}

    citations_per_year = Counter()

    url = f"https://api.semanticscholar.org/v1/paper/{semanticscholarID}?include_unknown_references=true"
    request_data = requests.get(url,headers=headers,allow_redirects=True,timeout=120)
    nb_try = 0
    while request_data.status_code != 200:
        print(semanticscholarID,request_data.status_code)
        nb_try += 1
        if nb_try >= 4:
            print("Number of try exceeded to fetch data")
            return None
        time.sleep(5)
        request_data = requests.get(url,headers=headers,allow_redirects=True,timeout=120)
    
    r_json = request_data.json()
    if "citations" in r_json:
        citations = r_json["citations"]
        for citation in citations:
            citations_per_year[citation["year"]] += 1
    else:
        citations_per_year = {y:None for y in YEARS}

    return citations_per_year

if __name__ == "__main__":
    load_dotenv(find_dotenv())

    paths_pdf = glob.glob("./data/pdfs/*/*.pdf")
    papers_names = [path.split("/")[-1].removesuffix(".pdf") for path in paths_pdf]
    venues_papers = [path.split("/")[-2] for path in paths_pdf]

    existing_data = pd.read_csv("./data/papers_citations_per_year.csv")
    with open("./data/papers_citations_per_year.csv", "a") as csv_file:
        fieldnames = ["title","venue_published","year_published","pdf_path","semanticscholar_id"]
        fieldnames += [f"citations_{year}" for year in YEARS]
        csvwriter = csv.writer(csv_file)
        paper_num = 0
        for path,title,venue in tqdm(zip(paths_pdf,papers_names,venues_papers),total=len(paths_pdf)):
            if existing_data['title'].str.contains(re.escape(str(title))).any():
                paper_num += 1
                continue
            if paper_num%100==0:
                time.sleep(1)
            semanticscholarID = get_paper_semanticscholarID(title)            
            
            row = [title,venue[:-4],venue[-4:],path,semanticscholarID]
            citations_per_year = {y:None for y in YEARS}
            if semanticscholarID:
                citations_per_year = get_paper_semanticscholar_data(semanticscholarID)        
            row += [citations_per_year.get(y,0) for y in YEARS]
            
            csvwriter.writerow(row)
            paper_num += 1