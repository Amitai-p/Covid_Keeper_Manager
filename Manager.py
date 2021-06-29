import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import *
import smtplib

run = True
from azure_sql_server import *

new_dictionary = False
global_flag_kill_thread = False
NAME_COMPONENT = 'Manager'
PORT_COMPONENT = '5004'
b = Database()
b.set_ip_by_table_name(NAME_COMPONENT)
b.set_port_by_table_name(NAME_COMPONENT, PORT_COMPONENT)

dict_workers_without_mask = {}
TIME_TO_WAIT_TO_ANALAYZER = 10
IP_LOCAL_HOST = '127.0.0.1'
STRING_OF_NAME_PORT_DB = '_port'
NAME_OF_IMAGE = 'img'
global config


# Return the url for this component.
def get_url_by_name(config, name_comp):
    url = 'http://' + config[name_comp + '_ip'] + ':' + config[name_comp + '_port'] + '/'
    return url


# Get the config and update the the url's of the component from the DB.
def update_config_ip_port(config):
    dict = b.get_ip_port_config(NAME_COMPONENT)
    for conf in dict:
        config[conf] = dict[conf]
    config["URL_CAMERAS"] = get_url_by_name(config, 'Camera')
    config["URL_ANALAYZER"] = get_url_by_name(config, 'Analayzer')
    return config


# Init the configuration for the program.
def init_config():
    config = {}
    config = update_config_ip_port(config)
    config["Minutes_between_mails"] = 30
    config["URL_CAMERAS"] = get_url_by_name(config, 'Camera')
    config["URL_ANALAYZER"] = get_url_by_name(config, 'Analayzer')
    config["USER_NAME_EMAIL"] = 'keepyourhealthmask'
    config["PASSWORD_EMAIL"] = 'Amitai5925'
    config["TIME_TO_SLEEP"] = 5
    return config


# Get the defult configuration from file.
def init_config_from_file():
    PATH_TO_CONFIG = 'config_json.txt'
    config = read_json(PATH_TO_CONFIG)
    config = update_config_ip_port(config)
    return config


# Insert the config into json file.
def inset_dict_json(path_to_file, config):
    config_json = json.dumps(config)
    with open(path_to_file, 'w') as json_file:
        json.dump(config_json, json_file)


import json


# Read the json file of the config.
def read_json(path_to_file):
    with open(path_to_file) as f:
        # From file to string.
        data = json.load(f)
        # From string to dictionary.
        data = json.loads(data)
    return data


config = init_config_from_file()


# Update the config after changes from another components.
def update_config():
    dict = b.get_manager_config_dict()
    for conf in dict:
        config[conf] = dict[conf]
    print(config)


# Check if we need to update the config.
def check_config():
    print("flag config: ", b.get_manager_config_flag())
    if b.get_manager_config_flag() == '1':
        update_config()


NAME_OF_FILE_FOR_CONVERT = 'testfile.jpg'


# Convert the images to bytes for sending.
def convert_bytes_to_image(data):
    data = bytes(data.decode('utf8')[:-1], 'utf-8')
    image_64_decode = base64.decodebytes(data)
    image_result = open(NAME_OF_FILE_FOR_CONVERT, 'wb')
    image_result.write(image_64_decode)
    image_result.close()
    image = cv2.imread(NAME_OF_FILE_FOR_CONVERT)
    return image


# Ask from the cameras to send the images.
def get_list_images_for_sending():
    headers = {'authentication': config['PASSWORD_EMAIL']}
    response = requests.get(config["URL_CAMERAS"], headers=headers)
    print(response)
    result = response.content
    return result


PATH_TO_SECRET_KEY = "secret.key"


# Load the secret key to decode the images.
def load_key():
    """
    Loads the key named `secret.key` from the current directory.
    """
    return open(PATH_TO_SECRET_KEY, "rb").read()


# Decode the images with the secret key.
def decrypt_images(images):
    from cryptography.fernet import Fernet
    key = load_key()
    f = Fernet(key)
    return f.decrypt(images)


# Get the images and send them to the analayzer.
def post_images_to_analayzer(images):
    images = decrypt_images(images)
    print(config["URL_ANALAYZER"])
    x = requests.post(config["URL_ANALAYZER"], data={'images': images})
    print("result of post to analayzer:   ", x)
    if (x.status_code != 200):
        return


# Get image, save local, return path.
def save_image(img):
    if not os.path.exists('saved_pictures'):
        os.makedirs('saved_pictures')
    import time
    path_to_save = "saved_pictures/face%s.jpg" % str(time.time())
    cv2.imwrite(path_to_save, img)
    return path_to_save


# Get path to image and delete.
def delete_image(path_to_image):
    try:
        os.remove(path_to_image)
    except:
        print("The image doesn't exist")


from datetime import *


# Check the difference between the time_last to time now.
def compare_times(time_last):
    time_now = datetime.now()
    diff_time = time_now - time_last
    diff_seconds = diff_time.total_seconds()
    return diff_seconds


