from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
import requests
import time
import json
import threading
import re
import json
import pytz
from collections import defaultdict
from datetime import datetime
from typing import List
import threading
import yfinance as yf
import requests
import sys
version = sys.version_info
if version.major < 3 or (version.major == 3 and version.minor < 10):
	raise RuntimeError("This script requires Python 3.10 or higher")
import os
from typing import Iterable

from fileStreams import getFileJsonStream
from utils import FileProgressLog

company = "apple"
fileOrFolderPath = r"r_" + company + "_comments.jsonl"
recursive = False
# YOUR_API_KEY = "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"
# base_url = "https://api.perplexity.ai"
index = 0
sentiment_count = None
currentYear = 2019
base_url = "https://api.deepinfra.com/v1/openai"
YOUR_API_KEY = "Z4FxfC1c8O0VBfCQjd3WRNAB3LyZWP2A"
tickers = {"nvidia": "nvda", "google" : "goog", "apple" : "aapl", "tesla" : "tsla", "test" : "test"}
def sentiment(progressLog, text, row, client, messages):
	try:
		global index
		created = row["created_utc"]
		body = row["body"]
		global sentiment_count
		global currentYear
		progressLog.onRow()
		if(len(body) < 500 and (text in body.lower() or tickers[text] in body.lower() or 'ipad' in body.lower() or 'iphone' in body.lower() or 'mac' in body.lower())):
			body = remove_emoji(body)
			if not body or body.isspace():
				return
			messages[1]["content"] = body
			
				# response = client.chat.completions.create(model="llama-3.1-sonar-small-128k-online",messages=messages,)
			response = client.chat.completions.create(model="meta-llama/Meta-Llama-3.1-8B-Instruct", messages=messages, max_tokens=1,)
			
			analysis = response.choices[0].message.content.lower()
			if 'neutral' in analysis.lower():
				analysis = 'neutral'
			elif 'positive' in analysis.lower():
				analysis = 'positive'
			elif 'negative' in analysis.lower():
				analysis = 'negative'
			if not (analysis == 'neutral' or analysis == 'positive' or analysis == 'negative'):
				return
			dt_eastern = datetime.utcfromtimestamp(int(created)).replace(tzinfo=pytz.timezone("US/Eastern"))
			print(dt_eastern)
			year = dt_eastern.year
			month = dt_eastern.month
			day = dt_eastern.day
			hour = dt_eastern.hour
			if year != currentYear:
				currentYear = year
				output_data = []
				for year, month in sentiment_count.items(): 
					for month, day in month.items():
						for day, hours in day.items():
							for hour, counts in hours.items():
								output_data.append({
									"Year": year,
									"Month": month,
									"Day": day,
									"Hour": hour,
									"Positive Amount": counts["positive"],
									"Negative Amount": counts["negative"],
									"Neutral Amount": counts["neutral"]})
				with open("recent_" + text + "_" + str(index) + ".json", 'w') as f:
					json.dump({"data": output_data}, f, indent=4)
			sentiment_count[year][month][day][hour][analysis] += 1
	except Exception as e :
			output_data = []
			for year, month in sentiment_count.items(): 
				for month, day in month.items():
					for day, hours in day.items():
						for hour, counts in hours.items():
							output_data.append({
								"Year": year,
								"Month": month,
								"Day": day,
								"Hour": hour,
								"Positive Amount": counts["positive"],
								"Negative Amount": counts["negative"],
								"Neutral Amount": counts["neutral"]})
			with open("recent_" + text + "_" + str(index) + ".json", 'w') as f:
				json.dump({"data": output_data}, f, indent=4)
			print(e)
			time.sleep(60)
def remove_emoji(text):
    #removes regular emojis
    RE_EMOJI = re.compile(u'([\U00002600-\U000027BF])|([\U0001f300-\U0001f64F])|([\U0001f680-\U0001f6FF])')
    text = RE_EMOJI.sub(r'', text)
    #returns the emojis of the format [emoji](img|string1|string2)
    return re.sub(r'\[.*?\)', '', text)

def processFile(path: str):
	global sentiment_count
	text = company
	
	client = OpenAI(api_key=YOUR_API_KEY, base_url=base_url)
	messages = [
        {
            "role": "system",
            "content": (
                "You are an expert in marketing and assessing the sentiment of reviews. I am going to give you reviews to respond with only 'positive', 'negative', or 'neutral' towards the use of " + text + " or " + tickers[text] + ". Refrain from the explaining your decision. If you cannot create content about the review, rate it as neutral"
            ),
        },
        {
            "role": "user",
            "content": (
                ""
            ),
        },
    ]

	print(f"Processing file {path}")
	with open(path, "rb") as f:
		sentiment_count = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0}))))
		jsonStream = getFileJsonStream(path, f)
		if jsonStream is None:
			print(f"Skipping unknown file {path}")
			return
		progressLog = FileProgressLog(path, f)
		try: 
			with ThreadPoolExecutor(max_workers=8) as executor:  # Adjust the number of workers as needed
				futures = [executor.submit(sentiment,progressLog,text,row,client,messages) for row in jsonStream]
				for future in futures:
					try:
						# Set a timeout for each task
						future.result(timeout=5)  # Timeout in seconds
					except TimeoutError:
						print(f"Task exceeded the timeout limit.")
					except Exception as e:
						print(f"Error occurred in task: {e}")
			executor.shutdown(wait=True)
		except Exception as e:
			output_data = []
			for year, month in sentiment_count.items(): 
				for month, day in month.items():
					for day, hours in day.items():
						for hour, counts in hours.items():
							output_data.append({
								"Year": year,
								"Month": month,
								"Day": day,
								"Hour": hour,
								"Positive Amount": counts["positive"],
								"Negative Amount": counts["negative"],
								"Neutral Amount": counts["neutral"]})
			with open("recent_" + text + "_" + str(index) + ".json", 'w') as f:
				json.dump({"data": output_data}, f, indent=4)
			print(e)
		output_data = []
		for year, month in sentiment_count.items(): 
			for month, day in month.items():
				for day, hours in day.items():
					for hour, counts in hours.items():
						output_data.append({
							"Year": year,
							"Month": month,
							"Day": day,
							"Hour": hour,
							"Positive Amount": counts["positive"],
							"Negative Amount": counts["negative"],
							"Neutral Amount": counts["neutral"]})
		with open("recent_" + text + "_" + str(index) + ".json", 'w') as f:
			json.dump({"data": output_data}, f, indent=4)

			# parent = row["parent_id"]	# id/name of the parent comment or post (e.g. t3_abc123 or t1_abc123)
			# link_id = row["link_id"]	# id/name of the post (e.g. t3_abc123)
		# print(text[index])
		# print(ticker[index])
		# progressLog.logProgress("\n")


	

def processFolder(path: str):
	global index
	fileIterator: Iterable[str]
	if recursive:
		def recursiveFileIterator():
			for root, dirs, files in os.walk(path):
				for file in files:
					yield os.path.join(root, file)
		fileIterator = recursiveFileIterator()
	else:
		fileIterator = os.listdir(path)
		fileIterator = (os.path.join(path, file) for file in fileIterator)
	
	for i, file in enumerate(fileIterator):
		index = i
		print(f"Processing file {i+1: 3} {file}")
		processFile(file)

def main():
	if os.path.isdir(fileOrFolderPath):
		processFolder(fileOrFolderPath)
	else:
		processFile(fileOrFolderPath)
	
	print("Done :>")

main()