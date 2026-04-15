import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
from markdownify import markdownify as md
import json
import time
import socket
import sys
import smtplib
from email.message import EmailMessage
from enum import Enum
import difflib
import html
#========================= Configuration =======================
env_urls = os.getenv("BASE_URLS")
Base_URLS = json.loads(env_urls)
REQUEST_TIMEOUT_IN_SEC = 600
SLEEP_TIME_IN_SEC = 1
#==============================================================

#========================= Email Configuration =======================
SMTP_SERVER = "smtp.gmail.com"  # Change this if your company uses a different server , example : smtp.office365.com
SMTP_PORT = 587                 # Standard port for TLS
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
SMTP_SERVER_TIMEOUT_IN_SEC = 60
#==============================================================

#====================== Web Page Operations ==========================
def get_sub_links_from_url(start_url):
    try:
        response = requests.get(start_url, timeout=REQUEST_TIMEOUT_IN_SEC)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        links = set()
        
        side_menu = soup.select_one('devsite-book-nav nav.devsite-book-nav')
        
        if not side_menu:
            return [start_url]
            
        for a_tag in side_menu.find_all('a', href=True):
            href = a_tag['href']
            full_url = urljoin(start_url, href).split('#')[0].rstrip('/')
            
            if "/about/versions/" in full_url:
                links.add(full_url)
            
        result = sorted(list(links))
        return result if result else [start_url]

    except Exception as e:
        raise Exception(f"Error in get_sub_links_from_url: {str(e)}")
              
def get_http_response(url):
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT_IN_SEC)
        response.raise_for_status()
        return response
    except Exception as e:
        error_msg = "Exp from get_http_response() , message : "+str(e)
        raise Exception(error_msg) from e


def get_content_from_web_page(response):
    try:
        content_type = response.headers.get('Content-Type', '').lower()

        if 'application/json' in content_type:
            data = response.json()

            data = transform_api_body_timestamps(data)

            html_content = "<html><body><article>"
            
            if isinstance(data, list):
                for i, cert in enumerate(data):
                    html_content += f"<pre>{cert}</pre>"
            else:
                html_content += f"<pre>{json.dumps(data, indent=2)}</pre>"
            
            html_content += "</article></body></html>"
            
            soup = BeautifulSoup(html_content, 'html.parser')
            return soup.find('article')

        else:
            soup = BeautifulSoup(response.text, 'html.parser')
            main_content = soup.find('article') or soup.find('main')
            return main_content

    except Exception as e:
        error_msg = "Exp from get_content_from_web_page(), message: "+str(e)
        raise Exception(error_msg) from e
    
def convert_web_page_to_md(main_content):
    try:
        if not main_content:
            return None

        # Converting HTML to Markdown
        markDown = md(str(main_content), heading_style="ATX")
        return markDown
    except Exception as e:
        error_msg = "Exp from convert_web_page_to_md() , message : "+str(e)
        raise Exception(error_msg) from e
    
def get_file_name_from_url(domain_url,sub_url):
    try:
        remaining_text = sub_url.replace(domain_url, "")
        page_name = remaining_text.strip("/").replace("/", "-")
        if not page_name :
            page_name = "index"
        
        file_name = f"{page_name}.md"
        return file_name
    except Exception as e:
        error_msg = "Exp from get_file_name_from_url() , message : "+str(e)
        raise Exception(error_msg) from e

def transform_api_body_timestamps(data):

    try:
        if not data or not isinstance(data, list):
            return data
        
        headers = data[0]
        
        if "timestamp" in headers:
            ts_index = headers.index("timestamp")
            
            for row in data[1:]:
                if len(row) > ts_index:
                    raw_ts = row[ts_index]
                    try:
                        dt_obj = datetime.strptime(raw_ts, '%Y%m%d%H%M%S')
                        human_time = dt_obj.strftime('%Y-%m-%d %H:%M:%S')
                        
                        row[ts_index] = human_time
                    except (ValueError, TypeError):
                        continue
        
        return data
        
    except Exception as e:
        error_msg = "Exp from transform_api_body_timestamps(), message: " + str(e)
        raise Exception(error_msg) from e
#==============================================================

