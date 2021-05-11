import threading
import Manager


def main():
    x = threading.Thread(target=Manager.start_listen_to_analayzer)
    x.start()
    start_new_round = True
    # counter = 0
    while True:
        # if flag == 0:
        #     start_new_round = True
        #     import time
        #     time.sleep(5)
        #     continue
        if start_new_round:
            import time
            time.sleep(5)
            start_new_round = False
        # print("iter")
        # if counter >= 5:
        #     import time
        #     time.sleep(5)
        #     continue
        # counter += 1
        # try:
        Manager.try_manager_iterate()
        # except:
        #     pass
        import time
        time.sleep(1)


if __name__ == '__main__':
    # Manager.try_connect_to_db()
    main()
