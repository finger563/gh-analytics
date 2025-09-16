from github import Github, Auth
import datetime
from tqdm import tqdm
from p_tqdm import p_map, t_map
import argparse

parser = argparse.ArgumentParser(description="GitHub Analysis: Closed PRs for an organization.")
parser.add_argument('--token', type=str, help='Access token for your user account', required=True)
# make a mutually exclusive group for the org, repo, and user
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('--org', type=str, help='Which organization to analyze PRs for')
group.add_argument('--repo', type=str, help='Which repo to analyze PRs for')
group.add_argument('--user', type=str, help='Which user to analyze PRs for')
parser.add_argument('--since_date', default='2022-01-01', type=str, help='Only select PRs after this ISO date (YYYY-mm-dd)')

args = parser.parse_args()
org = args.org
token = args.token
datestr = args.since_date

since_date = datetime.datetime.strptime(datestr, '%Y-%m-%d')

# using an access token
auth = Auth.Token(token)
g = Github(auth=auth)
user = g.get_user()
print(f"User associated with token: {user.login}")
print("")
print("Note: this does not analyze commits to main branch or repositories added, just all issues / PRs.")

fromdate = datetime.date.fromisoformat(datestr)
todate = datetime.date.today()
daygenerator = (fromdate + datetime.timedelta(x+1) for x in range(-1, (todate - fromdate).days))
num_working_days = sum(day.weekday() < 5 for day in daygenerator)

if num_working_days <= 0:
    print("Date is in the future, can't compute anything else... o.O")
    exit(-1)

try:
    if args.org:
        print(f"Counting closed PRs within org: {org} since {datestr}")
        print(f"Getting issues from org {args.org}")
        org = g.get_organization(org)
        issues = org.get_issues(filter='all', state='closed', since=since_date)
    elif args.repo:
        print(f"Counting closed PRs within repo: {args.repo} since {datestr}")
        print(f"Getting issues from repo {args.repo}")
        repo = g.get_repo(args.repo)
        issues = repo.get_issues(state='closed', since=since_date)
    elif args.user:
        print(f"Counting closed PRs by user: {args.user} since {datestr}")
        print(f"Getting issues from user {args.user}")
        user = g.get_user(args.user)
        repos = user.get_repos()
        issues = []
        for repo in repos:
            issues += repo.get_issues(state='closed', since=since_date)
except Exception as e:
    print(f"Error getting issues: {e}")
    exit(-1)

print(f"Total number of working days since {datestr}: {num_working_days}")
print(f"Total issues & prs closed since {datestr}:    {issues.totalCount}")
print(f"Number of issues & prs closed per working day: {issues.totalCount / num_working_days:.2f}")

pull_request_issues = []

# can't run this in paralell because the paginated list in the GH Python API doesn't support iterables the same way
for issue in tqdm(issues, ncols=80, total=issues.totalCount, desc="Separating the PRs"):
    if issue.pull_request:
        pull_request_issues.append(issue)

def as_pr(issue):
    # download the PR data
    return issue.as_pull_request()

# run this in parallel because we have to run GET() HTTP requests which takes time
prs = p_map(as_pr, pull_request_issues, ncols=80, desc="Analyzing the PRs")
total_loc_added = sum([pr.additions for pr in prs])
total_loc_removed = sum([pr.deletions for pr in prs])
total_commits = sum([pr.commits for pr in prs])

print(f"Total number of PRs closed: {len(pull_request_issues)}")
print(f"Total number of commits merged: {total_commits}")
print(f"Total number of lines of code added:   {total_loc_added}")
print(f"Total number of lines of code deleted: {total_loc_removed}")
print(f"Total number of lines of code delta:   {total_loc_added - total_loc_removed}")

print(f"Number of PRs closed per working day: {len(pull_request_issues) / num_working_days:.2f}")