#================ Store Operations ==================
def generate_dir_name_from_url(url):
    try:
        parsed_url = urlparse(url)
        
        domain = parsed_url.netloc.replace("www.", "")
        path = parsed_url.path
        
        combined = f"{domain}{path}"
        
        if "url=" in parsed_url.query:
            inner_url = parsed_url.query.split("url=")[1].split("&")[0]
            combined = f"{domain}-{inner_url}"

        for char in [".", "/", "?", "=", "&", ":"]:
            combined = combined.replace(char, "-")
            
        clean_name = "-".join(filter(None, combined.split("-")))
        
        return clean_name

    except Exception as e:
        error_msg = "Exp from generate_dir_name_from_url() , message : "+str(e)
        raise Exception(error_msg) from e
    
def create_directory(dir_name):
    try:
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
    except Exception as e:
        error_msg = "EXP from create_directory() , message : "+str(e)
        raise Exception(error_msg) from e 
    
def store_page_content_into_file(path_of_file,content):
    try:
        with open(path_of_file, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        error_msg = "Exp from store_page_content_into_file() , message : "+str(e)
        raise Exception(error_msg) from e
    
def is_file_name_exist(dir_name,fName):
    try:
        file_path = dir_name+"/"+fName

        if not os.path.exists(file_path):
            return False
        
        return True
    except Exception as e:
        error_msg = "Exp from is_file_name_exist() , message : "+str(e)
        raise Exception(error_msg) from e

def get_content_of_exist_file(dir_name,fName):
    try:
        file_path = dir_name+"/"+fName

        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        error_msg = "Exp from get_content_of_exist_file() , message : "+str(e)
        raise Exception(error_msg) from e
#==============================================================

#================ Sends the report via SMTP ==================
class EmailStatus:
    SUCCESS_TYPE = "SUCCESS"
    FAILED_TYPE = "FAILED"
    TIMEOUT_TYPE = "TIMEOUT"
    MISSING_TYPE = "MISSING_CREDENTIALS"

    def __init__(self, type, message=""):
        self.type = type
        self.message = message

    def is_failure(self):
        return self.type != EmailStatus.SUCCESS_TYPE

    def __str__(self):
        return self.message
    
def send_email_report(report_html):
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        return EmailStatus(EmailStatus.MISSING_TYPE, "Failed: Email credentials missing.")
    
    msg = EmailMessage()
    msg.set_content("Please use an HTML compatible email client to view the report.")
    msg.add_alternative(report_html, subtype='html')
    
    msg['Subject'] = "Android Attestation Root Certs Report"
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL

    # set mail as a high Priority 
    msg['X-Priority'] = '1 (Highest)'
    msg['Importance'] = 'High'

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=SMTP_SERVER_TIMEOUT_IN_SEC)
        server.set_debuglevel(0)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return EmailStatus(EmailStatus.SUCCESS_TYPE, "Email sent successfully via TLS.")
    except (socket.timeout, TimeoutError):
        return EmailStatus(EmailStatus.TIMEOUT_TYPE, "Exp from send_email_report() , message : SMTP server connection timed out.")
    except Exception as e:
        return EmailStatus(EmailStatus.FAILED_TYPE, f"Exp from send_email_report() , message : Failed to send email - {str(e)}")
    
def logEmailStatus(status_obj: EmailStatus):
    print(status_obj)
    if status_obj.is_failure():
        sys.exit(1)
#==============================================================

#======================Filteration Operations=============================
def is_old_content_is_match_current_content(old_content,current_content):
    if old_content == current_content:
        return True
    
    return False
#==============================================================

#=========================HTML and Table Operations ===========================
def add_new_row_in_change_table(changes_table_rows,content_of_change_table_rows,dir_name,file_name, old_content, new_content):
    try:
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()
        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if not tag == 'equal':
                old_part = "<br>".join(old_lines[i1:i2])
                new_part = "<br>".join(new_lines[j1:j2])
                changes_table_rows.append(f"| `{dir_name}` | `{file_name}` | 📝 Modified |")
                content_of_change_table_rows.append(f"| `{dir_name}` | `{file_name}` | {old_part} | {new_part}")
    except Exception as e:
        error_msg = "Exp from add_new_row_in_change_table() , message : "+str(e)
        raise Exception(error_msg) from e

