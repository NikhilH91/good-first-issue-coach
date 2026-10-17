import os
import re
import requests
import streamlit as st
from google import genai
from google.genai import types

st.set_page_config(page_title="Good First Issue Coach", page_icon="🌱", layout="wide")

st.title("🌱 Good First Issue Coach")
st.caption("AI-powered guide to help beginners conquer their first open-source PR.")

# Sidebar: API Key Configuration
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Enter Gemini/Google API Key:", type="password", value=os.environ.get("GEMINI_API_KEY", ""))
    github_token = st.text_input("GitHub Token (Optional, avoids rate limits):", type="password")

repo_url = st.text_input("Paste a public GitHub repo link:", placeholder="https://github.com/pallets/flask")

def extract_owner_repo(url):
    match = re.search(r"github\.com/([^/]+)/([^/]+)", url)
    if match:
        owner = match.group(1)
        repo = match.group(2).replace(".git", "")
        return owner, repo
    return None, None

def fetch_issues(owner, repo, token=None):
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
        
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    params = {"state": "open", "per_page": 5, "sort": "updated"}
    
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code == 200:
        # Filter out pull requests (GitHub API returns PRs in issues endpoint)
        issues = [i for i in resp.json() if "pull_request" not in i]
        return issues
    return []

def analyze_issue(client, issue_title, issue_body, repo_name):
    prompt = f"""
    You are a friendly senior open-source mentor helping a first-time Hacktoberfest contributor.
    
    Repository: {repo_name}
    Issue Title: {issue_title}
    Issue Description:
    \"\"\"{issue_body or "No description provided."}\"\"\"

    Please respond with:
    1. **Plain Language Summary**: Explain the bug/feature without complex jargon (2-3 sentences).
    2. **Difficulty Rating**: Score 1 to 5 (1=typo/docs, 5=complex architectural change) and why.
    3. **Where to Look**: Likely file paths or directories in the project.
    4. **Step-by-Step Action Plan**: 4-5 numbered, beginner-friendly instructions (fork, branch, change, test).
    5. **Drafted Pull Request Body**: A ready-to-copy PR template with Title, Motivation, and What Changed.
    """
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text

if st.button("Find & Coach Issues", type="primary"):
    if not api_key:
        st.error("Please enter your API Key in the sidebar.")
    elif not repo_url:
        st.warning("Please provide a GitHub repository link.")
    else:
        owner, repo = extract_owner_repo(repo_url)
        if not owner:
            st.error("Invalid GitHub URL format.")
        else:
            with st.spinner(f"Fetching open issues from {owner}/{repo}..."):
                issues = fetch_issues(owner, repo, github_token)
            
            if not issues:
                st.warning("No open issues found or GitHub API rate limit reached.")
            else:
                client = genai.Client(api_key=api_key)
                st.success(f"Found {len(issues)} open issues! Here are your coaching guides:")
                
                for idx, issue in enumerate(issues, start=1):
                    with st.expander(f"#{issue['number']}: {issue['title']}", expanded=(idx == 1)):
                        st.markdown(f"[View Issue on GitHub]({issue['html_url']})")
                        with st.spinner("Coach is analyzing this issue..."):
                            advice = analyze_issue(client, issue['title'], issue['body'], f"{owner}/{repo}")
                            st.markdown(advice)