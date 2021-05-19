import threading
import Manager


def main():
    x = threading.Thread(target=Manager.start_listen_to_analayzer)
    x.start()
    start_new_round = True
    Manager.b.set_manager_config_flag_to_1()
    while True:
        Manager.check_config_ip_port()
        flag = Manager.b.start_or_close_threads()
        Manager.check_config()
        if int(flag) == 0:
            start_new_round = True
            import time
            time.sleep(Manager.config["TIME_TO_SLEEP"])
            continue
        # In case of new round, wait that the cameras will take new pictures.
        if start_new_round:
            import time
            time.sleep(Manager.config["TIME_TO_SLEEP"])
            start_new_round = False
        Manager.try_manager_iterate()
        import time
        time.sleep(1)


if __name__ == '__main__':
    # print(Manager.config)
    # Manager.try_connect_to_db()
    main()