def add_new_row_in_not_change_table(not_change_table_rows,dir_name,file_name):
    not_change_table_rows.append(f"| `{dir_name}` | `{file_name}` | ✅ No Changes  |")

def add_new_row_in_new_file_table(new_file_table_rows,dir_name,file_name):
    new_file_table_rows.append(f"| `{dir_name}` | `{file_name}` | ✨ Added  |")

def get_tables_header():
    return f"""
        <html>
        <body style="padding: 20px; background-color: #fafafa;">
            <h2 style="color: #2c3e50; text-align: center; border-bottom: 2px solid #2c3e50; padding-bottom: 10px;">
                Android Docs Monitor Report
            </h2>
        """

def draw_html_table(table_title, title_of_column1, title_of_column2, title_of_column3, title_of_column4, rows):
    try:
        if not rows:
            return ""
        
        table_header = ""
        if(not title_of_column4):
            table_header = f"""
            <h3 style="font-family: Arial, sans-serif; color: #333; margin-top: 20px;">{table_title}</h3>
            <table style="border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; margin-bottom: 20px; table-layout: fixed; border: 1px solid #ddd;">
                <thead>
                    <tr style="background-color: #f2f2f2;">
                        <th style="padding: 12px; text-align: left; border: 1px solid #ddd; width: 45%; font-size: 14px;">{title_of_column1}</th>
                        <th style="padding: 12px; text-align: left; border: 1px solid #ddd; width: 45%; font-size: 14px;">{title_of_column2}</th>
                        <th style="padding: 12px; text-align: left; border: 1px solid #ddd; width: 45%; font-size: 14px;">{title_of_column3}</th>
                    </tr>
                </thead>
                <tbody>
            """
        
        if(title_of_column4):
            table_header = f"""
            <h3 style="font-family: Arial, sans-serif; color: #333; margin-top: 20px;">{table_title}</h3>
            <table style="border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; margin-bottom: 20px; table-layout: fixed; border: 1px solid #ddd;">
                <thead>
                    <tr style="background-color: #f2f2f2;">
                        <th style="padding: 12px; text-align: left; border: 1px solid #ddd; width: 45%; font-size: 14px;">{title_of_column1}</th>
                        <th style="padding: 12px; text-align: left; border: 1px solid #ddd; width: 45%; font-size: 14px;">{title_of_column2}</th>
                        <th style="padding: 12px; text-align: left; border: 1px solid #ddd; width: 45%; font-size: 14px;">{title_of_column3}</th>
                        <th style="padding: 12px; text-align: left; border: 1px solid #ddd; width: 45%; font-size: 14px;">{title_of_column4}</th>
                    </tr>
                </thead>
                <tbody>
            """

        table_body = ""
        for row in rows:
            parts = [p.strip() for p in row.split('|') if p.strip()]
            
            if len(parts) == 3:
                col1_raw = parts[0].replace('`', '')
                col2_raw = parts[1]
                col3_raw = parts[2]
            
                col1 = html.escape(col1_raw)
                col2 = html.escape(col2_raw)
                col3 = html.escape(col3_raw)

                status_color = "#28a745" if any(word in col3 for word in ["New", "Added"]) else "#333"
                if "No Changes" in col3: status_color = "#6c757d"
                if "Modified" in col3: status_color = "#e67e22"
                
                table_body += f"""
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd; font-family: 'Courier New', monospace; font-size: 13px; word-wrap: break-word; white-space: pre-wrap; vertical-align: top;">{col1}</td>
                    <td style="padding: 10px; border: 1px solid #ddd; font-family: 'Courier New', monospace; font-size: 13px; word-wrap: break-word; white-space: pre-wrap; vertical-align: top;">{col2}</td>
                    <td style="padding: 10px; border: 1px solid #ddd; font-family: 'Courier New', monospace; font-size: 13px; word-wrap: break-word; white-space: pre-wrap; vertical-align: top; color: {status_color};">{col3}</td>
                </tr>
                """

            if len(parts) == 4:
                col1_raw = parts[0].replace('`', '')
                col2_raw = parts[1]
                col3_raw = parts[2]
                col4_raw = parts[3]
                col1 = html.escape(col1_raw)
                col2 = html.escape(col2_raw)
                col3 = html.escape(col3_raw)
                col4 = html.escape(col4_raw)
                table_body += f"""
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd; font-family: 'Courier New', monospace; font-size: 13px; word-wrap: break-word; white-space: pre-wrap; vertical-align: top;">{col1}</td>
                    <td style="padding: 10px; border: 1px solid #ddd; font-family: 'Courier New', monospace; font-size: 13px; word-wrap: break-word; white-space: pre-wrap; vertical-align: top;">{col2}</td>
                    <td style="padding: 10px; border: 1px solid #ddd; font-family: 'Courier New', monospace; font-size: 13px; word-wrap: break-word; white-space: pre-wrap; vertical-align: top;">{col3}</td>
                    <td style="padding: 10px; border: 1px solid #ddd; font-family: 'Courier New', monospace; font-size: 13px; word-wrap: break-word; white-space: pre-wrap; vertical-align: top;">{col4}</td>
                </tr>
                """
        if not table_body:
            return ""
            
        return table_header + table_body + "</tbody></table>"
    except Exception as e:
        error_msg = "Exp from draw_html_table() , message : "+str(e)
        raise Exception(error_msg) from e

