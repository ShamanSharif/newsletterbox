import os
import imaplib
import email
from datetime import date
from bs4 import BeautifulSoup
from weasyprint import HTML
from dotenv import load_dotenv

load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
IMAP_SERVER = os.getenv("IMAP_SERVER")

# A list of dictionaries for the senders
SENDERS = [
    {"name": "Muggle Memo", "email": "mugglememo@newsletter.mugglememo.com"},
    {"name": "Rundown AI", "email": "news@daily.therundown.ai"},
    {"name": "Superhuman", "email": "superhuman@mail.joinsuperhuman.ai"},
    # Add other senders here
]


def fetch_todays_email_from_sender(sender_email, target_date=None):
    """
    Fetches the latest email from a specific sender on a given date.
    """
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_USER, EMAIL_PASSWORD)
    mail.select("inbox")

    if target_date:
        search_date = target_date.strftime("%d-%b-%Y")
    else:
        search_date = date.today().strftime("%d-%b-%Y")

    search_criteria = f'(FROM "{sender_email}" ON "{search_date}")'

    status, data = mail.search(None, search_criteria)
    if status != "OK":
        return None

    mail_ids = data[0].split()
    if not mail_ids:
        return None

    latest_email_id = mail_ids[-1]
    status, data = mail.fetch(latest_email_id, "(RFC822)")
    if status != "OK":
        return None

    for response_part in data:
        if isinstance(response_part, tuple):
            return email.message_from_bytes(response_part[1])

    return None


def clean_email_html(html_content, sender_name):
    """
    Cleans the HTML content of the email.
    Custom cleaning logic can be added here based on the sender.
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Generic cleaning (can be expanded)
    if sender_name == "Muggle Memo":
        # Find the element containing "Farhan" and remove everything after it
        farhan_element = soup.find(
            string=lambda text: "Farhan" in text if text else False
        )
        if farhan_element:
            element_to_keep = farhan_element.find_parent()
            if element_to_keep:
                for element in element_to_keep.find_all_next():
                    element.decompose()

        # Find and remove the "unsubscribe" link and its parent element
        unsubscribe_element = soup.find(
            string=lambda text: (
                "Update your email preferences or unsubscribe here" in text
                if text
                else False
            )
        )
        if unsubscribe_element:
            element_to_remove = unsubscribe_element.find_parent()
            if element_to_remove:
                element_to_remove.decompose()

    # Create a new, clean HTML structure
    new_soup = BeautifulSoup(
        """
    <html>
        <head>
            <title>Cleaned Email</title>
            <link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
            <style>
                body {
                    font-family: 'Lora', serif;
                    font-size: 14px;
                    line-height: 1.6;
                    max-width: 800px;
                    margin: 20px auto;
                    padding: 0 20px;
                    color: #333;
                }
                hr {
                    border: 0;
                    height: 1px;
                    background-color: #ccc;
                    margin: 2em 0;
                }
                img {
                    max-width: 100%;
                    height: auto;
                    display: block;
                    margin: 1.5em auto;
                    border-radius: 8px;
                }
                ul, ol {
                    padding-left: 25px;
                }
                li {
                    margin-bottom: 0.5em;
                }
                a {
                    color: #0C4A6E;
                }
            </style>
        </head>
        <body></body>
    </html>
    """,
        "html.parser",
    )
    body = new_soup.body

    # Add header
    header = new_soup.new_tag("h1")
    header.string = sender_name
    body.append(header)

    # Process and move content tags
    content_tags = soup.find_all(["h1", "h2", "h3", "h4", "p", "img", "ul", "ol"])
    for tag in content_tags:
        if tag.find_parent(["ul", "ol"]):
            continue
        if tag.name in ["h1", "h2", "h3", "h4"]:
            body.append(new_soup.new_tag("hr"))
        if tag.name in ["ul", "ol"]:
            new_list = new_soup.new_tag(tag.name)
            for li in tag.find_all("li", recursive=False):
                new_list.append(li.extract())
            body.append(new_list)
        else:
            body.append(tag.extract())

    return str(new_soup)


def create_pdf(html_content, output_path):
    """
    Creates a PDF from HTML content.
    """
    HTML(string=html_content).write_pdf(output_path)


if __name__ == "__main__":
    import sys
    from datetime import datetime

    if len(sys.argv) == 4:
        try:
            year = int(sys.argv[1])
            month = int(sys.argv[2])
            day = int(sys.argv[3])
            target_date = datetime(year, month, day).date()
        except ValueError:
            print("Error: Invalid date format. Use: python main.py YYYY MM DD")
            sys.exit(1)
    else:
        target_date = date.today()
        print(f"No date specified, using today's date: {target_date}")

    print(f"Fetching emails for {target_date.strftime('%Y-%m-%d')}")

    for sender in SENDERS:
        sender_name = sender["name"]
        sender_email = sender["email"]

        print(f"--> Checking for '{sender_name}' from '{sender_email}'")

        email_message = fetch_todays_email_from_sender(sender_email, target_date)

        if email_message:
            html_content = ""
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == "text/html":
                        html_content = part.get_payload(decode=True).decode()
                        break
            else:
                html_content = email_message.get_payload(decode=True).decode()

            if html_content:
                cleaned_html = clean_email_html(html_content, sender_name)

                output_dir = os.path.join("output", sender_name)
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)

                target_date_str = target_date.strftime("%Y-%m-%d")
                output_pdf_path = os.path.join(output_dir, f"{target_date_str}.pdf")

                create_pdf(cleaned_html, output_pdf_path)
                print(f"    PDF created at {output_pdf_path}")
            else:
                print("    No HTML content found in the email.")
        else:
            print("    No email found for this sender on the specified date.")
