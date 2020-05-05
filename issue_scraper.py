import requests
import json
import re
import pandas as pd
import time

from google_drive_utils import upload_df_to_gd

parser = argparse.ArgumentParser()
parser.add_argument('--github_username', required=True, type=str, help='Username for GitHub')
parser.add_argument('--access_token', required=True, type=str, help='Personal Access Token')
args = parser.parse_args()

def get_json_data_from_url(url):
    r = requests.get(url, auth=(args.github_username, args.access_token))
    
    # Sleep and return None if URL is not working. Sleep in case non-200 is due to rate limiting.
    if r.status_code != 200:
        time.sleep(1)
        return None
    
    data = json.loads(r.content)
    return data

issues = get_json_data_from_url("https://api.github.com/search/issues?q=label:duplicate&per_page=100&page=1")

number_pages = int(issues["total_count"] / 100)

for page in range(1, number_pages):

    # Get duplicate issues
    issues = get_json_data_from_url(f"https://api.github.com/search/issues?q=label:duplicate&per_page=100&page={page}")

    # Finds all mentions of a hash followed by numbers (E.g. #1234)
    issue_finder_regex = re.compile("#\d+")

    # Removes all code between code blocks (In order to reduce size of comments and only retain more human readable bits)
    code_cleaner_regex = re.compile("```([\S\s]+)```")

    issue_data_list = []

    if issues is None:
        continue

    for issue in issues["items"]:
        url = issue["url"]
        issue_title = issue["title"]
        issue_body = code_cleaner_regex.sub("[CODE]", issue["body"]) 
        issue_body_raw = issue["body"]
        issue_labels = [x["name"] for x in issue["labels"]]

        print(f"{issue_title}\n{url}\n\n")

        # Get comments
        comment_data = get_json_data_from_url(issue["comments_url"])

        if comment_data is None:
            continue

        dup_issues = issue_finder_regex.findall("".join([x["body"] for x in comment_data]))

        if len(dup_issues) <= 0:
            continue

        first_dup_issue = dup_issues[0]
        duplicate_issue_url = "/".join(url.split("/")[:-1]) + dup_issues[0].replace("#", "/")

        duplicate_data = get_json_data_from_url(duplicate_issue_url)

        if duplicate_data is None:
            continue

        duplicate_body = code_cleaner_regex.sub("[CODE]", duplicate_data["body"])
        duplicate_body_raw = duplicate_data["body"]
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

    upload_df_to_gd(f"github_issues_{page}.csv", pd.DataFrame(issue_data_list), "1Z6qifbWAhgSCDupyXb5nFCYxHZiJU21X")