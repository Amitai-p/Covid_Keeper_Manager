import threading
import Manager


# The runner of the finction try manager iterate.
def main():
    # Open thread to listen to the analayzer.
    x = threading.Thread(target=Manager.start_listen_to_analayzer)
    x.start()
    start_new_round = True
    # Set the flag to 1 for the first time to be updated.
    Manager.b.set_manager_config_flag_to_1()
    while True:
        Manager.check_config_ip_port()
        # Check if the user would like to start or end the program.
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
        try:
            Manager.try_manager_iterate()
        except:
            print('Manager continued')
        import time
        time.sleep(1)


if __name__ == '__main__':
    main()
