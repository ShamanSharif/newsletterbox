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
SENDER_EMAIL = os.getenv("SENDER_EMAIL")


def fetch_todays_email_from_sender(sender, target_date=None):
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_USER, EMAIL_PASSWORD)
    mail.select("inbox")

    if target_date:
        search_date = target_date.strftime("%d-%b-%Y")
    else:
        search_date = date.today().strftime("%d-%b-%Y")

    search_criteria = f'(FROM "{sender}" ON "{search_date}")'

    status, data = mail.search(None, search_criteria)
    mail_ids = data[0]
    id_list = mail_ids.split()

    if not id_list:
        return None

    latest_email_id = id_list[-1]

    status, data = mail.fetch(latest_email_id, "(RFC822)")

    for response_part in data:
        if isinstance(response_part, tuple):
            msg = email.message_from_bytes(response_part[1])
            return msg

    return None


def clean_email_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")

    # Find the element containing "Farhan" and remove everything after it
    farhan_element = soup.find(string=lambda text: "Farhan" in text if text else False)
    if farhan_element:
        element_to_keep = farhan_element.find_parent()
        if element_to_keep:
            for element in element_to_keep.find_all_next():
                element.decompose()

    # Find and remove the "unsubscribe" link and its parent element
    unsubscribe_element = soup.find(
        string=lambda text: "Update your email preferences or unsubscribe here"
        in text
        if text
        else False
    )
    if unsubscribe_element:
        element_to_remove = unsubscribe_element.find_parent()
        if element_to_remove:
            element_to_remove.decompose()

    # Create a new, clean HTML structure with JetBrains Mono font and minimalist styling
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
    header.string = "NewsLetterBox"
    body.append(header)

    # Process and move content tags
    content_tags = soup.find_all(["h1", "h2", "h3", "h4", "p", "img", "ul", "ol"])
    for tag in content_tags:
        # Skip tags that are inside a list, as they will be handled by the list processing
        if tag.find_parent(["ul", "ol"]):
            continue

        # Add a separator before each new major heading
        if tag.name in ["h1", "h2", "h3", "h4"]:
            body.append(new_soup.new_tag("hr"))

        # For lists, we need to rebuild them to ensure they are clean
        if tag.name in ["ul", "ol"]:
            new_list = new_soup.new_tag(tag.name)
            for li in tag.find_all("li", recursive=False):  # Only direct children
                new_list.append(li.extract())  # Extract and append the li
            body.append(new_list)
        else:
            body.append(tag.extract())  # Extract and append other tags

    return str(new_soup)


def create_pdf(html_content, output_path):
    HTML(string=html_content).write_pdf(output_path)


if __name__ == "__main__":
    import sys
    from datetime import datetime

    # Parse command line arguments for date (year month day)
    if len(sys.argv) == 4:
        try:
            year = int(sys.argv[1])
            month = int(sys.argv[2])
            day = int(sys.argv[3])
            target_date = datetime(year, month, day).date()
        except ValueError:
            print("Error: Invalid date format. Use: uv run main.py YYYY MM DD")
            sys.exit(1)
    else:
        # Default to today's date if no arguments provided
        target_date = date.today()
        print(f"No date specified, using today's date: {target_date}")

    print(f"Fetching emails from {target_date.strftime('%Y-%m-%d')}")
    email_message = fetch_todays_email_from_sender(SENDER_EMAIL, target_date)

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
            cleaned_html = clean_email_html(html_content)
            if not os.path.exists("output"):
                os.makedirs("output")
            target_date_str = target_date.strftime("%Y-%m-%d")
            output_pdf_path = f"output/{target_date_str}.pdf"
            create_pdf(cleaned_html, output_pdf_path)
            print(f"PDF created at {output_pdf_path}")
        else:
            print("No HTML content found in the email.")
    else:
        print("Could not fetch the latest email.")
