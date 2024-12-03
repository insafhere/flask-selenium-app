t=keyword_loop_search)
            thread.daemon = True  # Make the thread a daemon so it exits when the main program exits
            thread.start()