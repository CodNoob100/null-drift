import os
import json
import subprocess

ACTIVE_VULNERABILITIES = set()
OPEN_ISSUES = {}


def get_open_security_issues():
    cmd = [
        "gh",
        "issue",
        "list",
        "--state",
        "open",
        "--search",
        'in:title "Security Vulnerability:"',
        "--json",
        "number,title",
        "--limit",
        "200",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        issues = json.loads(result.stdout)
        for issue in issues:
            OPEN_ISSUES[issue["title"]] = issue["number"]
    except Exception as e:
        print(f"Failed to fetch open security issues: {e}")


def create_issue(title, body, assignees=[]):
    ACTIVE_VULNERABILITIES.add(title)

    if title in OPEN_ISSUES:
        print(f"Issue already exists for: {title}")
        return

    cmd = ["gh", "issue", "create", "--title", title, "--body", body]
    if assignees:
        assignees_str = ",".join(assignees)
        cmd.extend(["--assignee", assignees_str])

    print(f"Opening issue: {title}")
    try:
        subprocess.run(cmd, check=True)
    except Exception as e:
        print(f"Failed to create issue: {e}")


def close_stale_issues():
    for title, number in OPEN_ISSUES.items():
        if title not in ACTIVE_VULNERABILITIES:
            print(f"Closing stale issue #{number}: {title}")
            cmd = [
                "gh",
                "issue",
                "close",
                str(number),
                "-c",
                "Vulnerability has been automatically resolved by recent patches.",
            ]
            try:
                subprocess.run(cmd, check=True)
            except Exception as e:
                print(f"Failed to close issue #{number}: {e}")


def get_pr_author():
    actor = os.environ.get("GITHUB_ACTOR")
    if actor and actor != "github-actions[bot]":
        return actor
    return None


def process_gitleaks(report_path):
    if not os.path.exists(report_path):
        return
    with open(report_path, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return

    actor = get_pr_author()

    for finding in data:
        rule_id = finding.get("RuleID", "Secret")
        file_path = finding.get("File", "Unknown")
        commit = finding.get("Commit", "Unknown")
        author_email = finding.get("Email", "Unknown")

        title = (
            f"Security Vulnerability: Hardcoded Secret ({rule_id}) found in {file_path}"
        )

        body = "### Secret Scanning Alert\n\n"
        body += f"**Rule:** {rule_id}\n"
        body += f"**File:** {file_path}\n"
        body += f"**Commit:** {commit}\n"
        body += f"**Original Author Email:** {author_email}\n\n"

        if actor:
            body += f"cc @{actor} Please investigate and revoke this secret immediately if it is valid."

        assignees = [actor] if actor else []
        create_issue(title, body, assignees)


def process_osv(report_path):
    if not os.path.exists(report_path):
        return
    with open(report_path, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return

    actor = get_pr_author()

    results = data.get("results", [])
    for res in results:
        packages = res.get("packages", [])
        for pkg_info in packages:
            pkg = pkg_info.get("package", {})
            pkg_name = pkg.get("name", "Unknown")
            vulns = pkg_info.get("vulnerabilities", [])

            for v in vulns:
                vuln_id = v.get("id", "Unknown")
                details = v.get("details", "No details provided.")

                title = f"Security Vulnerability: {vuln_id} in dependency {pkg_name}"

                body = "### Dependency Vulnerability Alert\n\n"
                body += f"**Vulnerability ID:** {vuln_id}\n"
                body += f"**Package:** {pkg_name}\n\n"
                body += f"**Details:**\n{details}\n\n"

                if actor:
                    body += f"cc @{actor} Please update this dependency to a patched version."

                assignees = [actor] if actor else []
                create_issue(title, body, assignees)


def process_cargo_audit(report_path):
    if not os.path.exists(report_path):
        return
    with open(report_path, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return

    actor = get_pr_author()

    vulns = data.get("vulnerabilities", {}).get("list", [])
    for v in vulns:
        adv = v.get("advisory", {})
        pkg = v.get("package", {})

        vuln_id = adv.get("id", "Unknown")
        title_str = adv.get("title", "Unknown")
        pkg_name = pkg.get("name", "Unknown")

        title = (
            f"Security Vulnerability: {vuln_id} ({title_str}) in dependency {pkg_name}"
        )

        body = "### Dependency Vulnerability Alert (Cargo Audit)\n\n"
        body += f"**Vulnerability ID:** {vuln_id}\n"
        body += f"**Package:** {pkg_name}\n"
        body += f"**Version:** {v.get('package', {}).get('version', 'Unknown')}\n"
        body += f"**Description:** {v.get('advisory', {}).get('description', 'No description provided')}\n\n"

        if actor:
            body += f"cc @{actor} Please update this dependency to a patched version."

        assignees = [actor] if actor else []
        create_issue(title, body, assignees)


if __name__ == "__main__":
    get_open_security_issues()

    process_gitleaks("gitleaks_report.json")
    process_osv("osv_report.json")
    process_cargo_audit("audit_report.json")

    close_stale_issues()
