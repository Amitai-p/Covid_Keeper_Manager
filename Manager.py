import threading
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
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
global config


def get_url_by_name(config, name_comp):
    url = 'http://' + config[name_comp + '_ip'] + ':' + config[name_comp + '_port'] + '/'
    return url


def update_config_ip_port(config):
    dict = b.get_ip_port_config(NAME_COMPONENT)
    for conf in dict:
        config[conf] = dict[conf]
    config["URL_CAMERAS"] = get_url_by_name(config, 'Camera')
    config["URL_ANALAYZER"] = get_url_by_name(config, 'Analayzer')
    return config


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


config = init_config()
print(config)


def update_config():
    print(config)
    dict = b.get_manager_config_dict()
    print(dict)
    for conf in dict:
        config[conf] = dict[conf]
    print(config)


def check_config():
    print("flag config: ", b.get_manager_config_flag())
    if b.get_manager_config_flag() == '1':
        update_config()
        # update_flag_read_config()
        print("flag config: ", b.get_manager_config_flag())


def convert_bytes_to_image(data):
    data = bytes(data.decode('utf8')[:-1], 'utf-8')
    image_64_decode = base64.decodebytes(data)
    image_result = open('testfile.jpg', 'wb')
    image_result.write(image_64_decode)
    image_result.close()
    image = cv2.imread('testfile.jpg')
    return image


def get_list_images_for_sending():
    headers = {'authentication': config['PASSWORD_EMAIL']}
    response = requests.get(config["URL_CAMERAS"], headers=headers)
    print(response)
    result = response.content
    return result


def post_images_to_analayzer(images):
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


def compare_times(time_last):
    time_now = datetime.now()
    diff_time = time_now - time_last
    diff_seconds = diff_time.total_seconds()
    return diff_seconds


def check_if_got_mail(id_worker):
    time_last = b.get_max_time_of_event_by_id_worker(id_worker)
    if not time_last:
        return True
    diff_seconds = compare_times(time_last)
    print("diff seconds: ", diff_seconds)
    MINUTES_TO_SECONDES = 0.25
    if (diff_seconds > config["Minutes_between_mails"] * MINUTES_TO_SECONDES):
        return True
    return False


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
           <p style="text-align:left;"> Amitai  </p>
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


def get_dict_images(response):
    result = response
    data = json.loads(result)
    dict_images = {}
    for key in data:
        decoded_image_data = base64.decodebytes(bytes(data[key], encoding='utf8'))
        dict_images[key] = convert_bytes_to_image(decoded_image_data)
    return dict_images


def send_images_and_workers(dict_id_workers_without_mask):
    # connection get mails.
    for id in dict_id_workers_without_mask:
        if not check_if_got_mail(id):
            print("got mail just now")
            continue
        name, email = b.get_fullname_and_email_by_id(id)
        path_to_image = save_image(dict_id_workers_without_mask[id])
        send_mail(email, path_to_image, name)
        # update got mail.
        b.insert_event(id)
        delete_image(path_to_image)
    global dict_workers_without_mask
    dict_workers_without_mask = {}


def data_to_send(list_images):
    data = {}
    for i in range(len(list_images)):
        key = 'img' + str(i)
        data[key] = base64.encodebytes(list_images[i]).decode('utf-8')
    result = json.dumps(data)
    return result


from flask import (
    Flask,

    json)

# Create the application instance
app = Flask(__name__, template_folder="templates")


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
    #############
    send_images_and_workers(dict_workers_without_mask)
    return "OK"


def start_listen_to_analayzer():
    from waitress import serve
    serve(app, host=config[NAME_COMPONENT + '_ip'], port=int(config[NAME_COMPONENT + '_port']))


def check_config_ip_port():
    if b.get_flag_ip_port_by_table_name(NAME_COMPONENT) == '1':
        update_config_ip_port(config)
        print("after update:")
        print(config)


def try_manager_iterate():
    # get list of images.
    try:
        images = get_list_images_for_sending()
    except:
        print("The cameras have to start")
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


def manager():
    while True:
        print("run")
        # get list of images.
        images = get_list_images_for_sending()
        # In case of that there is no images. wait for the next time.
        while images == b'{}':
            import time
            time.sleep(1)
            images = get_list_images_for_sending()
        global dict_workers_without_mask
        global new_dictionary
        dict_workers_without_mask = None
        # Sending the images to the analayzer.
        post_images_to_analayzer(images)
        import time
        # Check the time of sending.
        time_before_send_to_analayzer = time.time()
        while not new_dictionary:
            import time
            time.sleep(0.5)
            # In case of problem with the analayzer.
            if (time.time() - time_before_send_to_analayzer > TIME_TO_WAIT_TO_ANALAYZER):
                break
        print("get data from post")
        if new_dictionary:
            print("length of dict: ", len(dict_workers_without_mask))
            if len(dict_workers_without_mask) > 0:
                print("sending")
                send_images_and_workers(dict_workers_without_mask)
        new_dictionary = False


#
# def starter_manager():
#     x = threading.Thread(target=listen_to_analayzer)
#     x.start()
#     manager()


# def main():
#     while True:
#         try:
#             starter_manager()
#         except:
#             print("Problem with starter")
#             import time
#             time.sleep(1)


from flask import Flask, jsonify, request
import json, os, signal


# #
# @app.route('/stop_server', methods=['GET'])
# def stop_server():
#     print("stopppp")
#     os.kill(os.getpid(), signal.SIGINT)
#     print("get pid")
#     return jsonify({"success": True, "message": "Server is shutting down..."})
#
#
# def stop_service():
#     response = requests.get('http://127.0.0.1:5000/stop_server')
#     print(response)
#     import time
#     time.sleep(10)


def try_connect_to_db():
    # b = Database()
    print("try connect")
    b.open_connection()
    print("open_connection")
    b.open_cursor()
    print("open cursur")
    # print(b.get_workers_to_images_dict())
    result = b.start_or_close_threads()
    print(result)
    a = 1


def run_manager_with_flag():
    print(b)

# If we're running in stand alone mode, run the application
# if __name__ == '__main__':
#     try_connect_to_db()
# main()