def get_tables_footer():
    return"""
            <p style="font-size: 12px; color: #888; text-align: center; margin-top: 30px;">
                This is an automated report.
            </p>
        </body>
        </html>
        """
#==============================================================

#================ Main Function ==================
if __name__ == "__main__":
    try:
        new_file_table_rows = []
        not_change_table_rows=[]
        change_table_rows = []
        content_of_change_table_rows = []


        for domain_url in Base_URLS: 
            dir_name = generate_dir_name_from_url(domain_url)
            create_directory(dir_name)
            all_links = get_sub_links_from_url(domain_url)
            # Go through all the links
            for i, url in enumerate(all_links, 1):
                file_name = get_file_name_from_url(domain_url,url)
                
                # Get current data
                response = get_http_response(url)
                web_page_content  = get_content_from_web_page(response)
                mark_down = convert_web_page_to_md(web_page_content)
                current_content = mark_down

                if(not is_file_name_exist(dir_name,file_name)):
                    file_path = os.path.join(dir_name, file_name)
                    store_page_content_into_file(file_path,current_content)
                    add_new_row_in_new_file_table(new_file_table_rows,dir_name,file_name)
                    continue

                old_content = get_content_of_exist_file(dir_name,file_name)

                if not is_old_content_is_match_current_content(old_content,current_content):
                    add_new_row_in_change_table(change_table_rows,content_of_change_table_rows,dir_name,file_name, old_content, current_content)
                    file_path = os.path.join(dir_name, file_name)
                    store_page_content_into_file(file_path,current_content)
                    continue

                if is_old_content_is_match_current_content(old_content,current_content):
                    add_new_row_in_not_change_table(not_change_table_rows,dir_name,file_name)
                

                # A slight delay (policy delay) to prevent Google from blocking your IP address.
                time.sleep(SLEEP_TIME_IN_SEC)


        final_report_html = get_tables_header()

        final_report_html += draw_html_table("✨ NEW FILES TABLE","Directory Name","File Name","Status","", new_file_table_rows)
        final_report_html += draw_html_table("📝 CHANGES TABLE","Directory Name","File Name","Status","", change_table_rows)
        final_report_html += draw_html_table("📝 CHANGES TABLE Content","Directory Name","File Name","Old Content","New Content", content_of_change_table_rows)
        final_report_html += draw_html_table("✅ NOT CHANGES TABLE","Directory Name","File Name","Status","", not_change_table_rows)

        final_report_html += get_tables_footer()

        # Step 5: Send Email (Regardless of outcome as requested)
        email_status = send_email_report(final_report_html)
        logEmailStatus(email_status)

    except Exception as e:
        error_msg = str(e)
        print(error_msg)

        # Send error as a report too
        email_status = send_email_report(error_msg)
        logEmailStatus(email_status)
#==============================================================

