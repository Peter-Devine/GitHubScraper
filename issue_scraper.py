import requests
import json
import re
import pandas as pd
import time
import argparse
from tqdm import tqdm

from google_drive_utils import upload_df_to_gd

parser = argparse.ArgumentParser()
parser.add_argument('--github_username', required=True, type=str, help='Username for GitHub')
parser.add_argument('--access_token', required=True, type=str, help='Personal Access Token')
args = parser.parse_args()

def get_json_data_from_url(url):
    r = requests.get(url, auth=(args.github_username, args.access_token))

    # Sleep and return None if URL is not working. Sleep in case non-200 is due to rate limiting.
    if r.status_code != 200:
        timeout_time_seconds = 210
        print(f"Timing out for {timeout_time_seconds} seconds after getting a {r.status_code} status code from {url}")
        time.sleep(timeout_time_seconds)
        return None

    data = json.loads(r.content)
    return data

issues = get_json_data_from_url("https://api.github.com/search/issues?q=label:duplicate&per_page=100&page=1")

number_pages = int(issues["total_count"] / 100)

page_bar = tqdm(range(1, number_pages))

for page in page_bar:
    page_bar.set_description(f"Page number {page}")

    # Get duplicate issues
    issues = get_json_data_from_url(f"https://api.github.com/search/issues?q=label:duplicate&per_page=100&page={page}")

    # Finds all mentions of a hash followed by numbers (E.g. #1234)
    issue_finder_regex = re.compile("#\d+")

    # Removes all code between code blocks (In order to reduce size of comments and only retain more human readable bits)
    code_cleaner_regex = re.compile("```([\S\s]+)```")

    issue_data_list = []

    if issues is None:
        continue

    issue_bar = tqdm(issues["items"], position=1, leave=True)

    for issue in issue_bar:
        try:
            url = issue["url"]
            issue_bar.set_description(f"Scraping issue {url}")

            issue_title = issue["title"]
            issue_body_raw = issue["body"]
            issue_body = code_cleaner_regex.sub("[CODE]", issue_body_raw) if issue_body_raw is not None else issue_body_raw
            issue_labels = [x["name"] for x in issue["labels"]]
            issue_number = url.split("/")[-1]

            # Get comments
            comment_data = get_json_data_from_url(issue["comments_url"])

            if comment_data is None:
                continue

            dup_issues = issue_finder_regex.findall("".join([x["body"] for x in comment_data]))

            # Make sure that we don't simply capture a reference to the current issue.
            dup_issues = [x for x in dup_issues if x != f"#{issue_number}"]

            if len(dup_issues) <= 0:
                continue

            first_dup_issue = dup_issues[0]
            duplicate_issue_url = "/".join(url.split("/")[:-1]) + dup_issues[0].replace("#", "/")

            duplicate_data = get_json_data_from_url(duplicate_issue_url)

            if duplicate_data is None:
                continue

            duplicate_body_raw = duplicate_data["body"]
            duplicate_body = code_cleaner_regex.sub("[CODE]", duplicate_body_raw) if duplicate_body_raw is not None else duplicate_body_raw
            duplicate_title = duplicate_data["title"]
            duplicate_labels = [x["name"] for x in duplicate_data["labels"]]

            issue_data_list.append({
                "url": url,
                "issue_title": issue_title,
                "issue_body": issue_body,
                "issue_body_raw": issue_body_raw,
                "issue_labels": issue_labels,
                "dup_issues": dup_issues,
                "first_dup_issue_url": duplicate_issue_url,
                "duplicate_body": duplicate_body,
                "duplicate_body_raw": duplicate_body_raw,
                "duplicate_title": duplicate_title,
                "duplicate_labels": duplicate_labels
            })
        except Exception as e:
            current_url = issue["url"]
            print(f"Error when scraping {current_url}:\n{e}\n\n")

    upload_df_to_gd(f"github_issues_{page}.csv", pd.DataFrame(issue_data_list), "1Z6qifbWAhgSCDupyXb5nFCYxHZiJU21X")
