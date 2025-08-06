import os
import requests
import pandas as pd
import time
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# --- CONFIGURATION ---
# Use your GitHub PAT from the .env file.
# IMPORTANT: Make sure you created a .env file in this folder and added your token:
# GITHUB_PERSONAL_ACCESS_TOKEN=ghp_YourTokenHere
GITHUB_TOKEN = os.getenv('GITHUB_PERSONAL_ACCESS_TOKEN')
if not GITHUB_TOKEN:
    raise ValueError("GitHub token not found. Please create a .env file with GITHUB_PERSONAL_ACCESS_TOKEN.")

# The repository we will collect data from. A large, active repo is best.
REPO_OWNER = 'pandas-dev'
REPO_NAME = 'pandas'

# Number of pages of pull requests to fetch (100 PRs per page).
# Start with a smaller number like 2-3 for testing.
PAGES_TO_FETCH = 3 

HEADERS = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}

# --- SCRIPT LOGIC ---

def get_rate_limit():
    """Checks the current GitHub API rate limit status."""
    response = requests.get('https://api.github.com/rate_limit', headers=HEADERS)
    if response.status_code == 200:
        rate_limit_data = response.json()['resources']['core']
        print(f"Rate Limit: {rate_limit_data['remaining']}/{rate_limit_data['limit']} requests remaining.")
        return rate_limit_data['remaining']
    return 0

def get_build_status_for_commit(sha):
    """
    For a given commit SHA, find the conclusion of the main CI check run.
    This is the most crucial part: linking a PR to its build outcome.
    """
    url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/{sha}/check-runs'
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        check_runs = response.json().get('check_runs', [])
        # We look for a common CI workflow name. This might need to be adjusted for other repos.
        # We prioritize 'CI' but fall back to the first completed check run if not found.
        ci_check = next((run for run in check_runs if 'CI' in run['name'] and run['status'] == 'completed'), None)
        if not ci_check:
            ci_check = next((run for run in check_runs if run['status'] == 'completed'), None)
        
        if ci_check:
            return ci_check['conclusion'] # 'success', 'failure', etc.
    return None


def main():
    """Main function to collect data and save it to a CSV."""
    all_pr_data = []

    print("Starting data collection...")
    get_rate_limit()

    for page in range(1, PAGES_TO_FETCH + 1):
        print(f"\nFetching page {page}/{PAGES_TO_FETCH} of pull requests...")
        
        # Fetch closed pull requests (as they have a final build status)
        prs_url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls?state=closed&per_page=100&page={page}'
        response = requests.get(prs_url, headers=HEADERS)

        if response.status_code != 200:
            print(f"Error fetching pull requests: {response.status_code} {response.text}")
            break

        pull_requests_summary = response.json()

        for pr_summary in pull_requests_summary:
            # We only care about merged PRs, as they are the ones that impact the main branch.
            if pr_summary.get('merged_at') and pr_summary.get('merge_commit_sha'):
                
                # --- FIX: Fetch the full details for this specific PR ---
                time.sleep(1) # Pause before the next request to respect rate limits
                detailed_pr_url = pr_summary['url']
                detailed_response = requests.get(detailed_pr_url, headers=HEADERS)
                if detailed_response.status_code != 200:
                    print(f"  Could not fetch details for PR #{pr_summary['number']}. Skipping.")
                    continue
                
                pr = detailed_response.json() # This 'pr' object has all the details
                # --- END FIX ---

                merge_commit_sha = pr['merge_commit_sha']
                
                # Get the build status for the merge commit
                build_status = get_build_status_for_commit(merge_commit_sha)

                if build_status:
                    pr_data = {
                        'pr_number': pr['number'],
                        'lines_added': pr['additions'],
                        'lines_deleted': pr['deletions'],
                        'files_changed': pr['changed_files'],
                        'commits': pr['commits'],
                        'comments': pr['comments'],
                        'author_association': pr['author_association'],
                        'build_status': 1 if build_status == 'failure' else 0 # Our target variable
                    }
                    all_pr_data.append(pr_data)
                    print(f"  Processed PR #{pr['number']}: Build Status = {build_status}")
                
                # Respect the API rate limit by pausing briefly
                time.sleep(1) 

        if get_rate_limit() < 50:
            print("Rate limit low. Stopping data collection.")
            break

    # Convert the collected data into a pandas DataFrame and save it
    df = pd.DataFrame(all_pr_data)
    df.to_csv('training_data.csv', index=False)
    
    print(f"\nData collection complete. Saved {len(df)} records to training_data.csv")
    print("Sample of the data:")
    print(df.head())


if __name__ == '__main__':
    main()