# Check the last time that this worker got mail from Covid Keeper and decide if he have to get more mail now.
def check_if_got_mail(id_worker):
    time_last = b.get_max_time_of_event_by_id_worker(id_worker)
    if not time_last:
        return True
    diff_seconds = compare_times(time_last)
    print("diff seconds: ", diff_seconds)
    MINUTES_TO_SECONDES = 60
    if (diff_seconds > config["Minutes_between_mails"] * MINUTES_TO_SECONDES):
        return True
    return False


# Get address of mail, path to iamge and name of worker and send him mail that he have to put a mask.
def send_mail(mail_address, path_to_image, name):
    server = smtplib.SMTP('smtp.gmail.com', 587)
    # start TLS for security
    server.starttls()
    hi = ",Hi %s" % name
    text = ".Please keep your health and put your mask"
    sender_email = "keepyourhealthmask@gmail.com"
    receiver_email = mail_address
    message = MIMEMultipart("alternative")
    message["Subject"] = "Keep your health"
    message["From"] = sender_email
    message["To"] = receiver_email
    # We assume that the image file is in the same directory that you run your Python script from
    encoded = base64.b64encode(open(path_to_image, "rb").read()).decode()
    html = f"""\
       <html>
        <body>
           <p style="text-align:left;"> {hi} </p>
           <br />
           <p style="text-align:left;"> {text} </p>
           <br />
           <p style="text-align:left;"> ,Thanks  </p>
           <p style="text-align:left;"> Covid keeper team  </p>
        </body>
       </html>
       """
    image = MIMEImage(open(path_to_image, "rb").read(), name=os.path.basename("picture"))
    part = MIMEText(html, "html")
    message.attach(part)
    message.attach(image)
    server.login(config["USER_NAME_EMAIL"], config["PASSWORD_EMAIL"])
    server.sendmail(
        sender_email, receiver_email, message.as_string()
    )
    print("sent")


# Convert the data from the post to dictionary.
def get_dict_images(response):
    result = response
    data = json.loads(result)
    dict_images = {}
    for key in data:
        decoded_image_data = base64.decodebytes(bytes(data[key], encoding='utf8'))
        dict_images[key] = convert_bytes_to_image(decoded_image_data)
    return dict_images


# Get dictionary of id's workers without mask and images of this events, and send them mails and save this events in
# the database.
def send_images_and_workers(dict_id_workers_without_mask):
    # connection get mails.
    for id in dict_id_workers_without_mask:
        if not check_if_got_mail(id):
            print("got mail just now")
            continue
        name, email = b.get_fullname_and_email_by_id(id)
        path_to_image = save_image(dict_id_workers_without_mask[id])
        try:
            send_mail(email, path_to_image, name)
        except:
            print('Can\'t send mail')
        # update that get mail.
        b.insert_event(id)
        delete_image(path_to_image)
    global dict_workers_without_mask
    dict_workers_without_mask = {}


# Prepare the data for sending to the analayzer with encode.
def data_to_send(list_images):
    data = {}
    for i in range(len(list_images)):
        key = NAME_OF_IMAGE + str(i)
        data[key] = base64.encodebytes(list_images[i]).decode('utf-8')
    result = json.dumps(data)
    return result


from flask import (
    Flask,
    json)

# Create the application instance
app = Flask(__name__, template_folder="templates")


# Wait for post from the analayzer and get the dictionary workers without mask.
@app.route('/', methods=['POST'])
def result():
    print("in result")
    global run
    run = False
    data = request.values
    for key in data:
        dict = data[key]
    print("get resquest, len dictionary: ", len(dict))
    dict_images = get_dict_images(dict)
    global dict_workers_without_mask
    dict_workers_without_mask = dict_images
    global new_dictionary
    new_dictionary = True
    return "OK"


# Open the listening to the analayzer.
def start_listen_to_analayzer():
    from waitress import serve
    serve(app, host=IP_LOCAL_HOST, port=int(config[NAME_COMPONENT + STRING_OF_NAME_PORT_DB]))


# Check if there is change at the config of the ips and ports.
def check_config_ip_port():
    if b.get_flag_ip_port_by_table_name(NAME_COMPONENT) == '1':
        update_config_ip_port(config)


from flask import request
import json, os


# Make one iterate for manage the flow of the program.
def try_manager_iterate():
    # get list of images.
    try:
        b.set_camera_config_flag_from_manager()
        flag = int(b.get_camera_config_flag())
        while flag == 1:
            import time
            time.sleep(1)
            flag = int(b.get_camera_config_flag())
        images = b.get_images_txt_from_storage()
        print('length images: ', len(images))
    except:
        print("The cameras have to start")
        return
    global dict_workers_without_mask
    global new_dictionary
    dict_workers_without_mask = None
    try:
        post_images_to_analayzer(images)
    except:
        print("The analayzer have to start")
    if new_dictionary:
        print("length of dict: ", len(dict_workers_without_mask))
        if len(dict_workers_without_mask) > 0:
            print("sending")
            send_images_and_workers(dict_workers_without_mask)
    new_dictionary = False
