import smtplib
import requests

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from inspect import cleandoc

def get_task_log():
    print('BEGIN: Fetching task log')
    octopus_url = get_octopusvariable('Octopus.Url')
    octopus_api_key = get_octopusvariable('Octopus.ApiKey')
    octopus_task_id = get_octopusvariable('Octopus.Task.Id')
    headers = {'X-Octopus-ApiKey': octopus_api_key}
    request_url = '/'.join([octopus_url, 'api/tasks', octopus_task_id, 'raw'])
    try:
        response = requests.get(request_url, headers=headers, verify=False)
        response = response.text
    except (requests.exceptions.ConnectTimeout, 
            requests.exceptions.RequestException) as e:
        failstep(e)
    print('END: Fetching task log')
    return response

def mailer():
    print('BEGIN: Sending email')
    from_addr = get_octopusvariable('Mail.From')
    to_addr = get_octopusvariable('Mail.To')

    msg = MIMEMultipart()
    msg['From'] = from_addr
    msg['To'] = to_addr
    msg['Subject'] = "Deployment sample mail"
    body = cleandoc(f'''Test''')

    msg.attach(MIMEText(body, 'plain'))

    print('Preparing attachment..')
    filename = "tasklog.txt"
    raw_log = get_task_log()
    payload = MIMEBase('application', 'octet-stream')
    payload.set_payload(raw_log)
    encoders.encode_base64(payload)
    payload.add_header('Content-Disposition', "attachment; filename= %s" % filename)

    msg.attach(payload)

    print('Sending mail..')
    server = smtplib.SMTP('atom.paypalcorp.com', 25)
    text = msg.as_string()
    server.sendmail(from_addr, to_addr, text)
    server.quit()
    printhighlight('Mail sent successfully!!')

if __name__ == "<run_path>":
    mailer()
