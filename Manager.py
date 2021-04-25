import json
import os
import threading
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import smtplib

run = True
from azure_sql_server_actual import *
from datetime import *

new_dictionary = False
global_flag_kill_thread = False
b = Database()
config = {}
config["TIME_BETWEEN_SENDS"] = 30
dict_workers_without_mask = {}


def convert_bytes_to_image(data):
    data = bytes(data.decode('utf8')[:-1], 'utf-8')
    # nparr = np.fromstring(img_str, np.uint8)
    image_64_decode = base64.decodebytes(data)
    image_result = open('testfile.jpg', 'wb')
    image_result.write(image_64_decode)
    image_result.close()
    image = cv2.imread('testfile.jpg')
    # cv2.imshow("Faces found", image)
    # cv2.waitKey(0)
    return image


# def get_images():
#     import requests
#     print("try to get images")
#     response = requests.get('http://127.0.0.1:5000/')
#     result = response.content
#     data = json.loads(result)
#     list_images = []
#     for key in data:
#         decoded_image_data = base64.decodebytes(bytes(data[key], encoding='utf8'))
#         list_images.append(convert_bytes_to_image(decoded_image_data))
#     return list_images


def get_list_images_for_sending():
    response = requests.get('http://127.0.0.1:5000/')
    result = response.content
    return result


def post_images_to_analayzer(images):
    # images = json.dumps(images)
    url = 'http://127.0.0.1:5002/'
    x = requests.post(url, data={'images': images})
    print("result of post to analayzer:   ", x)
    if (x.status_code != 200):
        return


# counter = 0
# size_n = 5
#
# # Get image, save local, return path.
# def save_image(img):
#     global counter
#     if not os.path.exists('Images'):
#         os.makedirs('Images')
#     path_to_save = "Images/img%s.jpg" % str(counter)
#     counter = (counter + 1) % size_n
#     cv2.imwrite(path_to_save, img)
#     return path_to_save
#
# def convert_image_to_varbinary(filename):
#     image = open(filename, 'rb')
#     image_read = image.read()
#     image_64_encode = base64.encodebytes(image_read)
#     image.close()
#     return image_64_encode
#
#
# def list_to_varbinary_list(list_images):
#     list_binary = []
#     for img in list_images:
#         list_binary.append(convert_image_to_varbinary())
#


# Get image, save local, return path.
def save_image(img):
    # print("img:   ",img)

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
    if (diff_seconds > config["TIME_BETWEEN_SENDS"]):
        return True
    return False


def sendMail(mailAddress, pathToImage, name):
    server = smtplib.SMTP('smtp.gmail.com', 587)
    # start TLS for security
    server.starttls()
    # Authentication
    # s.login("keepyourhealthmask", "Mask1234")
    hi = ",Hi %s" % name
    text = ".Please keep your health and put your mask"
    sender_email = "keepyourhealthmask@gmail.com"
    receiver_email = mailAddress
    message = MIMEMultipart("alternative")
    message["Subject"] = "Keep your health"
    message["From"] = sender_email
    message["To"] = receiver_email
    # We assume that the image file is in the same directory that you run your Python script from
    encoded = base64.b64encode(open(pathToImage, "rb").read()).decode()
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
    image = MIMEImage(open(pathToImage, "rb").read(), name=os.path.basename("picture"))
    part = MIMEText(html, "html")
    message.attach(part)
    message.attach(image)
    # with smtplib.SMTP("smtp.mailtrap.io", 587) as server:
    server.login("keepyourhealthmask", "Mask1234!")
    server.sendmail(
        sender_email, receiver_email, message.as_string()
    )
    print("sent")


def get_dict_images(response):
    import requests
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
        sendMail(email, path_to_image, name)
        # update got mail.
        b.insert_event(id)
        delete_image(path_to_image)
    global dict_workers_without_mask
    dict_workers_without_mask = {}


def data_to_send(list_images):
    data = {}
    for i in range(len(list_images)):
        key = 'img' + str(i)
        # data[key] = base64.encodebytes(list_images[i]).decode('utf-8')
        data[key] = base64.encodebytes(list_images[i]).decode('utf-8')
        # data[key] = list_images[i]
    result = json.dumps(data)
    return result


from flask import (
    Flask,
    render_template,
    jsonify, Response, request, json)

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
    # send_images_and_workers(dict_images)
    global dict_workers_without_mask
    dict_workers_without_mask = dict_images
    global new_dictionary
    new_dictionary = True
    return "OK"


def start_server():
    app.run(port=5004, debug=True)


def starter_manager():
    x = threading.Thread(target=run_manager)
    x.start()
    from waitress import serve
    serve(app, host="127.0.0.1", port=5004)
    # app.run(port=5004, debug=True)


def run_manager():
    import time
    print("run")
    images = get_list_images_for_sending()
    # In case that there is no images.
    while images == b'{}':
        time.sleep(1)
        images = get_list_images_for_sending()
    post_images_to_analayzer(images)


# starter_manager()


def listen_to_analayzer():
    print("listen")
    from waitress import serve
    serve(app, host="127.0.0.1", port=5004)


TIME_TO_WAIT_TO_ANALAYZER = 10


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
                send_images_and_workers(dict_workers_without_mask)
        new_dictionary = False


def starter_manager():
    x = threading.Thread(target=listen_to_analayzer)
    x.start()
    manager()


def main():
    while True:
        try:
            starter_manager()
        except:
            print("Problem with starter")
            import time
            time.sleep(1)


# If we're running in stand alone mode, run the application
if __name__ == '__main__':
    main()

