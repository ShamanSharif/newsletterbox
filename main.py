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


def fetch_todays_email_from_sender(sender):
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_USER, EMAIL_PASSWORD)
    mail.select("inbox")

    today = date.today().strftime("%d-%b-%Y")
    search_criteria = f'(FROM "{sender}" ON "{today}")'

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

    # Add header
    header = soup.new_tag("h1")
    header.string = "NewsLetterBox"
    soup.body.insert(0, header)

    # Remove tracking pixels
    for img in soup.find_all("img"):
        if "width" in img.attrs and "height" in img.attrs:
            if img["width"] == "1" and img["height"] == "1":
                img.decompose()

    # Remove specific footer section
    footer = soup.find("td", class_="b", bgcolor="#030712")
    if footer:
        footer.decompose()

    return str(soup)


def create_pdf(html_content, output_path):
    HTML(string=html_content).write_pdf(output_path)


if __name__ == "__main__":
    email_message = fetch_todays_email_from_sender(SENDER_EMAIL)

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
            today_str = date.today().strftime("%Y-%m-%d")
            output_pdf_path = f"output/{today_str}.pdf"
            create_pdf(cleaned_html, output_pdf_path)
            print(f"PDF created at {output_pdf_path}")
        else:
            print("No HTML content found in the email.")
    else:
        print("Could not fetch the latest email.")
